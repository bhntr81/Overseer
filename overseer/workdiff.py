"""The patch receipt of an attempt: what the workspace held after it, read-only.

A snapshot of a git workspace is taken before the implementation command and
another after it. The paths whose state differs between the two are the
attempt's change, and a git-style unified patch from the before state to the
after state of those paths is built in Python. Changes present before the
attempt are not attributed to it. Git is only read: no command that writes the
index, a ref, or the workspace is run, the optional index refresh is disabled,
and no hook, external diff, or text conversion can run. Every bound is
explicit, and what a bound or a rule withheld is recorded with the reason.
"""
import difflib
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess

from overseer.codemap import is_secret

MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_FILE_BYTES = 256 * 1024
MAX_HASH_BYTES = 64 * 1024 * 1024
MAX_BEFORE_BYTES = 8 * 1024 * 1024
MAX_DIFF_FILES = 200
MAX_PATCH_BYTES = 1024 * 1024
MAX_PATH_CHARS = 1024
MAX_LISTED = 200
MAX_PRE_EXISTING_LISTED = 50
GIT_TIMEOUT = 10
LIMITS = {'max_git_output_bytes': MAX_GIT_OUTPUT_BYTES, 'max_file_bytes': MAX_FILE_BYTES,
          'max_hash_bytes': MAX_HASH_BYTES, 'max_before_bytes': MAX_BEFORE_BYTES,
          'max_diff_files': MAX_DIFF_FILES, 'max_patch_bytes': MAX_PATCH_BYTES,
          'max_path_chars': MAX_PATH_CHARS, 'max_listed': MAX_LISTED,
          'max_pre_existing_listed': MAX_PRE_EXISTING_LISTED}
OID = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
TREE_ENTRY = re.compile(r'(?P<mode>[0-7]{6}) (?P<kind>blob|tree|commit) (?P<oid>[0-9a-f]{40,64})')
# A path git would quote, or that a patch header cannot carry plainly.
NEEDS_QUOTING = re.compile(r'[\x00-\x1f\x7f"\\]')
NOTE = ('the patch is what the workspace held after the implementation command, compared '
        'with its state at the start of the attempt; changes present before the attempt '
        'are not included; ignored files are not seen; renames are not detected')
GIT_OPTIONS = ['-c', 'core.quotepath=off', '-c', 'core.fsmonitor=false',
               '-c', 'core.untrackedCache=false', '-c', 'color.ui=false']


class GitProblem(Exception):
    """A git fact could not be read; the message is the recorded reason."""


def _git(root, *arguments, allow_failure=False):
    """Run one read-only git command and return its stdout bytes.

    The optional index refresh is disabled, so even git status writes nothing;
    no pager, prompt, system configuration, fsmonitor hook, or untracked cache
    is used. The output is bounded.
    """
    env = dict(os.environ)
    env.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', GIT_PAGER='cat', PAGER='cat',
               GIT_CONFIG_NOSYSTEM='1', LC_ALL='C')
    try:
        result = subprocess.run(['git', '-C', str(root), *GIT_OPTIONS, *arguments],
                                capture_output=True, timeout=GIT_TIMEOUT, env=env)
    except FileNotFoundError:
        raise GitProblem('git is not available on this machine') from None
    except subprocess.TimeoutExpired:
        raise GitProblem('git did not answer within %d seconds' % GIT_TIMEOUT) from None
    except (OSError, subprocess.SubprocessError) as error:
        raise GitProblem('git could not be run: %s' % type(error).__name__) from None
    if len(result.stdout) > MAX_GIT_OUTPUT_BYTES:
        raise GitProblem('git printed more than %d bytes' % MAX_GIT_OUTPUT_BYTES)
    if result.returncode and not allow_failure:
        raise GitProblem('git %s exited with status %d' % (arguments[0], result.returncode))
    return result.returncode, result.stdout


def _decode(raw):
    """Return a git path as text; a path that is not UTF-8 keeps its bytes as surrogates."""
    return raw.decode('utf-8', errors='surrogateescape')


def _utf8(path):
    """Return whether a path round-trips to UTF-8."""
    try:
        path.encode('utf-8')
    except UnicodeEncodeError:
        return False
    return True


def shown(path):
    """Return a path as it may be written into a record."""
    return path.encode('utf-8', errors='surrogateescape').decode('utf-8', errors='backslashreplace')


def _status(root, prefix):
    """Return {root-relative path: status letters} under the workspace prefix."""
    _, out = _git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                  '--no-renames')
    entries = {}
    for item in out.split(b'\0'):
        if len(item) < 4:
            continue
        path = _decode(item[3:])
        if prefix and not path.startswith(prefix):
            continue
        entries[path] = _decode(item[:2])
    return entries


def _identity(path):
    """Return the identity of a worktree path, its mode, and its regular-file size.

    The identity of a regular file or a symlink is its git blob id, so it can be
    compared with a commit's tree; a symlink's target is hashed as git hashes it
    and never followed or recorded. A file larger than the hash bound is
    identified by its size and modification time. A secret-named file is not
    opened; it is identified by its size and modification time.
    """
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None, None, None
    if stat.S_ISLNK(info.st_mode):
        target = os.fsencode(os.readlink(path))
        return _blob_id(target), '120000', None
    if not stat.S_ISREG(info.st_mode):
        return ('other', info.st_size, info.st_mtime_ns), None, None
    mode = '100755' if info.st_mode & 0o100 else '100644'
    if is_secret(path) or info.st_size > MAX_HASH_BYTES:
        return ('unhashed', info.st_size, info.st_mtime_ns), mode, info.st_size
    digest = hashlib.sha1(b'blob %d\0' % info.st_size)
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest(), mode, info.st_size


def _blob_id(data):
    """Return the git blob id of some bytes, as git computes it in a SHA-1 repository."""
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def _read(path, size):
    """Return the bytes of a regular file, or None when it is larger than the bound."""
    if size is None or size > MAX_FILE_BYTES:
        return None
    with open(path, 'rb') as handle:
        data = handle.read(MAX_FILE_BYTES + 1)
    return None if len(data) > MAX_FILE_BYTES else data


def snapshot(workspace, hold=True):
    """Record the state of a git workspace without changing it.

    The head, the status of every path under the workspace, and, for each path
    that is dirty or untracked, its identity and mode are recorded; its bytes
    are held in memory only when hold is true, the file is regular, not
    secret-named, within the file bound, and within the before budget. Nothing
    is written anywhere. A workspace that cannot be read returns the reason.
    """
    if not workspace:
        return {'captured': False, 'reason': 'the task names no workspace'}
    if not os.path.isdir(workspace):
        return {'captured': False, 'reason': 'the workspace is not a directory'}
    try:
        code, out = _git(workspace, 'rev-parse', '--show-toplevel', allow_failure=True)
        if code:
            return {'captured': False, 'reason': 'the workspace is not a git work tree'}
        root = _decode(out.strip())
        _, out = _git(workspace, 'rev-parse', '--show-prefix')
        prefix = _decode(out.strip())
        _, out = _git(root, 'rev-parse', '--show-object-format', allow_failure=True)
        if out.strip() not in (b'', b'sha1'):
            return {'captured': False, 'reason': 'the repository does not use SHA-1 object ids'}
        code, out = _git(root, 'rev-parse', '--verify', '-q', 'HEAD', allow_failure=True)
        head = out.strip().decode('ascii') if not code else None
        if head is not None and not OID.fullmatch(head):
            return {'captured': False, 'reason': 'git printed a head that is not an object id'}
        status = _status(root, prefix)
    except GitProblem as problem:
        return {'captured': False, 'reason': str(problem)}
    held = {}
    budget = MAX_BEFORE_BYTES
    for path, letters in sorted(status.items()):
        target = os.path.join(root, os.fsdecode(path.encode('utf-8', 'surrogateescape')))
        identity, mode, size = _identity(target)
        entry = {'identity': identity, 'mode': mode, 'bytes': None, 'withheld': None}
        if hold and identity is not None and mode not in (None, '120000'):
            if is_secret(target):
                entry['withheld'] = 'secret_name'
            elif size is not None and size > MAX_FILE_BYTES:
                entry['withheld'] = 'too_large'
            elif size is not None and size > budget:
                entry['withheld'] = 'before_budget'
            else:
                data = _read(target, size)
                if data is None:
                    entry['withheld'] = 'too_large'
                else:
                    entry['bytes'] = data
                    budget -= len(data)
        held[path] = entry
    return {'captured': True, 'reason': None, 'root': root, 'prefix': prefix, 'head': head,
            'status': status, 'held': held}


def _tree_entry(root, head, path):
    """Return (mode, blob id) of a path in a commit, or (None, None) when absent."""
    if head is None:
        return None, None
    _, out = _git(root, 'ls-tree', '-z', '--full-tree', head, '--',
                  path.encode('utf-8', 'surrogateescape'))
    for item in out.split(b'\0'):
        if not item:
            continue
        meta, _, name = item.partition(b'\t')
        match = TREE_ENTRY.fullmatch(meta.decode('ascii', errors='replace'))
        if match and _decode(name) == path and match.group('kind') == 'blob':
            return match.group('mode'), match.group('oid')
    return None, None


def _blob(root, oid):
    """Return the bytes of a blob within the file bound, or None."""
    _, out = _git(root, 'cat-file', '-s', oid)
    if int(out.strip() or b'0') > MAX_FILE_BYTES:
        return None
    _, out = _git(root, 'cat-file', 'blob', oid)
    return out


def _moved_paths(root, prefix, before, after):
    """Return the paths that differ between two commits, under the workspace prefix."""
    if before is None or after is None or before == after:
        return set()
    _, out = _git(root, 'diff-tree', '-r', '-z', '--name-only', '--no-renames',
                  '--no-commit-id', '--no-ext-diff', '--no-textconv', before, after)
    paths = set()
    for item in out.split(b'\0'):
        if item:
            path = _decode(item)
            if not prefix or path.startswith(prefix):
                paths.add(path)
    return paths


def _before_side(before, path):
    """Return (identity, mode, bytes, withheld) of a path at the before snapshot."""
    if path in before['held']:
        entry = before['held'][path]
        withheld = entry['withheld']
        if entry['identity'] is not None and entry['bytes'] is None and withheld is None \
                and entry['mode'] not in (None, '120000'):
            withheld = 'withheld_pre_existing'
        return entry['identity'], entry['mode'], entry['bytes'], withheld, True
    mode, oid = _tree_entry(before['root'], before['head'], path)
    return oid, mode, None, None, False


def _is_text(data):
    """Return whether bytes are text a unified patch can carry."""
    if b'\0' in data:
        return False
    try:
        data.decode('utf-8')
    except UnicodeDecodeError:
        return False
    return True


def _file_patch(path, status, old_mode, new_mode, old, new):
    """Return the git-style patch of one text file, or of a mode change alone."""
    header = ['diff --git a/%s b/%s\n' % (path, path)]
    if status == 'added':
        header.append('new file mode %s\n' % new_mode)
    elif status == 'deleted':
        header.append('deleted file mode %s\n' % old_mode)
    elif old_mode != new_mode:
        header.append('old mode %s\nnew mode %s\n' % (old_mode, new_mode))
    a = old.decode('utf-8').splitlines(keepends=True) if old is not None else []
    b = new.decode('utf-8').splitlines(keepends=True) if new is not None else []
    tab = '\t' if ' ' in path else ''
    source = '/dev/null' if status == 'added' else 'a/%s%s' % (path, tab)
    target = '/dev/null' if status == 'deleted' else 'b/%s%s' % (path, tab)
    body = []
    insertions = deletions = 0
    for line in difflib.unified_diff(a, b, source, target, n=3):
        if line.startswith('--- ') or line.startswith('+++ '):
            # A name with a space ends with a tab, as git writes it.
            body.append(line)
            continue
        if line.startswith('+') and not line.startswith('+++'):
            insertions += 1
        elif line.startswith('-') and not line.startswith('---'):
            deletions += 1
        if line.endswith('\n'):
            body.append(line)
        else:
            body.append(line + '\n\\ No newline at end of file\n')
    return ''.join(header + body), insertions, deletions


def _changes(before, after):
    """Return the sorted changed paths with both sides, between two snapshots."""
    root = before['root']
    candidates = set(before['status']) | set(after['status'])
    candidates |= _moved_paths(root, before['prefix'], before['head'], after['head'])
    changed = []
    for path in sorted(candidates):
        old_id, old_mode, old_bytes, withheld, pre_existing = _before_side(before, path)
        target = os.path.join(root, os.fsdecode(path.encode('utf-8', 'surrogateescape')))
        new_id, new_mode, new_size = _identity(target)
        if (old_id, old_mode) == (new_id, new_mode):
            continue
        changed.append({'path': path, 'target': target, 'old_id': old_id, 'old_mode': old_mode,
                        'old_bytes': old_bytes, 'withheld': withheld,
                        'pre_existing': pre_existing, 'new_id': new_id, 'new_mode': new_mode,
                        'new_size': new_size})
    return changed


def _status_word(change):
    """Return the status of one changed path."""
    if change['old_id'] is None:
        return 'added'
    if change['new_id'] is None:
        return 'deleted'
    if (change['old_mode'] == '120000') != (change['new_mode'] == '120000'):
        return 'type_changed'
    if change['old_id'] == change['new_id']:
        return 'mode_changed'
    return 'modified'


def capture(before, workspace):
    """Return (patch_text, receipt, after) for what changed since the snapshot.

    Each changed path is patched from its before content: the held bytes of a
    path that was dirty or untracked at the start, or the before head's blob of
    a path that was clean, so a commit the attempt made is inside the patch and
    the user's own earlier edit is not. A secret-named path is listed without
    content and without a hash; a binary file is recorded by its hashes; a
    symlink's target is not recorded; a file over the bound, a pre-existing
    file whose bytes were not held, a path that is not UTF-8 or needs quoting,
    and every file past the patch bound are withheld with the reason. The
    patch is cut only at a file boundary.
    """
    if not before.get('captured'):
        return '', {'captured': False, 'reason': before.get('reason'), 'limits': dict(LIMITS)}, None
    after = snapshot(workspace, hold=False)
    if not after.get('captured'):
        return '', {'captured': False, 'reason': after.get('reason'),
                    'limits': dict(LIMITS)}, None
    try:
        return _capture(before, after)
    except GitProblem as problem:
        return '', {'captured': False, 'reason': str(problem), 'limits': dict(LIMITS)}, None
    except OSError as error:
        return '', {'captured': False, 'reason': 'the workspace could not be read: %s'
                    % type(error).__name__, 'limits': dict(LIMITS)}, None


def _capture(before, after):
    """Return the patch, the receipt, and the after snapshot; see capture."""
    root, prefix = before['root'], before['prefix']
    changed = _changes(before, after)
    files = []
    pieces = []
    patch_bytes = 0
    stopped = False
    for change in changed[:MAX_DIFF_FILES]:
        relative = change['path'][len(prefix):]
        status = _status_word(change)
        entry = {'path': shown(relative)[:MAX_PATH_CHARS], 'status': status, 'content': None,
                 'insertions': 0, 'deletions': 0}
        if len(shown(relative)) > MAX_PATH_CHARS:
            entry['path_truncated'] = True
        files.append(entry)
        content = None
        if entry.get('path_truncated'):
            content = 'path_too_long'
        elif not _utf8(change['path']):
            content = 'path_not_utf8'
        elif NEEDS_QUOTING.search(change['path']):
            content = 'path_needs_quoting'
        elif is_secret(change['target']) or is_secret(change['path']):
            content = 'secret_name'
        elif change['old_mode'] == '120000' or change['new_mode'] == '120000':
            content = 'symlink'
        elif change['withheld'] in ('withheld_pre_existing', 'too_large', 'before_budget') \
                and change['pre_existing']:
            content = 'withheld_pre_existing' if change['withheld'] != 'too_large' else 'too_large'
        if content is None:
            old = change['old_bytes']
            if not change['pre_existing'] and change['old_id'] is not None:
                old = _blob(root, change['old_id'])
                if old is None:
                    content = 'too_large'
            new = None
            if content is None and change['new_id'] is not None:
                new = _read(change['target'], change['new_size'])
                if new is None:
                    content = 'too_large'
            if content is None and ((old is not None and not _is_text(old))
                                    or (new is not None and not _is_text(new))):
                content = 'binary'
                entry['before_sha256'] = hashlib.sha256(old).hexdigest() if old is not None else None
                entry['after_sha256'] = hashlib.sha256(new).hexdigest() if new is not None else None
        if content is None:
            if stopped:
                content = 'omitted_by_bound'
            else:
                piece, insertions, deletions = _file_patch(
                    relative, status, change['old_mode'], change['new_mode'], old, new)
                size = len(piece.encode('utf-8'))
                if patch_bytes + size > MAX_PATCH_BYTES:
                    stopped = True
                    content = 'omitted_by_bound'
                else:
                    pieces.append(piece)
                    patch_bytes += size
                    content = 'in_patch'
                    entry['insertions'] = insertions
                    entry['deletions'] = deletions
        entry['content'] = content
    patch = ''.join(pieces)
    data = patch.encode('utf-8')
    withheld = {}
    for entry in files:
        if entry['content'] not in ('in_patch', 'omitted_by_bound'):
            withheld[entry['content']] = withheld.get(entry['content'], 0) + 1
    in_patch = [entry for entry in files if entry['content'] == 'in_patch']
    omitted = sum(1 for entry in files if entry['content'] == 'omitted_by_bound')
    beyond = max(0, len(changed) - MAX_DIFF_FILES)
    groups = {}
    for change in changed:
        relative = change['path'][len(prefix):]
        top = relative.split('/', 1)[0] if '/' in relative else '.'
        groups[shown(top)] = groups.get(shown(top), 0) + 1
    changed_paths = {change['path'] for change in changed}
    untouched = sorted(path for path in before['status'] if path not in changed_paths)
    receipt = {
        'version': 1, 'captured': True, 'reason': None,
        'head_before': before['head'], 'head_after': after['head'],
        'head_moved': before['head'] != after['head'],
        'stats': {
            'files_changed': len(changed),
            'files_in_patch': len(in_patch),
            'files_withheld': dict(sorted(withheld.items())),
            'files_omitted': omitted,
            'files_beyond_bound': beyond,
            'insertions': sum(entry['insertions'] for entry in in_patch),
            'deletions': sum(entry['deletions'] for entry in in_patch),
            'complete': len(in_patch) == len(changed),
            'patch_bytes': len(data),
            'patch_sha256': hashlib.sha256(data).hexdigest(),
        },
        'paths': [{'top': top, 'count': groups[top]} for top in sorted(groups)],
        'files': files,
        'pre_existing': {'count': len(untouched),
                         'paths': [shown(path[len(prefix):])
                                   for path in untouched[:MAX_PRE_EXISTING_LISTED]]},
        'changed_by_checks': None,
        'ignored_files_seen': False,
        'renames_detected': False,
        'note': NOTE,
        'limits': dict(LIMITS),
    }
    return patch, receipt, after


def changed_since(after, workspace):
    """Return the paths whose state changed since a snapshot, status only, bounded."""
    if not after or not after.get('captured'):
        return None
    later = snapshot(workspace, hold=False)
    if not later.get('captured'):
        return None
    prefix = after['prefix']
    paths = []
    for change in _changes(after, later):
        paths.append({'path': shown(change['path'][len(prefix):])[:MAX_PATH_CHARS],
                      'status': _status_word(change)})
    return {'count': len(paths), 'paths': paths[:MAX_LISTED]}


def unchecked(reason):
    """Return the receipt of a capture that could not be made at all."""
    return {'version': 1, 'captured': False, 'reason': reason, 'limits': dict(LIMITS)}
