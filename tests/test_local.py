"""Single-program mode (`overseer here`): one client in this terminal, no tmux."""
import os
from pathlib import Path
import pty
import tempfile
import threading
import tty
import unittest
from unittest import mock

from overseer import local
from overseer.local import PANE, PtyBackend, run_attached
from overseer.terminal import Screen


def backend(process="claude", prompt="❯ "):
    master, slave = pty.openpty()
    tty.setraw(slave)  # as a client's TUI sets it, so Enter arrives as \r
    screen = Screen(40, 5)
    screen.feed(prompt)
    item = PtyBackend(process, 4242, master, screen, threading.Lock(), threading.Lock())
    return item, master, slave


def drain(fd):
    os.set_blocking(fd, False)
    data = b""
    try:
        while True:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            data += chunk
    except BlockingIOError:
        pass
    return data


class PtyBackendTests(unittest.TestCase):
    def setUp(self):
        self.backend, self.master, self.slave = backend()
        self.addCleanup(os.close, self.master)
        self.addCleanup(os.close, self.slave)

    def test_one_pane_until_the_client_exits(self):
        self.assertEqual(self.backend.panes(), [PANE])
        self.backend.exited = True
        self.assertEqual(self.backend.panes(), [])

    def test_snapshot_is_the_screen_and_is_ready_at_the_prompt(self):
        snapshot = self.backend.snapshot()
        self.assertEqual((snapshot.pane, snapshot.process, snapshot.pid), (PANE, "claude", "4242"))
        self.assertEqual(snapshot.cursor_line, "❯")
        self.assertTrue(snapshot.ready)

    @mock.patch("overseer.local.time.sleep")
    def test_send_types_the_reply_then_submits_it(self, sleep):
        self.backend.send(self.backend.snapshot(), "next step")
        self.assertEqual(drain(self.slave), b"next step\r")
        sleep.assert_called_once()

    def test_a_changed_screen_is_not_typed_into(self):
        original = self.backend.snapshot()
        self.backend.screen.feed("\r\nworking…")
        with self.assertRaises(RuntimeError):
            self.backend.send(original, "next step")
        self.assertEqual(drain(self.slave), b"")

    def test_nothing_is_sent_after_the_client_exited(self):
        original = self.backend.snapshot()
        self.backend.exited = True
        with self.assertRaises(RuntimeError):
            self.backend.send(original, "next step")


class RunAttachedRefusalTests(unittest.TestCase):
    def run_attached(self, client="claude", cwd="."):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            return run_attached(client, [], Path(directory) / "config.json", state, cwd,
                                mock.Mock(return_value={}), mock.Mock(), mock.Mock())

    def test_needs_a_terminal(self):
        with mock.patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "needs a terminal"):
                self.run_attached()

    def test_watches_only_known_clients(self):
        with mock.patch("sys.stdin.isatty", return_value=True), \
                mock.patch("sys.stdout.isatty", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "codex, claude, or opencode"):
                self.run_attached(client="bash")

    def test_refuses_a_missing_directory(self):
        with mock.patch("sys.stdin.isatty", return_value=True), \
                mock.patch("sys.stdout.isatty", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "not a directory"):
                self.run_attached(cwd="/nonexistent/overseer-here")

    def test_invalid_state_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text("[1, 2]", encoding="utf-8")
            with self.assertRaises(ValueError):
                local._load_state(state)
            self.assertEqual(state.read_text(encoding="utf-8"), "[1, 2]")


if __name__ == "__main__":
    unittest.main()
