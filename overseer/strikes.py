"""Repair lineage and the consecutive-failure freeze for the factory ledger.

This module is self-contained ledger logic over a passed-in sqlite3 connection.
It computes the freeze bound, counts consecutive strikes, decides the freeze,
and records the lineage. It never imports ``overseer.factory`` or
``subprocess``, runs no command, and reads no file outside the database. Every
read and write happens on the connection the caller gives it, inside the
caller's transaction, so a strike is recorded in the same transaction as the
job's final transition.

A lineage is a chain of attempts at one objective: a root attempt and the
repairs submitted against it with ``repair_of``. A terminal ``failed`` state is
a strike; ``passed`` closes the lineage; an operator act (``cancelled`` or a
refused approval) is neither a strike nor a reset. When the consecutive strikes
of a lineage reach its bound, the lineage is frozen and no further repair may be
submitted against it until an operator releases it with a named note.

Only command-mode jobs carry a lineage. The internal probe modes (``fixture``,
``fake_provider``, ``isolation_probe``) are never tracked.
"""
import json
import time

# The blueprint's policy: one implementation attempt plus at most two repairs
# (docs/SOFTWARE_FACTORY_BLUEPRINT_V2.txt:352). A contract may lower it.
BLUEPRINT_BOUND = 3
LINEAGE_STATES = ('open', 'frozen', 'released', 'closed')
PROBE_MODES = ('fixture', 'fake_provider', 'isolation_probe')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS repairs (
    job_id TEXT PRIMARY KEY NOT NULL,
    parent_id TEXT,
    lineage_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lineages (
    lineage_id TEXT PRIMARY KEY NOT NULL,
    root_job TEXT NOT NULL,
    state TEXT NOT NULL,
    strikes INTEGER NOT NULL,
    bound INTEGER NOT NULL,
    bound_source TEXT NOT NULL,
    detail TEXT NOT NULL,
    updated REAL NOT NULL);
'''


def ensure_tables(db):
    """Create the lineage tables if they are absent. Safe to call repeatedly."""
    db.executescript(SCHEMA)


def bound_for(allowance):
    """Return (bound, source) for a contract repair allowance.

    The bound is one attempt plus the allowed repairs, capped at the blueprint's
    three. ``source`` names which limit applied, so a lowered bound is honest
    about coming from the contract rather than the blueprint.
    """
    repairs = allowance if isinstance(allowance, int) and allowance >= 0 else 0
    contract_bound = 1 + repairs
    if contract_bound < BLUEPRINT_BOUND:
        return contract_bound, 'contract_allowance'
    return BLUEPRINT_BOUND, 'blueprint'


def is_strike(final_state):
    """A terminal ``failed`` state is the only strike."""
    return final_state == 'failed'


def _allowance(spec):
    """Read the contract's repair allowance from a spec, defaulting to zero."""
    try:
        value = spec['contract']['budget']['repair_allowance']
    except (KeyError, TypeError):
        return 0
    return value if isinstance(value, int) and value >= 0 else 0


def _event(db, job_id, state, detail):
    db.execute('INSERT INTO events(job_id,at,state,detail) VALUES(?,?,?,?)',
               (job_id, time.time(), state, detail))


def _lineage_id_for_job(db, job_id):
    row = db.execute('SELECT lineage_id FROM repairs WHERE job_id=?', (job_id,)).fetchone()
    return row[0] if row else None


def lineage(db, lineage_id):
    """Return the lineage row as a dict, or None when it does not exist."""
    row = db.execute('SELECT * FROM lineages WHERE lineage_id=?', (lineage_id,)).fetchone()
    return dict(row) if row else None


def _create_root(db, job_id, allowance):
    """Open a new lineage rooted at ``job_id`` and return its id."""
    bound, source = bound_for(allowance)
    db.execute(
        'INSERT INTO lineages(lineage_id,root_job,state,strikes,bound,bound_source,detail,updated)'
        ' VALUES(?,?,?,?,?,?,?,?)',
        (job_id, job_id, 'open', 0, bound, source, 'lineage opened', time.time()))
    db.execute('INSERT INTO repairs(job_id,parent_id,lineage_id) VALUES(?,?,?)',
               (job_id, None, job_id))
    return job_id


def join_lineage(db, job_id, parent_id):
    """Attach ``job_id`` to the lineage of ``parent_id`` as a repair.

    Lazily roots the parent's lineage if it has none yet. Raises ``ValueError``
    when the parent job is unknown or when the lineage is frozen, naming the
    lineage, its strikes, and its bound so the refusal is legible.
    """
    parent = db.execute('SELECT spec FROM jobs WHERE id=?', (parent_id,)).fetchone()
    if parent is None:
        raise ValueError('unknown parent job for a repair: ' + str(parent_id))
    lineage_id = _lineage_id_for_job(db, parent_id)
    if lineage_id is None:
        lineage_id = _create_root(db, parent_id, _allowance(json.loads(parent[0])))
    row = lineage(db, lineage_id)
    if row['state'] == 'frozen':
        raise ValueError(
            'lineage %s is frozen after %d consecutive failures (bound %d); '
            'release it before submitting another repair'
            % (lineage_id, row['strikes'], row['bound']))
    db.execute('INSERT INTO repairs(job_id,parent_id,lineage_id) VALUES(?,?,?)',
               (job_id, parent_id, lineage_id))
    return lineage_id


def record_terminal(db, job_id, final_state, spec):
    """Record a command-mode job's terminal state against its lineage.

    A ``passed`` state closes an existing lineage; a ``failed`` state is a
    strike that opens a lineage if the job had none and freezes it on reaching
    the bound. Any other state, and every probe-mode job, is left untouched.
    The caller runs this inside the transaction that records the final
    transition, and before that transition's own event, so the terminal state
    stays the lineage's last event.
    """
    if (spec or {}).get('mode') in PROBE_MODES:
        return
    lineage_id = _lineage_id_for_job(db, job_id)
    if final_state == 'passed':
        if lineage_id is not None:
            db.execute('UPDATE lineages SET state=?,detail=?,updated=? WHERE lineage_id=?',
                       ('closed', 'a passed attempt closed the lineage', time.time(), lineage_id))
            _event(db, job_id, 'closed', 'passed attempt closed lineage ' + lineage_id)
        return
    if not is_strike(final_state):
        return
    if lineage_id is None:
        lineage_id = _create_root(db, job_id, _allowance(spec))
    row = lineage(db, lineage_id)
    if row['state'] == 'closed':
        return
    strikes = row['strikes'] + 1
    db.execute('UPDATE lineages SET strikes=?,updated=? WHERE lineage_id=?',
               (strikes, time.time(), lineage_id))
    _event(db, job_id, 'strike',
           'strike %d of %d on lineage %s' % (strikes, row['bound'], lineage_id))
    if row['state'] in ('open', 'released') and strikes >= row['bound']:
        detail = ('lineage %s frozen after %d consecutive failures; bound %d (%s)'
                  % (lineage_id, strikes, row['bound'], row['bound_source']))
        db.execute('UPDATE lineages SET state=?,detail=?,updated=? WHERE lineage_id=?',
                   ('frozen', detail, time.time(), lineage_id))
        _event(db, job_id, 'frozen', detail)


def release(db, lineage_id, decider, note):
    """Reopen a frozen lineage with a named, recorded note.

    The decider is recorded, not authorized, exactly as the approval decider is.
    Release resets the consecutive-strike count and grants a fresh bound of
    attempts. Raises ``ValueError`` on a missing decider or note, an unknown
    lineage, or a lineage that is not frozen.
    """
    if not isinstance(decider, str) or not decider.strip():
        raise ValueError('a named decider is required to release a lineage')
    if not isinstance(note, str) or not note.strip():
        raise ValueError('a release note is required')
    row = lineage(db, lineage_id)
    if row is None:
        raise ValueError('unknown lineage: ' + str(lineage_id))
    if row['state'] != 'frozen':
        raise ValueError('only a frozen lineage can be released; this one is ' + row['state'])
    detail = 'released by %s; note: %s' % (decider.strip(), note.strip())
    db.execute('UPDATE lineages SET state=?,strikes=?,detail=?,updated=? WHERE lineage_id=?',
               ('released', 0, detail, time.time(), lineage_id))
    _event(db, row['root_job'], 'released', detail)
    return lineage(db, lineage_id)
