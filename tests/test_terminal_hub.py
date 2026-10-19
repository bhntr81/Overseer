import json
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class HubLauncherTests(unittest.TestCase):
    def launch(self, sessions):
        config = {'session': 'solver', 'labels': {'solver': 'Solver', 'club': 'Club'}}
        def run(args, **kwargs):
            output = '\n'.join(sessions) if args[:2] == ['tmux', 'list-sessions'] else ''
            return SimpleNamespace(stdout=output)
        with patch.object(Path, 'read_text', return_value=json.dumps(config)), \
             patch('subprocess.run', side_effect=run), patch('subprocess.Popen') as popen, \
             patch.object(sys, 'argv', ['terminal-hub']), patch.object(sys, 'path', [str(ROOT/'scripts'), *sys.path]):
            runpy.run_path(str(ROOT/'scripts/terminal-hub'), run_name='__main__')
            return popen.call_args.args[0]

    def test_prefers_saved_session(self):
        self.assertEqual(self.launch(['solver', 'club'])[-1], '=solver')

    def test_surviving_project_fallback(self):
        self.assertEqual(self.launch(['club'])[-1], '=club')

    def test_no_projects_does_not_start_agents(self):
        with self.assertRaisesRegex(SystemExit, 'No existing Overseer'):
            self.launch(['unrelated'])
