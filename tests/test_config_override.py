"""OVERSEER_CONFIG selects the configuration file; unset, it is <repo>/config.json.

Written before the implementation and frozen. The override only chooses a path: the
file is still read-only to Overseer, and a missing one still says to copy the example.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from overseer import configfile

ROOT = Path(__file__).resolve().parent.parent


class ConfigOverrideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_default_is_config_json_beside_the_repository(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("OVERSEER_CONFIG", None)
            self.assertEqual(configfile.default_path(self.dir), self.dir / "config.json")

    def test_the_variable_overrides_the_default(self):
        other = self.dir / "elsewhere" / "mine.json"
        with patch.dict(os.environ, {"OVERSEER_CONFIG": str(other)}):
            self.assertEqual(configfile.default_path(self.dir), other)

    def test_an_empty_variable_is_ignored(self):
        with patch.dict(os.environ, {"OVERSEER_CONFIG": ""}):
            self.assertEqual(configfile.default_path(self.dir), self.dir / "config.json")

    @unittest.skipIf(os.name == 'nt', 'drives the tmux monitor command line, which native Windows refuses')
    def test_the_cli_reads_the_chosen_file_and_never_writes_it(self):
        chosen = self.dir / "mine.json"
        shutil.copyfile(ROOT / "config.example.json", chosen)
        before = chosen.read_bytes()
        env = dict(os.environ, OVERSEER_CONFIG=str(chosen), TMUX_TMPDIR=str(self.dir))
        env.pop("TMUX", None)
        result = subprocess.run(
            [sys.executable, "-B", "-m", "overseer", "run", "--once", "--state", str(self.dir / "s.json")],
            cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(chosen.read_bytes(), before)

    @unittest.skipIf(os.name == 'nt', 'drives the tmux monitor command line, which native Windows refuses')
    def test_a_missing_chosen_file_is_named_in_the_error(self):
        missing = self.dir / "nope.json"
        env = dict(os.environ, OVERSEER_CONFIG=str(missing), TMUX_TMPDIR=str(self.dir))
        env.pop("TMUX", None)
        result = subprocess.run(
            [sys.executable, "-B", "-m", "overseer", "run", "--once", "--state", str(self.dir / "s.json")],
            cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(missing), result.stderr)
        self.assertIn("config.example.json", result.stderr)
        self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
