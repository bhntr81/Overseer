"""One request in, a working program out: overseer.build, end to end with a fake agent."""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from tests.fakeclient import make_client
except ImportError:
    from fakeclient import make_client

from overseer import build, orchestrate
from overseer.provider import _claude_argv, build_task

# A fake Claude Code: writes a one-file program and an overseer_check.py that
# really runs it, then reports the objective done in the status-block format.
FAKE_AGENT = r'''
import json, sys
from pathlib import Path
Path("SEEN_PROMPT.txt").write_text(sys.argv[-1], encoding="utf-8")
Path("hello.py").write_text("print('hello from the factory')\n", encoding="utf-8")
Path("overseer_check.py").write_text(
    "import subprocess, sys\n"
    "out = subprocess.run([sys.executable, 'hello.py'], capture_output=True, text=True).stdout\n"
    "sys.exit(0 if 'hello from the factory' in out else 1)\n", encoding="utf-8")
print("Built hello.py and its check.")
print("STATUS: SUCCESS")
print("TESTS_PASSED: TRUE")
print("FILES_MODIFIED: [hello.py, overseer_check.py]")
print("NEXT_AGENT_INSTRUCTION: " + json.dumps(""))
print("OVERSEER_DONE")
'''


class PrepareTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        self.env = {'LOCALAPPDATA': str(self.base / 'appdata')}

    def which(self, name):
        return {'claude': '/bin/claude', 'py': None, 'python3': sys.executable,
                'python': sys.executable}.get(name)

    def test_a_new_program_gets_its_folder_spec_check_and_preamble(self):
        folder = self.base / 'calc'
        job = build.prepare('new', 'a calculator that adds two numbers', str(folder),
                            env=self.env, which=self.which, now=lambda: 1000)
        self.assertTrue((folder / '.git').is_dir())
        self.assertIn('a calculator that adds two numbers', (folder / 'SPEC.md').read_text(encoding='utf-8'))
        spec = job['loop_spec']
        self.assertEqual(spec['checks'], [[sys.executable, 'overseer_check.py']])
        self.assertEqual(spec['permission_mode'], 'bypassPermissions')
        self.assertEqual(spec['runner'], 'claude')
        self.assertTrue(spec['size'])
        self.assertIn('NEXT_AGENT_INSTRUCTION', spec['preamble'])
        self.assertIn('overseer_check.py', spec['preamble'])
        self.assertIn('SPEC.md', spec['preamble'])
        self.assertTrue(Path(job['ledger']).is_relative_to(self.base / 'appdata'))
        self.assertFalse(Path(job['ledger']).is_relative_to(folder))

    def test_without_commands_the_agent_may_only_edit(self):
        job = build.prepare('new', 'x', str(self.base / 'p'), allow_commands=False,
                            env=self.env, which=self.which)
        self.assertEqual(job['loop_spec']['permission_mode'], 'acceptEdits')

    def test_continue_uses_the_folder_as_it_is_and_reads_its_notes(self):
        folder = self.base / 'existing'
        folder.mkdir()
        (folder / 'main.py').write_text('print(1)\n', encoding='utf-8')
        job = build.prepare('continue', '', str(folder), env=self.env, which=self.which)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['main.py'])
        self.assertIn('unfinished', job['loop_spec']['objective'])
        self.assertIn('SESSION_HANDOFF.md', job['loop_spec']['preamble'])

    def test_refusals_say_what_is_wrong(self):
        full = self.base / 'full'
        full.mkdir()
        (full / 'x').write_text('x', encoding='utf-8')
        cases = [
            (('new', 'x', str(full)), {}, 'non-empty'),
            (('new', '', str(self.base / 'n')), {}, 'describe'),
            (('continue', '', str(self.base / 'missing')), {}, 'does not exist'),
            (('new', 'x', str(self.base / 'm')), {'which': lambda n: None}, 'not installed'),
            (('new', 'x', ''), {}, 'folder'),
        ]
        for args, extra, words in cases:
            with self.subTest(words=words):
                options = {'env': self.env, 'which': self.which}
                options.update(extra)
                with self.assertRaises(build.BuildError) as caught:
                    build.prepare(*args, **options)
                self.assertIn(words, str(caught.exception))

    def test_python_is_found_without_the_store_alias(self):
        store = r'C:\Users\u\AppData\Local\Microsoft\WindowsApps\python.exe'
        self.assertEqual(build.find_python(lambda n: {'py': 'C:/py.exe'}.get(n)), ['C:/py.exe', '-3'])
        self.assertIsNone(build.find_python(lambda n: store if n == 'python' else None))

    def test_the_ledger_is_stable_for_a_folder(self):
        one = build.ledger_for(self.base / 'a', self.env)
        self.assertEqual(one, build.ledger_for(self.base / 'a', self.env))
        self.assertNotEqual(one, build.ledger_for(self.base / 'b', self.env))


class PromptTests(unittest.TestCase):
    def test_every_job_gets_note_brief_preamble_then_instruction(self):
        prompt = orchestrate._compose_prompt({'preamble': 'PRE'}, 'BRIEF', 'DO IT', 'NOTE')
        self.assertEqual(prompt.split('\n\n'),
                         ['Message from the operator (follow it): NOTE', 'BRIEF', 'PRE', 'DO IT'])
        self.assertEqual(orchestrate._compose_prompt({}, '', 'DO IT', None), 'DO IT')

    def test_claude_permission_mode_is_passed_and_checked(self):
        self.assertIn('acceptEdits', _claude_argv('x', None))
        argv = _claude_argv('x', 'opus', permission_mode='bypassPermissions')
        self.assertEqual(argv[argv.index('--permission-mode') + 1], 'bypassPermissions')
        with self.assertRaises(ValueError):
            _claude_argv('x', None, permission_mode='yolo')
        spec, _ = build_task('t', 'o', '/tmp', [['x']], 'go', runner='claude',
                             permission_mode='bypassPermissions')
        self.assertIn('bypassPermissions', spec['implementation'])


class EndToEndTests(unittest.TestCase):
    def test_one_request_becomes_a_program_whose_check_passes(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, base, True)
        bin_dir = base / 'bin'
        bin_dir.mkdir()
        make_client(bin_dir, 'claude', FAKE_AGENT)
        path = str(bin_dir) + os.pathsep + os.environ.get('PATH', '')
        env = {'LOCALAPPDATA': str(base / 'appdata')}
        folder = base / 'hello'
        notes = ['print the greeting in green if you can']
        with mock.patch.dict(os.environ, {'PATH': path}):
            job = build.prepare('new', 'a program that says hello', str(folder), env=env,
                                steps=3, now=lambda: 2000)
            job['loop_spec']['timeout_seconds'] = 60
            result = build.run(job, steer=lambda: notes.pop() if notes else None)
        self.assertEqual(result['state'], 'done', result)
        self.assertEqual(result['iterations'], 1)
        seen = (folder / 'SEEN_PROMPT.txt').read_text(encoding='utf-8')
        self.assertTrue(seen.startswith('Message from the operator (follow it): print the greeting'))
        self.assertIn('[Overseer build]', seen)
        check = subprocess.run([sys.executable, 'overseer_check.py'], cwd=str(folder))
        self.assertEqual(check.returncode, 0)
        db = sqlite3.connect(job['ledger'])
        try:
            states = [row[0] for row in db.execute('SELECT state FROM jobs')]
        finally:
            db.close()
        self.assertEqual(states, ['passed'])


if __name__ == '__main__':
    unittest.main()
