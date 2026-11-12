"""The skill provenance of an attempt, read and checked at its start.

The provenance file declares the skills installed for this project, where they
came from, and the hashes of their installed files. The factory reads and
validates it, and checks the installed bytes against the recorded hashes. It
runs argument-vector commands and supplies no skill to them, and whether a
client loaded a skill is not observable here, so no skill is ever recorded as
active, loaded, or used. Every bound is explicit, and a file that cannot be
read or validated is recorded with the reason; it never fails an attempt.
"""
import hashlib
import json
import os
from pathlib import Path
import re

from overseer.codemap import is_secret

MAX_PROVENANCE_BYTES = 64 * 1024
MAX_SKILLS = 32
MAX_SKILL_FILES = 16
MAX_FIELD_CHARS = 256
MAX_SKILL_FILE_BYTES = 256 * 1024
MAX_REJECTED = 32
MAX_OTHER_KEYS = 32

SKILL_NAME = re.compile(r'^[a-z0-9][a-z0-9-]{0,63}$')
FILE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
SHA256 = re.compile(r'^[0-9a-f]{64}$')
REVISION = re.compile(r'^[0-9a-f]{40}$')
OTHER_KEY = re.compile(r'[A-Za-z0-9_.-]{1,64}')
TOP_LEVEL = ('schema_version', 'recorded_at', 'repository', 'revision', 'license', 'skills')
TEXT_FIELDS = ('source_path', 'status', 'runtime_activation', 'runtime_discovery')
SKILL_REASON = ('declared by the provenance file; installed bytes checked at the start of '
                'this attempt; Overseer supplies no skill to an attempt; activation is not '
                'observable here')
NOTE = ('the provenance file declares these skills and their installed bytes were checked '
        'at the start of this attempt; the factory runs argument-vector commands and '
        'supplies no skill to them; whether a client loaded a skill is not observed')
LIMITS = {'max_provenance_bytes': MAX_PROVENANCE_BYTES, 'max_skills': MAX_SKILLS,
          'max_skill_files': MAX_SKILL_FILES, 'max_field_chars': MAX_FIELD_CHARS,
          'max_skill_file_bytes': MAX_SKILL_FILE_BYTES, 'max_rejected': MAX_REJECTED,
          'max_other_keys': MAX_OTHER_KEYS}


def _empty(path, reason, present=False, size=None, digest=None):
    """Return the record of a provenance file that could not be used."""
    return {'version': 1, 'path': str(path), 'present': present, 'bytes': size,
            'sha256': digest, 'valid': False, 'reason': reason, 'schema_version': None,
            'repository': None, 'revision': None, 'license': None, 'recorded_at': None,
            'other_keys': [], 'other_keys_unlisted': 0, 'notes': [], 'skills': [], 'declared_count': 0,
            'installed_verified_count': 0, 'supplied_count': 0,
            'activation_observed_count': 0, 'rejected': [], 'rejected_count': 0,
            'rejected_truncated': False, 'note': NOTE, 'limits': dict(LIMITS)}


def unchecked(path, reason):
    """Return the record of a provenance that could not be checked at all."""
    return _empty(path, reason, present=None)


def _text(value, absolute=False):
    """Return whether a value is short text without control characters.

    Text that cannot be encoded as UTF-8, such as a lone surrogate JSON
    allows, is refused, because a path made of it cannot be opened.
    """
    if not isinstance(value, str) or not value.strip() or len(value) > MAX_FIELD_CHARS:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    try:
        value.encode('utf-8')
    except UnicodeEncodeError:
        return False
    # A path recorded on a POSIX machine is still absolute when read on Windows.
    return not absolute or os.path.isabs(value) or value.startswith('/')


def _entry_problem(entry, seen):
    """Return why one skill entry cannot be kept, or None."""
    if not isinstance(entry, dict):
        return 'the entry is not an object'
    name = entry.get('name')
    if not isinstance(name, str) or not SKILL_NAME.fullmatch(name):
        return 'the name is not a lowercase skill name'
    if name in seen:
        return 'the name %s is declared twice' % name
    for field in TEXT_FIELDS:
        if not _text(entry.get(field)):
            return 'the %s is not short text without control characters' % field
    if not _text(entry.get('installed_path'), absolute=True):
        return 'the installed_path is not a short absolute path'
    files = entry.get('upstream_files_sha256')
    if not isinstance(files, dict) or not files or len(files) > MAX_SKILL_FILES:
        return 'the upstream_files_sha256 is not an object of 1 to %d files' % MAX_SKILL_FILES
    for key, value in files.items():
        # The rejected key is not copied into the reason: a rejected value
        # never reaches the evidence.
        if not isinstance(key, str) or not FILE_NAME.fullmatch(key):
            return 'a file name of upstream_files_sha256 is not a plain file name'
        if not isinstance(value, str) or not SHA256.fullmatch(value):
            return 'a hash of upstream_files_sha256 is not 64 lowercase hex characters'
    license_hash = entry.get('license_sha256')
    if not isinstance(license_hash, str) or not SHA256.fullmatch(license_hash):
        return 'the license_sha256 is not 64 lowercase hex characters'
    return None


def _check_file(installed, name, expected):
    """Return the outcome of one installed file against its recorded hash.

    The file is not opened when its name marks it as a secret, when its real
    path leaves the installed directory, or when it is larger than the bound;
    the size is checked before it is opened. No content is kept.
    """
    target = Path(installed) / name
    result = {'name': name, 'expected': expected, 'outcome': None, 'observed': None}
    try:
        return _check_target(installed, target, expected, result)
    except (OSError, ValueError):
        result['outcome'] = 'unreadable'
        return result


def _check_target(installed, target, expected, result):
    """Return the outcome of one checked path; see _check_file."""
    if is_secret(target):
        result['outcome'] = 'secret_name'
        return result
    root = os.path.realpath(installed)
    real = os.path.realpath(target)
    if os.path.commonpath([root, real]) != root:
        result['outcome'] = 'outside'
        return result
    if not os.path.lexists(target):
        result['outcome'] = 'missing'
        return result
    if not os.path.isfile(real):
        result['outcome'] = 'not_a_file'
        return result
    if os.stat(real).st_size > MAX_SKILL_FILE_BYTES:
        result['outcome'] = 'too_large'
        return result
    # The read is bounded too, so a file that grows after its size was taken
    # is not read whole.
    with open(real, 'rb') as handle:
        data = handle.read(MAX_SKILL_FILE_BYTES + 1)
    if len(data) > MAX_SKILL_FILE_BYTES:
        result['outcome'] = 'too_large'
        return result
    observed = hashlib.sha256(data).hexdigest()
    if observed == expected:
        result['outcome'] = 'match'
    else:
        result['outcome'] = 'mismatch'
        result['observed'] = observed
    return result


def provenance(path):
    """Read, validate, and check the skill provenance file at the start of an attempt.

    Only the listed fields are copied; an unknown top-level key is named, not
    copied, and the blueprint block, which holds a host path outside the
    repository, is not copied. A file with more skills than the bound is
    rejected whole, so a truncated list is never presented as the whole. An
    entry that fails is rejected with its reason and its siblings are kept.
    The license file is not checked, because the provenance names no path for
    it. Nothing is supplied to the attempt and no activation is observed.
    """
    path = Path(path)
    try:
        info = os.stat(path)
    except FileNotFoundError:
        return _empty(path, 'the provenance file does not exist')
    except OSError as error:
        return _empty(path, 'the provenance file could not be read: %s' % error.strerror)
    if not os.path.isfile(path):
        return _empty(path, 'the provenance path is not a regular file', present=True)
    if info.st_size > MAX_PROVENANCE_BYTES:
        return _empty(path, 'the provenance file is larger than %d bytes' % MAX_PROVENANCE_BYTES,
                      present=True, size=info.st_size)
    try:
        with open(path, 'rb') as handle:
            raw = handle.read(MAX_PROVENANCE_BYTES + 1)
    except OSError as error:
        return _empty(path, 'the provenance file could not be read: %s' % error.strerror,
                      present=True, size=info.st_size)
    if len(raw) > MAX_PROVENANCE_BYTES:
        return _empty(path, 'the provenance file is larger than %d bytes' % MAX_PROVENANCE_BYTES,
                      present=True, size=len(raw))
    digest = hashlib.sha256(raw).hexdigest()
    try:
        data = json.loads(raw.decode('utf-8'))
    except UnicodeDecodeError:
        return _empty(path, 'the provenance file is not UTF-8 text', True, len(raw), digest)
    except ValueError:
        return _empty(path, 'the provenance file is not JSON', True, len(raw), digest)
    if not isinstance(data, dict):
        return _empty(path, 'the provenance file is not a JSON object', True, len(raw), digest)
    if type(data.get('schema_version')) is not int or data.get('schema_version') != 1:
        return _empty(path, 'the provenance schema_version is not 1', True, len(raw), digest)
    entries = data.get('skills')
    if not isinstance(entries, list):
        return _empty(path, 'the provenance skills field is not a list', True, len(raw), digest)
    if len(entries) > MAX_SKILLS:
        return _empty(path, 'the provenance file declares %d skills, more than %d'
                      % (len(entries), MAX_SKILLS), True, len(raw), digest)
    record = _empty(path, None, True, len(raw), digest)
    record['valid'] = True
    record['schema_version'] = 1
    for field in ('repository', 'license', 'recorded_at'):
        value = data.get(field)
        record[field] = value if _text(value) else None
    for field in ('repository', 'license', 'recorded_at'):
        if field in data and record[field] is None:
            record['notes'].append('the %s is not short text and was not copied' % field)
    revision = data.get('revision')
    if isinstance(revision, str) and REVISION.fullmatch(revision):
        record['revision'] = revision
    else:
        record['revision'] = None
        record['notes'].append('the revision is not 40 lowercase hex characters and was '
                               'not copied')
    # Only plain key names are listed, and at most a bound of them; a key that
    # is not plain is counted, never copied.
    others = sorted(key for key in data if key not in TOP_LEVEL)
    plain = [key for key in others if OTHER_KEY.fullmatch(key)]
    record['other_keys'] = plain[:MAX_OTHER_KEYS]
    record['other_keys_unlisted'] = len(others) - len(record['other_keys'])
    seen = set()
    skills = []
    rejected = []
    for index, entry in enumerate(entries):
        problem = _entry_problem(entry, seen)
        if problem:
            rejected.append({'index': index, 'reason': problem})
            continue
        seen.add(entry['name'])
        files = [_check_file(entry['installed_path'], name, expected)
                 for name, expected in sorted(entry['upstream_files_sha256'].items())]
        skills.append({
            'name': entry['name'],
            'source_path': entry['source_path'],
            'installed_path': entry['installed_path'],
            'declared_status': entry['status'],
            'declared_runtime_activation': entry['runtime_activation'],
            'declared_runtime_discovery': entry['runtime_discovery'],
            'license_sha256': entry['license_sha256'],
            'files': files,
            'installed_verified': all(item['outcome'] == 'match' for item in files),
            # No code passes a skill to a command, and nothing observes a load.
            'supplied_to_attempt': False,
            'activation_observed': False,
            'reason': SKILL_REASON,
        })
    skills.sort(key=lambda skill: skill['name'])
    record['skills'] = skills
    record['declared_count'] = len(skills)
    record['installed_verified_count'] = sum(1 for skill in skills if skill['installed_verified'])
    record['supplied_count'] = sum(1 for skill in skills if skill['supplied_to_attempt'])
    record['activation_observed_count'] = sum(1 for skill in skills
                                              if skill['activation_observed'])
    record['rejected'] = rejected[:MAX_REJECTED]
    record['rejected_count'] = len(rejected)
    record['rejected_truncated'] = len(rejected) > MAX_REJECTED
    if rejected:
        record['reason'] = '%d skill entries were rejected' % len(rejected)
    return record
