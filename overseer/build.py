"""One prompt in, a working program out: the factory loop set up from a single request.

Two modes share one engine. ``new`` creates a project folder, writes the request
into it as SPEC.md and builds the program from nothing. ``continue`` points at a
folder that already exists and has the worker find and finish whatever is left
there. Either way the loop runs one fresh worker session per step, so each
session is given the same preamble: what is being built, where its notes are,
and how to report.

"Working" is not the worker's word. Every project carries ``overseer_check.py``,
which the worker writes and keeps honest (it runs the program's real tests, or
runs the program, and exits 0 only when it works), and the factory runs it
itself after every step. The loop stops at OVERSEER_DONE with that check
passing, or when it needs a person, or at the step limit.

The ledger, evidence and step plan live under the user's local application
data, keyed by the project folder, so the project itself gains only SPEC.md
(new projects), SESSION_HANDOFF.md and overseer_check.py.
"""
import hashlib
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path

from overseer import hostos
from overseer import orchestrate
from overseer import target as target_module
from overseer.factory import Factory

MODES = ('new', 'continue')
RUNNER_PROGRAMS = {'claude': 'claude', 'codex': 'codex', 'opencode': 'opencode'}
CHECK_FILE = 'overseer_check.py'
DEFAULT_STEPS = 12

_REPORT = (
    'End every answer with these four lines, exactly:\n'
    'STATUS: SUCCESS or STUCK_NEEDS_ESCALATION\n'
    'TESTS_PASSED: TRUE or FALSE\n'
    'FILES_MODIFIED: [the files you changed]\n'
    'NEXT_AGENT_INSTRUCTION: "the next concrete step, as one JSON string under 1500 characters; '
    'empty when nothing is left"\n'
    'Then one line: OVERSEER_STEP_DONE when more remains, OVERSEER_DONE when the whole objective '
    'works and python overseer_check.py passes, or OVERSEER_NEEDS_INPUT if you cannot go on '
    'without the user.')

_RULES = (
    'You are one step of an automated build; the next step is a new session that knows only '
    'what is in this folder. Keep SESSION_HANDOFF.md current: the objective, what works, what '
    'is left, how to run it. Keep overseer_check.py at the folder root: a Python script that '
    'runs the real tests or the program itself and exits 0 only when it works; never make it '
    'pass by skipping work. Do one bounded step, run the check yourself, then report.')


class BuildError(ValueError):
    """A request that cannot be started, with a message for the person."""


def app_dir(env=None):
    env = os.environ if env is None else env
    base = env.get('LOCALAPPDATA') or env.get('XDG_STATE_HOME') or str(Path.home() / '.local' / 'state')
    return Path(base) / 'Overseer'


def ledger_for(folder, env=None):
    """The ledger of one project folder: stable for the folder, apart from it."""
    folder = Path(folder).resolve()
    slug = re.sub(r'[^A-Za-z0-9_-]+', '-', folder.name).strip('-')[:40] or 'project'
    digest = hashlib.sha256(str(folder).lower().encode()).hexdigest()[:10]
    return app_dir(env) / 'projects' / ('%s-%s' % (slug, digest)) / 'jobs.sqlite3'


def find_python(which=shutil.which):
    """The command that runs overseer_check.py, or None.

    The Windows launcher comes first: a bare ``python`` on Windows is often the
    Store alias, which opens the Store instead of running the script.
    """
    launcher = which('py')
    if launcher:
        return [launcher, '-3']
    for name in ('python3', 'python'):
        found = which(name)
        if found and 'WindowsApps' not in found:
            return [found]
    return None


def available_runners(which=shutil.which):
    """Which coding agents are installed, by runner name."""
    return {name: bool(which(program)) for name, program in RUNNER_PROGRAMS.items()}


def _objective(mode, request):
    request = ' '.join((request or '').split())
    if mode == 'new':
        return 'Build this program so that it works: ' + request
    focus = (' Focus on: ' + request) if request else ''
    return ('Continue the unfinished work in this repository and bring it to a working, '
            'verified state.' + focus)


def _preamble(mode, objective):
    if mode == 'new':
        where = 'The full request is in SPEC.md; build exactly that, simply, and make it run.'
    else:
        where = ('Find what is unfinished from SESSION_HANDOFF.md, README, TODO or ROADMAP files, '
                 'failing tests and recent git history; do not redo finished work or invent '
                 'features. If overseer_check.py is missing, write it around the existing tests.')
    return '\n'.join(['[Overseer build] Objective: ' + objective[:400], where, _RULES, _REPORT])


def prepare(mode, request, folder, runner='claude', model=None, allow_commands=True,
            steps=DEFAULT_STEPS, env=None, which=shutil.which, now=time.time):
    """Check the request and set up the folder; return the job: ledger, loop spec, target."""
    if mode not in MODES:
        raise BuildError('unknown mode %r' % mode)
    if runner not in RUNNER_PROGRAMS:
        raise BuildError('unknown agent %r' % runner)
    if not which(RUNNER_PROGRAMS[runner]):
        raise BuildError('%s is not installed or not on PATH' % RUNNER_PROGRAMS[runner])
    python = find_python(which)
    if python is None:
        raise BuildError('Python 3 is needed to run overseer_check.py; install it from python.org')
    if not str(folder or '').strip():
        raise BuildError('choose a project folder')
    folder = Path(folder).expanduser().resolve()
    request = (request or '').strip()
    if mode == 'new':
        if not request:
            raise BuildError('describe the program you want')
        spec = ledger_for(folder, env).parent / 'SPEC.md'
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text('# What to build\n\n' + request + '\n', encoding='utf-8')
        try:
            target_module.init(str(folder), spec=str(spec), allow_nested=True)
        except target_module.TargetError as error:
            raise BuildError(str(error)) from error
    elif not folder.is_dir():
        raise BuildError('the folder does not exist: %s' % folder)
    objective = _objective(mode, request)
    loop_spec = {
        'objective': objective,
        'preamble': _preamble(mode, objective),
        'id_prefix': 'build-%d' % int(now()),
        'runner': runner,
        'checks': [python + [CHECK_FILE]],
        'size': True,
        'daily_cap': max(1, int(steps)),
        'timeout_seconds': 1800,
        'permission_mode': 'bypassPermissions' if allow_commands else 'acceptEdits',
    }
    if model:
        loop_spec['model'] = model
    ledger = ledger_for(folder, env)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    (ledger.parent / 'build.json').write_text(json.dumps(
        {'mode': mode, 'request': request, 'folder': str(folder), 'loop_spec': loop_spec,
         'started': now()}, indent=2), encoding='utf-8')
    return {'ledger': str(ledger), 'loop_spec': loop_spec, 'target': str(folder)}


def run(job, steer=None):
    """Run the prepared job to a stop condition; returns the loop's result.

    A Stop pauses the project's ledger; pressing Build again is the person
    asking for dispatch back, so a paused ledger is unpaused first.
    """
    factory = Factory(job['ledger'])
    try:
        if orchestrate._paused(factory.db):
            factory.unpause('a new build was started')
    finally:
        factory.close()
    return orchestrate.run_loop(job['ledger'], job['loop_spec'], job['target'], steer=steer)


def stop(job, kill=hostos.kill_group):
    """Stop a running build: pause dispatch, and end the worker now if one is running."""
    factory = Factory(job['ledger'])
    try:
        rows = factory.db.execute("SELECT child_group FROM jobs WHERE state IN ('running','checking')"
                                  ' AND child_group IS NOT NULL').fetchall()
        for row in rows:
            try:
                kill(row['child_group'])
            except (ProcessLookupError, OSError):
                pass
        factory.pause('stopped from the Overseer window')
    finally:
        factory.close()


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='Build a program from one request, or finish a repo.')
    parser.add_argument('mode', choices=MODES)
    parser.add_argument('folder')
    parser.add_argument('request', nargs='?', default='')
    parser.add_argument('--agent', default='claude', choices=sorted(RUNNER_PROGRAMS))
    parser.add_argument('--model')
    parser.add_argument('--steps', type=int, default=DEFAULT_STEPS)
    parser.add_argument('--no-commands', action='store_true',
                        help='let the agent edit files but not run commands')
    args = parser.parse_args(argv)
    try:
        job = prepare(args.mode, args.request, args.folder, args.agent, args.model,
                      not args.no_commands, args.steps)
    except BuildError as error:
        print('overseer build: %s' % error, file=sys.stderr)
        return 2
    result = run(job)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get('state') == 'done' else 2


if __name__ == '__main__':
    raise SystemExit(main())
