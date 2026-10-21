"""The unattended factory feed loop.

`python3 -m overseer.orchestrate --db DB --loop LOOP.json --target DIR [--once]
[--dry-run]` drives the factory without a human in the seat. Each iteration
builds a command-mode job from the loop spec with `overseer.provider.build_task`,
submits it (as a repair of the previous job after a failure), runs it, reads the
worker report, and feeds that report's `NEXT_AGENT_INSTRUCTION` into the next
iteration.

The first instruction is the loop spec's objective; every later instruction
comes only from a valid status block, and a missing or invalid block stops the
loop with `needs_input` — no instruction is ever invented. Before each
submission the loop stops, in order, when dispatch is paused, the lineage is
frozen, the last job awaits approval (the loop never decides), the worker asked
for input, the daily cap is reached, or the objective is done. The daily cap is
counted from ledger events, so it holds across a restart, and an flock beside
the database allows one loop per ledger.

For unattended safety the loop drives the free OpenCode gateway by default and
never silently inherits a paid session: the runner defaults to ``opencode``
unless the loop spec names one.
"""
import argparse
import fcntl
import json
import os
import time
from pathlib import Path

from overseer import route
from overseer.factory import Factory
from overseer.provider import build_task
from overseer.tmux import CLIENTS

DAILY_CAP = 12
NEEDS_INPUT = 'OVERSEER_NEEDS_INPUT'
DONE = 'OVERSEER_DONE'
# States that mean a human must look; the loop prints OVERSEER_NEEDS_INPUT and
# exits 2 for all of them, and OVERSEER_DONE / exit 0 only for 'done'.
HOLD_STATES = ('needs_input', 'frozen', 'paused', 'cap')


def _paused(db):
    row = db.execute('SELECT paused FROM dispatch_pause WHERE id=1').fetchone()
    return bool(row and row['paused'])


def _daily_count(db, now):
    row = db.execute('SELECT COUNT(*) FROM events WHERE state=? AND at>=?',
                     ('running', now - 86400)).fetchone()
    return row[0]


def _tail(path, limit=64 * 1024):
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as handle:
            if size > limit:
                handle.seek(size - limit)
            return handle.read(limit).decode('utf-8', 'replace')
    except OSError:
        return ''


def _report_block(evidence):
    try:
        return json.loads((Path(evidence) / 'worker_report.json').read_text()).get('block')
    except (OSError, ValueError):
        return None


def _result(state, iterations, last_job, detail):
    return {'state': state, 'iterations': iterations, 'last_job': last_job, 'detail': detail}


def run_loop(db_path, loop_spec, target, once=False, dry_run=False, env=None,
             opencode='opencode', now=None, router=None):
    """Drive the factory from the loop spec until a stop condition. Returns a result."""
    now = time.time if now is None else now
    router = route.start_session if router is None else router
    escalate_to = loop_spec.get('escalate_to') or 'none'
    cap = loop_spec.get('daily_cap', DAILY_CAP)
    # Default to the runner of the session that launched Overseer; the provider
    # inherits it when this is None, and falls back to free OpenCode only when no
    # session is detected.
    runner = loop_spec.get('runner')
    checks = loop_spec.get('checks') or []
    prefix = loop_spec['id_prefix']
    lock_path = Path(db_path).with_name(Path(db_path).name + '.loop.lock')
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with lock_path.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return _result('error', 0, None, 'another loop owns this ledger')
        factory = Factory(db_path)
        try:
            return _drive(factory, loop_spec, target, prefix, checks, runner, cap,
                          once, dry_run, env, opencode, now, escalate_to, router)
        finally:
            factory.close()


def _escalation_prompt(factory, lineage_root, lineage):
    """Build the escalation prompt from ledger facts only; never raw log text."""
    rows = factory.db.execute(
        'SELECT j.id, j.run_id, j.evidence FROM jobs j JOIN repairs r ON j.id=r.job_id'
        ' WHERE r.lineage_id=? ORDER BY j.seq', (lineage_root,)).fetchall()
    attempts = '; '.join('%s run=%s' % (row['id'], row['run_id'] or '?') for row in rows)
    evidence = '; '.join(row['evidence'] for row in rows if row['evidence'])
    failing = []
    if rows and rows[-1]['evidence']:
        try:
            record = json.loads((Path(rows[-1]['evidence']) / 'handoff.json').read_text())
            failing = (record.get('failing_acceptance_ids') or {}).get('value') or []
        except (OSError, ValueError):
            failing = []
    return ('Overseer escalation. Lineage %s froze: %s. Attempts: %s. '
            'Failing acceptance identifiers: %s. Evidence directories: %s. '
            'Investigate the root cause from the evidence; do not blindly retry.'
            % (lineage_root, lineage['detail'], attempts,
               ', '.join(failing) or 'none', evidence))


def _escalate(factory, lineage_root, lineage, escalate_to, target, dry_run, router, cap, now):
    """Route one escalation session for a frozen lineage. Only a freeze routes.

    At most once per lineage: a recorded escalation_routed event blocks a second
    route. Honours dry-run and the daily cap. No model may answer a human
    decision, so a pause or an approval wait never reaches here.
    """
    if escalate_to == 'none' or escalate_to not in CLIENTS or dry_run:
        return
    if factory.db.execute("SELECT 1 FROM events WHERE job_id=? AND state='escalation_routed'",
                          (lineage_root,)).fetchone():
        return
    if _daily_count(factory.db, now()) >= cap:
        return
    prompt = _escalation_prompt(factory, lineage_root, lineage)
    pane = router('overseer-escalate-%s' % lineage_root, escalate_to, target, prompt)
    with factory.db:
        factory.event(lineage_root, 'escalation_routed',
                      'routed a frozen lineage to %s; pane %s' % (escalate_to, pane))


def _drive(factory, loop_spec, target, prefix, checks, runner, cap,
           once, dry_run, env, opencode, now, escalate_to, router):
    instruction = loop_spec['objective']
    last_job = None
    last_failed = False
    lineage_root = None
    pending_needs_input = False
    done = False
    iteration = 0
    while True:
        if _paused(factory.db):
            return _result('paused', iteration, last_job, 'factory dispatch is paused')
        if lineage_root is not None:
            lineage = factory.lineage(lineage_root)
            if lineage and lineage['state'] == 'frozen':
                _escalate(factory, lineage_root, lineage, escalate_to, target,
                          dry_run, router, cap, now)
                return _result('frozen', iteration, last_job, lineage['detail'])
        if last_job is not None and factory.inspect(last_job)['state'] == 'awaiting_approval':
            return _result('needs_input', iteration, last_job,
                           'the last job awaits a decision; the loop never decides')
        if pending_needs_input:
            return _result('needs_input', iteration, last_job,
                           'the worker asked for input or left no usable instruction')
        if _daily_count(factory.db, now()) >= cap:
            return _result('cap', iteration, last_job, 'the daily iteration cap was reached')
        if done:
            return _result('done', iteration, last_job, 'the objective reported done')
        if instruction is None:
            return _result('needs_input', iteration, last_job, 'no instruction to feed')

        task_id = '%s-%d' % (prefix, iteration)
        spec, resolved = build_task(
            task_id, loop_spec['objective'], target, checks, instruction,
            model=loop_spec.get('model'), runner=runner, env=env,
            timeout_seconds=loop_spec.get('timeout_seconds', 600),
            opencode=opencode, repair_allowance=loop_spec.get('repair_allowance', 1))
        if loop_spec.get('envelope'):
            spec['envelope'] = loop_spec['envelope']
        if dry_run:
            result = _result('dry_run', iteration, None,
                             'dry run: the next job was built but not submitted')
            result['runner'] = resolved['runner']
            return result

        factory.submit(spec, repair_of=(last_job if last_failed else None))
        result = factory.run_one()
        iteration += 1
        last_job = task_id

        if factory.inspect(task_id)['state'] == 'awaiting_approval':
            return _result('needs_input', iteration, last_job,
                           'the job awaits a decision; the loop never decides')
        passed = bool(result) and result.get('state') == 'passed'
        evidence = result.get('evidence') if result else None
        block = _report_block(evidence) if evidence else None
        tail = _tail(Path(evidence) / '00.log') if evidence else ''

        if not passed:
            last_failed = True
            if lineage_root is None:
                lineage_root = task_id
        else:
            last_failed = False
            lineage_root = None

        if NEEDS_INPUT in tail:
            pending_needs_input = True
        elif block and block.get('valid'):
            if passed and block.get('status') == 'SUCCESS' and DONE in tail \
                    and not block.get('next_instruction'):
                done = True
            elif block.get('next_instruction'):
                instruction = block['next_instruction']
            else:
                pending_needs_input = True
        else:
            pending_needs_input = True

        if once:
            if done:
                return _result('done', iteration, last_job, 'done on the single iteration')
            if pending_needs_input:
                return _result('needs_input', iteration, last_job, 'needs input after one iteration')
            return _result('once', iteration, last_job, 'one iteration complete')


def main(argv=None):
    parser = argparse.ArgumentParser(description='Drive the factory unattended.')
    parser.add_argument('--db', required=True)
    parser.add_argument('--loop', required=True)
    parser.add_argument('--target', required=True)
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true')
    args = parser.parse_args(argv)
    loop_spec = json.loads(Path(args.loop).read_text())
    result = run_loop(args.db, loop_spec, args.target, once=args.once, dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    if result['state'] == 'done':
        print(DONE)
        return 0
    if result['state'] == 'error':
        return 1
    if result['state'] in ('dry_run', 'once'):
        return 0
    print(NEEDS_INPUT)
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
