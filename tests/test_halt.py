import os
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from overseer.__main__ import main
from overseer.halt import HALTED, PAUSED, clear, note, render
from overseer.policy import STOP_REASON


STOP = "client requested no further automatic continuation"
NEEDS_INPUT = "OVERSEER_NEEDS_INPUT"


def halted_entry(reason=STOP, kind=HALTED, session="gone-session", pane="%0"):
    """Return a pane entry that carries a halt record."""
    return {"halt": {"reason": reason, "kind": kind, "resume": "answer it in the pane",
                     "session": session, "pane": pane, "at": 1.0}}


class HaltRecordTests(unittest.TestCase):
    """An intentional halt is recorded once, announced once, and cleared on resume."""

    def test_a_client_stop_records_a_halted_entry_with_the_exact_reason(self):
        entry = {}
        with self.assertLogs("overseer", level="INFO") as logs:
            record = note(entry, STOP_REASON, "OVERSEER_DONE\n› ", "%0", 100.0)
        self.assertIsNotNone(record)
        self.assertEqual(entry["halt"]["reason"], STOP)
        self.assertEqual(entry["halt"]["kind"], HALTED)
        self.assertEqual(entry["halt"]["pane"], "%0")
        self.assertEqual(entry["halt"]["at"], 100.0)
        self.assertTrue(entry["halt"]["session"])
        notices = [line for line in logs.output if "paused automatic turns" in line]
        self.assertEqual(len(notices), 1)
        self.assertIn("[OVERSEER] Session ", notices[0])
        self.assertIn("paused automatic turns: %s" % STOP, notices[0])

    def test_a_needs_input_turn_records_the_marker_itself(self):
        entry = {}
        note(entry, STOP_REASON, "OVERSEER_NEEDS_INPUT\n› ", "%0", 1.0, session="s")
        self.assertEqual(entry["halt"]["reason"], NEEDS_INPUT)
        self.assertEqual(entry["halt"]["kind"], HALTED)
        earlier = {}
        note(earlier, STOP_REASON, "OVERSEER_NEEDS_INPUT\n› prompt\ndone\n› ",
             "%0", 1.0, session="s")
        self.assertEqual(earlier["halt"]["reason"], STOP)

    def test_the_notice_is_logged_once_and_not_repeated(self):
        entry = {}
        with self.assertLogs("overseer", level="INFO") as logs:
            note(entry, STOP_REASON, "OVERSEER_DONE\n› ", "%0", 1.0, session="s")
            again = note(entry, STOP_REASON, "OVERSEER_DONE\n› ", "%0", 2.0, session="s")
        self.assertIsNone(again)
        self.assertEqual(entry["halt"]["at"], 1.0)
        notices = [line for line in logs.output if "paused automatic turns" in line]
        self.assertEqual(len(notices), 1)
        with self.assertLogs("overseer", level="INFO") as logs:
            changed = note(entry, STOP_REASON, "OVERSEER_NEEDS_INPUT\n› ",
                           "%0", 3.0, session="s")
        self.assertIsNotNone(changed)
        self.assertEqual(entry["halt"]["reason"], NEEDS_INPUT)
        notices = [line for line in logs.output if "paused automatic turns" in line]
        self.assertEqual(len(notices), 1)

    def test_a_transient_reason_neither_records_nor_clears_a_halt(self):
        entry = {}
        note(entry, "waiting for idle threshold", "text\n› ", "%0", 1.0, session="s")
        self.assertNotIn("halt", entry)
        note(entry, "cooldown", "text\n› ", "%0", 2.0, session="s")
        self.assertNotIn("halt", entry)
        note(entry, STOP_REASON, "OVERSEER_DONE\n› ", "%0", 3.0, session="s")
        before = dict(entry["halt"])
        note(entry, "cooldown", "text\n› ", "%0", 4.0, session="s")
        self.assertEqual(entry["halt"], before)

    def test_a_successful_send_clears_the_halt_record(self):
        entry = {}
        note(entry, STOP_REASON, "OVERSEER_DONE\n› ", "%0", 1.0, session="s")
        clear(entry)
        self.assertNotIn("halt", entry)
        clear(entry)
        self.assertNotIn("halt", entry)

    def test_the_halted_section_lists_a_pane_whose_session_is_gone(self):
        state = {"%0:123": halted_entry(), "_queue": {"waiting": [], "active": None},
                 "_model_decisions": {}}
        lines = render(state)
        text = "\n".join(lines)
        self.assertIn("HALTED", lines[0])
        self.assertIn("PAUSED", lines[0])
        self.assertIn("Reason: %s" % STOP, text)
        self.assertIn("%0", text)
        self.assertNotIn("_queue", text)
        self.assertNotIn("_model_decisions", text)

    @unittest.skipIf(os.name == 'nt', 'drives the tmux monitor command line, which native Windows refuses')
    def test_the_status_command_shows_the_halted_section(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({"%0:123": halted_entry()}))
            buffer = io.StringIO()
            example = Path(__file__).resolve().parent.parent / "config.example.json"
            with patch.dict("os.environ", {"OVERSEER_CONFIG": str(example)}):
                with patch.object(sys, "argv", ["overseer", "status", "--state", str(path)]):
                    with patch("sys.stdout", buffer):
                        main()
        output = buffer.getvalue()
        self.assertIn("HALTED", output)
        self.assertIn("Reason: %s" % STOP, output)
        self.assertIn("%0", output)


if __name__ == "__main__":
    unittest.main()
