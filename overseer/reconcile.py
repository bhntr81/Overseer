"""The successor's side of the blueprint's handoff record.

The blueprint asks that the successor checks the ledger and the workspace
before trusting the summary, and that it reconciles a disagreement. This
module is that check: it compares a persisted handoff record with the facts of
the ledger row and of the workspace, and it reports the disagreements it
finds. It resolves nothing, it re-verifies nothing, and nothing in this
report changes an attempt's outcome.

The module reads no ledger and starts no process. The factory gathers the
ledger row (LEDGER_KEYS and 'found') and the workspace facts (WORKSPACE_KEYS,
'read', and 'dirty') and hands them over as plain values.

Every fact that could not be obtained is named with the reason that it could
not be obtained, and it is never counted as agreement.
"""

import hashlib
import json
import os
from pathlib import Path

MAX_RECORD_BYTES = 64 * 1024
MAX_JSON_DEPTH = 64
MAX_IDENTIFIERS = 20
MAX_DISAGREEMENTS = 32

LIMITS = {'max_record_bytes': MAX_RECORD_BYTES, 'max_json_depth': MAX_JSON_DEPTH,
          'max_identifiers': MAX_IDENTIFIERS, 'max_disagreements': MAX_DISAGREEMENTS}

RECORD_KIND = 'handoff_record'
REPORT_KIND = 'handoff_reconciliation'

# A file whose name marks it as a secret is never read for its content. The
# rule is a copy of the codemap module's rule, so that this module imports
# nothing from it; a test holds the two copies together.
SECRET_SUFFIXES = ('.pem', '.key', '.p12', '.pfx', '.jks', '.keystore', '.ppk',
                    '.asc', '.gpg', '.kdbx')
SECRET_NAMES = frozenset({
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519', 'credentials', 'credentials.json',
    'secrets.json', '.npmrc', '.pypirc', '.netrc', 'auth.json', 'token.json',
})

TEXT_FIELDS = ('job_id', 'run_id', 'spec_hash', 'state', 'detail')
REVISION_FIELDS = ('base_revision', 'candidate_revision')
LIST_FIELDS = ('completed_acceptance_ids', 'failing_acceptance_ids',
               'not_run_acceptance_ids')
# The record field, the ledger key it is compared with, and the kind of a mismatch.
IDENTITY = (('job_id', 'id', 'job_id_mismatch'),
            ('run_id', 'run_id', 'run_id_mismatch'),
            ('spec_hash', 'spec_hash', 'spec_hash_mismatch'),
            ('state', 'state', 'state_mismatch'),
            ('detail', 'detail', 'detail_mismatch'))
LEDGER_KEYS = ('id', 'state', 'detail', 'spec_hash', 'run_id', 'evidence', 'acceptance_ids',
               'recorded_sha256', 'recorded_sha256_reason')
WORKSPACE_KEYS = ('path', 'reason', 'root', 'head')

NOTE = ('this report records a disagreement between the handoff record, the ledger row, and '
        'the workspace; it does not resolve one; the ledger row and the workspace remain the '
        'authority, and nothing in this report changes an attempt\'s outcome')

MANIFEST_REASON = ('the context manifest is not rewritten because its digest is already recorded '
                   'in the ledger; rewriting it would leave the ledger claiming a digest the '
                   'file no longer has')


def is_secret(path):
    """Report whether a file's name marks it as a secret."""
    name = Path(path).name.casefold()
    if name in SECRET_NAMES or name.startswith('.env'):
        return True
    if any(name.endswith(suffix) for suffix in SECRET_SUFFIXES):
        return True
    return 'secret' in name or 'credential' in name or 'password' in name


def _depth(value):
    """Return the nesting depth of a parsed value, without recursing."""
    deepest = 0
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        deepest = max(deepest, depth)
        if depth > MAX_JSON_DEPTH:
            return depth
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
    return deepest


def _schema_problem(record):
    """Return the reason the record's shape is wrong, or None when it is right."""
    if record.get('kind') != RECORD_KIND:
        return 'the record\'s kind is %s, not %s' % (json.dumps(record.get('kind')), RECORD_KIND)
    for field in TEXT_FIELDS:
        if not isinstance(record.get(field), str):
            return ('the record\'s field %r is %s, not text'
                    % (field, type(record.get(field)).__name__))
    for field in REVISION_FIELDS + LIST_FIELDS:
        value = record.get(field)
        if not isinstance(value, dict) or not isinstance(value.get('source'), str):
            return 'the record\'s field %r is not an object with a value and a source' % field
        item = value.get('value')
        if field in REVISION_FIELDS and item is not None and not isinstance(item, str):
            return 'the record\'s field %r has a revision that is not text' % field
        if field in LIST_FIELDS and not (isinstance(item, list)
                                         and all(isinstance(entry, str) for entry in item)):
            return 'the record\'s field %r does not hold a list of text' % field
    return None


def _read_bytes(path):
    """Return the record's bytes, or the reason they could not be read.

    The size is checked before the file is opened, and the read is capped, so
    a file that grows after its size was taken is not read whole.
    """
    too_large = 'the record is larger than the %d byte bound' % MAX_RECORD_BYTES
    try:
        if os.stat(path).st_size > MAX_RECORD_BYTES:
            return None, too_large
        with path.open('rb') as handle:
            data = handle.read(MAX_RECORD_BYTES + 1)
    except FileNotFoundError:
        return None, 'the record does not exist'
    except OSError as error:
        return None, 'the record could not be read: %s' % type(error).__name__
    if len(data) > MAX_RECORD_BYTES:
        return None, too_large
    return data, None


def read_record(path):
    """Return the record's digest and value, or the reason it could not be read."""
    result = {'path': str(path) if path is not None else None, 'sha256': None,
              'record': None, 'read': False, 'reason': None}
    if path is None:
        result['reason'] = 'the job has no run evidence directory'
        return result
    path = Path(path)
    if is_secret(path):
        result['reason'] = 'the file name marks it as a secret'
        return result
    data, result['reason'] = _read_bytes(path)
    if data is None:
        return result
    result['sha256'] = hashlib.sha256(data).hexdigest()
    try:
        parsed = json.loads(data.decode('utf-8'))
    except UnicodeDecodeError:
        result['reason'] = 'the record is not UTF-8 text'
        return result
    except RecursionError:
        result['reason'] = 'the record is nested deeper than the parser allows'
        return result
    except json.JSONDecodeError:
        result['reason'] = 'the record is not JSON'
        return result
    if not isinstance(parsed, dict):
        result['reason'] = 'the record is not a JSON object'
    elif _depth(parsed) > MAX_JSON_DEPTH:
        result['reason'] = 'the record is nested deeper than the %d level bound' % MAX_JSON_DEPTH
    else:
        result['reason'] = _schema_problem(parsed)
    if result['reason'] is None:
        result['record'] = parsed
        result['read'] = True
    return result


def _disagreement(kind, record_side, authority_side, reason):
    """Return one disagreement: what the record says and what the authority says."""
    return {'kind': kind, 'record': record_side, 'authority': authority_side, 'reason': reason}


def _compare_identifiers(record, contract, disagreements, unverifiable):
    """Compare the record's three identifier lists with the stored contract, as sets.

    The lists must be disjoint and their union must be the contract's
    identifiers; a partial overlap is a mismatch, never an agreement.
    """
    if contract is None:
        unverifiable.append({'fact': 'acceptance_ids',
                             'reason': 'the stored job names no contract, so there is no '
                                       'authority to compare the identifier lists against'})
        return
    if len(contract) > MAX_IDENTIFIERS:
        unverifiable.append({'fact': 'acceptance_ids',
                             'reason': 'the stored contract names more than %d acceptance '
                                       'identifiers' % MAX_IDENTIFIERS})
        return
    lists = {name: list(record[name + '_acceptance_ids']['value'])
             for name in ('completed', 'failing', 'not_run')}
    sets = [set(items) for items in lists.values()]
    disjoint = sum(len(items) for items in sets) == len(set().union(*sets))
    if not disjoint or set().union(*sets) != set(contract):
        disagreements.append(_disagreement(
            'acceptance_ids_mismatch', lists, sorted(set(contract)),
            'the record\'s completed, failing, and not-run identifier lists are not '
            'disjoint or do not cover the contract\'s acceptance identifiers'))


def _compare_revisions(record, workspace, disagreements, not_applicable):
    """Compare the record's revisions with the workspace's current HEAD."""
    head = workspace.get('head')
    base = record['base_revision']['value']
    candidate = record['candidate_revision']['value']
    if candidate is None:
        not_applicable.append({
            'fact': 'candidate_revision',
            'reason': 'the record says HEAD did not move during the attempt, so there is no '
                      'candidate revision to compare with the workspace'})
    elif head != candidate:
        disagreements.append(_disagreement(
            'candidate_revision_mismatch', candidate, head,
            'the record\'s candidate revision is not the workspace\'s current HEAD'))
    if base is None:
        not_applicable.append({
            'fact': 'base_revision',
            'reason': 'the record carries no base revision, so the workspace\'s revision '
                      'cannot be anchored to it'})
    elif head not in (base, candidate):
        disagreements.append(_disagreement(
            'base_revision_unanchored', base, head,
            'the workspace\'s current HEAD is neither the record\'s base revision nor its '
            'candidate revision'))


def _verdict(disagreements, unverifiable):
    """Return the verdict and its reason; a disagreement outranks an unverifiable fact."""
    if disagreements:
        return 'disagree', ('%d disagreement(s) found between the record, the ledger row, and '
                            'the workspace' % len(disagreements))
    if unverifiable:
        return 'unverifiable', ('no disagreement was found, but %d fact(s) could not be '
                                'obtained' % len(unverifiable))
    return 'agree', 'the record agrees with the ledger row and with the workspace'


def compare(record_info, ledger, workspace):
    """Return the report comparing the record with the ledger row and the workspace."""
    disagreements = []
    unverifiable, not_applicable = [], []
    record = record_info.get('record')
    if not record_info.get('read'):
        unverifiable.append({'fact': 'record', 'reason': record_info.get('reason')})
    if not workspace.get('read'):
        unverifiable.append({'fact': 'workspace', 'reason': workspace.get('reason')})
    if record_info.get('read'):
        for field, key, kind in IDENTITY:
            if record.get(field) != ledger.get(key):
                disagreements.append(_disagreement(
                    kind, record.get(field), ledger.get(key),
                    'the record\'s %s and the ledger row\'s %s differ' % (field, key)))
        _compare_identifiers(record, ledger.get('acceptance_ids'), disagreements, unverifiable)
        recorded = ledger.get('recorded_sha256')
        if recorded is None:
            unverifiable.append({'fact': 'recorded_sha256',
                                 'reason': ledger.get('recorded_sha256_reason')
                                 or 'the ledger records no digest for the handoff record'})
        elif record_info.get('sha256') != recorded:
            disagreements.append(_disagreement(
                'digest_mismatch', record_info.get('sha256'), recorded,
                'the digest of the record file as read back is not the digest the ledger '
                'recorded for it'))
        if workspace.get('read'):
            _compare_revisions(record, workspace, disagreements, not_applicable)
    beyond = max(0, len(disagreements) - MAX_DISAGREEMENTS)
    disagreements = disagreements[:MAX_DISAGREEMENTS]
    verdict, reason = _verdict(disagreements, unverifiable)
    ledger_block = {key: ledger.get(key) for key in LEDGER_KEYS}
    ledger_block.update(found=bool(ledger.get('found')),
                        recorded_sha256_source='the ledger handoff event')
    workspace_block = {key: workspace.get(key) for key in WORKSPACE_KEYS}
    workspace_block.update(read=bool(workspace.get('read')), dirty=bool(workspace.get('dirty')))
    return {
        'version': 1,
        'kind': REPORT_KIND,
        'job_id': ledger.get('id'),
        'run_id': ledger.get('run_id'),
        'verdict': verdict,
        'reason': reason,
        'record': {'path': record_info.get('path'), 'sha256': record_info.get('sha256'),
                   'read': bool(record_info.get('read')), 'reason': record_info.get('reason')},
        'ledger': ledger_block,
        'workspace': workspace_block,
        'disagreements': disagreements,
        'disagreement_count': len(disagreements),
        'disagreements_beyond_bound': beyond,
        'unverifiable': unverifiable,
        'not_applicable': not_applicable,
        'manifest_updated': False,
        'manifest_reason': MANIFEST_REASON,
        'limits': dict(LIMITS),
        'note': NOTE,
    }
