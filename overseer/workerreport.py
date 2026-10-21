"""Capture a worker's status block from the implementation command's log.

After the implementation command runs, the factory reads a bounded tail of its
merged stdout/stderr log (``00.log``) and parses the AGENTS.md status block out
of it with ``overseer.statusblock``. The result is recorded as evidence; it is
never a verdict. Pass or fail stays decided by the acceptance exit codes, so a
``TESTS_PASSED: TRUE`` claim on a run whose acceptance failed is recorded as a
disagreement that changes nothing. A ``STUCK_NEEDS_ESCALATION`` block sets the
``escalate`` flag; the factory, not this module, acts on it.

Only the last 64 KiB of the log is read, and the size is checked before the
file is opened, so an oversized log never pulls more than the tail into memory.
The digest recorded is of the exact bytes read.
"""
import hashlib
from pathlib import Path

from overseer import statusblock

LOG_NAME = '00.log'
MAX_LOG_BYTES = 64 * 1024


def _unavailable(reason):
    return {'captured': False, 'reason': reason, 'log': LOG_NAME,
            'log_bytes_read': 0, 'log_truncated': False, 'log_sha256': None,
            'block': statusblock.parse(''), 'claim': None,
            'claim_disagrees': False, 'escalate': False, 'final_state': None}


def capture(evidence, final_state):
    """Return the worker-report record for one attempt's implementation log.

    ``evidence`` is the run directory and ``final_state`` is the state the exit
    codes decided. The record carries the parsed block, the bytes read and their
    digest, whether a success claim disagrees with the outcome, and whether the
    worker asked to escalate.
    """
    log = Path(evidence) / LOG_NAME
    if not log.is_file():
        return _unavailable('no implementation command log was written')
    size = log.stat().st_size
    truncated = size > MAX_LOG_BYTES
    with log.open('rb') as handle:
        if truncated:
            handle.seek(size - MAX_LOG_BYTES)
        data = handle.read(MAX_LOG_BYTES)
    block = statusblock.parse(data.decode('utf-8', 'replace'))
    claim = None
    if block['valid']:
        claim = 'TRUE' if block['tests_passed'] else 'FALSE'
    # A success claim that the exit codes contradict is recorded, not trusted.
    claim_disagrees = bool(block['valid'] and block['tests_passed'] is True
                           and final_state != 'passed')
    escalate = bool(block['valid'] and block['status'] == statusblock.STATUS_STUCK)
    return {
        'captured': True, 'reason': None, 'log': LOG_NAME,
        'log_bytes_read': len(data), 'log_truncated': truncated,
        'log_sha256': hashlib.sha256(data).hexdigest(),
        'block': block, 'claim': claim, 'claim_disagrees': claim_disagrees,
        'escalate': escalate, 'final_state': final_state,
    }
