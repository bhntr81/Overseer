"""Explicit, single-worker local jobs. Trusted commands only; not a sandbox."""
import argparse
from contextlib import contextmanager
import fcntl
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


def validate(spec):
    if not isinstance(spec, dict) or set(spec) - {'id', 'objective', 'workspace', 'implementation', 'checks', 'timeout_seconds'}:
        raise ValueError('unknown task fields or invalid task object')
    if not isinstance(spec.get('id'), str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.-]{0,79}', spec['id']):
        raise ValueError('id must be a short filesystem-safe identifier')
    if not isinstance(spec.get('objective'), str) or not spec['objective'].strip():
        raise ValueError('objective is required')
    if not isinstance(spec.get('workspace'), str) or not Path(spec['workspace']).is_absolute() or not Path(spec['workspace']).is_dir():
        raise ValueError('workspace must be an existing absolute directory')
    if type(spec.get('timeout_seconds')) is not int or not 1 <= spec['timeout_seconds'] <= 3600:
        raise ValueError('timeout_seconds must be 1..3600 per command')
    if not isinstance(spec.get('checks'), list) or not spec['checks'] or len(spec['checks']) > 20:
        raise ValueError('one to twenty acceptance commands required')
    for argv in [spec.get('implementation'), *spec['checks']]:
        if not isinstance(argv, list) or not argv or not all(isinstance(v, str) and v and '\0' not in v for v in argv):
            raise ValueError('commands must be nonempty argument arrays; no implicit shell')
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
        ''')

    def close(self):
        self.db.close()

    def event(self, job_id, state, detail):
        self.db.execute('INSERT INTO events(job_id,at,state,detail) VALUES(?,?,?,?)',
                        (job_id, time.time(), state, detail))

    def submit(self, spec):
        validate(spec)
        data = canonical(spec)
        digest = hashlib.sha256(data.encode()).hexdigest()
        with self.db:
            old = self.db.execute('SELECT spec_hash FROM jobs WHERE id=?', (spec['id'],)).fetchone()
            if old:
                if old['spec_hash'] != digest:
                    raise ValueError('task ID already exists with a different immutable specification')
                return False
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
        result['events'] = [dict(r) for r in self.db.execute('SELECT * FROM events WHERE job_id=? ORDER BY seq', (job_id,))]
        return result

    @contextmanager
    def worker_lock(self):
        with self.path.with_suffix('.lock').open('a') as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError('another factory worker owns this database') from None
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def transition(self, job_id, state, detail):
        with self.db:
            self.db.execute('UPDATE jobs SET state=?,detail=? WHERE id=?', (state, detail, job_id))
            self.event(job_id, state, detail)

    def reconcile(self):
        with self.worker_lock():
            rows = self.db.execute("SELECT id FROM jobs WHERE state IN ('running','checking')").fetchall()
            for row in rows:
                self.transition(row['id'], 'needs_reconciliation', 'worker exited without final evidence; inspect workspace and child processes')
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

    def cancel(self, job_id):
        with self.db:
            cur = self.db.execute("UPDATE jobs SET state='cancelled' WHERE id=? AND state='queued'", (job_id,))
            if cur.rowcount != 1:
                raise ValueError('only a queued job can be cancelled here')
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

    def run_one(self):
        with self.worker_lock():
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute("SELECT 1 FROM jobs WHERE state IN ('running','checking','needs_reconciliation')").fetchone():
                self.db.rollback()
                raise RuntimeError('unresolved prior run; reconcile/inspect it before dispatch')
            row = self.db.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY seq LIMIT 1").fetchone()
            if row is None:
                self.db.commit()
                return None
            job_id = row['id']
            spec = json.loads(row['spec'])
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
            try:
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
            (evidence/'summary.json').write_text(json.dumps({'id': job_id, 'run_id': run_id, 'state': final,
                'detail': detail, 'spec_hash': row['spec_hash'], 'results': results,
                'tokens': None, 'cost_usd': None}, indent=2))
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
        else:
            result = [dict(r) for r in factory.db.execute('SELECT id,state,run_id,detail,evidence FROM jobs ORDER BY seq')]
        print(json.dumps(result, indent=2))
        return 1 if args.action == 'run-one' and result and result['state'] != 'passed' else 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as error:
        print(json.dumps({'error': str(error)}))
        return 1
    finally:
        factory.close()


if __name__ == '__main__':
    raise SystemExit(main())
