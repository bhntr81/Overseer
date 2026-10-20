"""Explicit project targeting: only scoped panes are managed."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from overseer.__main__ import settings
from overseer.tmux import Tmux, client_directory, under


WORKSPACE = str(Path(__file__).resolve().parents[1])
BINDING = f"{os.getpid()}:0"


def inventory(rows):
    """Return a fake tmux command that answers list-panes."""
    def fake(*args):
        if args[0] == 'list-panes':
            return "".join("\t".join(str(field) for field in row) + "\n" for row in rows)
        return ''
    return fake


def row(pane, enabled, session, title, binding='', path='/tmp/elsewhere'):
    return (pane, enabled, session, title, binding, path)


class ScopeTests(unittest.TestCase):
    def test_enrolled_pane_is_managed(self):
        backend = Tmux()
        with patch('overseer.tmux.command', side_effect=inventory([row('%0', '1', 's', 't')])):
            self.assertEqual(backend.panes(), ['%0'])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'WATCHED')

    def test_untargeted_pane_is_ignored(self):
        backend = Tmux()
        with patch('overseer.tmux.command', side_effect=inventory([row('%0', '0', 'other', 'Other')])):
            self.assertEqual(backend.panes(), [])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'OUT OF SCOPE')

    def test_targeted_pane_is_managed_without_enrollment(self):
        backend = Tmux(targets=['other'])
        with patch('overseer.tmux.command', side_effect=inventory([row('%0', '0', 'other', 'Other')])):
            self.assertEqual(backend.panes(), ['%0'])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'TARGETED')

    def test_target_matches_pane_id_and_title(self):
        backend = Tmux(targets=['%3', 'Review BOOM'])
        rows = [row('%3', '0', 'a', 'x'), row('%4', '0', 'b', 'Review BOOM mentions')]
        with patch('overseer.tmux.command', side_effect=inventory(rows)):
            self.assertEqual(backend.panes(), ['%3', '%4'])

    def test_target_glob_matches(self):
        backend = Tmux(targets=['overseer-*'])
        rows = [row('%0', '0', 'overseer-one', 'x'), row('%1', '0', 'other', 'y')]
        with patch('overseer.tmux.command', side_effect=inventory(rows)):
            self.assertEqual(backend.panes(), ['%0'])

    def test_path_scope_uses_the_client_directory(self):
        backend = Tmux(target_paths=[os.getcwd()])
        rows = [row('%0', '0', 'other', 'Other', BINDING, '/tmp/elsewhere')]
        with patch('overseer.tmux.command', side_effect=inventory(rows)):
            self.assertEqual(backend.panes(), ['%0'])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'TARGETED')

    def test_path_scope_ignores_a_client_outside_it(self):
        backend = Tmux(target_paths=[os.getcwd() + '-elsewhere'])
        rows = [row('%0', '0', 'other', 'Other', BINDING, '/tmp/elsewhere')]
        with patch('overseer.tmux.command', side_effect=inventory(rows)):
            self.assertEqual(backend.panes(), [])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'OUT OF SCOPE')

    def test_exclusion_wins_over_a_target(self):
        backend = Tmux(exclusions=['other'], targets=['other'])
        with patch('overseer.tmux.command', side_effect=inventory([row('%0', '0', 'other', 'Other')])):
            self.assertEqual(backend.panes(), [])
            self.assertEqual(backend.scope(backend.inventory()[0]), 'EXCLUDED')

    def test_exclusion_wins_over_enrollment(self):
        backend = Tmux(exclusions=['%0'])
        with patch('overseer.tmux.command', side_effect=inventory([row('%0', '1', 's', 't')])):
            self.assertEqual(backend.panes(), [])

    def test_transport_refuses_to_send_to_an_unscoped_pane(self):
        backend = Tmux()
        pane = row('%0', '0', 'other', 'Other')
        with patch('overseer.tmux.command', side_effect=inventory([pane])):
            with self.assertRaisesRegex(RuntimeError, 'excluded or no longer watched'):
                backend.send(type('S', (), {'pane': '%0'})(), 'Continue.')

    def test_a_targeted_pane_may_be_read_and_written(self):
        backend = Tmux(targets=['other'])
        rows = [row('%0', '0', 'other', 'Other')]
        metadata = "%0\tcodex\t123\t1\t0\t0\t0\t2\t\n"

        def fake(*args):
            if args[0] == 'list-panes':
                return inventory(rows)(*args)
            if args[0] == 'display-message':
                return metadata
            if args[0] == 'capture-pane':
                return 'Would you like me to continue?\n›\n'
            return ''

        with patch('overseer.tmux.command', side_effect=fake):
            self.assertEqual(backend.panes(), ['%0'])
            snapshot = backend.snapshot('%0')
        self.assertEqual(snapshot.pane, '%0')
        self.assertTrue(snapshot.ready)

    def test_under_rejects_a_sibling_directory(self):
        self.assertTrue(under('/home/kali/Projects/Overseer', '/home/kali/Projects'))
        self.assertFalse(under('/home/kali/Projects/Overseer2', '/home/kali/Projects/Overseer'))
        self.assertFalse(under('', '/home/kali/Projects'))

    def test_client_directory_prefers_the_bridged_client(self):
        self.assertEqual(client_directory('%0', BINDING, '/tmp/elsewhere'), os.getcwd())
        self.assertEqual(client_directory('%0', '', '/tmp/elsewhere'), '/tmp/elsewhere')

    def test_settings_resolve_a_relative_target_path(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.json'
            path.write_text(json.dumps({"poll_seconds": 30, "idle_seconds": 1, "cooldown_seconds": 1,
                                        "max_per_day": 1, "dry_run": True, "target_paths": ["."]}))
            config = settings(path)
        self.assertEqual(config['target_paths'], [str(Path(directory).resolve())])

    def test_settings_reject_a_malformed_scope(self):
        for key, value in (("targets", "not-a-list"), ("target_paths", [1])):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'config.json'
                path.write_text(json.dumps({"poll_seconds": 30, "idle_seconds": 1, "cooldown_seconds": 1,
                                            "max_per_day": 1, "dry_run": True, key: value}))
                with self.assertRaises(ValueError):
                    settings(path)


if __name__ == '__main__':
    unittest.main()
