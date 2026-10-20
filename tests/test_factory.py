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

from overseer.factory import (
    CONTRACT_FIELDS, FAKE_PROVIDER_VERIFIER_ID, FIXTURE_VERIFIER_ID,
    MEMORY_KINDS, PROVIDER_NAMES, REQUEST_INPUT_FIELDS, Factory, canonical,
    fixture_candidate_path, repository_identity, validate,
)

ROOT = Path(__file__).resolve().parents[1]


def attach_contract(spec, **overrides):
    """Give a command-mode spec a valid contract block for its acceptance commands."""
    block = {
        'role': 'implementation',
        'risk_tier': 'low',
        'external_effects': [],
        'protected_paths': [],
        'approval_requirements': [],
        'acceptance_ids': [f'A{index + 1}' for index in range(len(spec.get('checks') or []))],
        'required_capabilities': [],
        'project_constraints': [],
        'measured_evidence': None,
        'provider_availability': None,
        'budget': {
            'wall_time_seconds': 600, 'token_limit': None, 'cost_limit_usd': None,
            'resource_limits': None, 'repair_allowance': 0,
        },
    }
    block.update(overrides)
    spec = dict(spec)
    spec['contract'] = block
    return spec


def store_legacy_job(factory, spec, state='queued'):
    """Write a job row the way the ledger held it before the contract rule."""
    data = canonical(spec)
    digest = hashlib.sha256(data.encode()).hexdigest()
    factory.db.execute(
        'INSERT INTO jobs(id,spec,spec_hash,state,created) VALUES(?,?,?,?,?)',
        (spec['id'], data, digest, state, time.time()))
    factory.db.commit()
    return digest


class FactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root/'state'/'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def spec(self, name='one'):
        return attach_contract({'id': name, 'objective': 'write and independently verify result',
                'workspace': str(self.root), 'timeout_seconds': 2,
                'implementation': [sys.executable, '-c', "from pathlib import Path; Path('result').write_text('ok')"],
                'checks': [[sys.executable, '-c', "from pathlib import Path; assert Path('result').read_text() == 'ok'"]]})

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
        spec = attach_contract(spec)
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.f.submit(spec)

    def test_failed_check_is_not_passed(self):
        spec = self.spec()
        spec['checks'] = [[sys.executable, '-c', 'raise SystemExit(3)']]
        spec = attach_contract(spec)
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
        spec = attach_contract(spec)
        self.f.submit(spec)
        self.assertEqual(self.f.run_one()['state'], 'passed')

    def test_log_size_is_bounded(self):
        spec = self.spec()
        spec['implementation'] = [sys.executable, '-c', "print('x' * 3000000)"]
        spec['checks'] = [[sys.executable, '-c', 'pass']]
        spec = attach_contract(spec)
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


class ContractTests(unittest.TestCase):
    """The required contract block: validated, recorded, never enforced."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'state' / 'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def contract(self, **overrides):
        block = {
            'role': 'implementation',
            'risk_tier': 'medium',
            'external_effects': ['publishes a release note'],
            'protected_paths': ['secrets'],
            'approval_requirements': ['operator-review'],
            'acceptance_ids': ['A1'],
            'required_capabilities': ['filesystem write'],
            'project_constraints': ['keep the public API stable'],
            'measured_evidence': None,
            'provider_availability': None,
            'budget': {
                'wall_time_seconds': 600,
                'token_limit': None,
                'cost_limit_usd': None,
                'resource_limits': {'cpu_seconds': 60, 'memory_mb': 512,
                                    'process_count': 4, 'disk_mb': 64},
                'repair_allowance': 1,
            },
        }
        block.update(overrides)
        return block

    def command_spec(self, name='one', checks=None, contract=None):
        spec = {
            'id': name, 'objective': 'write and independently verify result',
            'workspace': str(self.root), 'timeout_seconds': 2,
            'implementation': [sys.executable, '-c',
                               "from pathlib import Path; Path('result').write_text('ok')"],
            'checks': checks or [[sys.executable, '-c',
                                  "from pathlib import Path; assert Path('result').read_text() == 'ok'"]],
        }
        if contract is not None:
            spec['contract'] = contract
            return spec
        return attach_contract(spec)

    def contract_spec(self, name='one', contract=None, checks=None):
        return self.command_spec(name, checks, self.contract() if contract is None else contract)

    def test_valid_contract_is_accepted_and_recorded(self):
        spec = self.contract_spec('contract-one')
        self.assertTrue(self.f.submit(spec))
        saved = self.f.inspect('contract-one')
        self.assertEqual(saved['contract'], spec['contract'])
        self.assertEqual(saved['spec']['contract'], spec['contract'])
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        recorded = json.loads((Path(result['evidence']) / 'task.json').read_text())
        self.assertEqual(recorded['contract'], spec['contract'])

    def test_missing_contract_field_is_rejected(self):
        for field in CONTRACT_FIELDS:
            with self.subTest(field=field):
                block = self.contract()
                del block[field]
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('missing', block))

    def test_unmeasured_contract_fields_accept_null(self):
        for field in ('measured_evidence', 'provider_availability'):
            with self.subTest(field=field):
                block = self.contract()
                block[field] = None
                self.assertTrue(self.f.submit(self.contract_spec('null-' + field, block)))

    def test_wrong_contract_types_are_rejected(self):
        cases = (
            {'role': 7},
            {'risk_tier': 3},
            {'external_effects': 'not a list'},
            {'required_capabilities': 'not a list'},
            {'project_constraints': 'not a list'},
            {'measured_evidence': 'not a list'},
            {'provider_availability': 'not an object'},
            {'budget': 'not an object'},
        )
        for index, case in enumerate(cases):
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('wrong-' + str(index), self.contract(**case)))

    def test_wrong_budget_values_are_rejected(self):
        def budget(**overrides):
            block = self.contract()
            block['budget'].update(overrides)
            return block

        cases = (
            budget(wall_time_seconds=True),
            budget(wall_time_seconds=86401),
            budget(wall_time_seconds=0),
            budget(token_limit=-1),
            budget(token_limit='1000'),
            budget(cost_limit_usd=-0.5),
            budget(cost_limit_usd=True),
            budget(repair_allowance=11),
            budget(repair_allowance=False),
            budget(resource_limits={'disk_mb': -1}),
            budget(resource_limits={'unknown_limit': 1}),
            budget(resource_limits='none'),
        )
        for index, block in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('budget-' + str(index), block))

    def test_unknown_key_inside_the_contract_is_rejected(self):
        for key in ('verifier', 'sandbox', 'approver'):
            with self.subTest(key=key):
                block = self.contract()
                block[key] = 'anything'
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('unknown-' + key, block))

    def test_unknown_key_inside_the_budget_is_rejected(self):
        block = self.contract()
        block['budget']['savings'] = 0.42
        with self.assertRaises(ValueError):
            self.f.submit(self.contract_spec('budget-extra', block))

    def test_protected_paths_must_stay_inside_the_workspace(self):
        for path in ('../outside', '/etc/passwd', 'a/../../b', '.', '', 'secrets/../../etc'):
            with self.subTest(path=path):
                block = self.contract(protected_paths=[path])
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('protected', block))
        inside = self.contract(protected_paths=['secrets', 'src/config.json'])
        self.assertTrue(self.f.submit(self.contract_spec('protected-inside', inside)))

    def test_acceptance_ids_must_match_the_acceptance_commands(self):
        second = [sys.executable, '-c', 'pass']
        checks = [[sys.executable, '-c',
                   "from pathlib import Path; assert Path('result').read_text() == 'ok'"], second]
        cases = (
            self.contract(acceptance_ids=['A1']),
            self.contract(acceptance_ids=['A1', 'A1']),
            self.contract(acceptance_ids=['A1', 'not an id']),
            self.contract(acceptance_ids=[]),
        )
        for index, block in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('acceptance-' + str(index), block, checks))
        matched = self.contract(acceptance_ids=['A1', 'A2'])
        self.assertTrue(self.f.submit(self.contract_spec('acceptance-ok', matched, checks)))

    def test_controller_modes_still_reject_a_contract_block(self):
        specs = (
            {'id': 'f', 'objective': 'verify a trusted fixture candidate',
             'mode': 'fixture', 'fixture': 'known_good'},
            {'id': 'p', 'objective': 'run the fake provider', 'mode': 'fake_provider',
             'scenario': 'success'},
            {'id': 'i', 'objective': 'probe the boundary', 'mode': 'isolation_probe'},
        )
        for spec in specs:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    self.f.submit({**spec, 'contract': self.contract()})

    def test_contract_is_covered_by_the_frozen_spec_hash(self):
        spec = self.contract_spec('frozen')
        self.assertTrue(self.f.submit(spec))
        stored = self.f.inspect('frozen')
        self.assertEqual(stored['spec_hash'], hashlib.sha256(canonical(spec).encode()).hexdigest())
        changed = self.contract_spec('frozen')
        changed['contract']['risk_tier'] = 'high'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.f.submit(changed)
        self.assertFalse(self.f.submit(self.contract_spec('frozen')))

    def test_routing_policy_required_inputs_have_code_counterparts(self):
        policy = json.loads((ROOT / 'factory' / 'routing-policy.json').read_text())
        self.assertEqual(set(policy['required_inputs']), set(REQUEST_INPUT_FIELDS))
        self.assertEqual(policy['status'],
                         'required_inputs_have_validated_code_counterparts_no_runtime_router')
        self.assertTrue(set(policy['providers']) <= PROVIDER_NAMES)
        spec = self.contract_spec('policy')
        validate(spec)
        self.assertTrue(self.f.submit(spec))
        stored = self.f.inspect('policy')
        self.assertEqual(stored['spec_hash'], hashlib.sha256(canonical(spec).encode()).hexdigest())
        wrong_types = {
            'role': 1, 'risk_tier': 1, 'required_capabilities': 'text',
            'project_constraints': 'text', 'measured_evidence': 'text',
            'provider_availability': 'text', 'budget': 'text',
        }
        for name, location in REQUEST_INPUT_FIELDS.items():
            if location.startswith('contract.'):
                field = location.split('.', 1)[1]
                with self.subTest(input=name, missing=True):
                    block = self.contract()
                    del block[field]
                    with self.assertRaises(ValueError):
                        self.f.submit(self.contract_spec('policy-missing', block))
                with self.subTest(input=name, wrong_type=True):
                    block = self.contract()
                    block[field] = wrong_types[field]
                    with self.assertRaises(ValueError):
                        self.f.submit(self.contract_spec('policy-wrong', block))
            elif location == 'id':
                with self.subTest(input=name):
                    spec_without_id = self.contract_spec('policy-no-id')
                    del spec_without_id['id']
                    with self.assertRaises(ValueError):
                        self.f.submit(spec_without_id)

    def test_unhashable_contract_values_are_validation_errors(self):
        cases = (
            ('role', ['implementation']),
            ('role', {'role': 'implementation'}),
            ('risk_tier', ['low']),
            ('risk_tier', {'risk': 'low'}),
            ('acceptance_ids', [['A1']]),
            ('acceptance_ids', [{'id': 'A1'}]),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                block = self.contract()
                block[field] = value
                with self.assertRaises(ValueError):
                    self.f.submit(self.contract_spec('unhashable', block))

    def test_invalid_task_reports_a_json_error_without_a_traceback(self):
        spec = self.contract_spec('cli-bad')
        spec['contract']['role'] = ['not', 'a', 'string']
        path = self.root / 'bad.json'
        path.write_text(json.dumps(spec))
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        result = subprocess.run(
            [sys.executable, '-m', 'overseer.factory', '--db',
             str(self.root / 'cli' / 'jobs.sqlite3'), 'submit', str(path)],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn('error', json.loads(result.stdout))
        self.assertNotIn('Traceback', result.stderr)

    def test_a_spec_without_a_contract_still_runs(self):
        spec = {'id': 'legacy', 'objective': 'write and independently verify result',
                'workspace': str(self.root), 'timeout_seconds': 5,
                'implementation': [sys.executable, '-c',
                                   "from pathlib import Path; Path('result').write_text('ok')"],
                'checks': [[sys.executable, '-c',
                            "from pathlib import Path; assert Path('result').read_text() == 'ok'"]]}
        with self.assertRaisesRegex(ValueError, 'contract'):
            self.f.submit(spec)
        # A job stored before the rule is never re-validated, is not rewritten,
        # and is still dispatched and inspected.
        digest = store_legacy_job(self.f, spec)
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        saved = self.f.inspect('legacy')
        self.assertIsNone(saved['contract'])
        self.assertEqual(saved['spec_hash'], digest)
        self.assertNotIn('contract', saved['spec'])


class EnvelopeTests(unittest.TestCase):
    """The envelope block and the awaiting-approval gate."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'state' / 'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def envelope(self, **overrides):
        block = {
            'mode': 'draft_change',
            'scope': ['src/', 'tests/'],
            'requires_decision': True,
            'decider': 'operator',
        }
        block.update(overrides)
        return block

    def command_spec(self, name='one', envelope=None, checks=None):
        spec = {
            'id': name, 'objective': 'write and independently verify result',
            'workspace': str(self.root), 'timeout_seconds': 5,
            'implementation': [sys.executable, '-c',
                               "from pathlib import Path; Path('marker').write_text('ok')"],
            'checks': checks or [[sys.executable, '-c',
                                  "from pathlib import Path; assert Path('marker').read_text() == 'ok'"]],
        }
        if envelope is not None:
            spec['envelope'] = envelope
        return attach_contract(spec)

    def envelope_spec(self, name='one', envelope=None):
        return self.command_spec(name, self.envelope() if envelope is None else envelope)

    def run_cli(self, *arguments, expect=0):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        result = subprocess.run(
            [sys.executable, '-m', 'overseer.factory', '--db',
             str(self.root / 'cli' / 'jobs.sqlite3'), *arguments],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=env)
        self.assertEqual(result.returncode, expect, result.stderr)
        return result

    def test_valid_envelope_is_accepted_and_recorded(self):
        spec = self.envelope_spec('env-one')
        self.assertTrue(self.f.submit(spec))
        saved = self.f.inspect('env-one')
        self.assertEqual(saved['envelope'], spec['envelope'])
        self.assertEqual(saved['spec']['envelope'], spec['envelope'])
        self.assertIsNone(saved['approval'])
        self.f.decide('env-one', 'granted', 'operator', 'note')
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        recorded = json.loads((Path(result['evidence']) / 'task.json').read_text())
        self.assertEqual(recorded['envelope'], spec['envelope'])

    def test_envelope_field_validation_is_strict(self):
        cases = (
            ('mode', 'not-a-mode'),
            ('scope', 'not a list'),
            ('scope', []),
            ('scope', ['']),
            ('scope', [123]),
            ('scope', ['x' * 201]),
            ('requires_decision', 'yes'),
            ('decider', ''),
            ('decider', '   '),
            ('decider', 12),
            ('decider', 'x' * 81),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                block = self.envelope()
                block[field] = value
                with self.assertRaises(ValueError) as caught:
                    self.f.submit(self.envelope_spec('invalid', block))
                self.assertIn(field, str(caught.exception))
        for field in ('mode', 'scope', 'requires_decision', 'decider'):
            with self.subTest(missing=field):
                block = self.envelope()
                del block[field]
                with self.assertRaises(ValueError):
                    self.f.submit(self.envelope_spec('invalid', block))
        with self.subTest(unknown='verifier'):
            block = self.envelope()
            block['verifier'] = 'anything'
            with self.assertRaises(ValueError):
                self.f.submit(self.envelope_spec('invalid', block))

    def test_unhashable_envelope_values_are_validation_errors(self):
        cases = (
            ('mode', ['draft_change']),
            ('mode', {'mode': 'draft_change'}),
            ('scope', {'scope': ['src/']}),
            ('requires_decision', []),
            ('decider', {'decider': 'operator'}),
        )
        for field, value in cases:
            with self.subTest(field=field, value=value):
                block = self.envelope()
                block[field] = value
                with self.assertRaises(ValueError):
                    self.f.submit(self.envelope_spec('unhashable', block))

    def test_requires_decision_accepts_only_real_booleans(self):
        for value in (1, 0, 'true', None):
            with self.subTest(value=value):
                block = self.envelope(requires_decision=value)
                with self.assertRaises(ValueError):
                    self.f.submit(self.envelope_spec('boolean', block))
        for value in (True, False):
            with self.subTest(value=value):
                block = self.envelope(requires_decision=value)
                self.assertTrue(self.f.submit(self.envelope_spec('boolean-' + str(value), block)))

    def test_controller_modes_reject_an_envelope_and_keep_their_key_sets(self):
        specs = (
            ({'id': 'f', 'objective': 'o', 'mode': 'fixture', 'fixture': 'known_good'},
             {'id', 'objective', 'mode', 'fixture'}),
            ({'id': 'p', 'objective': 'o', 'mode': 'fake_provider', 'scenario': 'success'},
             {'id', 'objective', 'mode', 'scenario'}),
            ({'id': 'i', 'objective': 'o', 'mode': 'isolation_probe'},
             {'id', 'objective', 'mode'}),
        )
        for spec, accepted in specs:
            with self.subTest(spec=spec):
                with self.assertRaises(ValueError):
                    self.f.submit({**spec, 'envelope': self.envelope()})
                with self.assertRaises(ValueError):
                    self.f.submit({**spec, 'contract': {}})
                source = dict(spec)
                source['id'] = source['id'] + '-plain'
                self.assertTrue(self.f.submit(source))
                stored = json.loads(self.f.db.execute(
                    'SELECT spec FROM jobs WHERE id=?', (source['id'],)).fetchone()['spec'])
                self.assertEqual(set(stored), accepted)

    def test_envelope_is_covered_by_the_frozen_spec_hash(self):
        spec = self.envelope_spec('frozen')
        self.assertTrue(self.f.submit(spec))
        changed = self.envelope_spec('frozen')
        changed['envelope']['mode'] = 'release'
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.f.submit(changed)
        self.assertFalse(self.f.submit(self.envelope_spec('frozen')))

    def test_a_waiting_task_is_not_dispatched(self):
        self.assertTrue(self.f.submit(self.envelope_spec('waiting')))
        self.assertEqual(self.f.inspect('waiting')['state'], 'awaiting_approval')
        self.assertIsNone(self.f.run_one())
        self.assertFalse((self.root / 'marker').exists())
        self.assertEqual(self.f.inspect('waiting')['state'], 'awaiting_approval')
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE id='waiting' AND run_id IS NOT NULL").fetchone()['n'], 0)
        runs = self.root / 'state' / 'runs'
        self.assertFalse(runs.exists() and any(runs.iterdir()))

    def test_a_waiting_task_does_not_starve_queued_work(self):
        self.assertTrue(self.f.submit(self.envelope_spec('waiting')))
        self.assertTrue(self.f.submit(self.command_spec('ordinary')))
        result = self.f.run_one()
        self.assertEqual(result['id'], 'ordinary')
        self.assertTrue((self.root / 'marker').exists())
        self.assertEqual(self.f.inspect('waiting')['state'], 'awaiting_approval')

    def test_a_grant_queues_the_task_and_records_the_decider(self):
        self.assertTrue(self.f.submit(self.envelope_spec('granted')))
        decided = self.f.decide('granted', 'granted', 'operator', 'a note')
        self.assertEqual(decided['state'], 'queued')
        record = self.f.inspect('granted')['approval']
        self.assertEqual(record['decision'], 'granted')
        self.assertEqual(record['decider'], 'operator')
        self.assertEqual(record['note'], 'a note')
        self.assertGreater(record['at'], 0)
        self.assertEqual(record['spec_hash'], self.f.inspect('granted')['spec_hash'])
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        self.assertTrue((self.root / 'marker').exists())

    def test_a_refusal_is_terminal_and_records_no_run(self):
        self.assertTrue(self.f.submit(self.envelope_spec('refused')))
        decided = self.f.decide('refused', 'refused', 'operator', 'not now')
        self.assertEqual(decided['state'], 'refused')
        self.assertEqual(self.f.inspect('refused')['approval']['decision'], 'refused')
        self.assertIsNone(self.f.run_one())
        self.assertFalse((self.root / 'marker').exists())

    def test_decisions_fail_closed(self):
        self.assertTrue(self.f.submit(self.envelope_spec('closed')))
        with self.assertRaises(ValueError):
            self.f.decide('unknown-job', 'granted', 'operator')
        with self.assertRaises(ValueError):
            self.f.decide('closed', 'maybe', 'operator')
        with self.assertRaises(ValueError):
            self.f.decide('closed', 'granted', '   ')
        self.f.decide('closed', 'granted', 'operator', 'first')
        with self.assertRaises(ValueError):
            self.f.decide('closed', 'refused', 'operator', 'second')
        record = self.f.inspect('closed')['approval']
        self.assertEqual(record['decision'], 'granted')
        self.assertEqual(record['note'], 'first')
        self.f.db.execute("UPDATE jobs SET state='running' WHERE id='closed'")
        with self.assertRaises(ValueError):
            self.f.decide('closed', 'refused', 'operator')

    def test_the_decider_identity_is_recorded_not_authorized(self):
        block = self.envelope(decider='factory-director')
        self.assertTrue(self.f.submit(self.envelope_spec('identity', block)))
        self.f.decide('identity', 'granted', 'someone-else', 'note')
        saved = self.f.inspect('identity')
        self.assertEqual(saved['envelope']['decider'], 'factory-director')
        self.assertEqual(saved['approval']['decider'], 'someone-else')

    def test_the_decision_survives_a_backup_and_restore(self):
        self.assertTrue(self.f.submit(self.envelope_spec('restored')))
        self.f.decide('restored', 'granted', 'operator', 'note')
        before = self.f.inspect('restored')['approval']
        destination = self.root / 'backup.sqlite3'
        self.f.backup(destination)
        self.f.restore(destination)
        after = self.f.inspect('restored')
        self.assertEqual(after['approval'], before)
        self.assertEqual(after['state'], 'queued')

    def test_cancelling_a_waiting_task_records_that_nothing_ran(self):
        self.assertTrue(self.f.submit(self.envelope_spec('cancelled')))
        self.f.cancel('cancelled')
        saved = self.f.inspect('cancelled')
        self.assertEqual(saved['state'], 'cancelled')
        self.assertIn('dispatched no command', saved['detail'])
        self.assertIn('no external effect', saved['detail'])
        self.assertIsNone(saved['approval'])
        self.assertEqual(self.f.db.execute(
            "SELECT COUNT(*) AS n FROM approvals WHERE job_id='cancelled'").fetchone()['n'], 0)
        with self.assertRaises(ValueError):
            self.f.decide('cancelled', 'granted', 'operator')
        with self.assertRaises(ValueError):
            self.f.cancel('cancelled')

    def test_dispatch_is_refused_without_a_recorded_grant(self):
        self.assertTrue(self.f.submit(self.envelope_spec('forced')))
        self.f.db.execute("UPDATE jobs SET state='queued' WHERE id='forced'")
        self.f.db.commit()
        self.assertIsNone(self.f.run_one())
        self.assertEqual(self.f.inspect('forced')['state'], 'awaiting_approval')
        self.assertFalse((self.root / 'marker').exists())

    def test_the_decide_command_reports_errors_as_json(self):
        spec = self.envelope_spec('cli')
        path = self.root / 'cli.json'
        path.write_text(json.dumps(spec))
        self.run_cli('submit', str(path))
        granted = self.run_cli('decide', 'cli', '--decision', 'granted', '--decider', 'operator')
        self.assertEqual(json.loads(granted.stdout)['state'], 'queued')
        failed = self.run_cli('decide', 'missing', '--decision', 'granted', '--decider', 'operator', expect=1)
        self.assertIn('error', json.loads(failed.stdout))
        self.assertNotIn('Traceback', failed.stderr)
        status = self.run_cli('status')
        rows = json.loads(status.stdout)
        self.assertEqual(rows[0]['approval']['decider'], 'operator')
        self.assertEqual(rows[0]['id'], 'cli')

    def test_cancel_refuses_a_task_that_started_running_in_between(self):
        self.assertTrue(self.f.submit(self.command_spec('racing')))
        competing = sqlite3.connect(self.db, timeout=10)

        def trace(statement):
            if statement.strip().upper().startswith('UPDATE JOBS SET STATE'):
                competing.execute("UPDATE jobs SET state='running' WHERE id='racing'")
                competing.commit()

        self.f.db.set_trace_callback(trace)
        try:
            with self.assertRaises(ValueError):
                self.f.cancel('racing')
        finally:
            self.f.db.set_trace_callback(None)
            competing.close()
        saved = self.f.inspect('racing')
        self.assertEqual(saved['state'], 'running')
        events = [e['state'] for e in saved['events']]
        self.assertNotIn('cancelled', events)

    def test_the_decision_updates_the_job_detail(self):
        self.assertTrue(self.f.submit(self.envelope_spec('detail-granted')))
        granted = self.f.decide('detail-granted', 'granted', 'operator', 'a note')
        self.assertIn('granted', granted['detail'])
        self.assertIn('operator', granted['detail'])
        self.assertNotIn('waiting for a recorded decision', granted['detail'])
        self.assertTrue(self.f.submit(self.envelope_spec('detail-refused')))
        refused = self.f.decide('detail-refused', 'refused', 'operator', 'not now')
        self.assertIn('refused', refused['detail'])
        self.assertIn('dispatched no command', refused['detail'])
        self.assertIn('no external effect', refused['detail'])
        self.assertNotIn('waiting for a recorded decision', refused['detail'])

    def test_a_task_that_needs_no_decision_is_queued_and_runs(self):
        block = self.envelope(requires_decision=False)
        self.assertTrue(self.f.submit(self.envelope_spec('no-decision', block)))
        self.assertEqual(self.f.inspect('no-decision')['state'], 'queued')
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        self.assertTrue((self.root / 'marker').exists())
        self.assertIsNone(self.f.inspect('no-decision')['approval'])

    def test_the_status_rows_carry_the_same_detail_as_inspect(self):
        self.assertTrue(self.f.submit(self.envelope_spec('status-detail')))
        self.f.decide('status-detail', 'granted', 'operator', 'note')
        path = self.root / 'status.json'
        path.write_text(json.dumps(self.envelope_spec('status-detail')))
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        result = subprocess.run(
            [sys.executable, '-m', 'overseer.factory', '--db', str(self.db), 'status'],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)
        row = [r for r in rows if r['id'] == 'status-detail'][0]
        self.assertEqual(row['detail'], self.f.inspect('status-detail')['detail'])
        self.assertIn('granted', row['detail'])


class ContextTests(unittest.TestCase):
    """The context manifest and the four memory record kinds."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'state' / 'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def command_spec(self, name='one', contract=None, checks=None, envelope=None):
        spec = {
            'id': name, 'objective': 'write and independently verify result',
            'workspace': str(self.root), 'timeout_seconds': 5,
            'implementation': [sys.executable, '-c',
                               "from pathlib import Path; Path('marker').write_text('ok')"],
            'checks': checks or [[sys.executable, '-c',
                                  "from pathlib import Path; assert Path('marker').read_text() == 'ok'"]],
        }
        if contract is not None:
            spec['contract'] = contract
        if envelope is not None:
            spec['envelope'] = envelope
        if contract is None:
            return attach_contract(spec)
        return spec

    def envelope(self, **overrides):
        block = {
            'mode': 'draft_change',
            'scope': ['src/'],
            'requires_decision': True,
            'decider': 'operator',
        }
        block.update(overrides)
        return block

    def contract(self, **overrides):
        block = {
            'role': 'implementation',
            'risk_tier': 'medium',
            'external_effects': [],
            'protected_paths': [],
            'approval_requirements': [],
            'acceptance_ids': ['A1'],
            'required_capabilities': [],
            'project_constraints': [],
            'measured_evidence': None,
            'provider_availability': None,
            'budget': {
                'wall_time_seconds': 600, 'token_limit': None, 'cost_limit_usd': None,
                'resource_limits': None, 'repair_allowance': 0,
            },
        }
        block.update(overrides)
        return block

    def manifest_of(self, result):
        return json.loads((Path(result['evidence']) / 'context.json').read_text())

    def git(self, *arguments, cwd=None):
        return subprocess.run(['git', *arguments], cwd=cwd, capture_output=True, text=True,
                              timeout=60)

    def test_a_context_manifest_is_written_into_the_run_evidence_directory(self):
        self.assertTrue(self.f.submit(self.command_spec('manifest')))
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        self.assertTrue((Path(result['evidence']) / 'context.json').is_file())

    def test_the_context_manifest_names_the_objective_and_the_spec_hash(self):
        spec = self.command_spec('named')
        self.assertTrue(self.f.submit(spec))
        result = self.f.run_one()
        manifest = self.manifest_of(result)
        self.assertEqual(manifest['version'], 1)
        self.assertEqual(manifest['job_id'], 'named')
        self.assertEqual(manifest['run_id'], result['run_id'])
        self.assertEqual(manifest['objective'], spec['objective'])
        self.assertEqual(manifest['spec_hash'], result['spec_hash'])
        self.assertEqual(manifest['mode'], 'command')

    def test_the_context_manifest_lists_the_commands_actually_run(self):
        self.assertTrue(self.f.submit(self.command_spec('commands')))
        result = self.f.run_one()
        commands = self.manifest_of(result)['commands_actually_run']
        self.assertEqual([c['stage'] for c in commands], ['implementation', 'acceptance'])
        self.assertEqual(commands[0]['argv'], self.command_spec('commands')['implementation'])
        self.assertEqual(commands[1]['argv'], self.command_spec('commands')['checks'][0])
        self.assertEqual(commands[0]['exit_code'], 0)
        self.assertFalse(commands[0]['timed_out'])
        failing = self.command_spec('failing')
        failing['checks'] = [[sys.executable, '-c', 'raise SystemExit(3)']]
        failing = attach_contract(failing)
        self.assertTrue(self.f.submit(failing))
        failed = self.f.run_one()
        self.assertEqual(failed['state'], 'failed')
        stopped = self.manifest_of(failed)['commands_actually_run']
        self.assertEqual([c['stage'] for c in stopped], ['implementation', 'acceptance'])
        self.assertEqual(stopped[-1]['exit_code'], 3)

    def test_the_context_manifest_marks_a_non_repository_workspace_honestly(self):
        workspace = self.root / 'plain'
        workspace.mkdir()
        spec = self.command_spec('plain')
        spec['workspace'] = str(workspace)
        self.assertTrue(self.f.submit(spec))
        result = self.f.run_one()
        repository = self.manifest_of(result)['repository']
        probe = self.git('-C', str(workspace), 'rev-parse', '--show-toplevel')
        if probe.returncode == 0:
            self.assertTrue(repository['present'])
        else:
            self.assertFalse(repository['present'])
            self.assertTrue(repository['reason'])
            self.assertNotIn('root', repository)
            self.assertNotIn('base_commit', repository)
        with patch.dict(os.environ, {'PATH': str(self.root / 'empty-bin')}):
            (self.root / 'empty-bin').mkdir(exist_ok=True)
            identity = repository_identity(str(workspace))
        self.assertFalse(identity['present'])
        self.assertIn('git', identity['reason'])

    def test_the_context_manifest_names_the_repository_root_and_base_commit(self):
        workspace = self.root / 'repo'
        workspace.mkdir()
        self.git('init', '--quiet', str(workspace))
        (workspace / 'file.txt').write_text('content\n')
        self.git('-c', 'user.email=test@example.invalid', '-c', 'user.name=test',
                'add', 'file.txt', cwd=str(workspace))
        self.git('-c', 'user.email=test@example.invalid', '-c', 'user.name=test',
                'commit', '--quiet', '-m', 'initial', cwd=str(workspace))
        head = self.git('-C', str(workspace), 'rev-parse', 'HEAD').stdout.strip()
        spec = self.command_spec('repo')
        spec['workspace'] = str(workspace)
        self.assertTrue(self.f.submit(spec))
        result = self.f.run_one()
        repository = self.manifest_of(result)['repository']
        self.assertTrue(repository['present'])
        self.assertEqual(repository['base_commit'], head)
        self.assertEqual(Path(repository['root']).resolve(), workspace.resolve())
        self.assertIn('rev-parse', repository['base_commit_source'])

    def test_the_context_manifest_records_the_contract_acceptance_ids(self):
        self.assertTrue(self.f.submit(self.command_spec('with-contract', self.contract())))
        with_contract = self.manifest_of(self.f.run_one())
        self.assertEqual(with_contract['acceptance_ids'], ['A1'])
        self.assertEqual(with_contract['acceptance_ids_source'], 'contract')
        # A stored job from before the contract rule carries no identifiers.
        legacy = {'id': 'without-contract', 'objective': 'write and independently verify result',
                  'workspace': str(self.root), 'timeout_seconds': 5,
                  'implementation': [sys.executable, '-c',
                                     "from pathlib import Path; Path('marker').write_text('ok')"],
                  'checks': [[sys.executable, '-c',
                              "from pathlib import Path; assert Path('marker').read_text() == 'ok'"]]}
        store_legacy_job(self.f, legacy)
        without = self.manifest_of(self.f.run_one())
        self.assertEqual(without['acceptance_ids'], [])
        self.assertEqual(without['acceptance_ids_source'], 'absent')

    def test_the_context_manifest_records_what_it_supplied_and_why(self):
        self.assertTrue(self.f.submit(self.command_spec('supplied')))
        manifest = self.manifest_of(self.f.run_one())
        items = [entry['item'] for entry in manifest['supplied']]
        self.assertEqual(items, ['objective', 'required_behavior', 'relevant_code_and_interfaces',
                                  'recent_verified_failures', 'applicable_decisions',
                                  'deeper_evidence'])
        for entry in manifest['supplied']:
            self.assertTrue(entry['why'])
            if entry['source'] is None:
                self.assertTrue(entry['why'])

    def test_the_context_manifest_marks_unmeasured_values_as_unmeasured(self):
        self.assertTrue(self.f.submit(self.command_spec('unmeasured')))
        manifest = self.manifest_of(self.f.run_one())
        self.assertIsNone(manifest['environment']['tokens'])
        self.assertIsNone(manifest['environment']['cost_usd'])
        for name in ('tokens', 'cost_usd', 'candidate_revision', 'remaining_budget'):
            self.assertIn(name, manifest['unmeasured'])
        text = json.dumps(manifest)
        self.assertNotIn('output_truncated', text)
        self.assertNotIn('stdout', text)
        self.assertNotIn('stderr', text)
        self.assertFalse(manifest['memory']['consumed'])

    def test_memory_records_of_the_four_kinds_are_stored_and_queryable(self):
        self.assertTrue(self.f.submit(self.command_spec('memory')))
        self.assertTrue(self.f.submit(self.command_spec('other')))
        self.f.record_memory('memory', 'verified_fact', 'the package passed the test',
                             'the acceptance command', 'the package', 'a new release',
                             revision='abc123', environment='linux')
        self.f.record_memory('memory', 'decision', 'keep the filter semantics',
                             'the operator', 'the filter', 'a new requirement',
                             owner='operator', reason='compatibility')
        self.f.record_memory('memory', 'hypothesis', 'a new import flow may reduce effort',
                             'a note', 'the importer', 'a measurement')
        self.f.record_memory('memory', 'historical_attempt', 'the earlier OCR change failed',
                             'an old run', 'the OCR tool', 'a new fixture')
        records = self.f.memory('memory')
        self.assertEqual(len(records), 4)
        self.assertEqual({record['kind'] for record in records}, set(MEMORY_KINDS))
        self.assertEqual(len(self.f.memory('memory', kind='decision')), 1)
        self.assertEqual(self.f.memory('memory', kind='decision')[0]['kind'], 'decision')
        self.assertEqual(self.f.memory('other'), [])
        self.assertEqual(len(self.f.inspect('memory')['memory']), 4)

    def test_a_hypothesis_is_stored_and_read_back_as_unverified(self):
        self.assertTrue(self.f.submit(self.command_spec('hypothesis')))
        record = self.f.record_memory('hypothesis', 'hypothesis', 'the flow may be faster',
                                      'a note', 'the importer', 'a measurement')
        self.assertFalse(record['verified'])
        self.assertFalse(record['current'])
        self.assertFalse(self.f.memory('hypothesis')[0]['verified'])

    def test_a_decision_can_name_a_superseding_decision(self):
        self.assertTrue(self.f.submit(self.command_spec('decisions')))
        first = self.f.record_memory('decisions', 'decision', 'keep the old behaviour',
                                     'the operator', 'the filter', 'a new requirement',
                                     owner='operator', reason='compatibility')
        second = self.f.record_memory('decisions', 'decision', 'replace the old behaviour',
                                      'the operator', 'the filter', 'a new requirement',
                                      owner='operator', reason='measured', supersedes=first['record_id'])
        self.assertEqual(second['supersedes'], first['record_id'])
        records = {record['record_id']: record for record in self.f.memory('decisions')}
        self.assertEqual(records[first['record_id']]['superseded_by'], second['record_id'])
        self.assertFalse(records[first['record_id']]['current'])
        self.assertTrue(records[second['record_id']]['current'])
        self.assertIsNone(records[second['record_id']]['verified'])

    def test_every_memory_record_carries_its_source_timestamp_component_and_invalidation(self):
        self.assertTrue(self.f.submit(self.command_spec('fields')))
        record = self.f.record_memory('fields', 'historical_attempt', 'it failed',
                                      'an old run', 'the tool', 'a new fixture')
        self.assertTrue(record['source'])
        self.assertTrue(record['affected_component'])
        self.assertTrue(record['invalidation_condition'])
        self.assertGreater(record['at'], 0)
        for missing in ('source', 'affected_component', 'invalidation_condition'):
            with self.subTest(missing=missing):
                arguments = {'entry': 'it failed', 'source': 'an old run',
                             'affected_component': 'the tool',
                             'invalidation_condition': 'a new fixture'}
                arguments[missing] = ''
                with self.assertRaises(ValueError):
                    self.f.record_memory('fields', 'historical_attempt', **arguments)

    def test_a_verified_fact_must_bind_to_a_revision_and_an_environment(self):
        self.assertTrue(self.f.submit(self.command_spec('fact')))
        with self.assertRaises(ValueError):
            self.f.record_memory('fact', 'verified_fact', 'it passed', 'a run',
                                 'the package', 'a new release', revision='abc')
        with self.assertRaises(ValueError):
            self.f.record_memory('fact', 'verified_fact', 'it passed', 'a run',
                                 'the package', 'a new release', environment='linux')
        record = self.f.record_memory('fact', 'verified_fact', 'it passed', 'a run',
                                      'the package', 'a new release',
                                      revision='abc123', environment='linux')
        self.assertTrue(record['verified'])
        self.assertTrue(record['current'])

    def test_memory_record_validation_rejects_bad_input(self):
        self.assertTrue(self.f.submit(self.command_spec('invalid')))
        with self.assertRaises(ValueError):
            self.f.record_memory('invalid', 'not_a_kind', 'entry', 'source', 'component', 'condition')
        with self.assertRaises(ValueError):
            self.f.record_memory('missing-job', 'hypothesis', 'entry', 'source',
                                 'component', 'condition')
        with self.assertRaises(ValueError):
            self.f.record_memory('invalid', 'hypothesis', '', 'source', 'component', 'condition')
        with self.assertRaises(ValueError):
            self.f.record_memory('invalid', 'decision', 'entry', 'source', 'component',
                                 'condition', owner='operator', reason='why',
                                 supersedes='no-such-record')
        with self.assertRaises(ValueError):
            self.f.record_memory('invalid', 'decision', 'entry', 'source', 'component',
                                 'condition', reason='why')

    def test_the_ledger_records_the_manifest_path_and_digest(self):
        self.assertTrue(self.f.submit(self.command_spec('ledger')))
        result = self.f.run_one()
        manifest_path = Path(result['evidence']) / 'context.json'
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        summary = json.loads((Path(result['evidence']) / 'summary.json').read_text())
        self.assertEqual(summary['context_manifest']['path'], str(manifest_path))
        self.assertEqual(summary['context_manifest']['sha256'], digest)
        events = [event for event in self.f.inspect('ledger')['events']
                  if event['state'] == 'context_manifest']
        self.assertEqual(len(events), 1)
        self.assertIn(digest, events[0]['detail'])

    def test_the_manifest_and_memory_records_survive_a_backup_and_restore(self):
        self.assertTrue(self.f.submit(self.command_spec('durable')))
        self.f.record_memory('durable', 'verified_fact', 'it passed', 'a run',
                             'the package', 'a new release',
                             revision='abc123', environment='linux')
        result = self.f.run_one()
        manifest_path = Path(result['evidence']) / 'context.json'
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        destination = self.root / 'backup.sqlite3'
        self.f.backup(destination)
        self.f.restore(destination)
        records = self.f.memory('durable')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['entry'], 'it passed')
        events = [event for event in self.f.inspect('durable')['events']
                  if event['state'] == 'context_manifest']
        self.assertIn(digest, events[0]['detail'])
        self.assertTrue(manifest_path.is_file())

    def test_the_existing_acceptance_lease_restore_and_approval_paths_still_pass(self):
        self.assertTrue(self.f.submit(self.command_spec('acceptance')))
        accepted = self.f.run_one()
        self.assertEqual(accepted['state'], 'passed')
        self.assertTrue(self.f.submit(self.command_spec('lease', envelope=self.envelope())))
        self.assertEqual(self.f.inspect('lease')['state'], 'awaiting_approval')
        self.f.decide('lease', 'granted', 'operator', 'note')
        self.assertEqual(self.f.inspect('lease')['state'], 'queued')
        destination = self.root / 'backup.sqlite3'
        self.f.backup(destination)
        self.f.restore(destination)
        self.assertEqual(self.f.inspect('acceptance')['state'], 'passed')

    def test_a_ledger_without_the_memory_table_opens_and_restores(self):
        legacy = self.root / 'legacy.sqlite3'
        connection = sqlite3.connect(legacy)
        connection.execute('CREATE TABLE jobs (seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,'
                           ' spec TEXT NOT NULL, spec_hash TEXT NOT NULL, state TEXT NOT NULL,'
                           ' created REAL NOT NULL, started REAL, finished REAL, run_id TEXT,'
                           ' evidence TEXT, detail TEXT, child_group INTEGER)')
        connection.commit()
        connection.close()
        factory = Factory(legacy)
        self.addCleanup(factory.close)
        self.assertTrue(self.f.submit(self.command_spec('legacy-job')))
        destination = self.root / 'legacy-backup.sqlite3'
        self.f.backup(destination)
        self.f.restore(destination)
        self.assertEqual(len(self.f.memory('legacy-job')), 0)


class RequiredContractTests(unittest.TestCase):
    """The contract block is required for new command-mode submissions."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'state' / 'jobs.sqlite3'
        self.f = Factory(self.db)
        self.addCleanup(self.f.close)

    def command_spec(self, name='one'):
        return {'id': name, 'objective': 'write and independently verify result',
                'workspace': str(self.root), 'timeout_seconds': 5,
                'implementation': [sys.executable, '-c',
                                   "from pathlib import Path; Path('marker').write_text('ok')"],
                'checks': [[sys.executable, '-c',
                            "from pathlib import Path; assert Path('marker').read_text() == 'ok'"]]}

    def test_a_command_mode_task_without_a_contract_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self.f.submit(self.command_spec('no-contract'))
        self.assertIn('contract', str(caught.exception))
        self.assertEqual(
            self.f.db.execute("SELECT COUNT(*) AS n FROM jobs WHERE id='no-contract'").fetchone()['n'], 0)

    def test_a_command_mode_task_with_a_contract_is_accepted(self):
        self.assertTrue(self.f.submit(attach_contract(self.command_spec('with-contract'))))
        self.assertEqual(self.f.inspect('with-contract')['state'], 'queued')

    def test_the_controller_modes_still_run_without_a_contract(self):
        specs = (
            {'id': 'f', 'objective': 'o', 'mode': 'fixture', 'fixture': 'known_good'},
            {'id': 'p', 'objective': 'o', 'mode': 'fake_provider', 'scenario': 'success'},
            {'id': 'i', 'objective': 'o', 'mode': 'isolation_probe'},
        )
        for spec in specs:
            with self.subTest(spec=spec):
                self.assertTrue(self.f.submit(spec))
        self.assertEqual(self.f.run_one()['state'], 'passed')

    def test_a_stored_legacy_job_still_runs_and_is_not_rewritten(self):
        spec = self.command_spec('legacy')
        digest = store_legacy_job(self.f, spec)
        result = self.f.run_one()
        self.assertEqual(result['state'], 'passed')
        saved = self.f.inspect('legacy')
        self.assertIsNone(saved['contract'])
        self.assertEqual(saved['spec_hash'], digest)
        self.assertNotIn('contract', saved['spec'])

    def test_the_repository_example_task_carries_a_valid_contract(self):
        spec = json.loads((ROOT / 'factory' / 'tasks' / 'overseer-checks.json').read_text())
        self.assertEqual(set(spec['contract']), set(CONTRACT_FIELDS))
        validate(spec)
        self.assertTrue(self.f.submit(spec))
        self.assertEqual(self.f.inspect(spec['id'])['contract']['risk_tier'],
                         spec['contract']['risk_tier'])

    def test_the_runner_reports_the_missing_contract_as_a_json_error(self):
        path = self.root / 'no-contract.json'
        path.write_text(json.dumps(self.command_spec('cli-no-contract')))
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        result = subprocess.run(
            [sys.executable, '-m', 'overseer.factory', '--db',
             str(self.root / 'cli' / 'jobs.sqlite3'), 'submit', str(path)],
            capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=env)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('contract', json.loads(result.stdout)['error'])
        self.assertNotIn('Traceback', result.stderr)
