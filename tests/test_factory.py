import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from overseer.factory import Factory


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root/'state'/'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def spec(self, name='one'):
        return {'id': name, 'objective': 'write and independently verify result',
                'workspace': str(self.root), 'timeout_seconds': 2,
                'implementation': [sys.executable, '-c', "from pathlib import Path; Path('result').write_text('ok')"],
                'checks': [[sys.executable, '-c', "from pathlib import Path; assert Path('result').read_text() == 'ok'"]]}

    def test_real_change_and_independent_acceptance_persist(self):
        self.f.submit(self.spec())
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        self.assertEqual((self.root/'result').read_text(), 'ok')
        other = Factory(self.db)
        self.addCleanup(other.close)
        saved = other.inspect('one')
        self.assertEqual(saved['run_id'], result['run_id'])
        evidence = Path(saved['evidence'])
        self.assertEqual(len(json.loads((evidence/'results.json').read_text())), 2)
        self.assertIsNone(self.f.run_one())

    def test_frozen_spec_and_duplicate_submission(self):
        spec = self.spec()
        self.assertTrue(self.f.submit(spec))
        self.assertFalse(self.f.submit(spec))
        spec['checks'] = [[sys.executable, '-c', 'pass']]
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.f.submit(spec)

    def test_failed_check_is_not_passed(self):
        spec = self.spec()
        spec['checks'] = [[sys.executable, '-c', 'raise SystemExit(3)']]
        self.f.submit(spec)
        result = self.f.run_one()
        self.assertEqual(result['state'], 'failed')
        self.assertIn('acceptance failed', result['detail'])

    def test_timeout_and_missing_executable(self):
        spec = self.spec()
        spec['timeout_seconds'] = 1
        spec['implementation'] = [sys.executable, '-c', 'import time; time.sleep(30)']
        self.f.submit(spec)
        result = self.f.run_one()
        self.assertEqual(result['state'], 'failed')
        self.assertIn('timed out', result['detail'])
        self.assertIsNone(result['child_group'])
        spec = self.spec('missing')
        spec['implementation'] = ['/does/not/exist']
        self.f.submit(spec)
        self.assertEqual(self.f.run_one()['state'], 'failed')

    def test_worker_lock_and_interrupted_run_do_not_redispatch(self):
        self.f.submit(self.spec())
        other = Factory(self.db)
        self.addCleanup(other.close)
        with self.f.worker_lock():
            with self.assertRaisesRegex(RuntimeError, 'another factory worker'):
                other.run_one()
        self.f.transition('one', 'running', 'simulated crash after reservation')
        with self.assertRaisesRegex(RuntimeError, 'unresolved'):
            self.f.run_one()
        self.assertEqual(self.f.reconcile(), 1)
        self.assertEqual(self.f.inspect('one')['state'], 'needs_reconciliation')
        with self.assertRaisesRegex(RuntimeError, 'unresolved'):
            self.f.run_one()
        self.f.resolve('one', 'inspected; no subprocess dispatched')
        self.assertEqual(self.f.inspect('one')['state'], 'failed')
        self.assertIsNone(self.f.run_one())

    def test_fifo_cancel(self):
        self.f.submit(self.spec('first'))
        self.f.submit(self.spec('second'))
        self.f.cancel('first')
        self.assertEqual(self.f.run_one()['id'], 'second')

    def test_argv_is_not_interpreted_by_shell(self):
        spec = self.spec()
        spec['implementation'] = [sys.executable, '-c', 'import sys; print(sys.argv[1])', '$(touch unexpected)']
        spec['checks'] = [[sys.executable, '-c', "from pathlib import Path; assert not Path('unexpected').exists()"]]
        self.f.submit(spec)
        self.assertEqual(self.f.run_one()['state'], 'passed')

    def test_log_size_is_bounded(self):
        spec = self.spec()
        spec['implementation'] = [sys.executable, '-c', "print('x' * 3000000)"]
        spec['checks'] = [[sys.executable, '-c', 'pass']]
        self.f.submit(spec)
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        self.assertLess((Path(result['evidence'])/'00.log').stat().st_size, 2100000)

    def test_invalid_id_types_are_validation_errors(self):
        for value in (None, 123, [], {}):
            spec = self.spec()
            spec['id'] = value
            with self.assertRaises(ValueError):
                self.f.submit(spec)

    def test_launch_setup_failure_kills_child_before_task_executes(self):
        spec = self.spec()
        self.f.submit(spec)
        real_popen = subprocess.Popen
        children = []
        def launch(*args, **kwargs):
            child = real_popen(*args, **kwargs)
            children.append(child)
            return child
        with patch('overseer.factory.subprocess.Popen', side_effect=launch), \
             patch('selectors.DefaultSelector', side_effect=RuntimeError('injected selector failure')):
            with self.assertRaisesRegex(RuntimeError, 'selector failure'):
                self.f.run_one()
        self.assertIsNotNone(children[0].poll())
        self.assertFalse((self.root/'result').exists())
        self.assertEqual(self.f.inspect('one')['state'], 'needs_reconciliation')

    def test_persistence_failure_never_releases_launch_gate(self):
        self.f.submit(self.spec())
        database = self.f.db
        class FailOnce:
            failed = False
            def __getattr__(self, name):
                return getattr(database, name)
            def __enter__(self):
                database.__enter__()
                return self
            def __exit__(self, *args):
                return database.__exit__(*args)
            def execute(self, sql, *args):
                if 'SET child_group=?' in sql and not self.failed:
                    self.failed = True
                    raise sqlite3.OperationalError('injected persistence failure')
                return database.execute(sql, *args)
        self.f.db = FailOnce()
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, 'persistence failure'):
                self.f.run_one()
            self.assertFalse((self.root/'result').exists())
            self.assertEqual(self.f.inspect('one')['state'], 'needs_reconciliation')
        finally:
            self.f.db = database

    def test_hard_worker_crash_requires_reconciliation(self):
        spec = self.spec()
        spec['implementation'] = [sys.executable, '-c', 'import time; time.sleep(30)']
        self.f.submit(spec)
        worker = subprocess.Popen([sys.executable, '-m', 'overseer.factory', '--db', str(self.db), 'run-one'],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        group = None
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                group = self.f.inspect('one')['child_group']
                if group:
                    break
                time.sleep(.02)
            self.assertIsNotNone(group)
            worker.kill()
            worker.wait()
            self.assertEqual(self.f.reconcile(), 1)
            with self.assertRaisesRegex(RuntimeError, 'unresolved'):
                self.f.run_one()
            with self.assertRaisesRegex(RuntimeError, 'process group still exists'):
                self.f.resolve('one', 'cannot release a live child')
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.wait()
            if group:
                try:
                    os.killpg(group, signal.SIGKILL)
                except ProcessLookupError:
                    pass
