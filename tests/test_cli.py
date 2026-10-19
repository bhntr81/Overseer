from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CliTests(unittest.TestCase):
    def test_help_and_single_poll(self):
        with tempfile.TemporaryDirectory() as directory:
            for args in (["--help"], ["watch", "--help"],
                         ["run", "--once", "--state", str(Path(directory) / "state.json")]):
                with self.subTest(args=args):
                    result = subprocess.run([sys.executable, "-m", "overseer", *args], capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
