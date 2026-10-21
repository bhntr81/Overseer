"""Parse the AGENTS.md worker status block out of bounded terminal or log text.

The block is four lines, in this order:

    STATUS: SUCCESS | STUCK_NEEDS_ESCALATION
    TESTS_PASSED: TRUE | FALSE
    FILES_MODIFIED: [a.py, b.py]
    NEXT_AGENT_INSTRUCTION: "a JSON-quoted string"

The result is data, never executed. The instruction is decoded with
``json.loads`` as a plain string, so a block carrying code is returned as text
and nothing in the input is evaluated. Values are closed and fields are
bounded; an unknown or over-bound value is reported invalid with a reason,
never truncated into validity. The last complete block in the text wins, ANSI
escape sequences are stripped, and only the last 64 KiB of input is considered.

The control-character rule is the monitor's own sent-line rule, imported from
``overseer.policy`` so the two stay in step rather than drifting. This module
adds no dependency beyond the standard library and that sibling rule, and it
reads nothing and runs nothing.
"""
import json

from overseer.policy import ANSI, _controls

STATUS_SUCCESS = 'SUCCESS'
STATUS_STUCK = 'STUCK_NEEDS_ESCALATION'
STATUS_VALUES = (STATUS_SUCCESS, STATUS_STUCK)
TESTS_VALUES = {'TRUE': True, 'FALSE': False}
KEYS = ('STATUS', 'TESTS_PASSED', 'FILES_MODIFIED', 'NEXT_AGENT_INSTRUCTION')

MAX_INPUT_CHARS = 64 * 1024
MAX_INSTRUCTION_CHARS = 4000
MAX_FILES_MODIFIED = 200

# The unfilled template placeholders are never a value.
_TEMPLATE_STATUS = '[SUCCESS | STUCK_NEEDS_ESCALATION]'
_TEMPLATE_TESTS = '[TRUE | FALSE]'


def _result(found, valid, reason, status=None, tests_passed=None,
            files_modified=None, next_instruction=None):
    return {'found': found, 'valid': valid, 'reason': reason, 'status': status,
            'tests_passed': tests_passed, 'files_modified': files_modified,
            'next_instruction': next_instruction}


def _value(line, key):
    """Return the text after ``KEY:`` on a stripped line, or None if not that key."""
    body = line.strip()
    prefix = key + ':'
    if not body.startswith(prefix):
        return None
    return body[len(prefix):].strip()


def _find_last_block(lines):
    """Return the four raw values of the last complete, in-order block, or None."""
    found = None
    for index in range(len(lines) - 3):
        values = [_value(lines[index + offset], KEYS[offset]) for offset in range(4)]
        if all(value is not None for value in values):
            found = values
    return found


def _files(raw):
    """Parse a bracketed FILES_MODIFIED list, or raise ValueError."""
    text = raw.strip()
    if not (text.startswith('[') and text.endswith(']')):
        raise ValueError('files_modified is not a bracketed list')
    inner = text[1:-1].strip()
    if not inner:
        return []
    entries = [part.strip() for part in inner.split(',') if part.strip()]
    if len(entries) > MAX_FILES_MODIFIED:
        raise ValueError('files_modified has more than %d entries' % MAX_FILES_MODIFIED)
    return entries


def _instruction(raw):
    """Decode the JSON-quoted instruction, bounded, or raise ValueError."""
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError('next_instruction is not a JSON-quoted string')
    if not isinstance(value, str):
        raise ValueError('next_instruction is not a JSON string')
    if len(value) > MAX_INSTRUCTION_CHARS:
        raise ValueError('next_instruction is longer than %d characters' % MAX_INSTRUCTION_CHARS)
    if _controls(value):
        raise ValueError('next_instruction contains a control character')
    return value


def parse(text):
    """Parse the last status block from bounded text. It never evaluates the text."""
    if not isinstance(text, str):
        return _result(False, False, 'input is not text')
    cleaned = ANSI.sub('', text[-MAX_INPUT_CHARS:])
    block = _find_last_block(cleaned.splitlines())
    if block is None:
        return _result(False, False, 'no status block found')
    status_raw, tests_raw, files_raw, instruction_raw = block
    if status_raw == _TEMPLATE_STATUS or tests_raw == _TEMPLATE_TESTS:
        return _result(True, False, 'template not filled')
    if status_raw not in STATUS_VALUES:
        return _result(True, False, 'unknown status: ' + status_raw)
    if tests_raw not in TESTS_VALUES:
        return _result(True, False, 'unknown tests_passed: ' + tests_raw)
    try:
        files = _files(files_raw)
    except ValueError as error:
        return _result(True, False, str(error), status=status_raw,
                       tests_passed=TESTS_VALUES[tests_raw])
    try:
        instruction = _instruction(instruction_raw)
    except ValueError as error:
        return _result(True, False, str(error), status=status_raw,
                       tests_passed=TESTS_VALUES[tests_raw], files_modified=files)
    return _result(True, True, 'ok', status=status_raw,
                   tests_passed=TESTS_VALUES[tests_raw], files_modified=files,
                   next_instruction=instruction)
