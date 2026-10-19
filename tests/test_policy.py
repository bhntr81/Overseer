import unittest

from overseer.policy import Policy, classify


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


if __name__ == "__main__":
    unittest.main()
