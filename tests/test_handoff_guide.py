"""The writer handoff names the prompt-writing guide carried in this repository."""
from pathlib import Path
import unittest
from unittest import mock

from overseer import policy
from overseer.policy import next_prompt
from tests.test_policy import step_screen

ROOT = Path(__file__).resolve().parents[1]


class HandoffNamesTheGuideTests(unittest.TestCase):
    def test_the_guide_is_the_one_in_this_repository_and_exists(self):
        self.assertEqual(Path(policy.PROMPT_GUIDE), ROOT / 'promptwriting' / 'GUIDE.md')
        self.assertTrue(Path(policy.PROMPT_GUIDE).is_file())

    def test_the_handoff_tells_the_writer_to_follow_the_guide_by_absolute_path(self):
        prompt, kind = next_prompt(step_screen(), "Continue.")
        self.assertEqual(kind, "writer handoff prompt")
        self.assertTrue(Path(policy.PROMPT_GUIDE).is_absolute())
        self.assertIn("follow " + Path(policy.PROMPT_GUIDE).as_posix(), prompt)
        self.assertIn("prompt-writing agent", prompt)

    def test_the_handoff_stays_sendable_with_the_guide_named(self):
        prompt, _ = next_prompt(step_screen(), "Continue.")
        self.assertLessEqual(len(prompt), policy.MAX_PROMPT)
        self.assertNotIn("\n", prompt)
        self.assertIsNone(policy.BLOCKED.search(prompt))

    def test_a_missing_guide_is_not_named(self):
        missing = ROOT / 'promptwriting' / 'absent' / 'GUIDE.md'
        with mock.patch.object(policy, 'PROMPT_GUIDE', missing):
            prompt, kind = next_prompt(step_screen(), "Continue.")
        self.assertEqual(kind, "writer handoff prompt")
        self.assertNotIn("GUIDE.md", prompt)
        self.assertIn("prompt-writing agent", prompt)

    def test_a_guide_path_that_cannot_be_sent_is_not_named(self):
        with mock.patch.object(policy, 'PROMPT_GUIDE', ROOT / ('x' * 1200) / 'GUIDE.md'), \
                mock.patch.object(Path, 'is_file', return_value=True):
            prompt, kind = next_prompt(step_screen(), "Continue.")
        self.assertEqual(kind, "writer handoff prompt")
        self.assertNotIn("GUIDE.md", prompt)
        self.assertLessEqual(len(prompt), policy.MAX_PROMPT)


if __name__ == '__main__':
    unittest.main()
