import unittest

from overseer.usageguard import (
    DEFAULT_THRESHOLD_PERCENT,
    remaining_percent,
    should_wind_down,
    used_percent,
    winddown_prompt,
)


class UsedPercentTests(unittest.TestCase):
    def test_reads_the_weekly_usage_line(self):
        self.assertEqual(used_percent("You've used 75% of your weekly limit"), 75)

    def test_no_usage_line_is_unknown(self):
        self.assertIsNone(used_percent("just an ordinary pane with no usage line"))

    def test_the_most_constrained_limit_wins(self):
        text = ("You've used 40% of your weekly limit\n"
                "You've used 96% of your session limit\n")
        self.assertEqual(used_percent(text), 96)

    def test_ansi_escapes_are_stripped_before_matching(self):
        text = "\x1b[2mYou've used \x1b[1m88%\x1b[0m of your weekly limit\x1b[0m"
        self.assertEqual(used_percent(text), 88)

    def test_a_percent_over_one_hundred_is_clamped(self):
        self.assertEqual(used_percent("used 120% of your weekly limit"), 100)

    def test_only_the_last_64_kib_is_considered(self):
        far = "You've used 99% of your weekly limit\n"
        text = far + ("x" * (64 * 1024)) + "\nno usage here at the end\n"
        self.assertIsNone(used_percent(text))

    def test_matches_a_five_hour_limit_phrasing(self):
        self.assertEqual(used_percent("You've used 97% of your 5-hour limit"), 97)


class RemainingPercentTests(unittest.TestCase):
    def test_remaining_is_the_complement_of_used(self):
        self.assertEqual(remaining_percent("used 95% of your weekly limit"), 5)

    def test_remaining_is_unknown_without_a_usage_line(self):
        self.assertIsNone(remaining_percent("nothing to see"))


class ShouldWindDownTests(unittest.TestCase):
    def test_winds_down_at_the_threshold(self):
        self.assertTrue(should_wind_down("used 95% of your weekly limit"))

    def test_winds_down_past_the_threshold(self):
        self.assertTrue(should_wind_down("used 99% of your weekly limit"))

    def test_does_not_wind_down_with_room_to_spare(self):
        self.assertFalse(should_wind_down("used 75% of your weekly limit"))

    def test_unknown_usage_never_winds_down(self):
        self.assertFalse(should_wind_down("no usage line present at all"))

    def test_a_custom_threshold_is_respected(self):
        text = "used 85% of your weekly limit"
        self.assertFalse(should_wind_down(text, threshold_percent=5))
        self.assertTrue(should_wind_down(text, threshold_percent=20))

    def test_the_default_threshold_is_five_percent(self):
        self.assertEqual(DEFAULT_THRESHOLD_PERCENT, 5)


class WindDownPromptTests(unittest.TestCase):
    def test_the_prompt_is_a_nonempty_single_line_instruction(self):
        prompt = winddown_prompt()
        self.assertIsInstance(prompt, str)
        self.assertTrue(prompt.strip())
        self.assertNotIn("\n", prompt)

    def test_the_prompt_tells_the_worker_to_stop_not_start_new_work(self):
        prompt = winddown_prompt().lower()
        self.assertIn("stop", prompt)
        self.assertTrue("do not start" in prompt or "don't start" in prompt)


if __name__ == "__main__":
    unittest.main()
