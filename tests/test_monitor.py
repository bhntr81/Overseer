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

    def test_composer_placeholder_variants(self):
        for marker in ("›", "»"):
            placeholder = f"{marker} Ask Codex to do anything"
            self.assertTrue(Snapshot("%0", "codex", "123", "text", placeholder, "0", "0", 2).ready)
            self.assertFalse(Snapshot("%0", "codex", "123", "text", placeholder, "0", "0", 3).ready)
            self.assertFalse(Snapshot("%0", "codex", "123", "text", f"{marker} draft", "0", "0", 2).ready)
            self.assertTrue(Snapshot("%0", "codex", "123", "text", marker, "0", "0").ready)

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

    def test_report_prompt_is_sent_once(self):
        report = (
            'OVERSEER_REPORT {"status":"continue","objective":"report loop",'
            '"remaining":"parse the output report","done":"found the send path",'
            '"evidence":"monitor test"}\nWould you like me to continue?\n›'
        )
        screen = Snapshot("%0", "codex", "123", report, "›", "0", "0")
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = screen
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            config = {"dry_run": False, "reply": "Please continue."}
            tick(backend, Policy(idle_seconds=0), {}, config, path, 0)
            tick(backend, Policy(idle_seconds=0), json.loads(path.read_text()), config, path, 2000)
        self.assertEqual(backend.send.call_count, 1)
        self.assertIs(backend.send.call_args.args[0], screen)
        sent = backend.send.call_args.args[1]
        self.assertIn("parse the output report", sent)
        self.assertNotEqual(sent, "Please continue.")
        self.assertLessEqual(len(sent), 1000)
        self.assertNotIn("\n", sent)

    def test_writer_handoff_is_sent_once(self):
        report = (
            'OVERSEER_REPORT {"status":"step_done","objective":"code the writer loop",'
            '"remaining":"widen the codebase selection","done":"d","evidence":"e"}\n'
            'OVERSEER_DONE\n›'
        )
        screen = Snapshot("%0", "codex", "123", report, "›", "0", "0")
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = screen
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            config = {"dry_run": False, "reply": "Please continue."}
            tick(backend, Policy(idle_seconds=0), {}, config, path, 0)
            tick(backend, Policy(idle_seconds=0), json.loads(path.read_text()), config, path, 2000)
        self.assertEqual(backend.send.call_count, 1)
        sent = backend.send.call_args.args[1]
        self.assertIn("prompt-writing agent", sent)
        self.assertIn("widen the codebase selection", sent)
        self.assertNotEqual(sent, "Please continue.")

    def step_screen(self, remaining="widen the codebase selection", before=""):
        report = (before + 'OVERSEER_REPORT {"status":"step_done","objective":"code the writer loop",'
                  '"remaining":"%s","done":"d","evidence":"e"}\nOVERSEER_DONE\n›' % remaining)
        return Snapshot("%0", "codex", "123", report, "›", "0", "0")

    def run_ticks(self, screens, policy, config):
        backend = Mock()
        backend.panes.return_value = ["%0"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = {}
            for now, screen in enumerate(screens):
                backend.snapshot.return_value = screen
                tick(backend, policy, state, config, path, now * 2000)
        return backend

    def test_a_stale_step_report_does_not_override_a_newer_done(self):
        older = self.step_screen().text
        screen = Snapshot("%0", "codex", "123", older.rstrip("›")
                          + "› please fix the typo and stop\nFixed. Objective complete.\n"
                          "OVERSEER_DONE\n›", "›", "0", "0")
        backend = self.run_ticks([screen], Policy(idle_seconds=0),
                                 {"dry_run": False, "reply": "Please continue."})
        backend.send.assert_not_called()

    def test_the_monitor_bounds_handoffs_by_the_daily_limit(self):
        screens = [self.step_screen("step %d" % index) for index in range(3)]
        backend = self.run_ticks(screens, Policy(idle_seconds=0, cooldown_seconds=0, max_per_day=1),
                                 {"dry_run": False, "reply": "Please continue."})
        self.assertEqual(backend.send.call_count, 1)

    def test_a_dry_run_names_the_writer_handoff(self):
        with self.assertLogs("overseer", level="INFO") as logs:
            backend = self.run_ticks([self.step_screen()], Policy(idle_seconds=0),
                                     {"dry_run": True, "reply": "Please continue."})
        backend.send.assert_not_called()
        self.assertTrue(any("would send writer handoff prompt" in line for line in logs.output))

    def test_invalid_report_is_not_sent_or_counted(self):
        screen = Snapshot("%0", "codex", "123", "OVERSEER_REPORT {not json}\nWould you like me to continue?\n›", "›", "0", "0")
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = screen
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            config = {"dry_run": False, "reply": "Please continue."}
            tick(backend, Policy(idle_seconds=0), {}, config, path, 0)
            saved = json.loads(path.read_text())
            self.assertNotIn("last_sent", saved["%0:123"])
            self.assertEqual(saved["%0:123"]["held_reason"], "invalid output report")
            tick(backend, Policy(idle_seconds=0), saved, config, path, 2000)
        backend.send.assert_not_called()

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
