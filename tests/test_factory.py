import json
import hashlib
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

from overseer.factory import FAKE_PROVIDER_VERIFIER_ID, FIXTURE_VERIFIER_ID, Factory, fixture_candidate_path


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

    def fixture_spec(self, name='fixture', scenario='known_good'):
        return {'id': name, 'objective': 'verify a trusted fixture candidate',
                'mode': 'fixture', 'fixture': scenario}

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

    def test_trusted_fixture_passes_with_candidate_and_verifier_receipt(self):
        self.f.submit(self.fixture_spec())
        with patch('overseer.factory.subprocess.Popen', side_effect=AssertionError('fixture must not launch commands')):
            result = self.f.run_one()

        self.assertEqual(result['state'], 'passed')
        inspected = self.f.inspect('fixture')
        receipt = inspected['fixture_verification']
        candidate = Path(result['evidence']) / receipt['candidate_path']
        self.assertEqual(receipt['candidate_sha256'], hashlib.sha256(candidate.read_bytes()).hexdigest())
        self.assertRegex(receipt['verifier_id'], r'^fixture-answer-v1:[0-9a-f]{64}$')
        self.assertTrue(receipt['accepted'])
        self.assertTrue(inspected['evidence_valid'])
        saved = json.loads((Path(result['evidence']) / 'verification.json').read_text())
        self.assertEqual(saved['candidate_sha256'], receipt['candidate_sha256'])
        self.assertEqual(saved['verifier_id'], receipt['verifier_id'])

    def test_known_bad_fixture_fails_independent_verification(self):
        self.f.submit(self.fixture_spec(scenario='known_bad'))
        result = self.f.run_one()
        self.assertEqual(result['state'], 'failed')
        receipt = self.f.inspect('fixture')['fixture_verification']
        self.assertFalse(receipt['accepted'])
        self.assertTrue(self.f.inspect('fixture')['evidence_valid'])

    def test_fixture_rejects_commands_callbacks_and_verifier_overrides(self):
        base = self.fixture_spec('invalid')
        invalid_specs = (
            base | {'implementation': [sys.executable, '-c', 'pass']},
            base | {'checks': [[sys.executable, '-c', 'pass']]},
            base | {'verifier': {'expected_answer': 41}},
            base | {'candidate_path': '../outside'},
            base | {'callback': 'arbitrary-code'},
            base | {'mode': 'plugin'},
        )
        for spec in invalid_specs:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                self.f.submit(spec)

    def test_fixture_candidate_path_rejects_escape_and_symlink(self):
        evidence = self.root / 'fixture-evidence'
        evidence.mkdir()
        outside = self.root / 'outside.txt'
        outside.write_text('protected')
        for path in ('../outside.txt', str(outside), 'nested/candidate.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                fixture_candidate_path(evidence, path)

        (evidence / 'candidate.json').symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            fixture_candidate_path(evidence, 'candidate.json')
        self.assertEqual(outside.read_text(), 'protected')

    def test_fixture_post_check_tampering_fails_closed(self):
        self.f.submit(self.fixture_spec(scenario='tamper_after_check'))
        result = self.f.run_one()
        self.assertEqual(result['state'], 'failed')
        self.assertIn('changed after verification', result['detail'])
        inspected = self.f.inspect('fixture')
        receipt = inspected['fixture_verification']
        self.assertFalse(receipt['accepted'])
        self.assertNotEqual(receipt['candidate_sha256'], receipt['final_candidate_sha256'])
        self.assertTrue(inspected['evidence_valid'])

    def test_inspect_invalidates_acceptance_after_candidate_tampering(self):
        self.f.submit(self.fixture_spec())
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        evidence = Path(result['evidence'])
        original_receipt = self.f.inspect('fixture')['fixture_verification']

        (evidence / original_receipt['candidate_path']).write_bytes(b'{"answer":41}\n')
        inspected = self.f.inspect('fixture')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])
        self.assertIn('invalidated', inspected['detail'])
        self.assertEqual(inspected['fixture_verification']['candidate_sha256'],
                         original_receipt['candidate_sha256'])
        self.assertEqual(self.f.inspect('fixture')['state'], 'invalidated')

    def test_inspect_invalidates_tampered_verification_file(self):
        self.f.submit(self.fixture_spec())
        result = self.f.run_one()
        evidence = Path(result['evidence'])
        saved = json.loads((evidence / 'verification.json').read_text())
        original_receipt = self.f.inspect('fixture')['fixture_verification']
        saved['candidate_sha256'] = '0' * 64
        (evidence / 'verification.json').write_text(json.dumps(saved))

        inspected = self.f.inspect('fixture')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])
        self.assertEqual(inspected['fixture_verification']['candidate_sha256'],
                         original_receipt['candidate_sha256'])

    def test_inspect_invalidates_string_flags_in_verification_file(self):
        for field in ('accepted', 'verifier_passed'):
            job_id = f'receipt-{field}'
            with self.subTest(field=field):
                self.f.submit(self.fixture_spec(name=job_id))
                result = self.f.run_one()
                self.assertEqual(result['state'], 'passed')
                evidence = Path(result['evidence'])
                original_receipt = self.f.inspect(job_id)['fixture_verification']
                saved = json.loads((evidence / 'verification.json').read_text())
                saved[field] = 'false'
                (evidence / 'verification.json').write_text(json.dumps(saved))

                inspected = self.f.inspect(job_id)
                self.assertEqual(inspected['state'], 'invalidated')
                self.assertFalse(inspected['evidence_valid'])
                self.assertEqual(inspected['fixture_verification'], original_receipt)
                flags = self.f.db.execute(
                    'SELECT accepted,verifier_passed FROM fixture_verifications WHERE job_id=?',
                    (job_id,),
                ).fetchone()
                self.assertEqual(tuple(flags), (1, 1))

    def test_inspect_invalidates_non_object_verification_json_without_raising(self):
        self.f.submit(self.fixture_spec())
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        evidence = Path(result['evidence'])
        original_receipt = self.f.inspect('fixture')['fixture_verification']
        (evidence / 'verification.json').write_text('[]')

        inspected = self.f.inspect('fixture')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])
        self.assertIn('invalid schema', inspected['evidence_problem'])
        self.assertEqual(inspected['fixture_verification'], original_receipt)

    def test_inspect_invalidates_non_utf8_verification_file_without_raising(self):
        self.f.submit(self.fixture_spec())
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        evidence = Path(result['evidence'])
        (evidence / 'verification.json').write_bytes(b'\xff')

        inspected = self.f.inspect('fixture')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])

    def test_inspect_invalidates_deeply_nested_verification_json(self):
        self.f.submit(self.fixture_spec())
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        evidence = Path(result['evidence'])
        original_receipt = self.f.inspect('fixture')['fixture_verification']
        nested_json = '[' * 2000 + '0' + ']' * 2000
        (evidence / 'verification.json').write_text(nested_json)

        inspected = self.f.inspect('fixture')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])
        self.assertEqual(inspected['fixture_verification'], original_receipt)
        stored_receipt = self.f.db.execute(
            'SELECT * FROM fixture_verifications WHERE job_id=?', ('fixture',),
        ).fetchone()
        self.assertEqual(dict(stored_receipt), original_receipt)

    def fake_spec(self, name, scenario):
        return {'id': name, 'objective': 'exercise the deterministic fake provider',
                'mode': 'fake_provider', 'scenario': scenario}

    def run_fake(self):
        with patch('overseer.factory.subprocess.Popen',
                   side_effect=AssertionError('fake provider called Popen')):
            return self.f.run_one()

    def test_fake_provider_success_receipt_is_bound_to_its_verifier(self):
        self.assertNotEqual(FAKE_PROVIDER_VERIFIER_ID, FIXTURE_VERIFIER_ID)
        self.f.submit(self.fake_spec('fake-good', 'success'))
        result = self.run_fake()
        self.assertEqual(result['state'], 'passed')
        self.assertIsNone(result['child_group'])
        receipt = result['fake_provider_verification']
        candidate = (Path(result['evidence']) / 'candidate.json').read_bytes()
        self.assertEqual(candidate, b'{"answer":42}\n')
        digest = hashlib.sha256(candidate).hexdigest()
        self.assertEqual(receipt['candidate_sha256'], digest)
        self.assertEqual(receipt['final_candidate_sha256'], digest)
        self.assertEqual(receipt['verifier_id'], FAKE_PROVIDER_VERIFIER_ID)
        self.assertEqual(receipt['accepted'], 1)
        self.assertEqual(receipt['verifier_passed'], 1)
        self.assertTrue(result['evidence_valid'])
        published = [item for item in result['attempts'] if item['state'] == 'published']
        self.assertEqual(len(published), 1)
        with self.assertRaises(ValueError):
            self.f.publish('fake-good', published[0]['attempt_id'],
                           published[0]['lease_generation'], published[0]['epoch'])
        self.assertEqual(self.f.inspect('fake-good')['state'], 'passed')
        (Path(result['evidence']) / 'candidate.json').write_bytes(b'{"answer":0}\n')
        inspected = self.f.inspect('fake-good')
        self.assertEqual(inspected['state'], 'invalidated')
        self.assertFalse(inspected['evidence_valid'])
        self.assertEqual(inspected['fake_provider_verification']['accepted'], 1)
        self.assertEqual(inspected['fake_provider_verification']['candidate_sha256'], digest)

    def test_fake_provider_incorrect_success_marker_is_not_acceptance(self):
        self.f.submit(self.fake_spec('fake-bad', 'incorrect'))
        result = self.run_fake()
        self.assertEqual(result['state'], 'failed')
        log = (Path(result['evidence']) / '00.log').read_text()
        self.assertIn('fake-provider worker marker: SUCCESS\n', log)
        receipt = result['fake_provider_verification']
        self.assertEqual(receipt['accepted'], 0)
        self.assertEqual(receipt['verifier_passed'], 0)
        self.assertNotEqual(result['state'], 'passed')
        self.assertEqual(result['attempts'][0]['state'], 'rejected')

    def test_fake_provider_timeout_does_not_accept_or_wait(self):
        self.f.submit(self.fake_spec('fake-slow', 'timeout'))
        started = time.monotonic()
        result = self.run_fake()
        self.assertLess(time.monotonic() - started, 1)
        self.assertEqual(result['state'], 'failed')
        self.assertIn('timed out', result['detail'])
        saved = json.loads((Path(result['evidence']) / 'results.json').read_text())
        self.assertTrue(saved[0]['timed_out'])
        self.assertLess(saved[0]['elapsed_seconds'], 1)
        self.assertIsNone(result['fake_provider_verification'])
        attempt = result['attempts'][0]
        self.assertEqual(attempt['state'], 'timed_out')
        with self.assertRaises(ValueError):
            self.f.publish('fake-slow', attempt['attempt_id'], attempt['lease_generation'], attempt['epoch'])
        self.assertEqual(self.f.inspect('fake-slow')['state'], 'failed')

    def test_fake_provider_interruption_rejects_stale_publish(self):
        self.f.submit(self.fake_spec('fake-stop', 'interrupted'))
        result = self.run_fake()
        self.assertEqual(result['state'], 'running')
        self.assertIsNone(result['finished'])
        partial = json.loads((Path(result['evidence']) / 'partial.json').read_text())
        self.assertIs(partial['complete'], False)
        self.assertEqual(partial['attempt_id'], result['attempts'][0]['attempt_id'])
        self.assertFalse((Path(result['evidence']) / 'candidate.json').exists())
        self.assertFalse((Path(result['evidence']) / 'verification.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'unresolved'):
            self.f.run_one()
        with self.assertRaises(ValueError):
            self.f.publish('fake-stop', partial['attempt_id'], partial['lease_generation'] + 1, partial['epoch'])
        inspected = self.f.inspect('fake-stop')
        self.assertEqual(inspected['state'], 'running')
        self.assertIsNone(inspected['fake_provider_verification'])
        self.assertEqual(inspected['attempts'][0]['state'], 'reserved')

    def test_replaced_lease_cannot_publish_and_new_lease_can(self):
        self.f.submit(self.fake_spec('fake-swap', 'interrupted'))
        result = self.run_fake()
        partial = json.loads((Path(result['evidence']) / 'partial.json').read_text())
        evidence = Path(result['evidence'])
        (evidence / 'candidate.json').write_bytes(b'{"answer":42}\n')
        replacement = self.f.replace_lease('fake-swap')
        with self.assertRaises(ValueError):
            self.f.publish('fake-swap', partial['attempt_id'], partial['lease_generation'], partial['epoch'])
        self.assertEqual(self.f.inspect('fake-swap')['state'], 'running')
        self.assertIsNone(self.f.db.execute(
            'SELECT 1 FROM fake_provider_verifications WHERE job_id=?', ('fake-swap',)
        ).fetchone())
        self.f.publish(
            'fake-swap', replacement['attempt_id'], replacement['lease_generation'], replacement['epoch']
        )
        inspected = self.f.inspect('fake-swap')
        self.assertEqual(inspected['state'], 'passed')
        self.assertEqual(inspected['fake_provider_verification']['lease_generation'], replacement['lease_generation'])
        self.assertEqual(inspected['fake_provider_verification']['accepted'], 1)
        self.assertEqual(inspected['attempts'][0]['state'], 'superseded')

    def test_restore_fences_pre_restore_lease_and_preserves_high_water(self):
        self.f.submit(self.fake_spec('fake-hold', 'interrupted'))
        result = self.run_fake()
        partial = json.loads((Path(result['evidence']) / 'partial.json').read_text())
        before = self.f.db.execute('SELECT epoch, lease_high_water FROM controller WHERE id=1').fetchone()
        self.assertEqual(before['epoch'], 1)
        self.assertEqual(before['lease_high_water'], partial['lease_generation'])
        destination = self.root / 'factory-backup.sqlite3'
        self.f.backup(destination)
        unchanged = self.f.db.execute('SELECT epoch, lease_high_water FROM controller WHERE id=1').fetchone()
        self.assertEqual(dict(unchanged), dict(before))
        replacement = self.f.replace_lease('fake-hold')
        self.assertGreater(replacement['lease_generation'], partial['lease_generation'])
        live_high = self.f.db.execute(
            'SELECT lease_high_water FROM controller WHERE id=1'
        ).fetchone()['lease_high_water']
        self.assertEqual(live_high, replacement['lease_generation'])
        new_epoch = self.f.restore(destination)
        controller = self.f.db.execute(
            'SELECT epoch, lease_high_water FROM controller WHERE id=1'
        ).fetchone()
        self.assertEqual(new_epoch, before['epoch'] + 1)
        self.assertEqual(controller['epoch'], before['epoch'] + 1)
        self.assertEqual(controller['lease_high_water'], live_high)
        with self.assertRaises(ValueError):
            self.f.publish(
                'fake-hold', replacement['attempt_id'],
                replacement['lease_generation'], replacement['epoch'],
            )
        with self.assertRaises(ValueError):
            self.f.publish('fake-hold', partial['attempt_id'], partial['lease_generation'], partial['epoch'])
        inspected = self.f.inspect('fake-hold')
        self.assertEqual(inspected['state'], 'needs_reconciliation')
        self.assertIsNone(inspected['fake_provider_verification'])

    def test_restore_invalidates_changed_candidates_and_keeps_generic_pass(self):
        self.f.submit(self.fixture_spec('artifact-fixture'))
        fixture = self.f.run_one()
        self.assertEqual(fixture['state'], 'passed')
        self.f.submit(self.fake_spec('artifact-fake', 'success'))
        fake = self.run_fake()
        self.assertEqual(fake['state'], 'passed')
        self.f.submit(self.spec('artifact-command'))
        command = self.f.run_one()
        self.assertEqual(command['state'], 'passed')
        fixture_receipt = dict(self.f.db.execute(
            'SELECT * FROM fixture_verifications WHERE job_id=?', ('artifact-fixture',)
        ).fetchone())
        fake_receipt = dict(self.f.db.execute(
            'SELECT * FROM fake_provider_verifications WHERE job_id=?', ('artifact-fake',)
        ).fetchone())
        (Path(fixture['evidence']) / 'candidate.json').unlink()
        (Path(fake['evidence']) / 'candidate.json').write_bytes(b'{"answer":0}\n')
        destination = self.root / 'artifact-backup.sqlite3'
        self.f.backup(destination)
        self.f.restore(destination)
        restored_states = {
            row['id']: row['state']
            for row in self.f.db.execute('SELECT id, state FROM jobs')
        }
        self.assertEqual(restored_states['artifact-fixture'], 'invalidated')
        self.assertEqual(restored_states['artifact-fake'], 'invalidated')
        self.assertEqual(restored_states['artifact-command'], 'passed')
        self.assertEqual(self.f.inspect('artifact-fixture')['state'], 'invalidated')
        self.assertEqual(self.f.inspect('artifact-fake')['state'], 'invalidated')
        self.assertEqual(self.f.inspect('artifact-command')['state'], 'passed')
        self.assertEqual(dict(self.f.db.execute(
            'SELECT * FROM fixture_verifications WHERE job_id=?', ('artifact-fixture',)
        ).fetchone()), fixture_receipt)
        self.assertEqual(dict(self.f.db.execute(
            'SELECT * FROM fake_provider_verifications WHERE job_id=?', ('artifact-fake',)
        ).fetchone()), fake_receipt)

    def test_restore_fence_failure_keeps_the_live_lease_counter(self):
        self.f.submit(self.fake_spec('fake-rewind', 'interrupted'))
        result = self.run_fake()
        partial = json.loads((Path(result['evidence']) / 'partial.json').read_text())
        (Path(result['evidence']) / 'candidate.json').write_bytes(b'{"answer":42}\n')
        destination = self.root / 'rewind-backup.sqlite3'
        self.f.backup(destination)
        self.f.db.execute('UPDATE controller SET epoch=5, lease_high_water=9 WHERE id=1')
        self.f.db.commit()
        with patch.object(Factory, '_invalidate_restored_candidates', side_effect=RuntimeError('fence failed')):
            with self.assertRaisesRegex(RuntimeError, 'fence failed'):
                self.f.restore(destination)
        controller = self.f.db.execute(
            'SELECT epoch, lease_high_water FROM controller WHERE id=1'
        ).fetchone()
        self.assertEqual(controller['epoch'], 5)
        self.assertEqual(controller['lease_high_water'], 9)
        with self.assertRaises(ValueError):
            self.f.publish(
                'fake-rewind', partial['attempt_id'], partial['lease_generation'], partial['epoch']
            )
        self.assertEqual(self.f.inspect('fake-rewind')['state'], 'running')
        self.assertIsNone(self.f.db.execute(
            'SELECT 1 FROM fake_provider_verifications WHERE job_id=?', ('fake-rewind',)
        ).fetchone())

    def test_restore_invalid_spec_still_fences_the_previous_lease(self):
        self.f.submit(self.fake_spec('fake-corrupt', 'interrupted'))
        result = self.run_fake()
        partial = json.loads((Path(result['evidence']) / 'partial.json').read_text())
        (Path(result['evidence']) / 'candidate.json').write_bytes(b'{"answer":42}\n')
        destination = self.root / 'corrupt-backup.sqlite3'
        self.f.backup(destination)
        self.f.db.execute('UPDATE controller SET epoch=5, lease_high_water=9 WHERE id=1')
        self.f.db.commit()
        planted = sqlite3.connect(destination)
        try:
            planted.execute(
                'INSERT INTO jobs(id,spec,spec_hash,state,created) VALUES(?,?,?,?,?)',
                ('not-json', 'NOTJSON', '0' * 64, 'passed', time.time()),
            )
            planted.commit()
        finally:
            planted.close()
        new_epoch = self.f.restore(destination)
        controller = self.f.db.execute(
            'SELECT epoch, lease_high_water FROM controller WHERE id=1'
        ).fetchone()
        self.assertEqual(new_epoch, 6)
        self.assertEqual(controller['epoch'], 6)
        self.assertGreaterEqual(controller['lease_high_water'], 9)
        with self.assertRaises(ValueError):
            self.f.publish(
                'fake-corrupt', partial['attempt_id'], partial['lease_generation'], partial['epoch']
            )
        self.assertEqual(self.f.inspect('fake-corrupt')['state'], 'needs_reconciliation')
        self.assertEqual(
            self.f.db.execute("SELECT state FROM jobs WHERE id='not-json'").fetchone()['state'],
            'invalidated',
        )

    def test_fake_provider_rejects_commands_and_unknown_scenarios(self):
        base = self.fake_spec('illegal', 'success')
        extras = (
            {'workspace': '/tmp'},
            {'implementation': [sys.executable, '-c', 'pass']},
            {'checks': [[sys.executable, '-c', 'pass']]},
            {'timeout_seconds': 1},
            {'fixture': 'known_good'},
            {'callback': 'accept'},
            {'verifier': 'answer-equals-42'},
            {'argv': ['sh', '-c', 'true']},
        )
        for extra in extras:
            with self.assertRaises(ValueError):
                self.f.submit({**base, **extra})
        unknown = dict(base)
        unknown['scenario'] = 'live-model'
        with self.assertRaisesRegex(ValueError, 'unknown fake-provider'):
            self.f.submit(unknown)
        command = self.spec('command-scenario')
        command['scenario'] = 'success'
        with self.assertRaises(ValueError):
            self.f.submit(command)
