import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from overseer.provider import (
    DEFAULT_MODEL, FREE_MODELS, MAX_INSTRUCTION_CHARS, is_free, worker_argv,
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
