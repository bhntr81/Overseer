"""Explicit, single-worker local jobs. Trusted commands only; not a sandbox."""
import argparse
from contextlib import contextmanager
import fcntl
from overseer.isolation import run_isolation_probe
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import subprocess
import sys
import time
import uuid

DEFAULT_DB = Path.home() / '.local/state/overseer/factory/jobs.sqlite3'
LIVE = ('running', 'checking', 'needs_reconciliation')


def canonical(spec):
    return json.dumps(spec, sort_keys=True, separators=(',', ':'))


FIXTURE_ALLOWED_PATHS = frozenset({'candidate.json'})
FIXTURE_CANDIDATES = {
    'known_good': b'{"answer":42}\n',
    'known_bad': b'{"answer":41}\n',
    'tamper_after_check': b'{"answer":42}\n',
}
FIXTURE_TAMPER_BYTES = b'{"answer":41}\n'
FIXTURE_VERIFIER_MANIFEST = {
    'version': 1,
    'verifier': 'json-answer-equals-42',
    'expected_answer': 42,
    'allowed_candidate_paths': sorted(FIXTURE_ALLOWED_PATHS),
    'fixture_bytes': {name: data.decode('utf-8') for name, data in FIXTURE_CANDIDATES.items()},
    'post_check_tamper_bytes': FIXTURE_TAMPER_BYTES.decode('utf-8'),
}
FIXTURE_VERIFIER_ID = 'fixture-answer-v1:' + hashlib.sha256(
    canonical(FIXTURE_VERIFIER_MANIFEST).encode('utf-8')
).hexdigest()

FAKE_PROVIDER_SCENARIOS = frozenset({'success', 'incorrect', 'timeout', 'interrupted'})
FAKE_PROVIDER_GOOD = b'{"answer":42}\n'
FAKE_PROVIDER_BAD = b'{"answer":41}\n'
FAKE_PROVIDER_VERIFIER_MANIFEST = {
    'version': 1,
    'verifier': 'fake-provider-json-answer-equals-42',
    'expected_answer': 42,
    'candidate_path': 'candidate.json',
    'scenarios': sorted(FAKE_PROVIDER_SCENARIOS),
}
FAKE_PROVIDER_VERIFIER_ID = 'fake-provider-answer-v1:' + hashlib.sha256(
    canonical(FAKE_PROVIDER_VERIFIER_MANIFEST).encode('utf-8')
).hexdigest()

# The closed contract block. These fields are recorded, never enforced.
CONTRACT_FIELDS = (
    'role', 'risk_tier', 'external_effects', 'protected_paths',
    'approval_requirements', 'acceptance_ids', 'required_capabilities',
    'project_constraints', 'measured_evidence', 'provider_availability', 'budget',
)
BUDGET_FIELDS = (
    'wall_time_seconds', 'token_limit', 'cost_limit_usd',
    'resource_limits', 'repair_allowance',
)
RESOURCE_LIMIT_NAMES = frozenset({
    'cpu_seconds', 'memory_mb', 'process_count', 'disk_mb',
})
CONTRACT_ROLES = frozenset({'implementation', 'verification', 'review', 'research'})
RISK_TIERS = frozenset({'low', 'medium', 'high'})
PROVIDER_NAMES = frozenset({'codex', 'claude', 'cursor', 'grok_build', 'grok_bot'})
IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}')
EVIDENCE_IDENTIFIER = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}')

# The closed envelope block. The mode, scope, and decider are recorded, never
# enforced; the only enforced part is the gate that keeps a task waiting.
ENVELOPE_FIELDS = ('mode', 'scope', 'requires_decision', 'decider')
ENVELOPE_MODES = frozenset({
    'investigation', 'draft_change', 'bounded_maintenance', 'release',
})
DECISIONS = frozenset({'granted', 'refused'})

# The four memory record kinds. They are stored and queryable, and nothing
# reads them to change a decision.
MEMORY_KINDS = ('verified_fact', 'decision', 'hypothesis', 'historical_attempt')

# Code counterpart for factory/routing-policy.json:9 required_inputs. The JSON
# file is not read at run time; the test suite proves the two agree.
REQUEST_INPUT_FIELDS = {
    'task_id': 'id',
    'spec_hash': 'derived: sha256 of the canonical spec',
    'role': 'contract.role',
    'risk': 'contract.risk_tier',
    'required_capabilities': 'contract.required_capabilities',
    'project_constraints': 'contract.project_constraints',
    'measured_evidence': 'contract.measured_evidence',
    'provider_availability': 'contract.provider_availability',
    'budget': 'contract.budget',
}


def fixture_candidate_path(evidence, relative_path):
    """Resolve the fixture's one allowed output file without following links."""
    if not isinstance(relative_path, str) or relative_path not in FIXTURE_ALLOWED_PATHS:
        raise ValueError('candidate path is not allowlisted')
    evidence = Path(evidence)
    if evidence.is_symlink():
        raise ValueError('fixture evidence directory cannot be a symlink')
    root = evidence.resolve(strict=True)
    candidate = root / relative_path
    if candidate.is_symlink():
        raise ValueError('fixture candidate path cannot be a symlink')
    if candidate.parent.resolve(strict=True) != root:
        raise ValueError('fixture candidate path escapes its evidence directory')
    if candidate.exists() and candidate.resolve(strict=True).parent != root:
        raise ValueError('fixture candidate path escapes its evidence directory')
    return candidate


def verify_fixture_candidate(candidate_bytes):
    """Controller-owned verifier; never executes candidate-provided code."""
    try:
        candidate = json.loads(candidate_bytes.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, 'candidate is not valid UTF-8 JSON'
    if not isinstance(candidate, dict) or candidate.get('answer') != 42:
        return False, 'candidate does not contain the expected answer'
    return True, 'candidate contains the expected answer'


def verify_fake_provider_candidate(candidate_bytes):
    """Distinct fake-provider verifier. Task input cannot change this rule."""
    try:
        candidate = json.loads(candidate_bytes.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False, 'candidate is not valid UTF-8 JSON'
    if not isinstance(candidate, dict) or set(candidate) != {'answer'} or candidate.get('answer') != 42:
        return False, 'candidate does not contain the expected answer'
    return True, 'candidate contains the expected answer'


def _text_list(contract, field, maximum, item_max):
    value = contract[field]
    if not isinstance(value, list):
        raise ValueError(f'contract {field} must be a list')
    if len(value) > maximum:
        raise ValueError(f'contract {field} accepts at most {maximum} entries')
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f'contract {field} entries must be nonempty text')
        if len(item) > item_max or '\0' in item:
            raise ValueError(f'contract {field} entries must be short text without NUL')
    return value


def _identifier_list(contract, field, maximum):
    value = contract[field]
    if not isinstance(value, list):
        raise ValueError(f'contract {field} must be a list')
    if len(value) > maximum:
        raise ValueError(f'contract {field} accepts at most {maximum} entries')
    for item in value:
        if not isinstance(item, str) or IDENTIFIER.fullmatch(item) is None:
            raise ValueError(f'contract {field} entries must be identifiers')
    return value


def _validate_budget(budget):
    if not isinstance(budget, dict):
        raise ValueError('contract budget must be an object')
    if set(budget) != set(BUDGET_FIELDS):
        raise ValueError('contract budget must have exactly: ' + ', '.join(BUDGET_FIELDS))
    wall = budget['wall_time_seconds']
    if type(wall) is not int or not 1 <= wall <= 86400:
        raise ValueError('contract budget wall_time_seconds must be an integer from 1 to 86400')
    tokens = budget['token_limit']
    if tokens is not None and (type(tokens) is not int or tokens < 0):
        raise ValueError('contract budget token_limit must be null or a nonnegative integer')
    cost = budget['cost_limit_usd']
    if cost is not None and (type(cost) not in (int, float) or cost < 0):
        raise ValueError('contract budget cost_limit_usd must be null or a nonnegative number')
    limits = budget['resource_limits']
    if limits is not None:
        if not isinstance(limits, dict):
            raise ValueError('contract budget resource_limits must be null or an object')
        for name, value in limits.items():
            if name not in RESOURCE_LIMIT_NAMES:
                raise ValueError(f'contract budget resource_limits has an unknown limit: {name}')
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(
                    f'contract budget resource_limits {name} must be null or a nonnegative integer')
    allowance = budget['repair_allowance']
    if type(allowance) is not int or not 0 <= allowance <= 10:
        raise ValueError('contract budget repair_allowance must be an integer from 0 to 10')


def _validate_protected_paths(paths, workspace):
    root = os.path.normpath(workspace)
    for path in paths:
        if not isinstance(path, str) or not path.strip() or '\0' in path:
            raise ValueError('contract protected_paths entries must be nonempty text without NUL')
        if path.startswith('/') or (len(path) > 1 and path[1] == ':'):
            raise ValueError('contract protected_paths entries must be relative')
        if '..' in Path(path).parts:
            raise ValueError('contract protected_paths entries cannot escape the workspace')
        joined = os.path.normpath(os.path.join(root, path))
        if joined == root or not joined.startswith(root + os.sep):
            raise ValueError('contract protected_paths entries must stay inside the workspace')


def validate_contract(contract, spec):
    """Validate the optional contract block of a command-mode task spec.

    The block is recorded, not enforced: it states a risk tier, protected
    paths, approval requirements, acceptance identifiers, and a budget, and
    nothing in the runner acts on those statements.
    """
    if not isinstance(contract, dict):
        raise ValueError('contract must be an object')
    if set(contract) != set(CONTRACT_FIELDS):
        raise ValueError('contract must have exactly: ' + ', '.join(CONTRACT_FIELDS))
    if not isinstance(contract['role'], str) or contract['role'] not in CONTRACT_ROLES:
        raise ValueError('contract role must be one of: ' + ', '.join(sorted(CONTRACT_ROLES)))
    if not isinstance(contract['risk_tier'], str) or contract['risk_tier'] not in RISK_TIERS:
        raise ValueError('contract risk_tier must be one of: ' + ', '.join(sorted(RISK_TIERS)))
    _text_list(contract, 'external_effects', 16, 200)
    _text_list(contract, 'required_capabilities', 32, 200)
    _text_list(contract, 'project_constraints', 32, 200)
    _identifier_list(contract, 'approval_requirements', 16)
    _validate_protected_paths(contract['protected_paths'], spec['workspace'])

    identifiers = contract['acceptance_ids']
    if not isinstance(identifiers, list):
        raise ValueError('contract acceptance_ids must be a list')
    if len(identifiers) != len(spec['checks']):
        raise ValueError('contract acceptance_ids must match the number of acceptance commands')
    for identifier in identifiers:
        if not isinstance(identifier, str) or IDENTIFIER.fullmatch(identifier) is None:
            raise ValueError('contract acceptance_ids entries must be identifiers')
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('contract acceptance_ids entries must be unique')

    evidence = contract['measured_evidence']
    if evidence is not None:
        if not isinstance(evidence, list) or len(evidence) > 32:
            raise ValueError('contract measured_evidence must be null or a list of at most 32 entries')
        for item in evidence:
            if not isinstance(item, str) or EVIDENCE_IDENTIFIER.fullmatch(item) is None:
                raise ValueError('contract measured_evidence entries must be evidence identifiers')

    availability = contract['provider_availability']
    if availability is not None:
        if not isinstance(availability, dict):
            raise ValueError('contract provider_availability must be null or an object')
        for name, available in availability.items():
            if name not in PROVIDER_NAMES:
                raise ValueError(f'contract provider_availability has an unknown provider: {name}')
            if type(available) is not bool:
                raise ValueError('contract provider_availability values must be booleans')

    _validate_budget(contract['budget'])
    return contract


def validate_envelope(envelope, spec):
    """Validate the optional envelope block of a command-mode task spec.

    The block names one of the blueprint's four capability modes, its declared
    scope, whether a fresh decision is required, and the decider named by the
    submitter. The mode, the scope, and the decider identity are recorded, not
    authorized: no roster is checked and nothing compares the commands with
    the declared scope.
    """
    if not isinstance(envelope, dict):
        raise ValueError('envelope must be an object')
    if set(envelope) != set(ENVELOPE_FIELDS):
        raise ValueError('envelope must have exactly: ' + ', '.join(ENVELOPE_FIELDS))
    mode = envelope['mode']
    if not isinstance(mode, str) or mode not in ENVELOPE_MODES:
        raise ValueError('envelope mode must be one of: ' + ', '.join(sorted(ENVELOPE_MODES)))
    scope = envelope['scope']
    if not isinstance(scope, list):
        raise ValueError('envelope scope must be a list')
    if not 1 <= len(scope) <= 16:
        raise ValueError('envelope scope must hold between one and sixteen entries')
    for item in scope:
        if not isinstance(item, str) or not item.strip():
            raise ValueError('envelope scope entries must be nonempty text')
        if len(item) > 200 or '\0' in item or any(ord(char) < 32 for char in item):
            raise ValueError('envelope scope entries must be short text without control characters')
    if type(envelope['requires_decision']) is not bool:
        raise ValueError('envelope requires_decision must be a boolean')
    decider = envelope['decider']
    if not isinstance(decider, str) or not decider.strip():
        raise ValueError('envelope decider must be nonempty text')
    if len(decider) > 80 or '\0' in decider or any(ord(char) < 32 for char in decider):
        raise ValueError('envelope decider must be short text without control characters')
    return envelope


def _run_git(workspace, *arguments):
    """Read one git fact without writing to the workspace."""
    try:
        result = subprocess.run(['git', '-C', workspace, *arguments],
                                capture_output=True, text=True, timeout=10)
    except FileNotFoundError:
        return None, 'git is not available on this machine'
    except (OSError, subprocess.SubprocessError) as error:
        return None, 'git failed: ' + str(error)
    if result.returncode:
        lines = (result.stderr or '').strip().splitlines()
        return None, lines[0] if lines else f'git exited with status {result.returncode}'
    return result.stdout.strip(), None


def repository_identity(workspace):
    """Report the repository identity of a workspace, or the real reason there is none."""
    if not workspace:
        return {'present': False, 'reason': 'the task specification names no workspace'}
    root, problem = _run_git(workspace, 'rev-parse', '--show-toplevel')
    if root is None:
        return {'present': False, 'reason': problem}
    commit, problem = _run_git(workspace, 'rev-parse', 'HEAD')
    if commit is None:
        return {'present': False, 'reason': problem}
    return {'present': True, 'root': root, 'base_commit': commit,
            'base_commit_source': 'git rev-parse HEAD observed at attempt start'}


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError('invalid task object')
    if not isinstance(spec.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', spec['id']):
        raise ValueError('id must be a short filesystem-safe identifier')
    if not isinstance(spec.get('objective'), str) or not spec['objective'].strip():
        raise ValueError('objective is required')

    if spec.get('mode') == 'fixture':
        if set(spec) != {'id', 'objective', 'mode', 'fixture'}:
            raise ValueError('fixture tasks cannot provide commands, paths, callbacks, or verifier rules')
        if not isinstance(spec['fixture'], str) or spec['fixture'] not in FIXTURE_CANDIDATES:
            raise ValueError('unknown trusted fixture scenario')
        return spec

    if spec.get('mode') == 'fake_provider':
        if set(spec) != {'id', 'objective', 'mode', 'scenario'}:
            raise ValueError('fake-provider tasks cannot provide commands, paths, callbacks, or verifier rules')
        if not isinstance(spec.get('scenario'), str) or spec['scenario'] not in FAKE_PROVIDER_SCENARIOS:
            raise ValueError('unknown fake-provider scenario')
        return spec

    if spec.get('mode') == 'isolation_probe':
        if set(spec) != {'id', 'objective', 'mode'}:
            raise ValueError('isolation probes cannot provide commands, paths, callbacks, or verifier rules')
        return spec

    if 'mode' in spec or 'fixture' in spec or 'scenario' in spec or set(spec) - {
        'id', 'objective', 'workspace', 'implementation', 'checks', 'timeout_seconds',
        'contract', 'envelope'
    }:
        raise ValueError('unknown task fields or invalid task object')
    if not isinstance(spec.get('workspace'), str) or not Path(spec['workspace']).is_absolute() or not Path(spec['workspace']).is_dir():
        raise ValueError('workspace must be an existing absolute directory')
    if type(spec.get('timeout_seconds')) is not int or not 1 <= spec['timeout_seconds'] <= 3600:
        raise ValueError('timeout_seconds must be 1..3600 per command')
    if not isinstance(spec.get('checks'), list) or not spec['checks'] or len(spec['checks']) > 20:
        raise ValueError('one to twenty acceptance commands required')
    for argv in [spec.get('implementation'), *spec['checks']]:
        if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v and '\0' not in v for v in argv):
            raise ValueError('commands must be nonempty argument arrays; no implicit shell')
    if 'contract' not in spec:
        raise ValueError('command-mode tasks require a contract block')
    validate_contract(spec['contract'], spec)
    if 'envelope' in spec:
        validate_envelope(spec['envelope'], spec)
    return spec


class Factory:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(self.path, timeout=10)
        self.db.row_factory = sqlite3.Row
        os.chmod(self.path, 0o600)
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS jobs (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                spec TEXT NOT NULL, spec_hash TEXT NOT NULL, state TEXT NOT NULL,
                created REAL NOT NULL, started REAL, finished REAL,
                run_id TEXT, evidence TEXT, detail TEXT, child_group INTEGER);
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL,
                at REAL NOT NULL, state TEXT NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS fixture_verifications (
                job_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                candidate_path TEXT NOT NULL, candidate_sha256 TEXT NOT NULL,
                final_candidate_sha256 TEXT NOT NULL, verifier_id TEXT NOT NULL,
                verifier_passed INTEGER NOT NULL, accepted INTEGER NOT NULL,
                detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS controller (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                epoch INTEGER NOT NULL,
                lease_high_water INTEGER NOT NULL);
            INSERT INTO controller(id, epoch, lease_high_water)
                SELECT 1, 1, 0 WHERE NOT EXISTS (SELECT 1 FROM controller WHERE id = 1);
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                lease_generation INTEGER NOT NULL UNIQUE,
                epoch INTEGER NOT NULL,
                state TEXT NOT NULL,
                created REAL NOT NULL,
                detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS fake_provider_verifications (
                job_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL, lease_generation INTEGER NOT NULL,
                epoch INTEGER NOT NULL, candidate_path TEXT NOT NULL,
                candidate_sha256 TEXT NOT NULL, final_candidate_sha256 TEXT NOT NULL,
                verifier_id TEXT NOT NULL, verifier_passed INTEGER NOT NULL,
                accepted INTEGER NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals (
                job_id TEXT PRIMARY KEY NOT NULL,
                decision TEXT NOT NULL, decider TEXT NOT NULL,
                at REAL NOT NULL, note TEXT NOT NULL, spec_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memory_records (
                record_id TEXT PRIMARY KEY NOT NULL,
                job_id TEXT NOT NULL, kind TEXT NOT NULL, entry TEXT NOT NULL,
                source TEXT NOT NULL, at REAL NOT NULL,
                affected_component TEXT NOT NULL, invalidation_condition TEXT NOT NULL,
                revision TEXT, environment TEXT, owner TEXT, reason TEXT,
                supersedes TEXT, verified INTEGER NOT NULL);
        ''')
        self._lock_depth = 0

    def close(self):
        self.db.close()

    def event(self, job_id, state, detail):
        self.db.execute('INSERT INTO events(job_id,at,state,detail) VALUES(?,?,?,?)',
                        (job_id, time.time(), state, detail))

    def submit(self, spec):
        validate(spec)
        data = canonical(spec)
        digest = hashlib.sha256(data.encode()).hexdigest()
        envelope = spec.get('envelope')
        waiting = bool(envelope) and envelope.get('requires_decision') is True
        with self.db:
            old = self.db.execute('SELECT spec_hash FROM jobs WHERE id=?', (spec['id'],)).fetchone()
            if old:
                if old['spec_hash'] != digest:
                    raise ValueError('task ID already exists with a different immutable specification')
                return False
            if waiting:
                detail = ('waiting for a recorded decision before dispatch; envelope mode '
                          + envelope['mode'] + '; decider named in the envelope: ' + envelope['decider'])
                self.db.execute('INSERT INTO jobs(id,spec,spec_hash,state,created,detail) VALUES(?,?,?,?,?,?)',
                                (spec['id'], data, digest, 'awaiting_approval', time.time(), detail))
                self.event(spec['id'], 'awaiting_approval', detail)
            else:
                self.db.execute('INSERT INTO jobs(id,spec,spec_hash,state,created) VALUES(?,?,?,?,?)',
                                (spec['id'], data, digest, 'queued', time.time()))
                self.event(spec['id'], 'queued', 'explicit submission')
        return True

    def inspect(self, job_id):
        row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if row is None:
            raise ValueError('unknown job')
        result = dict(row)
        result['spec'] = json.loads(result['spec'])
        if result['spec'].get('mode') == 'fixture':
            receipt_row = self.db.execute(
                'SELECT * FROM fixture_verifications WHERE job_id=?', (job_id,)
            ).fetchone()
            if receipt_row is None:
                evidence_valid = False if result['state'] in ('passed', 'invalidated') else None
                evidence_problem = 'fixture verification receipt is not available'
                receipt = None
            else:
                receipt = dict(receipt_row)
                evidence_valid, evidence_problem = self._fixture_evidence_valid(result, receipt)
            if result['state'] == 'passed' and not evidence_valid:
                detail = 'fixture acceptance invalidated: ' + evidence_problem
                self.transition(job_id, 'invalidated', detail)
                row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
                result = dict(row)
                result['spec'] = json.loads(result['spec'])
            result['fixture_verification'] = receipt
            result['evidence_valid'] = evidence_valid
            result['evidence_problem'] = None if evidence_valid else evidence_problem
        elif result['spec'].get('mode') == 'fake_provider':
            receipt_row = self.db.execute(
                'SELECT * FROM fake_provider_verifications WHERE job_id=?', (job_id,)
            ).fetchone()
            if receipt_row is None:
                evidence_valid = False if result['state'] in ('passed', 'invalidated') else None
                evidence_problem = 'fake-provider verification receipt is not available'
                receipt = None
            else:
                receipt = dict(receipt_row)
                evidence_valid, evidence_problem = self._fake_evidence_valid(result, receipt)
            if result['state'] == 'passed' and not evidence_valid:
                detail = 'fake-provider acceptance invalidated: ' + evidence_problem
                self.transition(job_id, 'invalidated', detail)
                row = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
                result = dict(row)
                result['spec'] = json.loads(result['spec'])
            result['fake_provider_verification'] = receipt
            result['evidence_valid'] = evidence_valid
            result['evidence_problem'] = None if evidence_valid else evidence_problem
            result['attempts'] = [dict(r) for r in self.db.execute(
                'SELECT * FROM attempts WHERE job_id=? ORDER BY lease_generation', (job_id,))]
        result['contract'] = result['spec'].get('contract')
        result['envelope'] = result['spec'].get('envelope')
        result['memory'] = self.memory(job_id)
        approval_row = self.db.execute('SELECT * FROM approvals WHERE job_id=?', (job_id,)).fetchone()
        result['approval'] = dict(approval_row) if approval_row else None
        result['events'] = [dict(r) for r in self.db.execute('SELECT * FROM events WHERE job_id=? ORDER BY seq', (job_id,))]
        return result

    def _fixture_evidence_valid(self, job, receipt):
        evidence_fields = {
            'run_id', 'candidate_path', 'candidate_sha256',
            'final_candidate_sha256', 'verifier_id', 'verifier_passed',
            'accepted', 'detail',
        }
        receipt_fields = evidence_fields | {'job_id'}
        text_fields = (
            'job_id', 'run_id', 'candidate_path', 'candidate_sha256',
            'final_candidate_sha256', 'verifier_id', 'detail',
        )
        if set(receipt) != receipt_fields:
            return False, 'stored fixture verification receipt has an invalid schema'
        if any(type(receipt[field]) is not str for field in text_fields):
            return False, 'stored fixture verification receipt has invalid text field types'
        if any(type(receipt[field]) is not int or receipt[field] not in (0, 1)
               for field in ('verifier_passed', 'accepted')):
            return False, 'stored fixture verification receipt has invalid flag types'
        if receipt['candidate_path'] != 'candidate.json':
            return False, 'stored fixture verification receipt has an invalid candidate path'
        if receipt['job_id'] != job['id']:
            return False, 'stored fixture verification receipt refers to a different job'
        for field in ('candidate_sha256', 'final_candidate_sha256'):
            if re.fullmatch(r'[0-9a-f]{64}', receipt[field]) is None:
                return False, f'stored fixture verification receipt has an invalid {field}'
        if receipt['run_id'] != job['run_id']:
            return False, 'verification receipt refers to a different run'
        if receipt['verifier_id'] != FIXTURE_VERIFIER_ID:
            return False, 'verification receipt uses an unknown verifier identity'
        if bool(receipt['accepted']) and receipt['candidate_sha256'] != receipt['final_candidate_sha256']:
            return False, 'candidate changed after verification'
        try:
            candidate_path = fixture_candidate_path(job['evidence'], receipt['candidate_path'])
            candidate_bytes = candidate_path.read_bytes()
            actual_digest = hashlib.sha256(candidate_bytes).hexdigest()
        except (OSError, ValueError) as error:
            return False, f'fixture candidate is unavailable or unsafe: {error}'
        if actual_digest != receipt['final_candidate_sha256']:
            return False, 'candidate bytes changed after the verification record was written'
        if actual_digest == receipt['candidate_sha256']:
            verifier_passed, _ = verify_fixture_candidate(candidate_bytes)
            if bool(verifier_passed) != bool(receipt['verifier_passed']):
                return False, 'stored verifier outcome does not match the controller verifier'
        expected_acceptance = (
            bool(receipt['verifier_passed'])
            and receipt['candidate_sha256'] == receipt['final_candidate_sha256']
        )
        if bool(receipt['accepted']) != expected_acceptance:
            return False, 'stored acceptance does not match the verifier and final candidate digests'
        try:
            saved = json.loads((Path(job['evidence']) / 'verification.json').read_text())
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
            return False, f'verification evidence is unavailable or invalid: {error}'
        if not isinstance(saved, dict) or set(saved) != evidence_fields:
            return False, 'verification evidence has an invalid schema'
        if any(type(saved[field]) is not str for field in text_fields if field != 'job_id'):
            return False, 'verification evidence has invalid text field types'
        if type(saved['verifier_passed']) is not bool or type(saved['accepted']) is not bool:
            return False, 'verification evidence has invalid flag types'
        for field in ('candidate_sha256', 'final_candidate_sha256'):
            if re.fullmatch(r'[0-9a-f]{64}', saved[field]) is None:
                return False, f'verification evidence has an invalid {field}'
        if saved['candidate_path'] != 'candidate.json':
            return False, 'verification evidence has an invalid candidate path'
        for field in ('run_id', 'candidate_path', 'candidate_sha256',
                      'final_candidate_sha256', 'verifier_id', 'detail'):
            if saved.get(field) != receipt[field]:
                return False, f'verification evidence does not match its stored {field}'
        if saved['verifier_passed'] != bool(receipt['verifier_passed']):
            return False, 'verification evidence verifier outcome does not match'
        if saved['accepted'] != bool(receipt['accepted']):
            return False, 'verification evidence acceptance flag does not match'
        return True, 'candidate and controller verification receipt match'

    def _fake_evidence_valid(self, job, receipt):
        evidence_fields = {
            'run_id', 'attempt_id', 'lease_generation', 'epoch', 'candidate_path',
            'candidate_sha256', 'final_candidate_sha256', 'verifier_id',
            'verifier_passed', 'accepted', 'detail',
        }
        receipt_fields = evidence_fields | {'job_id'}
        text_fields = (
            'job_id', 'run_id', 'attempt_id', 'candidate_path',
            'candidate_sha256', 'final_candidate_sha256', 'verifier_id', 'detail',
        )
        if set(receipt) != receipt_fields:
            return False, 'stored fake-provider verification receipt has an invalid schema'
        if any(type(receipt[field]) is not str for field in text_fields):
            return False, 'stored fake-provider verification receipt has invalid text field types'
        if any(type(receipt[field]) is not int or isinstance(receipt[field], bool)
               for field in ('lease_generation', 'epoch')):
            return False, 'stored fake-provider verification receipt has invalid lease fields'
        if receipt['lease_generation'] < 1 or receipt['epoch'] < 1:
            return False, 'stored fake-provider verification receipt has an invalid lease value'
        if any(type(receipt[field]) is not int or receipt[field] not in (0, 1)
               for field in ('verifier_passed', 'accepted')):
            return False, 'stored fake-provider verification receipt has invalid flag types'
        if receipt['candidate_path'] != 'candidate.json':
            return False, 'stored fake-provider verification receipt has an invalid candidate path'
        if receipt['job_id'] != job['id'] or receipt['run_id'] != job['run_id']:
            return False, 'stored fake-provider verification receipt refers to a different job or run'
        if receipt['verifier_id'] != FAKE_PROVIDER_VERIFIER_ID:
            return False, 'verification receipt uses an unknown verifier identity'
        for field in ('candidate_sha256', 'final_candidate_sha256'):
            if re.fullmatch(r'[0-9a-f]{64}', receipt[field]) is None:
                return False, f'stored fake-provider verification receipt has an invalid {field}'
        attempt = self.db.execute(
            'SELECT * FROM attempts WHERE attempt_id=?', (receipt['attempt_id'],)
        ).fetchone()
        if attempt is None or attempt['job_id'] != job['id']:
            return False, 'stored fake-provider receipt refers to an unknown attempt'
        if attempt['lease_generation'] != receipt['lease_generation'] or attempt['epoch'] != receipt['epoch']:
            return False, 'stored fake-provider receipt does not match its attempt lease'
        if bool(receipt['accepted']) and attempt['state'] != 'published':
            return False, 'accepted fake-provider receipt is not a published attempt'
        if bool(receipt['accepted']) and receipt['candidate_sha256'] != receipt['final_candidate_sha256']:
            return False, 'candidate changed after verification'
        try:
            candidate_path = fixture_candidate_path(job['evidence'], receipt['candidate_path'])
            candidate_bytes = candidate_path.read_bytes()
            actual_digest = hashlib.sha256(candidate_bytes).hexdigest()
        except (OSError, ValueError) as error:
            return False, f'fake-provider candidate is unavailable or unsafe: {error}'
        if actual_digest != receipt['final_candidate_sha256']:
            return False, 'candidate bytes changed after the verification record was written'
        if actual_digest == receipt['candidate_sha256']:
            verifier_passed, _ = verify_fake_provider_candidate(candidate_bytes)
            if bool(verifier_passed) != bool(receipt['verifier_passed']):
                return False, 'stored verifier outcome does not match the controller verifier'
        expected_acceptance = (
            bool(receipt['verifier_passed'])
            and receipt['candidate_sha256'] == receipt['final_candidate_sha256']
        )
        if bool(receipt['accepted']) != expected_acceptance:
            return False, 'stored acceptance does not match the verifier and final candidate digests'
        try:
            saved = json.loads((Path(job['evidence']) / 'verification.json').read_text())
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
            return False, f'verification evidence is unavailable or invalid: {error}'
        if not isinstance(saved, dict) or set(saved) != evidence_fields:
            return False, 'verification evidence has an invalid schema'
        saved_text = (
            'run_id', 'attempt_id', 'candidate_path', 'candidate_sha256',
            'final_candidate_sha256', 'verifier_id', 'detail',
        )
        if any(type(saved[field]) is not str for field in saved_text):
            return False, 'verification evidence has invalid text field types'
        if any(type(saved[field]) is not int or isinstance(saved[field], bool)
               for field in ('lease_generation', 'epoch')):
            return False, 'verification evidence has invalid lease fields'
        if type(saved['verifier_passed']) is not bool or type(saved['accepted']) is not bool:
            return False, 'verification evidence has invalid flag types'
        for field in ('candidate_sha256', 'final_candidate_sha256'):
            if re.fullmatch(r'[0-9a-f]{64}', saved[field]) is None:
                return False, f'verification evidence has an invalid {field}'
        if saved['candidate_path'] != 'candidate.json':
            return False, 'verification evidence has an invalid candidate path'
        for field in saved_text + ('lease_generation', 'epoch'):
            if saved.get(field) != receipt[field]:
                return False, f'verification evidence does not match its stored {field}'
        if saved['verifier_passed'] != bool(receipt['verifier_passed']):
            return False, 'verification evidence verifier outcome does not match'
        if saved['accepted'] != bool(receipt['accepted']):
            return False, 'verification evidence acceptance flag does not match'
        return True, 'candidate and controller verification receipt match'

    @contextmanager
    def worker_lock(self):
        # flock is not reentrant across file descriptors. The depth counter lets
        # publish() run inside run_one(), which already holds this instance's lock.
        if self._lock_depth:
            self._lock_depth += 1
            try:
                yield
            finally:
                self._lock_depth -= 1
            return
        with self.path.with_suffix('.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('another factory worker owns this database') from None
            self._lock_depth = 1
            try:
                yield
            finally:
                self._lock_depth = 0
                fcntl.flock(lock, fcntl.LOCK_UN)

    def transition(self, job_id, state, detail):
        with self.db:
            self.db.execute('UPDATE jobs SET state=?,detail=? WHERE id=?', (state, detail, job_id))
            self.event(job_id, state, detail)

    def reconcile(self):
        with self.worker_lock():
            self.db.execute('BEGIN IMMEDIATE')
            try:
                rows = self.db.execute("SELECT id FROM jobs WHERE state IN ('running','checking')").fetchall()
                detail = 'worker exited without final evidence; inspect workspace and child processes'
                for row in rows:
                    self.db.execute('UPDATE jobs SET state=?,detail=? WHERE id=?',
                                    ('needs_reconciliation', detail, row['id']))
                    self.event(row['id'], 'needs_reconciliation', detail)
                    self.db.execute(
                        "UPDATE attempts SET state='superseded', detail=? WHERE job_id=? AND state='reserved'",
                        ('superseded by reconciliation', row['id']),
                    )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            return len(rows)

    def resolve(self, job_id, note):
        if not note.strip():
            raise ValueError('an inspection note is required')
        with self.worker_lock():
            row = self.inspect(job_id)
            if row['state'] != 'needs_reconciliation':
                raise ValueError('only an interrupted job can be resolved')
            if row['child_group']:
                try:
                    os.killpg(row['child_group'], 0)
                except ProcessLookupError:
                    pass
                else:
                    raise RuntimeError('recorded child process group still exists; inspect before resolution')
            self.transition(job_id, 'failed', 'operator reconciled, no automatic retry: ' + note)

    def decide(self, job_id, decision, decider, note=''):
        """Record the operator's decision for a task that is waiting.

        The decider name is recorded, not authorized: it is not compared with
        the envelope's decider and against no roster.
        """
        if not isinstance(decision, str) or decision not in DECISIONS:
            raise ValueError('decision must be one of: ' + ', '.join(sorted(DECISIONS)))
        if not isinstance(decider, str) or not decider.strip():
            raise ValueError('a named decider is required')
        if not isinstance(note, str):
            raise ValueError('the decision note must be text')
        with self.worker_lock():
            row = self.inspect(job_id)
            if row['state'] != 'awaiting_approval':
                raise ValueError('only a task awaiting approval can be decided')
            envelope = row['spec'].get('envelope') or {}
            detail = ('decision ' + decision + ' by ' + decider.strip()
                      + '; envelope mode ' + str(envelope.get('mode'))
                      + '; note: ' + note)
            if decision == 'granted':
                state = 'queued'
                job_detail = ('decision granted by ' + decider.strip()
                              + '; envelope mode ' + str(envelope.get('mode'))
                              + '; queued for dispatch; note: ' + note)
                event = 'approval_granted'
            else:
                state = 'refused'
                job_detail = ('decision refused by ' + decider.strip()
                              + '; envelope mode ' + str(envelope.get('mode'))
                              + '; the runner dispatched no command, started no child process, '
                              'and recorded no external effect for this task; note: ' + note)
                event = 'approval_refused'
            with self.db:
                try:
                    self.db.execute(
                        'INSERT INTO approvals(job_id,decision,decider,at,note,spec_hash)'
                        ' VALUES(?,?,?,?,?,?)',
                        (job_id, decision, decider.strip(), time.time(), note, row['spec_hash']),
                    )
                except sqlite3.IntegrityError:
                    raise ValueError('a decision was already recorded for this task') from None
                # The state and its detail change in the same transaction.
                self.db.execute('UPDATE jobs SET state=?,detail=? WHERE id=?',
                                (state, job_detail, job_id))
                self.event(job_id, event, detail)
        return self.inspect(job_id)

    def record_memory(self, job_id, kind, entry, source, affected_component,
                      invalidation_condition, **specific):
        """Store one memory record for a job.

        The records are stored and queryable. Nothing reads them to change a
        decision, and a hypothesis stays unverified until something measures
        it.
        """
        if kind not in MEMORY_KINDS:
            raise ValueError('memory kind must be one of: ' + ', '.join(MEMORY_KINDS))
        if self.db.execute('SELECT id FROM jobs WHERE id=?', (job_id,)).fetchone() is None:
            raise ValueError('unknown job')
        for name, value in (('entry', entry), ('source', source),
                            ('affected_component', affected_component),
                            ('invalidation_condition', invalidation_condition)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'memory {name} must be nonempty text')
            if len(value) > 2000 or '\0' in value or any(ord(char) < 32 for char in value):
                raise ValueError(f'memory {name} must be short text without control characters')
        revision = specific.get('revision')
        environment = specific.get('environment')
        owner = specific.get('owner')
        reason = specific.get('reason')
        supersedes = specific.get('supersedes')
        if kind == 'verified_fact':
            if not isinstance(revision, str) or not revision.strip():
                raise ValueError('a verified fact must bind to a revision')
            if not isinstance(environment, str) or not environment.strip():
                raise ValueError('a verified fact must bind to an environment')
        if kind == 'decision':
            if not isinstance(owner, str) or not owner.strip():
                raise ValueError('a decision must name an owner')
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError('a decision must record a reason')
            if supersedes is not None:
                target = self.db.execute(
                    'SELECT kind FROM memory_records WHERE record_id=? AND job_id=?',
                    (supersedes, job_id)).fetchone()
                if target is None or target['kind'] != 'decision':
                    raise ValueError(
                        'a superseding decision must name a decision of the same job')
        record_id = uuid.uuid4().hex
        with self.db:
            self.db.execute(
                'INSERT INTO memory_records(record_id,job_id,kind,entry,source,at,'
                'affected_component,invalidation_condition,revision,environment,owner,reason,'
                'supersedes,verified) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (record_id, job_id, kind, entry, source, time.time(), affected_component,
                 invalidation_condition, revision, environment, owner, reason, supersedes,
                 1 if kind == 'verified_fact' else 0))
        return self._memory_record(record_id)

    def memory(self, job_id, kind=None):
        """Return a job's memory records, optionally only one kind.

        The records are stored and queryable. Nothing consumes them.
        """
        if kind is not None and kind not in MEMORY_KINDS:
            raise ValueError('memory kind must be one of: ' + ', '.join(MEMORY_KINDS))
        rows = self.db.execute(
            'SELECT * FROM memory_records WHERE job_id=? ORDER BY at, rowid',
            (job_id,)).fetchall()
        records = [self._memory_record(row['record_id']) for row in rows]
        superseded_by = {}
        for record in records:
            if record['kind'] == 'decision' and record.get('supersedes'):
                superseded_by[record['supersedes']] = record['record_id']
        for record in records:
            if record['kind'] == 'decision':
                record['superseded_by'] = superseded_by.get(record['record_id'])
                record['current'] = record['superseded_by'] is None
        if kind is None:
            return records
        return [record for record in records if record['kind'] == kind]

    def _memory_record(self, record_id):
        row = self.db.execute(
            'SELECT * FROM memory_records WHERE record_id=?', (record_id,)).fetchone()
        if row is None:
            raise ValueError('unknown memory record')
        record = dict(row)
        if record['kind'] == 'verified_fact':
            record['verified'] = True
            record['current'] = True
        elif record['kind'] == 'decision':
            record['verified'] = None
            record['current'] = True
        else:
            record['verified'] = False
            record['current'] = False
        return record

    def _context_manifest(self, job_id, run_id, spec, spec_hash, results, epoch):
        """Record what the controller supplied for this attempt, and why."""
        contract = spec.get('contract') or {}
        acceptance_ids = list(contract.get('acceptance_ids') or [])
        workspace = spec.get('workspace')
        attempt = self.db.execute(
            'SELECT attempt_id, lease_generation, epoch FROM attempts WHERE job_id=?'
            ' ORDER BY lease_generation DESC LIMIT 1', (job_id,)).fetchone()
        counts = {kind: 0 for kind in MEMORY_KINDS}
        for row in self.db.execute('SELECT kind FROM memory_records WHERE job_id=?', (job_id,)):
            if row['kind'] in counts:
                counts[row['kind']] += 1
        commands = []
        for result in results:
            if 'argv' not in result:
                continue
            commands.append({
                'stage': result.get('stage'),
                'argv': list(result['argv']),
                'exit_code': result.get('exit_code'),
                'timed_out': bool(result.get('timed_out')),
                'elapsed_seconds': result.get('elapsed_seconds'),
                'log': result.get('log'),
            })
        acceptance_source = 'contract' if acceptance_ids else 'absent'
        supplied = [
            {'item': 'objective',
             'source': "task specification field 'objective'",
             'why': 'the objective is the purpose this attempt is judged against'},
            {'item': 'required_behavior',
             'source': ("the contract block's acceptance identifiers and the submitted "
                        'acceptance commands') if acceptance_ids else
                       "the task specification's acceptance commands",
             'why': 'the acceptance commands define the required behaviour of the attempt'},
            {'item': 'relevant_code_and_interfaces',
             'source': None,
             'why': 'no context builder exists: nothing is assembled from a codebase, '
                    'and no file or interface was read into this manifest'},
            {'item': 'recent_verified_failures',
             'source': None,
             'why': 'no failure history is assembled for this attempt'},
            {'item': 'applicable_decisions',
             'source': None,
             'why': 'memory records are stored and queryable, but no decision record was '
                    'consulted when this attempt was prepared'},
            {'item': 'deeper_evidence',
             'source': 'the run evidence directory and the recorded events',
             'why': 'the evidence directory holds the task, the results, the summary, '
                    'and this manifest'},
        ]
        return {
            'version': 1,
            'job_id': job_id,
            'run_id': run_id,
            'attempt_id': attempt['attempt_id'] if attempt else None,
            'lease_generation': attempt['lease_generation'] if attempt else None,
            'epoch': attempt['epoch'] if attempt else epoch,
            'spec_hash': spec_hash,
            'mode': spec.get('mode') or 'command',
            'objective': spec.get('objective'),
            'workspace': workspace,
            'repository': repository_identity(workspace),
            'acceptance_ids': acceptance_ids,
            'acceptance_ids_source': acceptance_source,
            'commands_actually_run': commands,
            'environment': {
                'timeout_seconds': spec.get('timeout_seconds'),
                'tokens': None,
                'cost_usd': None,
            },
            'supplied': supplied,
            'memory': {
                'kinds': list(MEMORY_KINDS),
                'records_for_job': counts,
                'consumed': False,
                'note': 'no memory record was consulted: nothing reads the memory kinds',
            },
            'unmeasured': ['tokens', 'cost_usd', 'candidate_revision', 'remaining_budget',
                           'unresolved_effects', 'environment_digest'],
        }

    def cancel(self, job_id):
        with self.db:
            row = self.db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                raise ValueError('unknown job')
            if row['state'] not in ('queued', 'awaiting_approval'):
                raise ValueError('only a queued or waiting job can be cancelled here')
            # The state change is guarded by the state that was observed, so a
            # task that started running in between is refused, not overwritten.
            cur = self.db.execute('UPDATE jobs SET state=? WHERE id=? AND state=?',
                                  ('cancelled', job_id, row['state']))
            if cur.rowcount != 1:
                raise ValueError('only a queued or waiting job can be cancelled here')
            if row['state'] == 'awaiting_approval':
                detail = ('operator cancelled a waiting task: the runner dispatched no command, '
                          'started no child process, and recorded no external effect')
                self.db.execute('UPDATE jobs SET detail=? WHERE id=?', (detail, job_id))
                self.event(job_id, 'cancelled', detail)
            else:
                self.event(job_id, 'cancelled', 'operator cancelled queued task')

    def execute(self, job_id, argv, cwd, timeout, log):
        started = time.monotonic()
        # Bounded captured output; drain the remainder so a noisy child cannot
        # deadlock or fill the evidence filesystem. stderr is merged with stdout.
        import selectors
        # The child cannot execute the task until its identity is durably saved.
        # Parent death before the one-byte release closes stdin and exits it.
        launch = ('import os,sys; gate=sys.stdin.buffer.read(1); '
                  'sys.exit(125) if gate != b"G" else None; '
                  'fd=os.open(os.devnull,os.O_RDONLY); os.dup2(fd,0); '
                  'os.execvpe(sys.argv[1],sys.argv[1:],os.environ)')
        child = subprocess.Popen([sys.executable, '-c', launch, *argv], cwd=cwd, stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        selector = None
        timed_out = False
        written = 0
        limit = 2 * 1024 * 1024
        try:
            with self.db:
                self.db.execute('UPDATE jobs SET child_group=? WHERE id=?', (child.pid, job_id))
            selector = selectors.DefaultSelector()
            selector.register(child.stdout, selectors.EVENT_READ)
            child.stdin.write(b'G')
            child.stdin.flush()
            child.stdin.close()
            with log.open('wb') as output:
                while selector.get_map():
                    if time.monotonic() - started >= timeout:
                        timed_out = True
                        break
                    for key, _ in selector.select(timeout=min(.1, max(0, timeout - (time.monotonic() - started)))):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            output.write(chunk[:max(0, limit - written)])
                            written += len(chunk)
                if written > limit:
                    output.write(b'\n[output truncated at 2 MiB]\n')
                remaining = timeout - (time.monotonic() - started)
                if not timed_out:
                    try:
                        child.wait(timeout=max(.001, remaining))
                    except subprocess.TimeoutExpired:
                        timed_out = True
        finally:
            # Clean up descendants even when the main command exits or its
            # captured pipe remains open. These are trusted local job processes.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            if selector is not None:
                selector.close()
            child.stdin.close()
            child.stdout.close()
            with self.db:
                self.db.execute('UPDATE jobs SET child_group=NULL WHERE id=?', (job_id,))
        return {'argv': argv, 'exit_code': child.returncode, 'timed_out': timed_out,
                'elapsed_seconds': time.monotonic() - started, 'log': str(log),
                'output_truncated': written > limit}

    def execute_fixture(self, job_id, spec, run_id, evidence):
        """Run one closed, controller-defined fixture without task code or subprocesses."""
        started = time.monotonic()
        scenario = spec['fixture']
        candidate_path = fixture_candidate_path(evidence, 'candidate.json')
        payload = FIXTURE_CANDIDATES[scenario]
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(candidate_path, flags, 0o600)
        with os.fdopen(fd, 'wb') as candidate_file:
            candidate_file.write(payload)

        self.transition(job_id, 'checking', 'controller-owned fixture verification')
        candidate_path = fixture_candidate_path(evidence, 'candidate.json')
        first_bytes = candidate_path.read_bytes()
        candidate_digest = hashlib.sha256(first_bytes).hexdigest()
        verifier_passed, verifier_detail = verify_fixture_candidate(first_bytes)

        # This deterministic fault case models a candidate mutation between
        # verification and acceptance. The final digest check must reject it.
        if scenario == 'tamper_after_check':
            candidate_path = fixture_candidate_path(evidence, 'candidate.json')
            with candidate_path.open('r+b') as candidate_file:
                candidate_file.seek(0)
                candidate_file.write(FIXTURE_TAMPER_BYTES)
                candidate_file.truncate()
                candidate_file.flush()
                os.fsync(candidate_file.fileno())

        candidate_path = fixture_candidate_path(evidence, 'candidate.json')
        final_bytes = candidate_path.read_bytes()
        final_digest = hashlib.sha256(final_bytes).hexdigest()
        changed_after_check = candidate_digest != final_digest
        accepted = verifier_passed and not changed_after_check
        if changed_after_check:
            detail = 'candidate changed after verification; acceptance failed closed'
        elif not verifier_passed:
            detail = verifier_detail
        else:
            detail = verifier_detail

        receipt = {
            'run_id': run_id,
            'candidate_path': 'candidate.json',
            'candidate_sha256': candidate_digest,
            'final_candidate_sha256': final_digest,
            'verifier_id': FIXTURE_VERIFIER_ID,
            'verifier_passed': verifier_passed,
            'accepted': accepted,
            'detail': detail,
        }
        (evidence / 'verification.json').write_text(json.dumps(receipt, indent=2, sort_keys=True))
        with self.db:
            self.db.execute(
                'INSERT INTO fixture_verifications '
                '(job_id,run_id,candidate_path,candidate_sha256,final_candidate_sha256,verifier_id,'
                'verifier_passed,accepted,detail) VALUES(?,?,?,?,?,?,?,?,?)',
                (job_id, run_id, receipt['candidate_path'], candidate_digest, final_digest,
                 FIXTURE_VERIFIER_ID, int(verifier_passed), int(accepted), detail),
            )

        worker_log = evidence / '00.log'
        worker_log.write_text(
            f"trusted built-in fixture: {scenario}\n"
            "fixture worker marker: SUCCESS\n"
            f"controller verifier: {'accepted' if accepted else 'rejected'}\n"
            f"detail: {detail}\n"
        )
        result = {
            'stage': 'fixture', 'fixture': scenario,
            'exit_code': 0 if accepted else 1, 'timed_out': False,
            'elapsed_seconds': time.monotonic() - started,
            'log': str(worker_log), 'output_truncated': False,
        }
        state = 'passed' if accepted else 'failed'
        return {'state': state, 'detail': detail, 'result': result, 'verification': receipt}

    def _controller_values(self):
        row = self.db.execute(
            'SELECT epoch, lease_high_water FROM controller WHERE id=1'
        ).fetchone()
        if row is None:
            raise RuntimeError('controller row is missing')
        epoch, high = row['epoch'], row['lease_high_water']
        if type(epoch) is not int or type(high) is not int or isinstance(epoch, bool) or isinstance(high, bool):
            raise RuntimeError('controller epoch or lease counter is invalid')
        if epoch < 1 or high < 0:
            raise RuntimeError('controller epoch or lease counter is invalid')
        return epoch, high

    def _max_generation(self):
        row = self.db.execute('SELECT MAX(lease_generation) AS max_generation FROM attempts').fetchone()
        value = row['max_generation']
        return 0 if value is None else value

    def _allocate_lease(self, job_id, detail):
        """Issue the next global lease. Caller owns the open transaction."""
        epoch, high = self._controller_values()
        generation = high + 1
        if generation <= high:
            raise RuntimeError('lease generation did not advance')
        updated = self.db.execute(
            'UPDATE controller SET lease_high_water=? WHERE id=1 AND lease_high_water=?',
            (generation, high),
        )
        if updated.rowcount != 1:
            raise RuntimeError('lease counter changed during allocation')
        attempt_id = uuid.uuid4().hex
        self.db.execute(
            'INSERT INTO attempts(attempt_id,job_id,lease_generation,epoch,state,created,detail) '
            'VALUES(?,?,?,?,?,?,?)',
            (attempt_id, job_id, generation, epoch, 'reserved', time.time(), detail),
        )
        return {
            'attempt_id': attempt_id, 'job_id': job_id, 'lease_generation': generation,
            'epoch': epoch, 'state': 'reserved',
        }

    def _write_candidate(self, evidence, payload):
        candidate_path = fixture_candidate_path(evidence, 'candidate.json')
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(candidate_path, flags, 0o600)
        with os.fdopen(fd, 'wb') as candidate_file:
            candidate_file.write(payload)

    def _insert_fake_receipt(self, job_id, receipt):
        self.db.execute(
            'INSERT INTO fake_provider_verifications '
            '(job_id,run_id,attempt_id,lease_generation,epoch,candidate_path,candidate_sha256,'
            'final_candidate_sha256,verifier_id,verifier_passed,accepted,detail) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (job_id, receipt['run_id'], receipt['attempt_id'], receipt['lease_generation'],
             receipt['epoch'], receipt['candidate_path'], receipt['candidate_sha256'],
             receipt['final_candidate_sha256'], receipt['verifier_id'],
             int(receipt['verifier_passed']), int(receipt['accepted']), receipt['detail']),
        )

    def _reject_fake_candidate(self, job_id, run_id, evidence, attempt):
        """Record a non-acceptance. The SUCCESS log line is not consulted."""
        candidate_path = fixture_candidate_path(evidence, 'candidate.json')
        candidate_bytes = candidate_path.read_bytes()
        verifier_passed, verifier_detail = verify_fake_provider_candidate(candidate_bytes)
        if verifier_passed:
            raise RuntimeError('incorrect fake-provider candidate passed verification')
        digest = hashlib.sha256(candidate_bytes).hexdigest()
        receipt = {
            'run_id': run_id,
            'attempt_id': attempt['attempt_id'],
            'lease_generation': attempt['lease_generation'],
            'epoch': attempt['epoch'],
            'candidate_path': 'candidate.json',
            'candidate_sha256': digest,
            'final_candidate_sha256': digest,
            'verifier_id': FAKE_PROVIDER_VERIFIER_ID,
            'verifier_passed': False,
            'accepted': False,
            'detail': verifier_detail,
        }
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self._insert_fake_receipt(job_id, receipt)
            updated = self.db.execute(
                "UPDATE attempts SET state='rejected', detail=? WHERE attempt_id=? AND state='reserved'",
                (verifier_detail, attempt['attempt_id']),
            )
            if updated.rowcount != 1:
                raise RuntimeError('incorrect scenario could not close its reserved attempt')
            (Path(evidence) / 'verification.json').write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + '\n'
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return receipt

    def _execute_fake_provider(self, job_id, spec, run_id, evidence):
        """Controller-owned scenario. No subprocess, socket, or sleep."""
        started = time.monotonic()
        scenario = spec['scenario']
        self.db.execute('BEGIN IMMEDIATE')
        try:
            attempt = self._allocate_lease(job_id, f'fake provider {scenario} reserved')
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        if scenario == 'interrupted':
            (evidence / 'partial.json').write_text(json.dumps({
                'attempt_id': attempt['attempt_id'],
                'complete': False,
                'epoch': attempt['epoch'],
                'lease_generation': attempt['lease_generation'],
            }, indent=2, sort_keys=True) + '\n')
            return {'leave_running': True}
        if scenario == 'timeout':
            self.db.execute('BEGIN IMMEDIATE')
            try:
                updated = self.db.execute(
                    "UPDATE attempts SET state='timed_out', detail=? WHERE attempt_id=? AND state='reserved'",
                    ('fake provider timed out before publication', attempt['attempt_id']),
                )
                if updated.rowcount != 1:
                    raise RuntimeError('timeout could not close the reserved attempt')
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            result = {
                'stage': 'fake_provider', 'scenario': scenario, 'exit_code': 1,
                'timed_out': True, 'elapsed_seconds': time.monotonic() - started,
                'log': None, 'output_truncated': False,
            }
            return {
                'leave_running': False, 'state': 'failed',
                'detail': 'fake provider timed out', 'results': [result], 'verification': None,
            }
        if scenario == 'incorrect':
            self._write_candidate(evidence, FAKE_PROVIDER_BAD)
            log = evidence / '00.log'
            log.write_text(
                'trusted fake provider: incorrect\n'
                'fake-provider worker marker: SUCCESS\n'
                'controller verifier: rejected\n'
            )
            receipt = self._reject_fake_candidate(job_id, run_id, evidence, attempt)
            result = {
                'stage': 'fake_provider', 'scenario': scenario, 'exit_code': 1,
                'timed_out': False, 'elapsed_seconds': time.monotonic() - started,
                'log': str(log), 'output_truncated': False,
            }
            return {
                'leave_running': False, 'state': 'failed', 'detail': receipt['detail'],
                'results': [result], 'verification': receipt,
            }
        if scenario == 'success':
            self._write_candidate(evidence, FAKE_PROVIDER_GOOD)
            self.transition(job_id, 'checking', 'controller-owned fake-provider verification')
            receipt = self.publish(
                job_id, attempt['attempt_id'], attempt['lease_generation'], attempt['epoch']
            )
            result = {
                'stage': 'fake_provider', 'scenario': scenario, 'exit_code': 0,
                'timed_out': False, 'elapsed_seconds': time.monotonic() - started,
                'log': None, 'output_truncated': False,
            }
            return {
                'leave_running': False, 'state': 'passed', 'detail': receipt['detail'],
                'results': [result], 'verification': receipt,
            }
        raise RuntimeError(f'unknown fake provider scenario: {scenario}')

    def publish(self, job_id, attempt_id, lease_generation, epoch):
        """Accept a fake-provider candidate only for the current reserved lease."""
        if type(lease_generation) is not int or isinstance(lease_generation, bool):
            raise ValueError('lease generation must be an integer')
        if type(epoch) is not int or isinstance(epoch, bool):
            raise ValueError('epoch must be an integer')
        with self.worker_lock():
            self.db.execute('BEGIN IMMEDIATE')
            try:
                receipt = self._publish_in_transaction(job_id, attempt_id, lease_generation, epoch)
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            return receipt

    def _publish_in_transaction(self, job_id, attempt_id, lease_generation, epoch):
        current_epoch, high = self._controller_values()
        attempt = self.db.execute(
            'SELECT * FROM attempts WHERE attempt_id=?', (attempt_id,)
        ).fetchone()
        job = self.db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
        if job is None or attempt is None:
            raise ValueError('publish lease does not match a reserved attempt')
        if epoch != current_epoch or attempt['epoch'] != epoch:
            raise ValueError('stale controller epoch')
        if (attempt['job_id'] != job_id or attempt['lease_generation'] != lease_generation
                or attempt['state'] != 'reserved'):
            raise ValueError('stale or closed lease')
        if job['state'] not in ('running', 'checking'):
            raise ValueError('job is not awaiting publication')
        if lease_generation < 1 or lease_generation > high:
            raise ValueError('lease generation is not current')
        spec = json.loads(job['spec'])
        if spec.get('mode') != 'fake_provider':
            raise ValueError('publish is only valid for a fake-provider attempt')
        newer = self.db.execute(
            "SELECT 1 FROM attempts WHERE job_id=? AND state='reserved' AND lease_generation>?",
            (job_id, lease_generation),
        ).fetchone()
        if newer is not None:
            raise ValueError('stale or closed lease')
        try:
            candidate_path = fixture_candidate_path(job['evidence'], 'candidate.json')
            first_bytes = candidate_path.read_bytes()
            final_bytes = candidate_path.read_bytes()
        except (OSError, ValueError) as error:
            raise ValueError('candidate was not accepted') from error
        verifier_passed, verifier_detail = verify_fake_provider_candidate(first_bytes)
        digest = hashlib.sha256(first_bytes).hexdigest()
        final_digest = hashlib.sha256(final_bytes).hexdigest()
        if not verifier_passed or digest != final_digest:
            raise ValueError('candidate was not accepted')
        receipt = {
            'run_id': job['run_id'],
            'attempt_id': attempt['attempt_id'],
            'lease_generation': attempt['lease_generation'],
            'epoch': attempt['epoch'],
            'candidate_path': 'candidate.json',
            'candidate_sha256': digest,
            'final_candidate_sha256': final_digest,
            'verifier_id': FAKE_PROVIDER_VERIFIER_ID,
            'verifier_passed': True,
            'accepted': True,
            'detail': verifier_detail,
        }
        self._insert_fake_receipt(job_id, receipt)
        updated = self.db.execute(
            "UPDATE attempts SET state='published', detail=? WHERE attempt_id=? AND state='reserved'",
            (verifier_detail, attempt_id),
        )
        if updated.rowcount != 1:
            raise ValueError('attempt is not reserved')
        updated = self.db.execute(
            "UPDATE jobs SET state='passed', detail=? WHERE id=? AND state IN ('running','checking')",
            (verifier_detail, job_id),
        )
        if updated.rowcount != 1:
            raise ValueError('job is not awaiting publication')
        self.event(job_id, 'passed', verifier_detail)
        (Path(job['evidence']) / 'verification.json').write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + '\n'
        )
        return receipt

    def replace_lease(self, job_id):
        with self.worker_lock():
            self.db.execute('BEGIN IMMEDIATE')
            try:
                job = self.db.execute('SELECT state FROM jobs WHERE id=?', (job_id,)).fetchone()
                if job is None or job['state'] not in ('running', 'checking'):
                    raise ValueError('lease replacement requires a running or checking job')
                reserved = self.db.execute(
                    "SELECT attempt_id FROM attempts WHERE job_id=? AND state='reserved'",
                    (job_id,),
                ).fetchall()
                if len(reserved) != 1:
                    raise ValueError('lease replacement requires exactly one reserved attempt')
                self.db.execute(
                    "UPDATE attempts SET state='superseded', detail=? WHERE attempt_id=? AND state='reserved'",
                    ('superseded by lease replacement', reserved[0]['attempt_id']),
                )
                attempt = self._allocate_lease(job_id, 'replacement lease')
                self.event(
                    job_id, job['state'],
                    f"lease replaced with generation {attempt['lease_generation']}",
                )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            return attempt

    def backup(self, destination):
        destination = Path(destination)
        if destination.exists():
            raise ValueError('backup destination already exists')
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.worker_lock():
            self.db.commit()
            target = sqlite3.connect(destination)
            try:
                self.db.backup(target)
            finally:
                target.close()
            os.chmod(destination, 0o600)

    def _ensure_side_tables(self):
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS controller (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                epoch INTEGER NOT NULL,
                lease_high_water INTEGER NOT NULL);
            INSERT INTO controller(id, epoch, lease_high_water)
                SELECT 1, 1, 0 WHERE NOT EXISTS (SELECT 1 FROM controller WHERE id = 1);
            CREATE TABLE IF NOT EXISTS attempts (
                attempt_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                lease_generation INTEGER NOT NULL UNIQUE,
                epoch INTEGER NOT NULL,
                state TEXT NOT NULL,
                created REAL NOT NULL,
                detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS fake_provider_verifications (
                job_id TEXT PRIMARY KEY, run_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL, lease_generation INTEGER NOT NULL,
                epoch INTEGER NOT NULL, candidate_path TEXT NOT NULL,
                candidate_sha256 TEXT NOT NULL, final_candidate_sha256 TEXT NOT NULL,
                verifier_id TEXT NOT NULL, verifier_passed INTEGER NOT NULL,
                accepted INTEGER NOT NULL, detail TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS approvals (
                job_id TEXT PRIMARY KEY NOT NULL,
                decision TEXT NOT NULL, decider TEXT NOT NULL,
                at REAL NOT NULL, note TEXT NOT NULL, spec_hash TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memory_records (
                record_id TEXT PRIMARY KEY NOT NULL,
                job_id TEXT NOT NULL, kind TEXT NOT NULL, entry TEXT NOT NULL,
                source TEXT NOT NULL, at REAL NOT NULL,
                affected_component TEXT NOT NULL, invalidation_condition TEXT NOT NULL,
                revision TEXT, environment TEXT, owner TEXT, reason TEXT,
                supersedes TEXT, verified INTEGER NOT NULL);
        ''')

    def _mark_restored_invalid(self, job, problem):
        detail = 'restored acceptance invalidated: ' + problem
        self.db.execute(
            'UPDATE jobs SET state=?, detail=? WHERE id=? AND state=?',
            ('invalidated', detail, job['id'], 'passed'),
        )
        self.event(job['id'], 'invalidated', detail)

    def _invalidate_restored_candidates(self):
        rows = self.db.execute("SELECT * FROM jobs WHERE state='passed'").fetchall()
        for row in rows:
            job = dict(row)
            try:
                spec = json.loads(job['spec'])
            except (json.JSONDecodeError, UnicodeError, RecursionError, TypeError):
                self._mark_restored_invalid(job, 'stored task specification is not valid JSON')
                continue
            if not isinstance(spec, dict):
                self._mark_restored_invalid(job, 'stored task specification is not an object')
                continue
            mode = spec.get('mode')
            try:
                if mode == 'fixture':
                    receipt_row = self.db.execute(
                        'SELECT * FROM fixture_verifications WHERE job_id=?', (job['id'],)
                    ).fetchone()
                    if receipt_row is None:
                        valid, problem = False, 'fixture verification receipt is not available'
                    else:
                        valid, problem = self._fixture_evidence_valid(job, dict(receipt_row))
                elif mode == 'fake_provider':
                    receipt_row = self.db.execute(
                        'SELECT * FROM fake_provider_verifications WHERE job_id=?', (job['id'],)
                    ).fetchone()
                    if receipt_row is None:
                        valid, problem = False, 'fake-provider verification receipt is not available'
                    else:
                        valid, problem = self._fake_evidence_valid(job, dict(receipt_row))
                else:
                    continue
            except (OSError, ValueError, TypeError, RecursionError) as error:
                valid, problem = False, f'restored acceptance could not be checked: {error}'
            if not valid:
                self._mark_restored_invalid(job, problem)

    def _remove_sqlite_file(self, path):
        path = Path(path)
        path.unlink(missing_ok=True)
        Path(str(path) + '-wal').unlink(missing_ok=True)
        Path(str(path) + '-shm').unlink(missing_ok=True)

    def _fence_restored_ledger(self, live_epoch, live_high):
        """Fence an already restored staging ledger. Caller owns that connection."""
        self._ensure_side_tables()
        restored_epoch, restored_high = self._controller_values()
        new_epoch = max(live_epoch, restored_epoch) + 1
        new_high = max(live_high, restored_high, self._max_generation())
        self.db.execute('BEGIN IMMEDIATE')
        try:
            updated = self.db.execute(
                'UPDATE controller SET epoch=?, lease_high_water=? WHERE id=1',
                (new_epoch, new_high),
            )
            if updated.rowcount != 1:
                raise RuntimeError('controller epoch was not advanced')
            self.db.execute(
                "UPDATE attempts SET state='superseded', detail=? WHERE state='reserved'",
                ('superseded by ledger restore',),
            )
            rows = self.db.execute(
                "SELECT id FROM jobs WHERE state IN ('running','checking')"
            ).fetchall()
            detail = 'restored under a new controller epoch; in-flight lease invalidated'
            for row in rows:
                self.db.execute(
                    'UPDATE jobs SET state=?, detail=? WHERE id=?',
                    ('needs_reconciliation', detail, row['id']),
                )
                self.event(row['id'], 'needs_reconciliation', detail)
            self._invalidate_restored_candidates()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return new_epoch

    def restore(self, backup):
        """Replace this ledger from a backup and fence every pre-restore lease.

        The backup is fenced in a staging file first. The live ledger is replaced
        only after that fenced snapshot is committed, so a fencing failure cannot
        rewind the epoch or lease counter.
        """
        backup = Path(backup)
        if not backup.is_file():
            raise ValueError('backup file is not available')
        with self.worker_lock():
            self.db.commit()
            live_epoch, live_high = self._controller_values()
            live_high = max(live_high, self._max_generation())
            staging_path = self.path.with_name(self.path.name + '.restore-staging')
            prior_path = self.path.with_name(self.path.name + '.restore-prior')
            self._remove_sqlite_file(staging_path)
            self._remove_sqlite_file(prior_path)
            original = self.db
            source = sqlite3.connect(backup)
            staged = sqlite3.connect(staging_path)
            staged.row_factory = sqlite3.Row
            prior = sqlite3.connect(prior_path)
            os.chmod(staging_path, 0o600)
            os.chmod(prior_path, 0o600)
            try:
                original.backup(prior)
                source.backup(staged)
                self.db = staged
                new_epoch = self._fence_restored_ledger(live_epoch, live_high)
                try:
                    staged.backup(original)
                except Exception:
                    prior.backup(original)
                    raise
                self.db = original
                epoch, high = self._controller_values()
                if epoch != new_epoch or high < live_high:
                    prior.backup(original)
                    raise RuntimeError('restored ledger is not fenced')
                return new_epoch
            finally:
                self.db = original
                source.close()
                staged.close()
                prior.close()
                self._remove_sqlite_file(staging_path)
                self._remove_sqlite_file(prior_path)

    def run_one(self):
        with self.worker_lock():
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('running','checking','needs_reconciliation')").fetchone():
                self.db.rollback()
                raise RuntimeError('unresolved prior run; reconcile/inspect it before dispatch')
            row = None
            while True:
                row = self.db.execute(
                    "SELECT * FROM jobs WHERE state='queued' ORDER BY seq LIMIT 1").fetchone()
                if row is None:
                    self.db.commit()
                    return None
                spec = json.loads(row['spec'])
                envelope = spec.get('envelope')
                if not (envelope and envelope.get('requires_decision') is True):
                    break
                # A task that declares it needs a decision runs only with a
                # recorded grant. The state and the record are written in one
                # transaction, so this re-check is the second lock on the gate.
                grant = self.db.execute(
                    "SELECT 1 FROM approvals WHERE job_id=? AND decision='granted'",
                    (row['id'],)).fetchone()
                if grant:
                    break
                detail = ('dispatch refused: the task declares it needs a fresh decision '
                          'and no grant is recorded in the ledger')
                self.db.execute('UPDATE jobs SET state=?,detail=? WHERE id=?',
                                ('awaiting_approval', detail, row['id']))
                self.event(row['id'], 'awaiting_approval', detail)
            job_id = row['id']
            run_id = uuid.uuid4().hex
            evidence = self.path.parent/'runs'/run_id
            evidence.mkdir(parents=True, mode=0o700)
            (evidence/'task.json').write_text(row['spec'])
            self.db.execute("UPDATE jobs SET state='running',run_id=?,evidence=?,started=? WHERE id=?",
                            (run_id, str(evidence), time.time(), job_id))
            self.event(job_id, 'running', 'durable reservation before command launch')
            self.db.commit()
            results = []
            final = 'failed'
            detail = 'not completed'
            fixture_verification = None
            fake_verification = None
            try:
                if spec.get('mode') == 'isolation_probe':
                    outcome = run_isolation_probe(evidence)
                    final, detail = outcome['state'], outcome['detail']
                    results.extend(outcome['results'])
                    (evidence/'results.json').write_text(json.dumps(results, indent=2))
                elif spec.get('mode') == 'fake_provider':
                    outcome = self._execute_fake_provider(job_id, spec, run_id, evidence)
                    if outcome.get('leave_running'):
                        return self.inspect(job_id)
                    final, detail = outcome['state'], outcome['detail']
                    fake_verification = outcome.get('verification')
                    results.extend(outcome['results'])
                    (evidence/'results.json').write_text(json.dumps(results, indent=2))
                elif spec.get('mode') == 'fixture':
                    outcome = self.execute_fixture(job_id, spec, run_id, evidence)
                    final, detail = outcome['state'], outcome['detail']
                    fixture_verification = outcome['verification']
                    results.append(outcome['result'])
                    (evidence/'results.json').write_text(json.dumps(results, indent=2))
                else:
                    for index, argv in enumerate([spec['implementation'], *spec['checks']]):
                        if index:
                            self.transition(job_id, 'checking', f'acceptance command {index}')
                        result = self.execute(job_id, argv, spec['workspace'], spec['timeout_seconds'], evidence/f'{index:02d}.log')
                        result['stage'] = 'implementation' if index == 0 else 'acceptance'
                        results.append(result)
                        (evidence/'results.json').write_text(json.dumps(results, indent=2))
                        if result['timed_out'] or result['exit_code'] != 0:
                            detail = f"{result['stage']} {'timed out' if result['timed_out'] else 'failed'}"
                            break
                    else:
                        final, detail = 'passed', 'implementation and all acceptance commands exited successfully; product review still required'
            except (OSError, ValueError) as error:
                detail = f'command setup failed: {error}'
            except BaseException:
                self.transition(job_id, 'needs_reconciliation', 'worker interrupted; inspect evidence before any retry')
                raise
            summary = {'id': job_id, 'run_id': run_id, 'state': final,
                'detail': detail, 'spec_hash': row['spec_hash'], 'results': results,
                'tokens': None, 'cost_usd': None}
            if fixture_verification is not None:
                summary['fixture_verification'] = fixture_verification
            if fake_verification is not None:
                summary['fake_provider_verification'] = fake_verification
            # The context manifest records what the controller supplied for
            # this attempt. Its path and digest go into the ledger with the
            # final state change, in one transaction.
            epoch, _ = self._controller_values()
            manifest = self._context_manifest(
                job_id, run_id, spec, row['spec_hash'], results, epoch)
            manifest_path = evidence / 'context.json'
            manifest_path.write_text(json.dumps(manifest, indent=2))
            manifest_digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            summary['context_manifest'] = {'path': str(manifest_path),
                                           'sha256': manifest_digest}
            (evidence/'summary.json').write_text(json.dumps(summary, indent=2))
            with self.db:
                self.event(job_id, 'context_manifest',
                           f'context.json sha256={manifest_digest}')
                self.transition(job_id, final, detail)
            with self.db:
                self.db.execute('UPDATE jobs SET finished=? WHERE id=?', (time.time(), job_id))
            return self.inspect(job_id)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest='action', required=True)
    submit = sub.add_parser('submit')
    submit.add_argument('file', type=Path)
    sub.add_parser('status')
    sub.add_parser('run-one')
    sub.add_parser('reconcile')
    for action in ['inspect', 'cancel', 'resolve']:
        child = sub.add_parser(action)
        child.add_argument('id')
        if action == 'resolve':
            child.add_argument('--note', required=True)
    decide = sub.add_parser('decide')
    decide.add_argument('id')
    decide.add_argument('--decision', required=True, choices=sorted(DECISIONS))
    decide.add_argument('--decider', required=True)
    decide.add_argument('--note', default='')
    args = parser.parse_args()
    os.umask(0o077)
    factory = Factory(args.db)
    try:
        if args.action == 'submit':
            result = {'created': factory.submit(json.loads(args.file.read_text()))}
        elif args.action == 'run-one':
            result = factory.run_one()
        elif args.action == 'inspect':
            result = factory.inspect(args.id)
        elif args.action == 'reconcile':
            result = {'interrupted': factory.reconcile()}
        elif args.action == 'resolve':
            factory.resolve(args.id, args.note)
            result = factory.inspect(args.id)
        elif args.action == 'cancel':
            factory.cancel(args.id)
            result = factory.inspect(args.id)
        elif args.action == 'decide':
            result = factory.decide(args.id, args.decision, args.decider, args.note)
        else:
            result = []
            for row in factory.db.execute(
                    'SELECT id,state,run_id,detail,evidence FROM jobs ORDER BY seq'):
                item = dict(row)
                approval = factory.db.execute(
                    'SELECT decision,decider,at,note,spec_hash FROM approvals WHERE job_id=?',
                    (row['id'],)).fetchone()
                item['approval'] = dict(approval) if approval else None
                result.append(item)
        print(json.dumps(result, indent=2))
        return 1 if args.action == 'run-one' and result and result['state'] != 'passed' else 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        print(json.dumps({'error': str(error)}))
        return 1
    finally:
        factory.close()


if __name__ == '__main__':
    raise SystemExit(main())
