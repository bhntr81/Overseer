"""Exercise real tmux delivery using an isolated, synthetic client."""

import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from overseer.__main__ import tick
from overseer.policy import Policy
from overseer.tmux import Tmux, command


@unittest.skipUnless(sys.platform == "linux" and shutil.which("tmux"), "requires Linux and tmux")
class TransportTests(unittest.TestCase):
    def test_actual_delivery_and_duplicate_prevention(self):
        with tempfile.TemporaryDirectory(prefix="overseer-test-") as directory:
            root = Path(directory)
            socket = root.name
            received = root / "received.txt"
            fixture = root / "fixture.py"
            client = root / "codex"
            client.symlink_to(sys.executable)
            fixture.write_text(
                "import ctypes,sys\n"
                "from pathlib import Path\n"
                "ctypes.CDLL(None).prctl(15,b'codex',0,0,0)\n"
                "print('\\033[2J\\033[15;1HWould you like me to continue?\\r\\n› ',end='',flush=True)\n"
                "for line in sys.stdin:\n"
                f" with Path({str(received)!r}).open('a') as output: output.write(line)\n"
            )

            def isolated(*args):
                return command("-L", socket, *args)

            try:
                pane = isolated("new-session", "-d", "-P", "-F", "#{pane_id}", "-s", "fixture",
                                shlex.join([str(client), str(fixture)])).strip()
                isolated("set-option", "-p", "-t", pane, "@overseer", "1")
                with patch("overseer.tmux.command", side_effect=isolated):
                    backend = Tmux()
                    deadline = time.monotonic() + 5
                    while not backend.snapshot(pane).ready and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertTrue(backend.snapshot(pane).ready)
                    state = {}
                    config = {"dry_run": False, "reply": "Synthetic continuation."}
                    path = root / "state.json"
                    tick(backend, Policy(idle_seconds=0), state, config, path, 1000)
                    deadline = time.monotonic() + 5
                    while not received.exists() and time.monotonic() < deadline:
                        time.sleep(.05)
                    self.assertEqual(received.read_text(), "Synthetic continuation.\n")
                    tick(backend, Policy(idle_seconds=0), json.loads(path.read_text()), config, path, 1001)
                    self.assertEqual(received.read_text(), "Synthetic continuation.\n")
            finally:
                subprocess.run(["tmux", "-L", socket, "kill-server"], capture_output=True)
