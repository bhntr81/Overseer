"""Model decisions: provider failures pause a pane until the operator chooses."""
import io
import json
from argparse import Namespace
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from overseer.__main__ import main, model_select, tick
from overseer.modelchoice import detect, find_entry, footer_shows, selected_index
from overseer.policy import Policy
from overseer.scheduler import phase
from overseer.tmux import Snapshot


MODEL_ERROR = (
    '■ {"type":"error","status":400,"error":{"type":"invalid_request_error","message":'
    '"The \'gpt-6-astra\' model is not supported when using Codex with a ChatGPT account."}}\n'
    '» Ask Codex to do anything\n'
)
CREDIT_ERROR = (
    '■ {"type":"error","status":429,"error":{"message":"You have insufficient credits."}}\n'
    '» Ask Codex to do anything\n'
)
AUTH_ERROR = (
    '■ {"type":"error","status":401,"error":{"message":"unauthorized"}}\n'
    '» Ask Codex to do anything\n'
)
QUESTION = 'Would you like me to continue?\n›'
DONE = '› next step\nFinished.\nWorked for 3s • 10:00 PM\n›'
CAPACITY = '■ Selected model is at capacity. Please try a different model.\n›'


class ModelChoiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.json'
        self.screens = {pane: Snapshot(pane, 'codex', pane[1:], QUESTION, '›', '0', '0')
                        for pane in ['%0', '%1']}
        self.backend = Mock()
        self.backend.panes.side_effect = lambda: list(self.screens)
        self.backend.snapshot.side_effect = lambda pane: self.screens[pane]
        self.state = {}
        self.config = {'serial_queue': True, 'dry_run': False, 'reply': 'Continue.',
                       'capacity_retry_seconds': 10, 'capacity_max_retries': 2}
        self.policy = Policy(idle_seconds=0, cooldown_seconds=0, continue_on_completion=True)

    def run_tick(self, now):
        tick(self.backend, self.policy, self.state, self.config, self.path, now)

    def change(self, pane, text, **kwargs):
        self.screens[pane] = replace(self.screens[pane], text=text, **kwargs)

    def resolve(self, pane, key):
        target = self.path.parent / 'model-resolutions.json'
        target.write_text(json.dumps({pane: {'key': key, 'provider': 'openai',
                                             'model': 'gpt-6-luna', 'at': 1.0}}))

    def test_detects_each_provider_failure(self):
        failure = detect(MODEL_ERROR)
        self.assertEqual(failure.name, 'unsupported_model')
        self.assertEqual(failure.detail, 'gpt-6-astra')
        self.assertEqual(detect(CREDIT_ERROR).name, 'credit_exhausted')
        self.assertEqual(detect(AUTH_ERROR).name, 'auth_failed')

    def test_ordinary_text_and_capacity_are_not_failures(self):
        self.assertIsNone(detect(QUESTION))
        self.assertIsNone(detect(DONE))
        self.assertIsNone(detect(CAPACITY))
        self.assertIsNone(detect('The model is not supported by our docs, in prose.\n›'))

    def test_error_above_a_completion_footer_does_not_block(self):
        text = '› next step\n' + MODEL_ERROR + 'Worked for 3s • 10:00 PM\n›'
        self.assertEqual(phase(Snapshot('%0', 'codex', '1', text, '›', '0', '0')), 'finished')

    def test_model_failure_pauses_the_pane_and_records_the_decision(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        sent = [call.args[0].pane for call in self.backend.send.call_args_list]
        self.assertNotIn('%0', sent)
        self.assertNotIn('%0:0', self.state['_queue']['waiting'])
        record = self.state['_model_decisions']['%0']
        self.assertEqual(record['name'], 'unsupported_model')
        self.assertEqual(record['detail'], 'gpt-6-astra')
        self.assertIn('model decision pending', self.state['%0:0']['queue_reason'])

    def test_blocked_pane_releases_the_slot_for_others(self):
        self.run_tick(0)
        self.assertEqual(self.backend.send.call_count, 1)
        self.change('%0', MODEL_ERROR)
        self.run_tick(10)
        self.assertEqual(self.state['_queue']['active']['key'], '%1:1')
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')

    def test_resolved_decision_does_not_pause_the_pane_again(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        key = self.state['_model_decisions']['%0']['key']
        self.resolve('%0', key)
        self.run_tick(10)
        self.assertIn('model decision applied', self.state['%0:0']['queue_reason'])

    def test_model_select_refuses_an_unknown_provider(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        args = Namespace(pane='%0', provider='imaginary', model=None, state=self.path)
        self.assertEqual(model_select(args), 1)
        self.assertIsNone(self.state['_model_decisions']['%0'].get('resolved'))

    def test_model_select_refuses_a_model_outside_the_permitted_list(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        args = Namespace(pane='%0', provider='openai', model='gpt-imaginary', state=self.path)
        self.assertEqual(model_select(args), 1)

    def test_interactive_choice_can_be_cancelled(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        args = Namespace(pane='%0', provider=None, model=None, state=self.path)
        with patch('sys.stdin', io.StringIO('\n')):
            self.assertEqual(model_select(args), 1)
        self.assertIsNone(self.state['_model_decisions']['%0'].get('resolved'))

    def test_status_lists_the_pending_decision(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        buffer = io.StringIO()
        with patch.object(sys, 'argv', ['overseer', 'status', '--state', str(self.path)]):
            with patch('sys.stdout', buffer):
                main()
        self.assertIn('MODEL DECISION PENDING', buffer.getvalue())

    def test_picker_entry_matching(self):
        lines = ['  Select Model and Effort', '› GPT-6-Luna', '  GPT-5.6-Terra', '  GPT-5.6-Luna']
        self.assertEqual(find_entry(lines, 'gpt-6-luna'), 1)
        self.assertEqual(find_entry(lines, {'id': 'gpt-5.6-terra', 'label': 'GPT-5.6-Terra'}), 2)
        self.assertIsNone(find_entry(lines, 'gpt-imaginary'))
        self.assertEqual(selected_index(lines), 1)

    def test_footer_check(self):
        text = '  GPT-6-Luna ultra · ~/Projects/Crypto-Cooking · Main [default]'
        self.assertTrue(footer_shows(text, {'id': 'gpt-6-luna', 'label': 'GPT-6-Luna'}))
        self.assertFalse(footer_shows(text, {'id': 'gpt-6-astra', 'label': 'GPT-6-Astra'}))


if __name__ == '__main__':
    unittest.main()
