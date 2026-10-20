import json
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from overseer.__main__ import tick
from overseer.policy import Policy
from overseer.scheduler import phase
from overseer.tmux import Snapshot

QUESTION = 'Would you like me to continue?\n›'
DONE = '› next step\nFinished.\nWorked for 3s • 10:00 PM\n›'
ERROR = '› next step\n■ Selected model is at capacity. Please try a different model.\n›'
BUSY = '› next step\n• Working (2s • esc to interrupt)\n›'


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.json'
        self.screens = {p: Snapshot(p, 'codex', p[1:], QUESTION, '›', '0', '0') for p in ['%0', '%1']}
        self.backend = Mock()
        self.backend.panes.side_effect = lambda: list(self.screens)
        self.backend.snapshot.side_effect = lambda p: self.screens[p]
        self.state = {}
        self.config = {'serial_queue': True, 'dry_run': False, 'reply': 'Continue.',
                       'capacity_retry_seconds': 10, 'capacity_max_retries': 2}
        self.policy = Policy(idle_seconds=0, cooldown_seconds=0, continue_on_completion=True)

    def run_tick(self, now):
        tick(self.backend, self.policy, self.state, self.config, self.path, now)

    def change(self, pane, text, **kwargs):
        self.screens[pane] = replace(self.screens[pane], text=text, **kwargs)

    def test_fifo_restart_and_unchanged_screen(self):
        self.run_tick(0)
        self.assertEqual(self.backend.send.call_count, 1)
        self.assertEqual(self.state['_queue']['waiting'], ['%1:1'])
        self.state = json.loads(self.path.read_text())
        self.run_tick(1000)
        self.assertEqual(self.backend.send.call_count, 1)
        self.change('%0', DONE)
        self.run_tick(1001)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.assertEqual(self.state['_queue']['waiting'], ['%0:0'])

    def test_busy_pane_later_in_inventory_blocks_dispatch(self):
        self.change('%1', BUSY)
        self.run_tick(0)
        self.backend.send.assert_not_called()
        self.change('%1', DONE)
        self.run_tick(1)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%0')

    def test_ambiguous_send_reserves_slot(self):
        self.backend.send.side_effect = RuntimeError('uncertain')
        self.run_tick(0)
        self.run_tick(2000)
        self.assertEqual(self.backend.send.call_count, 1)
        self.assertEqual(self.state['_queue']['active']['key'], '%0:0')

    def test_capacity_backoff_and_budget_across_restart(self):
        self.change('%0', ERROR)
        self.run_tick(0)
        self.backend.send.assert_not_called()
        self.run_tick(10)
        self.assertEqual(self.backend.send.call_count, 1)
        self.change('%0', '› retry\n• Read project instructions\n' + ERROR.split('\n', 1)[1])
        self.state = json.loads(self.path.read_text())
        self.run_tick(11)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.change('%1', 'OVERSEER_DONE\n' + DONE)
        self.run_tick(21)
        self.assertEqual(self.backend.send.call_count, 3)
        self.change('%0', '› retry\n• Read project instructions again\n' + ERROR.split('\n', 1)[1])
        self.run_tick(22)
        self.assertIsNone(self.state['_queue']['active'])
        self.assertIn('capacity retry limit', self.state['%0:0']['queue_reason'])
        self.run_tick(1000)
        self.assertEqual(self.backend.send.call_count, 3)

    def test_stop_draft_and_disappearing_active(self):
        self.run_tick(0)
        del self.screens['%0']
        self.change('%1', 'OVERSEER_NEEDS_INPUT\n' + QUESTION)
        self.run_tick(1)
        self.assertEqual(self.state['_queue']['waiting'], [])
        self.assertIsNone(self.state['_queue']['active'])
        self.change('%1', QUESTION, cursor_line='› draft')
        self.run_tick(2)
        self.assertEqual(self.backend.send.call_count, 1)

    def test_pid_replacement_does_not_inherit_slot(self):
        self.run_tick(0)
        self.change('%0', QUESTION, pid='new')
        self.run_tick(1)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.assertEqual(self.state['_queue']['waiting'], ['%0:new'])

    def test_dry_run_does_not_consume_budget(self):
        self.config['dry_run'] = True
        self.run_tick(0)
        self.backend.send.assert_not_called()
        self.assertNotIn('last_sent', self.state['%0:0'])
        self.assertIsNone(self.state['_queue']['active'])

    def test_observation_failure_blocks_dispatch(self):
        self.backend.snapshot.side_effect = RuntimeError('capture failed')
        self.run_tick(0)
        self.backend.send.assert_not_called()

    def test_missing_process_does_not_block_other_panes(self):
        errors = (
            FileNotFoundError(2, 'No such file or directory', '/proc/1174383/stat'),
            ProcessLookupError(3, 'No such process'),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.backend.send.reset_mock()
                self.state.clear()
                self.state['%0:1174383:5806804'] = {}

                def snapshot(pane, failure=error):
                    if pane == '%0':
                        raise failure
                    return self.screens[pane]

                self.backend.snapshot.side_effect = snapshot
                self.run_tick(0)
                self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
                self.assertEqual(self.backend.send.call_args.args[1], 'Continue.')
                self.assertEqual(self.state['%0:1174383:5806804']['queue_reason'], 'dead or stale process')

    def test_other_observation_error_still_blocks_live_panes(self):
        def snapshot(pane):
            if pane == '%0':
                raise RuntimeError('capture failed')
            return self.screens[pane]

        self.backend.snapshot.side_effect = snapshot
        self.run_tick(0)
        self.backend.send.assert_not_called()

    def test_capacity_history_and_prose_are_not_active(self):
        s = self.screens['%0']
        self.assertEqual(phase(replace(s, text=ERROR + '\n› new question\n' + DONE)), 'finished')
        self.assertEqual(phase(replace(s, text='The system is working.\n' + DONE)), 'finished')
        self.assertEqual(phase(replace(s, text=BUSY)), 'active')

    def test_stop_outside_tail_and_permission_after_capacity_do_not_send(self):
        self.change('%0', '› task\nOVERSEER_DONE\n' + 'details\n' * 25 + 'Worked for 1s • now\n›')
        self.change('%1', ERROR + '\nPermission required: approve deployment?')
        self.run_tick(0)
        self.run_tick(1000)
        self.backend.send.assert_not_called()

    def test_daily_limit_applies_to_capacity(self):
        self.change('%0', ERROR)
        self.policy.max_per_day = 1
        self.state['%0:0'] = {'sent_times': [0]}
        self.run_tick(0)
        self.backend.send.assert_not_called()
        self.assertEqual(self.state['%0:0']['queue_reason'], 'waiting for idle threshold')
        self.run_tick(10)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.assertEqual(self.state['%0:0']['queue_reason'], 'daily reply limit')

    def test_other_pane_starting_during_recheck_prevents_send(self):
        calls = {'%0': 0, '%1': 0}
        def snapshot(p):
            calls[p] += 1
            if p == '%1' and calls[p] == 2:
                return replace(self.screens[p], text=BUSY)
            return self.screens[p]
        self.backend.snapshot.side_effect = snapshot
        self.run_tick(0)
        self.backend.send.assert_not_called()

    def test_reservation_written_before_delivery(self):
        def check(s, reply):
            saved = json.loads(self.path.read_text())
            self.assertEqual(saved['_queue']['active']['key'], '%0:0')
            self.assertEqual(saved['%0:0']['last_sent'], 0)
        self.backend.send.side_effect = check
        self.run_tick(0)

    def test_new_routine_question_without_codex_footer_releases(self):
        self.run_tick(0)
        self.change('%0', '› Continue.\nVerified step one.\n' + QUESTION)
        self.run_tick(1)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')

    def test_ui_tip_change_does_not_release_capacity_slot(self):
        self.change('%0', ERROR)
        self.run_tick(0)
        self.run_tick(10)
        self.change('%0', ERROR + '\nTip: new tip')
        self.run_tick(20)
        self.assertEqual(self.backend.send.call_count, 1)

    def test_queue_sends_prompt_built_from_report(self):
        report = (
            'OVERSEER_REPORT {"status":"continue","objective":"report loop",'
            '"remaining":"parse the output report","done":"found the send path",'
            '"evidence":"queue test"}\n' + QUESTION
        )
        self.change('%0', report)
        self.change('%1', 'OVERSEER_DONE\n' + QUESTION)
        self.run_tick(0)
        self.backend.send.assert_called_once()
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%0')
        sent = self.backend.send.call_args.args[1]
        self.assertIn('parse the output report', sent)
        self.assertNotEqual(sent, 'Continue.')
        self.assertLessEqual(len(sent), 1000)
        self.assertNotIn('\n', sent)

    def test_invalid_report_does_not_take_the_queue_slot(self):
        self.change('%0', 'OVERSEER_REPORT {not json}\n' + QUESTION)
        self.run_tick(0)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.assertEqual(self.backend.send.call_args.args[1], 'Continue.')
        self.assertNotIn('last_sent', self.state['%0:0'])
        self.assertEqual(self.state['%0:0']['held_reason'], 'invalid output report')

    def test_done_report_does_not_send(self):
        self.change('%0', 'OVERSEER_REPORT {"status":"needs_input","objective":"x","remaining":"y","done":"z","evidence":"e"}\n' + QUESTION)
        self.run_tick(0)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
        self.assertEqual(self.state['%0:0']['queue_reason'], 'output report requested no further continuation')

    def test_capacity_retry_keeps_configured_reply(self):
        self.change('%0', 'OVERSEER_REPORT {"status":"continue","objective":"o","remaining":"should-not-use-this","done":"d","evidence":"e"}\n' + ERROR)
        self.change('%1', 'OVERSEER_DONE\n' + QUESTION)
        self.run_tick(0)
        self.backend.send.assert_not_called()
        self.run_tick(10)
        self.assertEqual(self.backend.send.call_args.args[1], 'Continue.')
        self.assertNotIn('should-not-use-this', self.backend.send.call_args.args[1])

    def test_observed_running_then_identical_capacity_releases(self):
        self.change('%0', ERROR)
        self.run_tick(0)
        self.run_tick(10)
        self.change('%0', BUSY)
        self.run_tick(11)
        self.change('%0', ERROR)
        self.run_tick(12)
        self.assertEqual(self.backend.send.call_args.args[0].pane, '%1')
