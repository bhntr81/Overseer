import json
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
            'sys.exit(step.get("exit", 0))\n'
            % (str(self.plan_path), str(self.counter), str(self.counter), str(self.argvlog)))
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        return str(fake)

    def spec(self, **over):
        s = {'id_prefix': 'loop', 'objective': 'FIRST STEP: begin the work',
             'checks': [[sys.executable, '-c', 'pass']], 'runner': 'opencode',
             'repair_allowance': 1, 'timeout_seconds': 15}
        s.update(over)
        return s

    def drive(self, plan, once=False, dry_run=False, **over):
        fake = self.make_fake(plan)
        return run_loop(str(self.db), self.spec(**over), str(self.target),
                        once=once, dry_run=dry_run, env={}, opencode=fake)

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
