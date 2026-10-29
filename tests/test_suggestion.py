"""A Claude composer showing only its dimmed suggestion is empty (pane %2, 2026-10-29)."""
import unittest

from overseer.tmux import Snapshot, suggestion_only

LIVE = "\x1b[39m❯\xa0\x1b[2mYes to (b), no to (a): keep visible evidence only\x1b[0m"


class SuggestionTests(unittest.TestCase):
    def test_the_live_suggestion_is_only_a_suggestion(self):
        self.assertTrue(suggestion_only(LIVE))

    def test_typed_text_is_not(self):
        self.assertFalse(suggestion_only("\x1b[39m❯\xa0typed by John"))

    def test_typed_text_after_a_suggestion_is_not(self):
        self.assertFalse(suggestion_only("❯ \x1b[2mghost\x1b[0m and typed"))

    def test_an_empty_composer_has_no_suggestion(self):
        self.assertFalse(suggestion_only("❯ "))

    def test_a_reset_by_22_ends_the_dim_run(self):
        self.assertFalse(suggestion_only("❯ \x1b[2mghost\x1b[22mtyped"))

    def test_a_ready_snapshot_uses_the_bare_prompt(self):
        snapshot = Snapshot("%2", "claude", "1", "text", "❯", "0", "0", 2)
        self.assertTrue(snapshot.ready)


if __name__ == "__main__":
    unittest.main()
