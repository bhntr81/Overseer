import json
import unittest

from overseer.policy import Policy, classify, hold, next_prompt


QUESTION = "Completed the current step.\nWould you like me to continue?\n› "


class PolicyTests(unittest.TestCase):
    def test_only_routine_questions(self):
        self.assertTrue(classify(QUESTION)[0])
        for text in ("Which database should I use?", "user@host:~$ ", "Done.",
                     "Would you like me to continue?\nAllow once",
                     "Delete the database. Would you like me to continue?",
                     "Would you like me to continue?\nThinking…",
                     "Would you like me to continue?\nesc to interrupt"):
            with self.subTest(text=text):
                self.assertFalse(classify(text)[0])

    def test_waits_for_stable_screen(self):
        policy, state = Policy(idle_seconds=60), {}
        self.assertFalse(policy.consider(state, QUESTION, 0)[0])
        self.assertFalse(policy.consider(state, QUESTION, 59)[0])
        self.assertTrue(policy.consider(state, QUESTION, 60)[0])
        self.assertFalse(policy.consider(state, "New output\n" + QUESTION, 61)[0])

    def test_repeat_and_cooldown(self):
        policy, state = Policy(idle_seconds=0, cooldown_seconds=10), {}
        self.assertTrue(policy.consider(state, QUESTION, 0)[0])
        policy.acknowledge(state, QUESTION, 0)
        self.assertFalse(policy.consider(state, QUESTION, 100)[0])
        self.assertFalse(policy.consider(state, "New\n" + QUESTION, 9)[0])
        self.assertTrue(policy.consider(state, "New\n" + QUESTION, 10)[0])

    def test_rolling_daily_limit(self):
        policy, state = Policy(idle_seconds=0, cooldown_seconds=0, max_per_day=1), {}
        policy.acknowledge(state, QUESTION, 0)
        self.assertFalse(policy.consider(state, "New\n" + QUESTION, 100)[0])
        self.assertTrue(policy.consider(state, "New\n" + QUESTION, 86400)[0])

    def test_old_question_outside_tail_is_ignored(self):
        self.assertFalse(classify(QUESTION + "\nprogress" * 20)[0])

    def test_clock_rollback_restarts_idle_wait(self):
        policy, state = Policy(idle_seconds=60), {}
        policy.consider(state, QUESTION, 100)
        self.assertFalse(policy.consider(state, QUESTION, 50)[0])
        self.assertEqual(state["stable_since"], 50)


def report(payload, trailer="Would you like me to continue?\n› "):
    return f"OVERSEER_REPORT {json.dumps(payload, separators=(',', ':'))}\n{trailer}"


CONTINUE_REPORT = {
    "status": "continue",
    "objective": "report loop",
    "remaining": "parse the output report",
    "done": "found the send path",
    "evidence": "policy tests",
}


class ReportPromptTests(unittest.TestCase):
    def test_continue_report_names_the_remaining_work(self):
        payload = dict(CONTINUE_REPORT, commands="UNIQUE_EXTRA_TOKEN")
        prompt, kind = next_prompt(report(payload), "Continue.")
        self.assertEqual(kind, "report-based prompt")
        self.assertIn("parse the output report", prompt)
        self.assertIn("report loop", prompt)
        self.assertIn("found the send path", prompt)
        self.assertNotIn("UNIQUE_EXTRA_TOKEN", prompt)
        self.assertNotIn("Continue.", prompt)
        self.assertLessEqual(len(prompt), 1000)
        self.assertFalse(any(ord(character) < 32 or ord(character) == 127 for character in prompt))
        self.assertNotIn("parse the output report", kind)

    def test_missing_report_uses_fallback(self):
        self.assertEqual(next_prompt(QUESTION, "Continue."), ("Continue.", "routine continuation"))

    def test_prose_mention_is_not_a_report(self):
        text = "Explain the OVERSEER_REPORT line in the README.\nOVERSEER_REPORT and a JSON object\n" + QUESTION
        self.assertEqual(next_prompt(text, "Continue."), ("Continue.", "routine continuation"))

    def test_stop_empty_and_invalid_do_not_fall_back(self):
        for status in ("done", "needs_input"):
            payload = dict(CONTINUE_REPORT, status=status)
            prompt, kind = next_prompt(report(payload), "Continue.")
            self.assertIsNone(prompt)
            self.assertEqual(kind, "output report requested no further continuation")
        blank = dict(CONTINUE_REPORT, remaining="   ")
        prompt, kind = next_prompt(report(blank), "Continue.")
        self.assertIsNone(prompt)
        self.assertEqual(kind, "report has no remaining work")
        missing = dict(CONTINUE_REPORT)
        del missing["objective"]
        prompt, kind = next_prompt(report(missing), "Continue.")
        self.assertIsNone(prompt)
        self.assertEqual(kind, "report has no remaining work")
        prompt, kind = next_prompt("OVERSEER_REPORT {not json}\n" + QUESTION, "Continue.")
        self.assertIsNone(prompt)
        self.assertEqual(kind, "invalid output report")

    def test_control_character_rejects_report(self):
        payload = dict(CONTINUE_REPORT, objective="bad\nline")
        prompt, kind = next_prompt(report(payload), "Continue.")
        self.assertIsNone(prompt)
        self.assertEqual(kind, "invalid output report")
        self.assertNotIn("bad", kind)

    def test_latest_report_wins(self):
        older = report({"status": "done", "objective": "old", "remaining": "old work", "done": "old", "evidence": "old"}, trailer="")
        newer = report(CONTINUE_REPORT)
        prompt, kind = next_prompt(older + newer, "Continue.")
        self.assertEqual(kind, "report-based prompt")
        self.assertIn("parse the output report", prompt)
        broken = older + "OVERSEER_REPORT {not json}\n" + QUESTION
        self.assertIsNone(next_prompt(broken, "Continue.")[0])

    def test_long_report_stays_one_bounded_line(self):
        payload = {
            "status": "continue",
            "objective": "o" * 5000,
            "remaining": "r" * 5000,
            "done": "d" * 5000,
            "evidence": "e" * 5000,
        }
        prompt, kind = next_prompt(report(payload), "Continue.")
        self.assertEqual(kind, "report-based prompt")
        self.assertLessEqual(len(prompt), 1000)
        self.assertNotIn("\n", prompt)

    def test_report_outside_classification_tail_is_still_read(self):
        text = report(CONTINUE_REPORT, trailer="") + ("note\n" * 30) + QUESTION
        self.assertTrue(classify(text)[0])
        prompt, kind = next_prompt(text, "Continue.")
        self.assertEqual(kind, "report-based prompt")
        self.assertIn("parse the output report", prompt)
        stopped = 'OVERSEER_REPORT {"status":"done","objective":"x","remaining":"y","done":"z","evidence":"e"}\n'
        stopped += ("note\n" * 30) + QUESTION
        self.assertTrue(classify(stopped)[0])
        self.assertEqual(next_prompt(stopped, "Continue.")[1], "output report requested no further continuation")

    def test_capacity_retry_keeps_the_configured_reply(self):
        prompt, kind = next_prompt(report(CONTINUE_REPORT), "Continue.", capacity=True)
        self.assertEqual((prompt, kind), ("Continue.", "routine continuation"))

    def test_hold_does_not_count_as_a_reply(self):
        policy, state = Policy(idle_seconds=0, cooldown_seconds=0), {}
        text = "OVERSEER_REPORT {not json}\n" + QUESTION
        self.assertTrue(policy.consider(state, text, 0)[0])
        hold(state, text, "invalid output report")
        self.assertEqual(policy.consider(state, text, 1), (False, "invalid output report"))
        self.assertNotIn("last_sent", state)
        self.assertEqual(state.get("sent_times"), [])


if __name__ == "__main__":
    unittest.main()
