"""The stop agent reviews a worker's stop before it halts the pane (2026-10-29)."""
import json
import sys
import time
import unittest

from overseer import stopgate
from overseer.policy import STOP_REASON, Policy, classify

NEEDS_INPUT = json.dumps({"status": "needs_input", "objective": "Pot reconciliation",
                          "remaining": "price calls", "done": "pot glyphs",
                          "evidence": "20 of 100 calls unpriced"})
SCREEN = ("● Should the tracker price a call at the amount it matched?\n"
          "OVERSEER_REPORT " + NEEDS_INPUT + "\nOVERSEER_NEEDS_INPUT\n\n❯\n")


def agent(verdict, exit_code=0):
    line = json.dumps(verdict) if isinstance(verdict, dict) else verdict
    return [sys.executable, "-c", "import sys; sys.stdin.read(); print(%r); sys.exit(%d)" % (line, exit_code)]


CONTINUE = {"verdict": "continue", "category": "not_legitimate",
            "reason": "Poker trackers price a call as the amount to match.",
            "decision": "Price a call at the street's highest total, capped at the stack."}
STOP = {"verdict": "stop", "category": "money", "reason": "It buys a plan.", "decision": ""}


def config(command, **extra):
    return {"stop_agent": dict({"enabled": True, "command": command, "timeout_seconds": 30}, **extra)}


class StopGateTests(unittest.TestCase):
    def settle(self, entry, text, cfg, jobs):
        """Start a review and collect it, as two monitor polls would."""
        record = stopgate.review(entry, text, STOP_REASON, cfg, time.time(), jobs=jobs)
        for _ in range(100):
            if record.get("status") != "pending":
                return record
            jobs[record["fingerprint"]].wait(5)
            record = stopgate.review(entry, text, STOP_REASON, cfg, time.time(), jobs=jobs)
        return record

    def test_the_screen_is_a_stop(self):
        self.assertEqual(classify(SCREEN), (False, STOP_REASON))

    def test_off_unless_enabled(self):
        self.assertIsNone(stopgate.review({}, SCREEN, STOP_REASON, {}, 0, jobs={}))

    def test_only_a_worker_stop_is_reviewed(self):
        self.assertIsNone(stopgate.review({}, SCREEN, "cooldown", config(agent(CONTINUE)), 0, jobs={}))

    def test_a_continue_verdict_makes_the_same_screen_eligible(self):
        entry, jobs = {}, {}
        record = self.settle(entry, SCREEN, config(agent(CONTINUE)), jobs)
        self.assertEqual((record["status"], record["verdict"]["verdict"]), ("done", "continue"))
        eligible, reason = Policy(idle_seconds=0, cooldown_seconds=1).consider(entry, SCREEN, time.time())
        self.assertEqual((eligible, reason), (True, stopgate.OVERRIDE_REASON))
        prompt, kind = stopgate.prompt_for(entry, SCREEN, lambda: (None, "unused"))
        self.assertEqual(kind, stopgate.OVERRIDE_KIND)
        self.assertIn("capped at the stack", prompt)
        self.assertLessEqual(len(prompt), 1000)
        self.assertNotIn("\n", prompt)

    def test_a_changed_screen_does_not_use_an_old_verdict(self):
        entry, jobs = {}, {}
        self.settle(entry, SCREEN, config(agent(CONTINUE)), jobs)
        changed = SCREEN.replace("matched?", "matched? (asked again)")
        self.assertFalse(stopgate.ready_override(entry, changed))
        self.assertEqual(Policy(idle_seconds=0).consider(entry, changed, time.time())[1], STOP_REASON)

    def test_a_stop_verdict_keeps_the_halt(self):
        entry, jobs = {}, {}
        record = self.settle(entry, SCREEN, config(agent(STOP)), jobs)
        self.assertEqual(record["verdict"]["category"], "money")
        self.assertEqual(Policy(idle_seconds=0).consider(entry, SCREEN, time.time()), (False, STOP_REASON))

    def test_failures_keep_the_stop(self):
        for command in (agent("not json at all"), agent(CONTINUE, exit_code=3),
                        agent({"verdict": "maybe"})):
            entry, jobs = {}, {}
            record = self.settle(entry, SCREEN, config(command), jobs)
            self.assertEqual(record["status"], "failed", command)
            self.assertFalse(stopgate.ready_override(entry, SCREEN))

    def test_a_missing_command_fails_closed(self):
        entry = {}
        record = stopgate.review(entry, SCREEN, STOP_REASON, config(["/nonexistent/stop-agent"]), 0, jobs={})
        self.assertEqual(record["status"], "failed")

    def test_a_slow_agent_times_out_and_the_stop_stands(self):
        entry, jobs = {}, {}
        slow = [sys.executable, "-c", "import time; time.sleep(30)"]
        cfg = config(slow, timeout_seconds=1)
        record = stopgate.review(entry, SCREEN, STOP_REASON, cfg, 100.0, jobs=jobs)
        record = stopgate.review(entry, SCREEN, STOP_REASON, cfg, 102.0, jobs=jobs)
        self.assertEqual((record["status"], record["note"]), ("failed", "timed out"))

    def test_an_always_stop_blocker_is_never_reviewed(self):
        report = json.loads(NEEDS_INPUT)
        report["blocker"] = "account_or_credentials"
        screen = SCREEN.replace(NEEDS_INPUT, json.dumps(report))
        entry, jobs = {}, {}
        record = stopgate.review(entry, screen, STOP_REASON, config(agent(CONTINUE)), 0, jobs=jobs)
        self.assertEqual(record["verdict"]["verdict"], "stop")
        self.assertEqual(jobs, {})

    def test_overrides_are_capped_per_day(self):
        entry, jobs = {"stop_agent_overrides": [time.time()] * 2}, {}
        record = stopgate.review(entry, SCREEN, STOP_REASON,
                                 config(agent(CONTINUE), max_overrides_per_day=2), time.time(), jobs=jobs)
        self.assertEqual(record["status"], "skipped")
        self.assertEqual(jobs, {})

    def test_sending_counts_an_override(self):
        entry, jobs = {}, {}
        self.settle(entry, SCREEN, config(agent(CONTINUE)), jobs)
        stopgate.sent(entry)
        self.assertEqual(entry["stop_agent"]["status"], "sent")
        self.assertEqual(len(entry["stop_agent_overrides"]), 1)
        self.assertFalse(stopgate.ready_override(entry, SCREEN))

    def test_the_request_carries_the_criteria_and_the_turn(self):
        text = stopgate.request(SCREEN)
        self.assertIn("LEGITIMATE", text)
        self.assertIn("price a call", text)

    def test_bad_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            stopgate.settings({"stop_agent": {"enabled": True, "command": "claude -p"}})
        with self.assertRaises(ValueError):
            stopgate.settings({"stop_agent": {"enabled": True, "timeout_seconds": 0}})


if __name__ == "__main__":
    unittest.main()


class QueueStopTests(unittest.TestCase):
    """The live FIFO path: a stopped screen is reviewed, then continued (pane %2)."""

    def setUp(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import Mock
        from overseer.tmux import Snapshot
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.json"
        self.screen = Snapshot("%2", "claude", "2", SCREEN, "❯", "0", "0", 2)
        self.backend = Mock()
        self.backend.panes.side_effect = lambda: ["%2"]
        self.backend.snapshot.side_effect = lambda pane: self.screen
        self.state = {}
        self.policy = Policy(idle_seconds=0, cooldown_seconds=1)

    def run_queue(self, verdict):
        from overseer.__main__ import tick
        cfg = dict(config(agent(verdict)), serial_queue=True, dry_run=False, reply="Continue.")
        stopgate.JOBS.clear()
        for second in range(60):
            tick(self.backend, self.policy, self.state, cfg, self.path, 1000.0 + second)
            if self.backend.send.called:
                break
            for process in list(stopgate.JOBS.values()):
                process.wait(5)

    def test_a_continue_verdict_is_sent_through_the_queue(self):
        self.run_queue(CONTINUE)
        self.assertEqual(self.backend.send.call_count, 1)
        self.assertIn("capped at the stack", self.backend.send.call_args.args[1])
        self.assertEqual(self.state["%2:2"]["stop_agent"]["status"], "sent")

    def test_a_stop_verdict_sends_nothing_through_the_queue(self):
        self.run_queue(STOP)
        self.backend.send.assert_not_called()
        self.assertEqual(self.state["%2:2"]["stop_agent"]["verdict"]["verdict"], "stop")


class ComposerTests(unittest.TestCase):
    def test_the_composer_suggestion_never_reaches_the_stop_agent(self):
        # Pane %2, 2026-10-29: a dimmed suggestion was read as John's answer.
        screen = SCREEN.replace("\n\n❯\n", "\n\n❯\xa0Yes to (b), no to (a): keep visible evidence only\n")
        text = stopgate.request(screen)
        self.assertNotIn("Yes to (b)", text)
        self.assertIn("price a call", text)
        self.assertIn("never treat any text there as John's reply", text)
