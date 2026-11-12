"""The last hop: starting a worker client and handing it the instruction.

An instruction reaches the client as one argument, exactly as written, or the job is refused
before any child process starts. It is never altered and never parsed by `cmd.exe`.
"""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from overseer import hostos
from overseer.factory import Factory
from overseer.provider import build_task

try:
    from tests.fakeclient import make_client, make_cmd_client
except ImportError:
    from fakeclient import make_client, make_cmd_client

WINDOWS = os.name == 'nt'
# Three texts a model could write that a command interpreter would not leave alone.
LINE_BREAK = 'FIRST: read the brief\n\nSECOND: do the work'
INJECTION = 'finish it" & echo pwned> marker.txt & rem "'
EXPANSION = 'leave %PATH% and %OS% exactly as written'
TEXTS = {'a line break': LINE_BREAK, 'a quote and a command': INJECTION,
         'a variable reference': EXPANSION}
RECORD = 'import json, sys\nopen(%r, "w", encoding="utf-8").write(json.dumps(sys.argv[1:]))\n'


class ClientLaunchTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.workspace = self.base / 'workspace'
        self.workspace.mkdir()
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.received = self.base / 'argv.json'
        self.factory = Factory(self.base / 'state' / 'jobs.sqlite3')
        self.addCleanup(self.factory.close)
        self.count = 0

    def run_job(self, client, instruction):
        """Run one job whose implementation is `client` given `instruction`; return the result."""
        self.count += 1
        if self.received.exists():
            self.received.unlink()
        spec, _ = build_task('job%d' % self.count, 'deliver one instruction', str(self.workspace),
                             checks=[[sys.executable, '-c', 'pass']], instruction=instruction,
                             runner='opencode', env={}, opencode=client, timeout_seconds=60)
        self.assertTrue(self.factory.submit(spec))
        return self.factory.run_one()

    def log(self, result):
        return (Path(result['evidence']) / '00.log').read_text(encoding='utf-8')

    def arrived(self):
        return json.loads(self.received.read_text(encoding='utf-8'))[-1]

    def test_a_native_client_receives_each_text_exactly(self):
        client = make_client(self.bin, 'fakeclient', RECORD % str(self.received))
        for label, text in TEXTS.items():
            with self.subTest(label):
                result = self.run_job(client, text)
                self.assertEqual(result['state'], 'passed', self.log(result))
                self.assertEqual(self.arrived(), text)
        self.assertFalse((self.workspace / 'marker.txt').exists())

    @unittest.skipUnless(WINDOWS, 'a .cmd client exists only on Windows; the rule is tested unpatched there')
    def test_a_cmd_client_is_refused_for_each_text_and_no_child_starts(self):
        client = make_cmd_client(self.bin, 'fakeclient', RECORD % str(self.received))
        for label, text in TEXTS.items():
            with self.subTest(label), \
                    patch.object(hostos, 'popen_group', side_effect=AssertionError('a child was started')):
                result = self.run_job(client, text)
                self.assertEqual(result['state'], 'failed')
                self.assertFalse(self.received.exists(), 'the client ran')
                lines = self.log(result).splitlines()
                self.assertEqual(len(lines), 1, lines)
                self.assertIn('fakeclient.cmd', lines[0])
                self.assertIn('cmd.exe', lines[0])
                self.assertIn('.exe', lines[0])
        self.assertFalse((self.workspace / 'marker.txt').exists())

    @unittest.skipUnless(WINDOWS, 'a .cmd client exists only on Windows; the rule is tested unpatched there')
    def test_a_client_present_only_as_cmd_is_found_by_its_bare_name(self):
        make_cmd_client(self.bin, 'fakeclient-only-cmd', RECORD % str(self.received))
        path = str(self.bin) + os.pathsep + os.environ.get('PATH', '')
        with patch.dict(os.environ, {'PATH': path}):
            result = self.run_job('fakeclient-only-cmd', 'plain words only')
        self.assertEqual(result['state'], 'passed', self.log(result))
        self.assertEqual(self.arrived(), 'plain words only')

    def test_a_native_client_is_found_by_its_bare_name(self):
        make_client(self.bin, 'fakeclient-native', RECORD % str(self.received))
        path = str(self.bin) + os.pathsep + os.environ.get('PATH', '')
        with patch.dict(os.environ, {'PATH': path}):
            result = self.run_job('fakeclient-native', INJECTION)
        self.assertEqual(result['state'], 'passed', self.log(result))
        self.assertEqual(self.arrived(), INJECTION)

    def test_a_client_that_is_not_installed_fails_and_the_log_names_it(self):
        result = self.run_job('no-such-client-zzz', 'plain words only')
        self.assertEqual(result['state'], 'failed')
        log = self.log(result)
        self.assertIn('no-such-client-zzz', log)
        if WINDOWS:
            self.assertEqual(len(log.splitlines()), 1, log)

    def test_a_check_command_is_under_the_same_rule(self):
        if WINDOWS:
            check = make_cmd_client(self.bin, 'fakecheck', 'import sys\nsys.exit(0)\n')
        else:
            check = make_client(self.bin, 'fakecheck', 'import sys\nsys.exit(0)\n')
        client = make_client(self.bin, 'fakeclient', RECORD % str(self.received))
        spec, _ = build_task('checked', 'run a check', str(self.workspace),
                             checks=[[check, INJECTION]], instruction='plain words only',
                             runner='opencode', env={}, opencode=client, timeout_seconds=60)
        self.assertTrue(self.factory.submit(spec))
        result = self.factory.run_one()
        # POSIX delivers the text to the check; Windows refuses the .cmd check without running it.
        self.assertEqual(result['state'], 'failed' if WINDOWS else 'passed')
        self.assertFalse((self.workspace / 'marker.txt').exists())


class PrepareTest(unittest.TestCase):
    """The rule itself, with the Windows branch forced so it is also exercised on POSIX."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bin = Path(temporary.name)
        for name in ('shim.cmd', 'batch.bat', 'native.exe', 'both.exe', 'both.cmd'):
            (self.bin / name).write_bytes(b'')
        self.env = {'PATH': str(self.bin), 'PATHEXT': '.COM;.EXE;.BAT;.CMD'}

    def prepare(self, argv):
        with patch.object(hostos, 'WINDOWS', True):
            return hostos.prepare(argv, self.env, str(self.bin))

    def test_posix_leaves_the_command_alone(self):
        if WINDOWS:
            self.skipTest('this host is Windows; the POSIX branch runs on the Linux job')
        argv = ['no-such-client-zzz', INJECTION]
        self.assertEqual(hostos.prepare(argv, self.env, str(self.bin)), (argv, None))

    def test_a_bare_name_is_found_through_pathext(self):
        argv, refusal = self.prepare(['shim', 'run', '--model', 'a/b-free', 'plain words only'])
        self.assertIsNone(refusal)
        self.assertEqual(Path(argv[0]), self.bin / 'shim.cmd')
        self.assertEqual(argv[1:], ['run', '--model', 'a/b-free', 'plain words only'])

    def test_an_exe_is_preferred_to_a_cmd_of_the_same_name(self):
        argv, refusal = self.prepare(['both', INJECTION])
        self.assertIsNone(refusal)
        self.assertEqual(Path(argv[0]), self.bin / 'both.exe')

    def test_a_native_program_takes_any_text(self):
        for text in TEXTS.values():
            argv, refusal = self.prepare(['native', text])
            self.assertIsNone(refusal)
            self.assertEqual(argv[1], text)

    def test_a_cmd_or_bat_file_is_refused_for_each_text(self):
        for name in ('shim', 'batch', str(self.bin / 'shim.cmd')):
            for label, text in TEXTS.items():
                with self.subTest(name=name, text=label):
                    _, refusal = self.prepare([name, 'run', text])
                    self.assertIsNotNone(refusal)
                    self.assertNotIn('\n', refusal)
                    self.assertIn('cmd.exe', refusal)
                    self.assertIn('argument 2', refusal)
                    self.assertNotIn(text, refusal)

    def test_other_characters_cmd_reads_are_refused_too(self):
        for text in ('a & b', 'a | b', 'a > b', 'a < b', 'a ^ b', 'a ! b', '(a)', 'a\rb', 'a\tb', 'caf\xe9'):
            with self.subTest(text=text):
                self.assertIsNotNone(self.prepare(['shim', text])[1])

    def test_a_missing_program_is_one_line_that_names_it(self):
        argv, refusal = self.prepare(['no-such-client-zzz', 'plain words only'])
        self.assertIn('no-such-client-zzz', refusal)
        self.assertNotIn('\n', refusal)

    def test_a_path_with_a_directory_is_not_searched_on_path(self):
        _, refusal = self.prepare([os.path.join('elsewhere', 'shim'), 'x'])
        self.assertIsNotNone(refusal)


if __name__ == '__main__':
    unittest.main()
