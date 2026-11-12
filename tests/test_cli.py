import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def test_help_and_single_poll(self):
        with tempfile.TemporaryDirectory() as directory:
            cases = [["--help"], ["watch", "--help"]]
            if os.name != "nt":  # a single poll drives tmux, which native Windows refuses
                cases.append(["run", "--once", "--state", str(Path(directory) / "state.json")])
            for args in cases:
                with self.subTest(args=args):
                    result = subprocess.run([sys.executable, "-m", "overseer", *args], capture_output=True, text=True,
                                            env=dict(os.environ, OVERSEER_CONFIG=str(Path(__file__).resolve().parent.parent / "config.example.json")))
                    self.assertEqual(result.returncode, 0, result.stderr)
