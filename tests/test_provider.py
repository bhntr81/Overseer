import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from overseer.factory import Factory
from overseer.provider import (
    DEFAULT_MODEL, DEFAULT_RUNNER, FREE_MODELS, MAX_INSTRUCTION_CHARS,
    build_task, detect_session, is_free, resolve_worker, worker_argv,
)


class ProviderTests(unittest.TestCase):
    def test_worker_argv_places_the_instruction_as_one_element(self):
        argv = worker_argv('implement add() in calc.py', model='opencode/x-free',
                           opencode='opencode')
        self.assertEqual(argv[0], 'opencode')
        self.assertIn('run', argv)
        self.assertIn('--standalone', argv)
        self.assertIn('--auto', argv)
        self.assertEqual(argv[argv.index('--model') + 1], 'opencode/x-free')
        # The instruction is exactly one element, equal to the input.
        self.assertEqual(argv.count('implement add() in calc.py'), 1)
        self.assertEqual(argv[-1], 'implement add() in calc.py')

    def test_a_tricky_instruction_is_not_split(self):
        tricky = "--rm -rf /; echo 'pwned' && rm \"x\"\nsecond line"
        argv = worker_argv(tricky, model='opencode/x-free')
        self.assertIn(tricky, argv)
        self.assertEqual(sum(1 for a in argv if a == tricky), 1)

    def test_an_empty_instruction_is_refused(self):
        with self.assertRaises(ValueError):
            worker_argv('   ', model='opencode/x-free')

    def test_a_nul_instruction_is_refused(self):
        with self.assertRaises(ValueError):
            worker_argv('do\x00it', model='opencode/x-free')

    def test_an_over_long_instruction_is_refused(self):
        with self.assertRaises(ValueError):
            worker_argv('x' * (MAX_INSTRUCTION_CHARS + 1), model='opencode/x-free')

    def test_a_bad_model_id_is_refused(self):
        with self.assertRaises(ValueError):
            worker_argv('do it', model='no-slash')

    def test_the_default_model_is_a_free_model(self):
        self.assertIn(DEFAULT_MODEL, FREE_MODELS)
        self.assertTrue(is_free(DEFAULT_MODEL))
        self.assertFalse(is_free('anthropic/claude-opus'))

    def test_a_fake_opencode_receives_the_instruction_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            out = tmp / 'argv.json'
            fake = tmp / 'opencode'
            fake.write_text('#!/usr/bin/env python3\n'
                            'import json, sys\n'
                            'open(%r, "w").write(json.dumps(sys.argv[1:]))\n' % str(out))
            fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
            instruction = "write calc.py; it must handle 'edge' cases & -flags"
            subprocess.run(worker_argv(instruction, model='opencode/x-free',
                                       opencode=str(fake)), check=True, timeout=30)
            received = json.loads(out.read_text())
            self.assertEqual(received.count(instruction), 1)


if __name__ == '__main__':
    unittest.main()


class SessionDetectionTests(unittest.TestCase):
    def test_a_claude_code_session_is_detected(self):
        d = detect_session({'CLAUDECODE': '1'})
        self.assertEqual(d['runner'], 'claude')
        self.assertEqual(d['marker'], 'CLAUDECODE')

    def test_an_opencode_session_is_detected(self):
        d = detect_session({'OPENCODE': '/home/x/.opencode/bin/opencode'})
        self.assertEqual(d['runner'], 'opencode')

    def test_a_codex_session_is_detected(self):
        d = detect_session({'CODEX_SANDBOX': 'seatbelt'})
        self.assertEqual(d['runner'], 'codex')

    def test_no_session_is_detected_in_a_bare_environment(self):
        d = detect_session({'PATH': '/usr/bin', 'HOME': '/home/x'})
        self.assertIsNone(d['runner'])


class ResolveWorkerTests(unittest.TestCase):
    def test_a_bare_environment_falls_back_to_opencode_free(self):
        r = resolve_worker('do the step', env={'PATH': '/usr/bin'})
        self.assertEqual(r['runner'], DEFAULT_RUNNER)
        self.assertEqual(r['runner'], 'opencode')
        self.assertEqual(r['model'], DEFAULT_MODEL)
        self.assertIn('run', r['argv'])
        self.assertIn('--standalone', r['argv'])
        self.assertIn('--format', r['argv'])
        self.assertEqual(r['argv'][-1], 'do the step')

    def test_resolve_inherits_a_detected_session(self):
        r = resolve_worker('fix it', env={'CLAUDECODE': '1'})
        self.assertEqual(r['runner'], 'claude')
        self.assertEqual(r['argv'][0], 'claude')
        self.assertIn('inherited', r['source'])
        self.assertEqual(r['argv'][-1], 'fix it')

    def test_an_explicit_runner_overrides_detection(self):
        r = resolve_worker('fix it', runner='opencode', env={'CLAUDECODE': '1'})
        self.assertEqual(r['runner'], 'opencode')
        self.assertIn('run', r['argv'])

    def test_an_explicit_model_is_used(self):
        r = resolve_worker('go', model='opencode/glm-5.3-flash-free', env={})
        self.assertEqual(r['model'], 'opencode/glm-5.3-flash-free')
        self.assertEqual(r['argv'][r['argv'].index('--model') + 1], 'opencode/glm-5.3-flash-free')

    def test_an_unknown_runner_is_refused(self):
        with self.assertRaises(ValueError):
            resolve_worker('go', runner='bard', env={})

    def test_the_resolved_instruction_is_one_whole_element(self):
        tricky = "rm -rf /; echo hi && touch x"
        r = resolve_worker(tricky, runner='codex', env={})
        self.assertEqual(sum(1 for a in r['argv'] if a == tricky), 1)
        self.assertEqual(r['argv'][-1], tricky)


class BuildTaskTests(unittest.TestCase):
    def test_build_task_produces_a_factory_valid_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            spec, resolved = build_task(
                'bt1', 'implement add', str(tmp),
                checks=[[sys.executable, '-c', 'pass']],
                instruction='Create calc.py with add(a,b).', env={})
            # It is a real, submittable factory task driven by the adapter argv.
            self.assertEqual(spec['implementation'], resolved['argv'])
            self.assertEqual(resolved['runner'], 'opencode')
            f = Factory(tmp / 'state' / 'jobs.sqlite3')
            self.addCleanup(f.close)
            self.assertTrue(f.submit(spec))
            self.assertEqual(f.inspect('bt1')['state'], 'queued')

    def test_build_task_acceptance_ids_match_the_checks(self):
        spec, _ = build_task('bt2', 'o', '/tmp/x',
                             checks=[['a'], ['b']], instruction='do', env={})
        self.assertEqual(spec['contract']['acceptance_ids'], ['A1', 'A2'])
