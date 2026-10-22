"""A report the worker's terminal broke across lines is read; one that stays unreadable is announced.

Observed 2026-10-22 on pane %7 (clubwpt-claude, 157 columns): Claude Code
renders a long line with hard newlines, indented two spaces and broken at a
space it drops, so `tmux capture-pane -p` (and `-J`) returned one ~700
character OVERSEER_REPORT as six lines. The report was taken as unreadable,
nothing was announced, and the pane sat idle.
"""
import json
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import Mock

from overseer.__main__ import tick
from overseer.policy import Policy, _report_state, classify, current_turn, next_prompt
from overseer.tmux import Snapshot

REPORT = {
    "status": "step_done",
    "objective": "Streamed HL8689 hands read on Kali with the pot checked automatically, "
                 "so review only covers exceptions",
    "remaining": "Add 921-wide board rank templates: crop board cards from "
                 "remote-results/stream-loop-HL8689-20261022/run chunk frames where the board reads "
                 "unconfirmed, label each by eye, add them to rank_templates/board; confirm no new "
                 "wrong cards on the 6 Oct corpus and HL8202 and that the test suite passes; re-read "
                 "the 6 chunks and report the pot check before and after; commit, push, and update NOW.md",
    "done": "Stream loop ran 6 chunks, 30 hands read, causes measured (d65b059)",
    "evidence": "11 of 30 hands all pots add up; frame 1443 2s/9c unconfirmed with empty slots matched 0.997",
}
LINE = "OVERSEER_REPORT " + json.dumps(REPORT, separators=(",", ":"))


def rendered(line, width=155):
    """The line as Claude Code draws it: broken at spaces it drops, each part indented two spaces."""
    return "\n".join("  " + part for part in textwrap.wrap(line, width, break_long_words=False,
                                                          break_on_hyphens=False))


def screen(body):
    return "❯ continue\n\n" + body + "\n  OVERSEER_STEP_DONE\n\n❯ \n"


class WrappedReportTests(unittest.TestCase):
    def test_a_report_broken_across_lines_is_read_whole(self):
        text = screen(rendered(LINE))
        self.assertGreater(len(rendered(LINE).splitlines()), 3)
        kind, fields = _report_state(current_turn(text))
        self.assertEqual(kind, "handoff")
        self.assertEqual(fields["remaining"], REPORT["remaining"])
        self.assertEqual(fields["objective"], REPORT["objective"])
        prompt, reason = next_prompt(text, "Please continue.")
        self.assertEqual(reason, "writer handoff prompt")
        self.assertIsNotNone(prompt)

    def test_a_long_word_broken_inside_still_reads(self):
        # A path longer than the line is cut with no space at the break.
        cut = LINE.index("HL8689-20261022") + 6
        text = screen("  " + LINE[:cut] + "\n  " + LINE[cut:])
        kind, fields = _report_state(current_turn(text))
        self.assertEqual(kind, "handoff")
        self.assertIn("HL8689", fields["remaining"])
        self.assertIn("20261022/run", fields["remaining"])

    def test_joining_is_bounded(self):
        broken = '  OVERSEER_REPORT {"status":"step_done","objective":"never closed'
        text = screen(broken + "\n" + "\n".join("  more words" for _ in range(14)))
        self.assertEqual(_report_state(current_turn(text))[0], "invalid")

    def test_joining_stops_at_another_report_and_the_latest_wins(self):
        broken = '  OVERSEER_REPORT {"status":"step_done","objective":"cut short'
        whole = "  OVERSEER_REPORT " + json.dumps({"status": "step_done", "objective": "o",
                                                     "remaining": "r"})
        kind, fields = _report_state(current_turn(screen(broken + "\n" + whole)))
        self.assertEqual((kind, fields["remaining"]), ("handoff", "r"))

    def test_joining_stops_at_a_marker_line(self):
        broken = '  OVERSEER_REPORT {"status":"step_done","objective":"o","remaining":"r"'
        text = "❯ go\n" + broken + '\n  OVERSEER_STEP_DONE\n  "}\n❯ \n'
        self.assertEqual(_report_state(current_turn(text))[0], "invalid")

    def test_a_one_line_report_is_unchanged(self):
        kind, fields = _report_state(current_turn(screen("  " + LINE)))
        self.assertEqual((kind, fields["remaining"]), ("handoff", REPORT["remaining"]))


class UnreadableReportTests(unittest.TestCase):
    TEXT = screen('  OVERSEER_REPORT {"status":"step_done","objective":"cut')

    def test_classify_names_an_unreadable_report(self):
        self.assertEqual(classify(self.TEXT), (True, "invalid output report"))

    def test_an_earlier_turns_unreadable_report_is_not_this_turns(self):
        text = '❯ old\n  OVERSEER_REPORT {"status":"step_done","objective":"cut\n❯ new\nWould you like me to continue?\n› '
        self.assertEqual(classify(text), (True, "routine continuation question"))

    def test_an_unreadable_report_is_announced_once_and_not_sent(self):
        backend = Mock()
        backend.panes.return_value = ["%0"]
        backend.snapshot.return_value = Snapshot("%0", "claude", "123", self.TEXT, "❯ ", "0", "0")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            state = {}
            config = {"dry_run": False, "reply": "Please continue."}
            policy = Policy(idle_seconds=0, cooldown_seconds=0)
            with self.assertLogs("overseer", level="INFO") as logs:
                for index in range(3):
                    tick(backend, policy, state, config, path, index * 100)
        backend.send.assert_not_called()
        halt = state["%0:123"]["halt"]
        self.assertEqual((halt["reason"], halt["kind"]), ("invalid output report", "PAUSED"))
        self.assertIn("one line", halt["resume"])
        notices = [line for line in logs.output if "paused automatic turns" in line]
        self.assertEqual(len(notices), 1)


if __name__ == "__main__":
    unittest.main()
