import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from overseer.__main__ import settings, tick
from overseer.policy import Policy
from overseer.tmux import Snapshot, Tmux


SCREEN = Snapshot("%0", "codex", "123", "Would you like me to continue?\n›", "›", "0", "0")


class MonitorTests(unittest.TestCase):
    def test_cursor_and_process_guards(self):
        self.assertTrue(SCREEN.ready)
        for field, value in (("process", "zsh"), ("cursor_line", "› my draft"),
                             ("mode", "1"), ("dead", "1")):
            data = dict(SCREEN.__dict__)
            data[field] = value
            self.assertFalse(Snapshot(**data).ready)

    def test_dry_run_never_sends(self):
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = SCREEN
        with tempfile.TemporaryDirectory() as directory:
            tick(backend, Policy(idle_seconds=0), {}, {"dry_run": True}, Path(directory) / "state.json", 0)
        backend.send.assert_not_called()

    def test_send_is_persisted_and_not_repeated_after_restart(self):
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = SCREEN
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"

            def verify_reserved(*args):
                self.assertEqual(json.loads(path.read_text())["%0:123"]["last_sent"], 0)

            backend.send.side_effect = verify_reserved
            config = {"dry_run": False, "reply": "Please continue."}
            tick(backend, Policy(idle_seconds=0), {}, config, path, 0)
            tick(backend, Policy(idle_seconds=0), json.loads(path.read_text()), config, path, 2000)
        backend.send.assert_called_once_with(SCREEN, "Please continue.")

    def test_changed_screen_is_not_sent(self):
        backend = Tmux()
        with patch.object(backend, "panes", return_value=["%0"]), patch.object(backend, "snapshot", return_value=Snapshot("%0", "zsh", "123", "$", "$", "0", "0")), patch("overseer.tmux.command") as command:
            with self.assertRaisesRegex(RuntimeError, "changed"):
                backend.send(SCREEN, "Please continue.")
            command.assert_not_called()

    def test_literal_text_and_enter_are_separate(self):
        backend = Tmux()
        with patch.object(backend, "panes", return_value=["%0"]), patch.object(backend, "snapshot", return_value=SCREEN), patch("overseer.tmux.command") as command:
            backend.send(SCREEN, "Please continue.")
            self.assertEqual(command.call_args_list[0].args, ("send-keys", "-t", "%0", "-l", "--", "Please continue."))
            self.assertEqual(command.call_args_list[1].args, ("send-keys", "-t", "%0", "Enter"))

    def test_config_rejects_control_characters(self):
        config = {"poll_seconds": 30, "idle_seconds": 180, "cooldown_seconds": 900,
                  "max_per_day": 12, "dry_run": True, "reply": "hello\ncommand"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config))
            with self.assertRaises(ValueError):
                settings(path)


if __name__ == "__main__":
    unittest.main()
