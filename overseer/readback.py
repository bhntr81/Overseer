"""Bounded read-back of a run's evidence, for the reconciliation.

A file is read with its size checked before it is opened and its read
capped, and every failure becomes a reason, never an exception. The results
check derives the completed, failing, and not-run identifiers from the exit
codes the context manifest recorded, with the same rule the handoff record
uses, and the manifest is trusted only when its digest is the one the ledger
recorded. No command is re-run, and the module reads no ledger and starts no
process.
"""

import hashlib
import json
import os
from pathlib import Path

from overseer.handoff import MAX_COMMANDS, MAX_IDENTIFIERS, acceptance

MAX_MANIFEST_BYTES = 1024 * 1024
SPEC_NAME = 'SPEC.md'
MAX_SPEC_BYTES = 64 * 1024
CATEGORIES = ('completed', 'failing', 'not_run')
NOUN = 'context manifest'

RESULTS_SOURCE = ('commands_actually_run in the run\'s context.json, whose digest the ledger '
                  'recorded in its context_manifest event; these are the exit codes the factory '
                  'recorded once at the end of the attempt, and no command is re-run')

RESULTS_REASON = ('the record\'s identifier lists do not follow from the exit codes the context '
                  'manifest recorded: an identifier is completed when its acceptance command '
                  'exited 0, failing when it exited non-zero or timed out, and not run when the '
                  'run stopped before it')


def depth(value, bound):
    """Return the nesting depth of a parsed value, without recursing past the bound."""
    deepest = 0
    stack = [(value, 1)]
    while stack:
        item, level = stack.pop()
        deepest = max(deepest, level)
        if level > bound:
            return level
        if isinstance(item, dict):
            stack.extend((child, level + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, level + 1) for child in item)
    return deepest


def read_bytes(path, bound, noun):
    """Return a file's bytes, or the reason they could not be read.

    The size is checked before the file is opened, and the read is capped, so
    a file that grows after its size was taken is not read whole.
    """
    too_large = 'the %s is larger than the %d byte bound' % (noun, bound)
    try:
        if os.stat(path).st_size > bound:
            return None, too_large
        with path.open('rb') as handle:
            data = handle.read(bound + 1)
    except FileNotFoundError:
        return None, 'the %s does not exist' % noun
    except OSError as error:
        return None, 'the %s could not be read: %s' % (noun, type(error).__name__)
    if len(data) > bound:
        return None, too_large
    return data, None


def _spec_absent(reason, path):
    return {'present': False, 'path': path, 'sha256': None, 'bytes': None, 'reason': reason}


def read_spec(workspace, bound=MAX_SPEC_BYTES):
    """Return the target SPEC.md pointer: present with its path and digest, or
    absent with the reason.

    A SPEC.md that is a symlink resolving outside the workspace is refused and
    recorded as absent; otherwise the file is read bounded, size checked first.
    A missing SPEC.md is absent, never an error. The spec is context only;
    nothing here enforces it.
    """
    if not workspace:
        return _spec_absent('the attempt has no workspace', None)
    root = Path(workspace)
    spec = root / SPEC_NAME
    if spec.is_symlink():
        real = os.path.realpath(str(spec))
        root_real = os.path.realpath(str(root))
        if real != root_real and not real.startswith(root_real + os.sep):
            return _spec_absent(
                'SPEC.md is a symlink that resolves outside the workspace; refused', str(spec))
    elif not spec.exists():
        return _spec_absent('no SPEC.md in the workspace', None)
    data, reason = read_bytes(spec, bound, 'target SPEC.md')
    if data is None:
        return _spec_absent(reason, str(spec))
    return {'present': True, 'path': str(spec), 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'reason': None}


def parse_object(data, noun, max_depth):
    """Return the JSON object the bytes hold, or the reason they do not hold one."""
    try:
        parsed = json.loads(data.decode('utf-8'))
    except UnicodeDecodeError:
        return None, 'the %s is not UTF-8 text' % noun
    except RecursionError:
        return None, 'the %s is nested deeper than the parser allows' % noun
    except json.JSONDecodeError:
        return None, 'the %s is not JSON' % noun
    if not isinstance(parsed, dict):
        return None, 'the %s is not a JSON object' % noun
    if depth(parsed, max_depth) > max_depth:
        return None, 'the %s is nested deeper than the %d level bound' % (noun, max_depth)
    return parsed, None


def _command_problem(commands):
    """Return the reason the manifest's command list is malformed, or None."""
    if not isinstance(commands, list):
        return 'the %s has no commands_actually_run list' % NOUN
    if len(commands) > MAX_COMMANDS:
        return 'the %s records more than %d commands' % (NOUN, MAX_COMMANDS)
    for index, command in enumerate(commands):
        exit_code = command.get('exit_code') if isinstance(command, dict) else None
        if (not isinstance(command, dict) or not isinstance(command.get('stage'), str)
                or not isinstance(command.get('timed_out'), bool)
                or isinstance(exit_code, bool)
                or not (exit_code is None or isinstance(exit_code, int))):
            return 'the %s\'s command at index %d is malformed' % (NOUN, index)
    return None


def read_results(path, recorded_sha256, recorded_reason, max_depth=64):
    """Return the results authority: the manifest's commands, or why it cannot be trusted.

    The steps run in a fixed order, and the first that fails names the reason:
    no evidence directory, no ledger digest, the bounded read, the digest
    check, the parse, and the shape of the command list.
    """
    info = {'path': str(path) if path is not None else None, 'sha256': None,
            'recorded_sha256': recorded_sha256, 'read': False, 'reason': None,
            'source': RESULTS_SOURCE, 'commands': None}
    if path is None:
        info['reason'] = 'the job has no run evidence directory'
        return info
    if recorded_sha256 is None:
        info['reason'] = recorded_reason or 'the ledger records no digest for the %s' % NOUN
        return info
    data, info['reason'] = read_bytes(path, MAX_MANIFEST_BYTES, NOUN)
    if data is None:
        return info
    info['sha256'] = hashlib.sha256(data).hexdigest()
    if info['sha256'] != recorded_sha256:
        info['reason'] = ('the digest of the %s as read back is not the digest the ledger '
                          'recorded for it' % NOUN)
        return info
    manifest, info['reason'] = parse_object(data, NOUN, max_depth)
    if manifest is None:
        return info
    info['reason'] = _command_problem(manifest.get('commands_actually_run'))
    if info['reason'] is None:
        info['commands'] = manifest['commands_actually_run']
        info['read'] = True
    return info


def _differing(identifiers, recorded, authority, ran):
    """Return each identifier whose recorded categories are not its derived one."""
    derived = {item: name for name in CATEGORIES for item in authority[name]}
    order = list(identifiers) + [item for name in CATEGORIES for item in recorded[name]]
    differing = []
    for item in dict.fromkeys(order):
        categories = [name for name in CATEGORIES if item in recorded[name]]
        if categories == [derived.get(item)]:
            continue
        index = identifiers.index(item) if item in identifiers else None
        command = ran[index] if index is not None and index < len(ran) else None
        differing.append({'id': item, 'record': categories, 'authority': derived.get(item),
                          'exit_code': command.get('exit_code') if command else None,
                          'timed_out': bool(command.get('timed_out')) if command else None})
    return differing


def compare_results(record, contract, info, disagreements, unverifiable, not_applicable):
    """Compare the record's identifier lists, as sets, with those the exit codes imply."""
    if contract is None or len(contract) > MAX_IDENTIFIERS:
        not_applicable.append({
            'fact': 'acceptance_results',
            'reason': 'the stored job names no usable contract, so no identifier can be mapped '
                      'onto a command; the acceptance_ids entry says why'})
        return
    if not info.get('read'):
        unverifiable.append({'fact': 'acceptance_results', 'reason': info.get('reason')})
        return
    identifiers = [str(value) for value in contract][:MAX_IDENTIFIERS]
    completed, failing, not_run, ran = acceptance(identifiers, info['commands'])
    authority = dict(zip(CATEGORIES, (completed, failing, not_run)))
    recorded = {name: list(record[name + '_acceptance_ids']['value']) for name in CATEGORIES}
    if all(set(recorded[name]) == set(authority[name]) for name in CATEGORIES):
        return
    differing = _differing(identifiers, recorded, authority, ran)
    disagreements.append({'kind': 'acceptance_results_mismatch', 'record': recorded,
                          'authority': authority, 'reason': RESULTS_REASON,
                          'identifiers': differing[:MAX_IDENTIFIERS],
                          'identifiers_beyond_bound': max(0, len(differing) - MAX_IDENTIFIERS)})
