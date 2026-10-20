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


STEP_REPORT = {
    "status": "step_done",
    "objective": "code the writer loop",
    "remaining": "widen the codebase selection",
    "done": "attached the memory records",
    "evidence": "250 tests pass",
}


def step_screen(payload=STEP_REPORT, marker="OVERSEER_DONE"):
    return report(payload, trailer=f"{marker}\n› ")


class WriterHandoffTests(unittest.TestCase):
    """A finished step with a named next step is handed to the prompt writer."""

    def assert_sendable(self, prompt):
        from overseer.policy import BLOCKED
        self.assertIsInstance(prompt, str)
        self.assertLessEqual(len(prompt), 1000)
        self.assertNotIn("\n", prompt)
        self.assertFalse(any(ord(char) < 32 or ord(char) == 127 for char in prompt))
        self.assertIsNone(BLOCKED.search(prompt))

    def test_a_step_done_report_yields_the_writer_handoff(self):
        prompt, kind = next_prompt(step_screen(), "Continue.")
        self.assertEqual(kind, "writer handoff prompt")
        self.assertNotEqual(prompt, "Continue.")
        for text in ("widen the codebase selection", "prompt-writing agent",
                     "ended that prompt, not the objective", "step_done",
                     "execute that prompt, verify it", "report needs_input"):
            self.assertIn(text, prompt)
        self.assert_sendable(prompt)

    def test_no_handoff_is_composed_with_an_empty_remaining(self):
        for change in ({"remaining": ""}, {"remaining": "     "}, {"remaining": None},
                       {"objective": ""}):
            payload = dict(STEP_REPORT, **change)
            self.assertEqual(next_prompt(step_screen(payload), "Continue."),
                             (None, "report has no remaining work"))
        missing = dict(STEP_REPORT)
        del missing["remaining"]
        self.assertEqual(next_prompt(step_screen(missing), "Continue."),
                         (None, "report has no remaining work"))
        no_objective = dict(STEP_REPORT)
        del no_objective["objective"]
        self.assertEqual(next_prompt(step_screen(no_objective), "Continue."),
                         (None, "report has no remaining work"))

    def test_needs_input_is_never_overridden(self):
        payload = dict(STEP_REPORT, status="needs_input")
        self.assertEqual(next_prompt(step_screen(payload, "OVERSEER_NEEDS_INPUT"), "Continue."),
                         (None, "output report requested no further continuation"))
        eligible, reason = classify(step_screen(STEP_REPORT, "OVERSEER_NEEDS_INPUT"))
        self.assertFalse(eligible)
        self.assertEqual(reason, "client requested no further automatic continuation")

    def test_a_legacy_done_report_still_stops(self):
        payload = dict(STEP_REPORT, status="done")
        screen = step_screen(payload)
        self.assertEqual(next_prompt(screen, "Continue."),
                         (None, "output report requested no further continuation"))
        self.assertFalse(classify(screen)[0])

    def test_overseer_done_after_a_step_done_report_continues(self):
        self.assertEqual(classify(step_screen()), (True, "finished step; writer handoff due"))
        stopped = "client requested no further automatic continuation"
        for screen in (step_screen(dict(STEP_REPORT, status="done")),
                       "OVERSEER_REPORT {not json}\nOVERSEER_DONE\n› ",
                       "Finished.\nOVERSEER_DONE\n› "):
            self.assertEqual(classify(screen, True, True), (False, stopped))

    def test_the_step_done_marker(self):
        from overseer.policy import STOP
        self.assertEqual(classify(step_screen(marker="OVERSEER_STEP_DONE")),
                         (True, "finished step; writer handoff due"))
        eligible, reason = classify("Finished.\nOVERSEER_STEP_DONE\n› ")
        self.assertFalse(eligible)
        self.assertNotEqual(reason, "client requested no further automatic continuation")
        self.assertIsNone(STOP.search("OVERSEER_STEP_DONE"))

    def test_blocked_text_still_wins_over_a_handoff(self):
        # The step marker would make the handoff due; the permission and
        # generation text must still block it.
        for trailer in ("Permission required: approve?\nOVERSEER_STEP_DONE\n› ",
                        "OVERSEER_STEP_DONE\n• Working (2s • esc to interrupt)\n› "):
            eligible, reason = classify(report(STEP_REPORT, trailer=trailer))
            self.assertFalse(eligible)
            self.assertEqual(reason, "active generation, permission, or sensitive action visible")

    def test_the_latest_report_wins(self):
        done = dict(STEP_REPORT, status="done")
        older_step = report(STEP_REPORT, trailer="") + report(done, trailer="OVERSEER_DONE\n› ")
        self.assertFalse(classify(older_step)[0])
        self.assertIsNone(next_prompt(older_step, "Continue.")[0])
        older_done = report(done, trailer="") + step_screen()
        self.assertTrue(classify(older_done)[0])
        self.assertEqual(next_prompt(older_done, "Continue.")[1], "writer handoff prompt")

    def test_the_handoff_loop_is_bounded(self):
        policy = Policy(idle_seconds=0, cooldown_seconds=0, max_per_day=2)
        state = {}
        screens = [step_screen(dict(STEP_REPORT, remaining="step %d" % index))
                   for index in range(3)]
        for now, screen in enumerate(screens[:2]):
            self.assertEqual(policy.consider(state, screen, now),
                             (True, "finished step; writer handoff due"))
            policy.acknowledge(state, screen, now)
        self.assertEqual(policy.consider(state, screens[1], 5),
                         (False, "already replied to this screen"))
        self.assertEqual(policy.consider(state, screens[2], 6), (False, "daily reply limit"))
        cooled = Policy(idle_seconds=0, cooldown_seconds=900, max_per_day=12)
        state = {}
        cooled.consider(state, screens[0], 0)
        cooled.acknowledge(state, screens[0], 0)
        self.assertEqual(cooled.consider(state, screens[1], 10), (False, "cooldown"))

    def test_every_prompt_states_the_loop(self):
        from pathlib import Path
        import tempfile
        from overseer.__main__ import settings
        from overseer.policy import BLOCKED, _REPORT_TAIL
        source = Path(__file__).resolve().parent.parent / "config.json"
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / "config.json"
            copy.write_text(source.read_text())
            reply = settings(copy)["reply"]
        self.assertLessEqual(len(reply), 1000)
        self.assertIsNone(BLOCKED.search(reply))
        for text in ("prompt-writing agent", "step_done", "OVERSEER_STEP_DONE",
                     "ends that prompt, not the objective",
                     "status is continue, step_done, done, or needs_input"):
            self.assertIn(text, reply)
        for text in ("step_done", "OVERSEER_STEP_DONE", "ends that prompt, not the objective",
                     "status is continue, step_done, done, or needs_input"):
            self.assertIn(text, _REPORT_TAIL)
        prompt, _ = next_prompt(report(CONTINUE_REPORT), "Continue.")
        self.assertIn("ends that prompt, not the objective", prompt)
        self.assert_sendable(prompt)

    def test_long_fields_still_fit_with_the_rule(self):
        long = {name: "x" * 5000 for name in ("objective", "remaining", "done", "evidence")}
        for status, screen in (("continue", report(dict(long, status="continue"))),
                               ("step_done", step_screen(dict(long, status="step_done")))):
            prompt, kind = next_prompt(screen, "Continue.")
            self.assertIsNotNone(prompt, status)
            self.assert_sendable(prompt)
            self.assertIn("x" * 40, prompt)
            self.assertIn("ends that prompt, not the objective", prompt)


class WriterHandoffReviewTests(unittest.TestCase):
    """The stops the first review of the handoff found open, now held."""

    def test_a_step_report_of_an_earlier_turn_never_overrides_a_stop(self):
        older = step_screen()
        screen = older + "please fix the typo and stop\nFixed. Objective complete.\nOVERSEER_DONE\n› "
        self.assertEqual(classify(screen),
                         (False, "client requested no further automatic continuation"))
        self.assertEqual(next_prompt(older + "next request\nOVERSEER_STEP_DONE\n› ", "Continue."),
                         (None, "step report belongs to an earlier turn"))

    def test_a_wrapped_echo_of_a_sent_prompt_never_starts_a_line_with_a_marker(self):
        import textwrap
        from pathlib import Path
        from overseer.policy import DONE_MARK, NEEDS_INPUT_MARK, STEP_DONE_MARK
        reply = json.loads((Path(__file__).resolve().parent.parent / "config.json").read_text())["reply"]
        prompts = [reply, next_prompt(step_screen(), "Continue.")[0],
                   next_prompt(report(CONTINUE_REPORT), "Continue.")[0]]
        for prompt in prompts:
            for width in range(30, 241):
                echo = "\n".join(textwrap.wrap(prompt, width, initial_indent="❯ ",
                                               subsequent_indent="  "))
                for mark in (DONE_MARK, NEEDS_INPUT_MARK, STEP_DONE_MARK):
                    self.assertIsNone(mark.search(echo), (width, mark.pattern))

    def test_a_quoted_step_report_followed_by_prose_does_not_override_done(self):
        screen = ("summarize the last report, then finish\n  "
                  + report(STEP_REPORT, trailer="")
                  + "Everything is finished now; the objective is complete.\nOVERSEER_DONE\n› ")
        self.assertEqual(classify(screen),
                         (False, "client requested no further automatic continuation"))

    def test_a_step_marker_of_a_new_turn_needs_a_report_of_that_turn(self):
        screen = (step_screen(marker="OVERSEER_STEP_DONE")
                  + "next request\nDone with that too.\nOVERSEER_STEP_DONE\n› ")
        self.assertFalse(classify(screen)[0])

    def test_a_needs_input_of_an_earlier_turn_does_not_stop_a_new_step(self):
        older = report(dict(STEP_REPORT, status="needs_input"), trailer="OVERSEER_NEEDS_INPUT\n› ")
        screen = older + "here is the input\n" + "detail\n" * 25 + step_screen(
            marker="OVERSEER_STEP_DONE")
        self.assertEqual(classify(screen), (True, "finished step; writer handoff due"))

    def test_needs_input_above_the_tail_still_stops(self):
        screen = report(STEP_REPORT, trailer="OVERSEER_NEEDS_INPUT\n" + "detail\n" * 25
                        + "OVERSEER_STEP_DONE\n› ")
        self.assertEqual(classify(screen),
                         (False, "client requested no further automatic continuation"))

    def test_a_step_report_without_a_marker_is_not_a_handoff(self):
        eligible, reason = classify(report(STEP_REPORT, trailer="Finished.\n› "))
        self.assertFalse(eligible)
        self.assertNotEqual(reason, "finished step; writer handoff due")

    def test_a_step_report_above_the_tail_is_read_from_the_turn(self):
        screen = report(STEP_REPORT, trailer="detail\n" * 25 + "OVERSEER_STEP_DONE\n› ")
        self.assertEqual(classify(screen), (True, "finished step; writer handoff due"))

    def test_the_handoff_names_the_objective(self):
        self.assertIn("code the writer loop", next_prompt(step_screen(), "Continue.")[0])
