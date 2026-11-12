"""Model decisions: provider failures pause a pane until the operator chooses."""
import io
import json
import os
import shutil
from argparse import Namespace
from dataclasses import replace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from overseer.__main__ import main, model_select, tick
from overseer.modelchoice import (
    detect, effort_screen, fallback_chain, find_entry, footer_shows, model_id, navigation,
    next_hop, picker_block, providers, selected_index,
)
from overseer.policy import Policy
from overseer.scheduler import phase
from overseer.tmux import Snapshot, Tmux

CONVERSATION = [
    '› Overseer workflow adoption check, authorized by the user. Read the instructions.',
    'Worked for 3s • 10:00 PM',
]
COMPOSER = '› Ask Codex to do anything'
PICKER = [
    '  Select Model and Effort',
    '',
    '› 1. GPT-6-Luna     Fast and affordable model for easier tasks.',
    '  2. GPT-5.6-Terra  Older balanced model for straightforward work.',
    '  3. GPT-5.6-Luna   Older fast and efficient model.',
    '',
    '  enter select · esc back',
]
EFFORT = [
    '  Select Reasoning Level for GPT-5.6-Terra',
    '',
    '  1. Low               Fast responses with lighter reasoning',
    '› 2. Medium (default)  Balances speed and reasoning depth for everyday tasks',
    '  3. High              Greater reasoning depth for complex problems',
    '',
    '  enter default · s session · esc back',
]
APPLIED = [
    '• Model changed to gpt-5.6-terra medium for this session only',
    '  GPT-5.6-Terra medium · ~/Projects/clubwpt-ocr · Main [default]',
    COMPOSER,
]
# An OpenCode screen while a turn runs, and the same screen once it ended.
OPENCODE_RUNNING = [
    ' ⠹ AGENTS and PLAYBOOK authorize +',
    '  ┃',
    '  ┃  $ curl -sSL https://example.com',
    '     ⠋ General Subagent - Verify details',
    '     Press ctrl+b to move running work to the background',
    '  ┃',
    '  ┃',
    '  ┃',
    '  ┃  Build · MiniMax M3.1 Flash Free OpenCode',
    '  ╹▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀',
    '   ■■■⬝⬝⬝ esc interrupt         ↓ 1 subagent · 134.6K (13%)  ctrl+p commands',
]
OPENCODE_RUNNING_CURSOR = 6
OPENCODE_IDLE = [
    '  ┃',
    '  ┃',
    '  ┃',
    '  ┃  Build · MiniMax M3.1 Flash Free OpenCode',
    '  ╹' + '▀' * 40,
    '   ~/Projects/Crypto-Cooking                      207.1K (21%)  ctrl+p commands',
]
OPENCODE_IDLE_CURSOR = 1
OPENCODE_FRESH = [
    '  ┃',
    '  ┃  Ask anything… "Fix broken tests"',
    '  ┃',
    '  ┃  Build · MiniMax M3.1 Flash Free OpenCode',
    '  ╹' + '▀' * 40,
    '   ~/Projects/Crypto-Cooking                 shift+tab agents  ctrl+p commands',
]
OPENCODE_FRESH_CURSOR = 1


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
        # The live config.json is local and ignored: run against the public example.
        shutil.copyfile(Path(__file__).resolve().parent.parent / 'config.example.json',
                        Path(self.tmp.name) / 'config.json')
        root = patch('overseer.__main__.ROOT', Path(self.tmp.name))
        root.start()
        self.addCleanup(root.stop)
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
        # Hermetic: the pane is a codex client, so the model check is reached; no live
        # tmux server is contacted and nothing can be routed.
        pane_backend = Mock()
        pane_backend.inspect.return_value = self.screens['%0']
        with patch('overseer.__main__.Tmux', return_value=pane_backend), \
                patch('overseer.__main__.resolve_route') as route:
            self.assertEqual(model_select(args), 1)
        route.assert_not_called()
        self.assertIsNone(self.state['_model_decisions']['%0'].get('resolved'))

    def test_interactive_choice_can_be_cancelled(self):
        self.change('%0', MODEL_ERROR)
        self.run_tick(0)
        args = Namespace(pane='%0', provider=None, model=None, state=self.path)
        with patch('sys.stdin', io.StringIO('\n')):
            self.assertEqual(model_select(args), 1)
        self.assertIsNone(self.state['_model_decisions']['%0'].get('resolved'))

    @unittest.skipIf(os.name == 'nt', 'drives the tmux monitor command line, which native Windows refuses')
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

    def test_excluded_model_is_never_offered(self):
        config = {
            'model_providers': {'openai': {'client': 'codex', 'label': 'OpenAI Codex', 'models': [
                {'id': 'gpt-6-luna', 'label': 'GPT-6-Luna'},
                {'id': 'gpt-5.6-terra', 'label': 'GPT-5.6-Terra'}]}},
            'allowed_providers': ['openai'],
            'fallback_policy': {'excluded_models': ['gpt-6-luna']},
        }
        offered = [model_id(model) for model in providers(config)[0]['models']]
        self.assertEqual(offered, ['gpt-5.6-terra'])

    def test_fallback_chain_starts_at_the_zero_credit_tier(self):
        config = {
            'model_providers': {
                'openai': {'client': 'codex', 'label': 'OpenAI Codex', 'models': ['gpt-5.6-terra']},
                'opencode': {'client': 'opencode', 'label': 'OpenCode', 'models': ['opencode/free']},
            },
            'fallback_policy': {'primary': ['claude', 'openai'], 'zero_credit': ['opencode']},
        }
        self.assertEqual(fallback_chain(config, 'credit_exhausted'), ['opencode'])
        self.assertEqual(fallback_chain(config, 'unsupported_model'), ['claude', 'openai'])
        self.assertEqual(next_hop(config, 'credit_exhausted', 'codex'), 'opencode')
        self.assertIsNone(next_hop(config, 'credit_exhausted', 'opencode'))

    def test_credit_failure_routes_to_the_zero_credit_tier_once(self):
        self.config['model_providers'] = {'opencode': {'client': 'opencode', 'label': 'OpenCode',
                                                       'models': [{'id': 'opencode/free', 'label': 'free'}]}}
        self.config['allowed_providers'] = ['opencode']
        self.config['fallback_policy'] = {'primary': ['openai'], 'zero_credit': ['opencode'],
                                          'excluded_models': ['gpt-6-luna'],
                                          'exhausted_status': 'CREDITS_EXHAUSTED_WAITING'}
        self.change('%0', CREDIT_ERROR)
        moved = {'pane': '%9', 'session': 'session-opencode', 'client': 'opencode',
                 'provider': 'opencode', 'directory': '/tmp/project', 'model': 'default'}
        with patch('overseer.scheduler.resolve_route', return_value=moved) as routed:
            self.run_tick(0)
            self.run_tick(10)
        routed.assert_called_once()
        self.assertEqual(self.state['_model_decisions']['%0']['resolved']['provider'], 'opencode')
        self.assertIn('routed to opencode', self.state['%0:0']['queue_reason'])
        self.assertTrue(self.state['_routes']['%9']['resume'])
        sent = [call.args[0].pane for call in self.backend.send.call_args_list]
        self.assertNotIn('%0', sent)

    def test_credit_failure_in_the_last_tier_waits(self):
        self.config['model_providers'] = {'opencode': {'client': 'opencode', 'label': 'OpenCode',
                                                       'models': [{'id': 'opencode/free', 'label': 'free'}]}}
        self.config['allowed_providers'] = ['opencode']
        self.config['fallback_policy'] = {'primary': ['openai'], 'zero_credit': ['opencode'],
                                          'excluded_models': ['gpt-6-luna'],
                                          'exhausted_status': 'CREDITS_EXHAUSTED_WAITING'}
        self.change('%0', CREDIT_ERROR, process='opencode',
                    cursor_line='┃  Ask anything… "Fix broken tests"')
        self.run_tick(0)
        self.assertEqual(self.state['%0:0']['queue_reason'], 'CREDITS_EXHAUSTED_WAITING')
        self.assertIsNone(self.state['_model_decisions']['%0']['resolved'])
        sent = [call.args[0].pane for call in self.backend.send.call_args_list]
        self.assertNotIn('%0', sent)
        self.run_tick(1000)
        self.assertEqual(self.state['%0:0']['queue_reason'], 'CREDITS_EXHAUSTED_WAITING')

    def test_opencode_composer_readiness(self):
        fresh = Snapshot('%0', 'opencode', '1', 'text', '┃  Ask anything… "Fix broken tests"', '0', '0')
        self.assertTrue(fresh.ready)
        # A finished turn leaves the composer box blank, not placeholdered.
        finished = Snapshot('%0', 'opencode', '1', 'text', '┃', '0', '0')
        self.assertTrue(finished.ready)
        draft = Snapshot('%0', 'opencode', '1', 'text', '┃  x', '0', '0')
        self.assertFalse(draft.ready)

    def test_picker_block_ignores_conversation_lines(self):
        screen = CONVERSATION + PICKER
        block = picker_block(screen)
        self.assertEqual(len(block), 5)
        self.assertEqual(find_entry(block, 'gpt-5.6-terra'), 2)
        self.assertEqual(selected_index(block), 1)
        self.assertNotIn('workflow adoption', ' '.join(block))

    def test_effort_screen_is_detected(self):
        self.assertTrue(effort_screen('\n'.join(CONVERSATION + EFFORT)))
        self.assertFalse(effort_screen('\n'.join(CONVERSATION + PICKER)))

    def test_navigation_reaches_the_target_from_either_side(self):
        self.assertEqual(navigation(2, 2), ('Down', 0))
        self.assertEqual(navigation(3, 1), ('Down', 2))
        self.assertEqual(navigation(1, 3), ('Up', 2))

    def test_driver_selects_the_model_and_applies_it_to_the_session(self):
        backend = Tmux()
        state = {'phase': 'start', 'keys': []}

        def fake(*args):
            if args[0] == 'capture-pane':
                return {'start': '\n'.join(CONVERSATION + [COMPOSER]),
                        'picker': '\n'.join(CONVERSATION + PICKER),
                        'effort': '\n'.join(CONVERSATION + EFFORT),
                        'applied': '\n'.join(CONVERSATION + APPLIED)}[state['phase']]
            if args[0] == 'display-message':
                return '\t'.join(['%4', 'codex', '1234', str(len(CONVERSATION)), '0', '0', '1', '2', ''])
            if args[0] == 'send-keys':
                key = args[-1]
                state['keys'].append(key)
                if key == '/model':
                    state['phase'] = 'typed'
                elif key == 'Enter' and state['phase'] == 'typed':
                    state['phase'] = 'picker'
                elif key == 'Enter' and state['phase'] == 'picker':
                    state['phase'] = 'effort'
                elif key == 's':
                    state['phase'] = 'applied'
            return ''

        with patch('overseer.tmux.command', side_effect=fake):
            reported = backend.select_model('%4', 'gpt-5.6-terra')
        self.assertEqual(reported, 'GPT-5.6-Terra medium')
        self.assertEqual(state['keys'], ['/model', 'Enter', 'Down', 'Enter', 's'])

    def test_driver_refuses_a_model_the_picker_does_not_offer(self):
        backend = Tmux()
        state = {'phase': 'start', 'keys': []}

        def fake(*args):
            if args[0] == 'capture-pane':
                return {'start': '\n'.join(CONVERSATION + [COMPOSER]),
                        'picker': '\n'.join(CONVERSATION + PICKER)}[state['phase']]
            if args[0] == 'display-message':
                return '\t'.join(['%4', 'codex', '1234', str(len(CONVERSATION)), '0', '0', '1', '2', ''])
            if args[0] == 'send-keys':
                key = args[-1]
                state['keys'].append(key)
                if key == '/model':
                    state['phase'] = 'typed'
                elif key == 'Enter' and state['phase'] == 'typed':
                    state['phase'] = 'picker'
            return ''

        with patch('overseer.tmux.command', side_effect=fake):
            with self.assertRaisesRegex(RuntimeError, 'does not offer'):
                backend.select_model('%4', 'gpt-imaginary')
        self.assertIn('Escape', state['keys'])
        self.assertNotIn('Down', state['keys'])
        self.assertNotIn('s', state['keys'])

    def opencode_screen(self, lines, cursor, pane='%0'):
        return Snapshot(pane, 'opencode', '7', '\n'.join(lines), lines[cursor],
                        '0', '0', 6)

    def test_opencode_running_turn_is_active(self):
        screen = self.opencode_screen(OPENCODE_RUNNING, OPENCODE_RUNNING_CURSOR)
        self.assertEqual(phase(screen), 'active')

    def test_opencode_finished_turn_is_finished(self):
        screen = self.opencode_screen(OPENCODE_IDLE, OPENCODE_IDLE_CURSOR)
        self.assertEqual(phase(screen), 'finished')
        fresh = self.opencode_screen(OPENCODE_FRESH, OPENCODE_FRESH_CURSOR)
        self.assertEqual(phase(fresh), 'finished')

    def test_opencode_turn_releases_the_reservation(self):
        idle = self.opencode_screen(OPENCODE_IDLE, OPENCODE_IDLE_CURSOR)
        running = self.opencode_screen(OPENCODE_RUNNING, OPENCODE_RUNNING_CURSOR)
        self.screens['%0'] = idle
        # A turn has already run, so the finished pane is eligible again.
        self.state['%0:7'] = {'ran_turn': True}
        self.run_tick(0)
        self.assertEqual(self.backend.send.call_count, 1)
        self.assertEqual(self.state['_queue']['active']['key'], '%0:7')
        self.screens['%0'] = running
        self.run_tick(10)
        self.screens['%0'] = idle
        self.run_tick(1000)
        # The finished OpenCode pane released the slot; the other pane took it.
        self.assertEqual(self.state['_queue']['active']['key'], '%1:1')

    def test_opencode_pane_is_not_answered_while_it_runs(self):
        self.screens['%0'] = self.opencode_screen(OPENCODE_RUNNING, OPENCODE_RUNNING_CURSOR)
        self.state['%0:7'] = {'ran_turn': True}
        self.run_tick(0)
        sent = [call.args[0].pane for call in self.backend.send.call_args_list]
        self.assertNotIn('%0', sent)


if __name__ == '__main__':
    unittest.main()
