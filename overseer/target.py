"""Scaffold a brand-new target repository for the factory to work in.

`python3 -m overseer.target init <dir> [--spec FILE]` creates an absent
directory (or accepts an empty existing one), initializes it as a git
repository, optionally copies a `SPEC.md`, and makes one initial commit with a
fixed, local committer identity. After that the first factory attempt has a
measurable base revision, so a handoff record reconciles against an anchored
commit instead of an unborn repository.

This module has its own git runner, which *writes*. It never reuses or loosens
the read-only runner in `overseer/workdiff.py`; a writing runner and a
read-only runner are kept apart on purpose. The committer identity is passed
through environment variables scoped to each call, so the user's git config is
never read for identity and never written.
"""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

GIT_TIMEOUT = 30
# A fixed, local identity, supplied per call. Nothing here writes git config.
_IDENTITY = {
    'GIT_AUTHOR_NAME': 'overseer-target', 'GIT_AUTHOR_EMAIL': 'overseer@localhost.invalid',
    'GIT_COMMITTER_NAME': 'overseer-target', 'GIT_COMMITTER_EMAIL': 'overseer@localhost.invalid',
}


class TargetError(ValueError):
    """A refusal: the target cannot be scaffolded as asked."""


def _git(root, *arguments):
    """Run a writing git command in ``root`` with the scoped identity."""
    env = dict(os.environ)
    env.update(_IDENTITY)
    result = subprocess.run(['git', *arguments], cwd=str(root),
                            capture_output=True, timeout=GIT_TIMEOUT, env=env)
    if result.returncode != 0:
        raise TargetError('git %s failed: %s'
                          % (arguments[0], result.stderr.decode('utf-8', 'replace').strip()))
    return result.stdout.decode('utf-8', 'replace')


def _nearest_existing(path):
    """Return the nearest ancestor of ``path`` that exists (``path`` itself if it does)."""
    probe = path
    while not probe.exists():
        if probe.parent == probe:
            return probe
        probe = probe.parent
    return probe


def _refuse_if_inside_work_tree(path):
    """Refuse a path that lies inside an existing git work tree, this repo included."""
    anchor = _nearest_existing(path)
    result = subprocess.run(['git', 'rev-parse', '--is-inside-work-tree'],
                            cwd=str(anchor), capture_output=True, timeout=GIT_TIMEOUT)
    if result.returncode == 0 and result.stdout.strip() == b'true':
        raise TargetError('refusing a path inside an existing git work tree: %s' % path)


def init(directory, spec=None, allow_nested=False):
    """Scaffold a target git repository and return its facts, or raise TargetError.

    The directory must be an absolute, non-symlinked path that is absent or an
    empty existing directory, and must not lie inside an existing git work tree
    unless ``allow_nested``. The window's "build a new program" passes it: a
    person who keeps their whole home folder in git (this author's machine)
    would otherwise be refused every project folder they could pick, and a
    repository nested in another is ordinary git, seen by the outer one as an
    untracked folder.
    """
    path = Path(directory)
    if not path.is_absolute():
        raise TargetError('the target directory must be an absolute path: %s' % directory)
    if path.is_symlink():
        raise TargetError('the target directory must not be a symlink: %s' % path)
    if path.exists():
        if not path.is_dir():
            raise TargetError('the target path exists and is not a directory: %s' % path)
        if any(path.iterdir()):
            raise TargetError('refusing a non-empty directory: %s' % path)
    if not allow_nested:
        _refuse_if_inside_work_tree(path)
    path.mkdir(parents=True, exist_ok=True)
    _git(path, 'init', '--quiet')
    copied = False
    if spec is not None:
        source = Path(spec)
        if not source.is_file():
            raise TargetError('the --spec file does not exist: %s' % spec)
        shutil.copyfile(str(source), str(path / 'SPEC.md'))
        _git(path, 'add', 'SPEC.md')
        _git(path, 'commit', '--quiet', '-m', 'scaffold target with SPEC.md')
        copied = True
    else:
        _git(path, 'commit', '--quiet', '--allow-empty', '-m', 'scaffold target')
    head = _git(path, 'rev-parse', 'HEAD').strip()
    return {'path': str(path), 'head': head, 'spec_copied': copied}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Scaffold a target repository.')
    sub = parser.add_subparsers(dest='action', required=True)
    init_parser = sub.add_parser('init')
    init_parser.add_argument('directory')
    init_parser.add_argument('--spec')
    args = parser.parse_args(argv)
    try:
        result = init(args.directory, args.spec)
    except (TargetError, OSError) as error:
        print(json.dumps({'error': str(error)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
