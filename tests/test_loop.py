import json
import os
import stat
import sys
import tempfile
import time
import unittest
from pathlib import Path

from overseer.factory import Factory
from overseer.orchestrate import run_loop


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.target = self.base / 'target'
        self.target.mkdir()
        self.db = self.base / 'state' / 'jobs.sqlite3'
        self.counter = self.base / 'counter.txt'
        self.plan_path = self.base / 'plan.json'
        self.argvlog = self.base / 'argv.jsonl'

    def make_fake(self, plan):
        self.plan_path.write_text(json.dumps(plan))
        fake = self.base / 'opencode'
        fake.write_text(
            '#!/usr/bin/env python3\n'
            'import json, sys\n'
            'plan = json.load(open(%r))\n'
            'try: n = int(open(%r).read())\n'
            'except Exception: n = 0\n'
            'open(%r, "w").write(str(n + 1))\n'
            'open(%r, "a").write(json.dumps(sys.argv[1:]) + "\\n")\n'
            'step = plan[min(n, len(plan) - 1)]\n'
            'if not step.get("no_block"):\n'
            '    print("STATUS: " + step.get("status", "SUCCESS"))\n'
            '    print("TESTS_PASSED: " + step.get("tests", "TRUE"))\n'
            '    print("FILES_MODIFIED: " + step.get("files", "[mod.py]"))\n'
            '    print("NEXT_AGENT_INSTRUCTION: " + json.dumps(step.get("next", "")))\n'
            'for marker in step.get("markers", []):\n'
            '    print(marker)\n'
            'if step.get("raw"):\n'
            '    print(step["raw"])\n'
            'sys.exit(step.get("exit", 0))\n'
            % (str(self.plan_path), str(self.counter), str(self.counter), str(self.argvlog)))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        if os.name == 'nt':
            # Windows runs no shebang script; a command file starts the same script.
            wrapper = self.base / 'opencode.cmd'
            wrapper.write_text('@"%s" "%s" %%*\n' % (sys.executable, fake))
            return str(wrapper)
        return str(fake)

    def spec(self, **over):
        s = {'id_prefix': 'loop', 'objective': 'FIRST STEP: begin the work',
             'checks': [[sys.executable, '-c', 'pass']], 'runner': 'opencode',
             'repair_allowance': 1, 'timeout_seconds': 15}
        s.update(over)
        return s

    def drive(self, plan, once=False, dry_run=False, router=None, **over):
        fake = self.make_fake(plan)
        return run_loop(str(self.db), self.spec(**over), str(self.target),
                        once=once, dry_run=dry_run, env={}, opencode=fake, router=router)

    def argv_calls(self):
        return [json.loads(line) for line in self.argvlog.read_text().splitlines()]

    def lineage(self, lineage_id):
        f = Factory(self.db)
        try:
            return f.db.execute('SELECT * FROM lineages WHERE lineage_id=?',
                                (lineage_id,)).fetchone()
        finally:
            f.close()

    def test_the_loop_feeds_the_next_instruction_as_one_argv_element(self):
        result = self.drive([
            {'next': 'SECOND STEP: finish the work', 'markers': []},
            {'next': '', 'markers': ['OVERSEER_DONE']},
        ])
        self.assertEqual(result['state'], 'done')
        calls = self.argv_calls()
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[1].count('SECOND STEP: finish the work'), 1)
        self.assertEqual(calls[1][-1], 'SECOND STEP: finish the work')

    def test_the_loop_stops_at_the_freeze_after_three_failures(self):
        result = self.drive([
            {'next': 'try again a', 'exit': 1},
            {'next': 'try again b', 'exit': 2},
            {'next': 'try again c', 'exit': 3},
            {'next': 'try again d', 'exit': 4},
        ], repair_allowance=2)
        self.assertEqual(result['state'], 'frozen')
        self.assertEqual(self.lineage('loop-0')['state'], 'frozen')

    def test_size_sets_the_budget_and_reports_the_assessment(self):
        result = self.drive([{'next': '', 'markers': ['OVERSEER_DONE']}], once=True,
                            size=True, repair_allowance=None)
        self.assertEqual(result['sizing']['tier'], 'trivial')
        f = Factory(self.db)
        try:
            budget = f.inspect('loop-0')['spec']['contract']['budget']
        finally:
            f.close()
        self.assertEqual(budget['repair_allowance'], result['sizing']['repair_allowance'])
        self.assertEqual(budget['wall_time_seconds'], result['sizing']['budget']['wall_time_seconds'])

    def test_size_picks_the_model_by_strength_and_escalates_after_a_failure(self):
        models = {'light': 'opencode/model-light', 'standard': 'opencode/model-standard', 'strong': 'opencode/model-strong'}
        result = self.drive([
            {'next': 'again', 'exit': 1},
            {'next': '', 'markers': ['OVERSEER_DONE']},
        ], size=True, strength_models=models, repair_allowance=1)
        self.assertEqual(result['sizing']['strength'], 'light')
        calls = self.argv_calls()
        self.assertIn('opencode/model-light', ' '.join(calls[0]))
        self.assertIn(models[result['sizing']['escalation_strength']], ' '.join(calls[1]))

    def test_size_tracks_steps_and_saves_the_plan_beside_the_ledger(self):
        result = self.drive([
            {'next': 'second', 'markers': ['OVERSEER_STEP_DONE']},
            {'next': '', 'markers': ['OVERSEER_DONE']},
        ], size={'breadth': 2, 'novelty': 2}, repair_allowance=None)
        evaluation = result['blueprint']['evaluation']
        self.assertEqual(evaluation['verdict'], 'done')
        self.assertGreaterEqual(evaluation['iterations_used'], 2)
        saved = json.loads(Path(str(self.db) + '.plan.json').read_text())
        self.assertEqual(saved['plan']['steps'][0]['status'], 'done')
        self.assertEqual(saved['plan']['steps'][-1]['status'], 'closed')

    def test_size_halts_for_the_operator_when_the_plan_stalls(self):
        result = self.drive([
            {'next': 'a', 'files': '[]'}, {'next': 'b', 'files': '[]'}, {'next': 'c', 'files': '[]'},
        ], size={'breadth': 2, 'novelty': 2}, repair_allowance=None)
        self.assertEqual(result['state'], 'needs_input')
        self.assertIn('plan halted', result['detail'])

    @unittest.skipIf(os.name == 'nt', 'the fake worker is a Windows command file, which cannot carry a multi-line argument')
    def test_size_gives_the_worker_the_step_brief_and_keeps_the_instruction(self):
        self.drive([{'next': 'SECOND STEP: finish the work', 'markers': ['OVERSEER_STEP_DONE']},
                    {'next': '', 'markers': ['OVERSEER_DONE']}],
                   size={'breadth': 2, 'novelty': 2}, repair_allowance=None)
        calls = self.argv_calls()
        self.assertIn('[Overseer plan] Step 1 of', calls[0][-1])
        self.assertIn('OVERSEER_STEP_DONE', calls[0][-1])
        self.assertTrue(calls[0][-1].endswith('FIRST STEP: begin the work'))
        self.assertIn('Step 2 of', calls[1][-1])
        self.assertTrue(calls[1][-1].endswith('SECOND STEP: finish the work'))

    def test_size_stops_for_confirmation_when_every_step_is_finished(self):
        result = self.drive([{'next': 'more', 'markers': ['OVERSEER_STEP_DONE']},
                             {'next': 'more', 'markers': []}], size=True, repair_allowance=None)
        self.assertEqual(result['state'], 'needs_input')
        self.assertIn('plan complete', result['detail'])
        self.assertEqual(result['iterations'], 1)

    def test_without_size_the_loop_is_unchanged(self):
        result = self.drive([{'next': '', 'markers': ['OVERSEER_DONE']}], once=True)
        self.assertNotIn('sizing', result)

    def test_the_loop_stops_when_dispatch_is_paused(self):
        f = Factory(self.db)
        f.pause('maintenance')
        f.close()
        result = self.drive([{'next': 'x', 'markers': ['OVERSEER_DONE']}])
        self.assertEqual(result['state'], 'paused')
        self.assertEqual(result['iterations'], 0)

    def test_the_loop_never_decides_an_approval(self):
        envelope = {'mode': 'bounded_maintenance', 'scope': ['the target'],
                    'requires_decision': True, 'decider': 'operator'}
        result = self.drive([{'next': 'x'}], envelope=envelope)
        self.assertEqual(result['state'], 'needs_input')
        f = Factory(self.db)
        try:
            approvals = f.db.execute('SELECT COUNT(*) FROM approvals').fetchone()[0]
            state = f.inspect('loop-0')['state']
        finally:
            f.close()
        self.assertEqual(approvals, 0)
        self.assertEqual(state, 'awaiting_approval')

    def test_the_loop_stops_on_needs_input(self):
        result = self.drive([{'next': 'x', 'markers': ['OVERSEER_NEEDS_INPUT']}])
        self.assertEqual(result['state'], 'needs_input')
        self.assertEqual(result['iterations'], 1)

    def test_the_daily_cap_holds_across_a_restart(self):
        f = Factory(self.db)
        now = time.time()
        for i in range(12):
            f.db.execute('INSERT INTO events(job_id,at,state,detail) VALUES(?,?,?,?)',
                         ('old-%d' % i, now, 'running', 'prior run'))
        f.db.commit()
        f.close()
        result = self.drive([{'next': 'x', 'markers': ['OVERSEER_DONE']}], daily_cap=12)
        self.assertEqual(result['state'], 'cap')
        self.assertEqual(result['iterations'], 0)

    def test_an_invalid_block_stops_the_loop_without_inventing_an_instruction(self):
        result = self.drive([{'no_block': True}, {'next': 'should never run'}])
        self.assertEqual(result['state'], 'needs_input')
        self.assertEqual(result['iterations'], 1)
        self.assertEqual(len(self.argv_calls()), 1)

    def test_the_loop_finishes_on_done(self):
        result = self.drive([{'next': '', 'markers': ['OVERSEER_DONE']}])
        self.assertEqual(result['state'], 'done')
        self.assertEqual(result['iterations'], 1)

    def test_dry_run_submits_nothing(self):
        result = self.drive([{'next': 'x', 'markers': ['OVERSEER_DONE']}], dry_run=True)
        self.assertEqual(result['state'], 'dry_run')
        f = Factory(self.db)
        try:
            jobs = f.db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]
        finally:
            f.close()
        self.assertEqual(jobs, 0)


if __name__ == '__main__':
    unittest.main()


class FakeRouter:
    def __init__(self):
        self.calls = []

    def __call__(self, name, client, directory, prompt=None):
        self.calls.append({'name': name, 'client': client,
                           'directory': directory, 'prompt': prompt})
        return 'pane-fake'


class EscalationTests(LoopTests):
    def test_a_frozen_loop_routes_once_to_the_configured_client(self):
        router = FakeRouter()
        plan = [{'exit': 1, 'next': 'retry'}] * 3
        r1 = self.drive(plan, router=router, escalate_to='claude', repair_allowance=1)
        self.assertEqual(r1['state'], 'frozen')
        self.assertEqual(len(router.calls), 1)
        self.assertEqual(router.calls[0]['client'], 'claude')
        self.assertEqual(router.calls[0]['directory'], str(self.target))
        # A second stop on the already-frozen lineage must not route again.
        r2 = self.drive(plan, router=router, escalate_to='claude', repair_allowance=1)
        self.assertEqual(r2['state'], 'frozen')
        self.assertEqual(len(router.calls), 1)

    def test_an_approval_wait_is_never_routed_to_a_model(self):
        router = FakeRouter()
        envelope = {'mode': 'bounded_maintenance', 'scope': ['t'],
                    'requires_decision': True, 'decider': 'op'}
        r = self.drive([{'next': 'x'}], router=router, escalate_to='claude', envelope=envelope)
        self.assertEqual(r['state'], 'needs_input')
        self.assertEqual(len(router.calls), 0)

    def test_the_escalation_prompt_carries_only_ledger_facts(self):
        router = FakeRouter()
        plan = [{'exit': 0, 'next': 'retry', 'raw': 'SENTINEL_RAW_LOG_DATA'}] * 3
        r = self.drive(plan, router=router, escalate_to='claude', repair_allowance=1,
                       checks=[[sys.executable, '-c', 'import sys; sys.exit(1)']])
        self.assertEqual(r['state'], 'frozen')
        self.assertEqual(len(router.calls), 1)
        prompt = router.calls[0]['prompt']
        self.assertIn('loop-0', prompt)
        self.assertIn('A1', prompt)
        self.assertIn('Evidence', prompt)
        self.assertNotIn('SENTINEL_RAW_LOG_DATA', prompt)

    def test_dry_run_routes_nothing(self):
        router = FakeRouter()
        r = self.drive([{'exit': 1, 'next': 'retry'}] * 3, router=router,
                       escalate_to='claude', dry_run=True, repair_allowance=1)
        self.assertEqual(r['state'], 'dry_run')
        self.assertEqual(len(router.calls), 0)


class InheritRunnerTests(LoopTests):
    def test_the_loop_inherits_the_launching_session_by_default(self):
        fake = self.make_fake([{'next': 'x', 'markers': ['OVERSEER_DONE']}])
        spec = self.spec()
        spec.pop('runner', None)  # no explicit runner -> inherit the session
        r = run_loop(str(self.db), spec, str(self.target), dry_run=True,
                     env={'CLAUDECODE': '1'}, opencode=fake)
        self.assertEqual(r['state'], 'dry_run')
        self.assertEqual(r['runner'], 'claude')

    def test_the_loop_falls_back_to_opencode_without_a_session(self):
        fake = self.make_fake([{'next': 'x', 'markers': ['OVERSEER_DONE']}])
        spec = self.spec()
        spec.pop('runner', None)
        r = run_loop(str(self.db), spec, str(self.target), dry_run=True,
                     env={}, opencode=fake)
        self.assertEqual(r['state'], 'dry_run')
        self.assertEqual(r['runner'], 'opencode')
