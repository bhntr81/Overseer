import unittest
from unittest.mock import patch

from overseer.policy import classify
from overseer.tmux import Snapshot, Tmux, matches


class ExclusionTests(unittest.TestCase):
    def test_labels_globs_and_exact_panes(self):
        values = ("%10", "overseer-kali-123", "Create hands-on red-team labs | kali")
        self.assertTrue(matches("labs", values))
        self.assertTrue(matches("*LABS*", values))
        self.assertTrue(matches("%10", values))
        self.assertFalse(matches("%1", values))
        self.assertFalse(matches("solver", values))

    def test_excluded_pane_is_never_sent_to(self):
        backend = Tmux(["labs"])
        # pane, enrolled, session, title, bridge binding, pane path
        inventory = "%0\t1\tsolver\tSolver\t\t/tmp/solver\n%1\t1\tkali\tKali labs\t\t/tmp/kali\n"
        with patch("overseer.tmux.command", return_value=inventory) as command:
            self.assertEqual(backend.panes(), ["%0"])
            with self.assertRaisesRegex(RuntimeError, "excluded"):
                backend.send(Snapshot("%1", "codex", "123", "", "›", "0", "0"), "Continue")
            self.assertTrue(all(call.args[0] == "list-panes" for call in command.call_args_list))

    def test_completed_turn_is_explicitly_configurable(self):
        screen = "Finished this step.\nWorked for 1m 15s • 7:59 PM\n› Ask Codex to do anything"
        self.assertFalse(classify(screen)[0])
        self.assertTrue(classify(screen, True)[0])
        self.assertFalse(classify("OVERSEER_DONE\n" + screen, True)[0])
        self.assertFalse(classify("• OVERSEER_NEEDS_INPUT\n" + screen, True)[0])

    def test_placeholder_requires_cursor_at_start(self):
        args = ("%0", "codex", "123", "", "› Ask Codex to do anything", "0", "0")
        self.assertTrue(Snapshot(*args, cursor_x=2).ready)
        self.assertFalse(Snapshot(*args, cursor_x=25).ready)
