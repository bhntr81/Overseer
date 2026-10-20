"""Durable FIFO for automatic sends; never interrupts existing terminal work."""
import logging
import re

from .policy import (
    ANSI, BLOCKED, COMPLETED, CONTINUE, DEFAULT_REPLY, STOP, classify, fingerprint, hold, next_prompt,
)

LOG = logging.getLogger('overseer')
ACTIVE = re.compile(r'^\s*[•·].*\b(?:esc to (?:interrupt|cancel)|ctrl.c to (?:interrupt|cancel))\b', re.I | re.M)
CAPACITY = re.compile(r'^\s*■ Selected model is at capacity\. Please try a different model\.\s*$', re.M)


def response(text):
    """Exclude preceding turns, but retain the current answer above its composer."""
    lines = ANSI.sub('', text).splitlines()
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith(('› ', '❯ ', '> ')) and line not in {'› Ask Codex to do anything'}:
            return '\n'.join(lines[i + 1:])
    return '\n'.join(lines)


def phase(snapshot):
    text = response(snapshot.text)
    if ACTIVE.search(text):
        return 'active'
    if not snapshot.ready:
        return 'unknown'
    if STOP.search(text):
        return 'stopped'
    # A quoted or historical error must not enable retries.
    match = CAPACITY.search(text)
    if match and not COMPLETED.search(text[match.end():]) and not BLOCKED.search(text[match.end():]):
        return 'capacity'
    if COMPLETED.search(text):
        return 'finished'
    if classify(text)[0]:
        return 'finished'
    return 'unknown'


def outcome(snapshot):
    """Fingerprint the answer through its outcome, excluding mutable UI tips."""
    text = response(snapshot.text)
    matches = [m for pattern in (CAPACITY, COMPLETED, STOP, CONTINUE)
               for m in pattern.finditer(text)]
    return fingerprint(text[:max(m.end() for m in matches)]) if matches else None


def _missing_process(error):
    """A reptyr target left /proc. Other observation errors stay fatal to the poll."""
    if isinstance(error, (FileNotFoundError, ProcessLookupError)):
        return True
    filename = getattr(error, 'filename', None) or ''
    return isinstance(error, OSError) and str(filename).startswith('/proc/')


def _mark_stale(state, pane):
    prefix = f'{pane}:'
    for key, entry in state.items():
        if key.startswith(prefix) and isinstance(entry, dict):
            entry['queue_reason'] = 'dead or stale process'


def tick_queue(backend, policy, state, config, path, now, save):
    fallback = config.get('reply', DEFAULT_REPLY)
    queue = state.setdefault('_queue', {'waiting': [], 'active': None})
    waiting = queue.setdefault('waiting', [])
    snapshots = {}
    stale = set()
    failed = False
    for pane in backend.panes():
        try:
            s = backend.snapshot(pane)
            snapshots[f'{pane}:{s.pid}'] = s
        except (RuntimeError, OSError, ValueError) as error:
            if _missing_process(error):
                stale.add(pane)
                _mark_stale(state, pane)
                LOG.warning('%s queue observation skipped: dead or stale process: %s', pane, error)
                continue
            LOG.warning('%s queue observation failed: %s', pane, error)
            failed = True
    # Unobserved panes cannot be assumed gone if any observation failed.
    if failed:
        save(path, state)
        return
    phases = {key: phase(s) for key, s in snapshots.items()}
    active = queue.get('active')
    if active:
        key = active['key']
        s = snapshots.get(key)
        if s is not None and phases[key] == 'active':
            active['observed_running'] = True
        if s is None:
            LOG.info('queue releases vanished, replaced, or excluded client %s', key)
            queue['active'] = None
        elif phases[key] in {'finished', 'stopped', 'capacity'} and (
                active.get('observed_running') or outcome(s) != active.get('outcome')):
            LOG.info('queue releases %s: %s', s.pane, phases[key])
            queue['active'] = None
        else:
            if phases[key] != 'active' and now - active['at'] >= 120 and not active.get('warned'):
                LOG.warning('queue holds %s: delivery or completion remains unconfirmed; inspect this pane', s.pane)
                active['warned'] = True
    decisions = {}
    candidates = set()
    for key, s in snapshots.items():
        entry = state.setdefault(key, {})
        capacity = phases[key] == 'capacity'
        entry['queue_kind'] = 'capacity' if capacity else 'continuation'
        if phases[key] == 'stopped':
            entry['queue_reason'] = 'client requested no further automatic continuation'
            continue
        if not s.ready or phases[key] == 'active':
            entry.pop('fingerprint', None)
            continue
        if phases[key] == 'finished':
            entry.pop('capacity_attempts', None)
        if capacity and entry.get('capacity_attempts', 0) >= config.get('capacity_max_retries', 3):
            entry['queue_reason'] = 'capacity retry limit reached; manual intervention needed'
            continue
        eligible, reason = policy.consider(entry, s.text, now, capacity=capacity,
                                           retry_seconds=config.get('capacity_retry_seconds', 120))
        if eligible and not capacity:
            prompt, kind = next_prompt(s.text, fallback)
            if prompt is None:
                eligible = False
                reason = kind
                hold(entry, s.text, kind)
                LOG.info('%s skipped: %s', s.pane, kind)
        entry['queue_reason'] = reason
        decisions[key] = eligible
        # Capacity failures take a place immediately and wait their backoff at
        # the head; exhausted daily budgets must not starve unrelated projects.
        candidate = eligible or (capacity and reason in {'waiting for idle threshold', 'cooldown'})
        if candidate and (not queue.get('active') or queue['active']['key'] != key):
            candidates.add(key)
    waiting[:] = [key for key in waiting if key in candidates]
    for key in snapshots:
        if key in candidates and key not in waiting:
            waiting.append(key)
            LOG.info('queue enqueued %s at position %s', snapshots[key].pane, len(waiting))
    save(path, state)
    if queue.get('active') or any(p == 'active' for p in phases.values()) or not waiting:
        return
    key = waiting[0]
    if not decisions.get(key):
        return
    s = snapshots[key]
    entry = state[key]
    if config['dry_run']:
        if entry.get('previewed') != entry['fingerprint']:
            _, kind = ('', 'routine continuation') if phases[key] == 'capacity' else next_prompt(s.text, fallback)
            if kind == 'report-based prompt':
                LOG.info('%s would send report-based prompt in FIFO queue (dry run)', s.pane)
            else:
                LOG.info('%s would run next in FIFO queue (dry run)', s.pane)
            entry['previewed'] = entry['fingerprint']
            save(path, state)
        return
    # Recheck ALL watched panes before reserving; another pane may have started
    # while the queue was being observed. send() separately rechecks the target.
    if set(backend.panes()) - stale != {s.pane for s in snapshots.values()}:
        return
    for old in snapshots.values():
        try:
            if backend.snapshot(old.pane) != old:
                return
        except (RuntimeError, OSError, ValueError):
            return
    outgoing, kind = (fallback, 'routine continuation') if phases[key] == 'capacity' else next_prompt(s.text, fallback)
    if outgoing is None:
        waiting.pop(0)
        hold(entry, s.text, kind)
        entry['queue_reason'] = kind
        LOG.info('%s skipped: %s', s.pane, kind)
        save(path, state)
        return
    waiting.pop(0)
    queue['active'] = {'key': key, 'pane': s.pane, 'fingerprint': fingerprint(s.text),
                       'outcome': outcome(s), 'at': now}
    policy.acknowledge(entry, s.text, now)
    if phases[key] == 'capacity':
        entry['capacity_attempts'] = entry.get('capacity_attempts', 0) + 1
    save(path, state)
    try:
        backend.send(s, outgoing)
        if kind == 'report-based prompt':
            LOG.info('%s sent report-based prompt', s.pane)
        else:
            LOG.info('%s dispatched from FIFO queue', s.pane)
    except (RuntimeError, OSError, ValueError) as error:
        # Retain the slot: an ambiguous send cannot safely be retried or overlapped.
        LOG.warning('%s queue delivery uncertain; reservation retained: %s', s.pane, error)
