"""Durable FIFO for automatic sends; never interrupts existing terminal work."""
import json
import logging
import re
import time

from .halt import clear, note
from .modelchoice import (
    RESOLUTIONS, detect, fallback_policy, next_hop, opencode_answer, opencode_empty,
    providers, running_marker,
)
from . import stopgate
from .policy import (
    ANSI, BLOCKED, COMPLETED, CONTINUE, DEFAULT_REPLY, STEP_DONE_MARK, STOP, classify,
    current_turn, fingerprint, hold, next_prompt, stop_requested,
)
from .route import resolve_route
from .tmux import CLIENTS

LOG = logging.getLogger('overseer')
ACTIVE = re.compile(r'^\s*[•·].*\b(?:esc to (?:interrupt|cancel)|ctrl.c to (?:interrupt|cancel))\b', re.I | re.M)
CAPACITY = re.compile(r'^\s*■ Selected model is at capacity\. Please try a different model\.\s*$', re.M)


def response(text):
    """Exclude preceding turns, but retain the current answer above its composer."""
    return current_turn(text)


def current_answer(snapshot):
    """Return the answer of the current turn."""
    text = response(snapshot.text)
    if snapshot.process == 'opencode':
        return opencode_answer(text)
    return text


def model_failure(snapshot):
    """Return the provider failure visible in the current answer, or None."""
    text = current_answer(snapshot)
    failure = detect(text)
    if failure is None:
        return None
    # A quoted or historical error must not pause a pane that has moved on.
    if COMPLETED.search(text[failure.end:]) or BLOCKED.search(text[failure.end:]):
        return None
    return failure


def phase(snapshot):
    text = current_answer(snapshot)
    if ACTIVE.search(text) or running_marker(text):
        return 'active'
    if not snapshot.ready:
        return 'unknown'
    if stop_requested(text, tail_only=False):
        return 'stopped'
    if model_failure(snapshot):
        return 'model_blocked'
    # A quoted or historical error must not enable retries.
    match = CAPACITY.search(text)
    if match and not COMPLETED.search(text[match.end():]) and not BLOCKED.search(text[match.end():]):
        return 'capacity'
    if COMPLETED.search(text):
        return 'finished'
    if snapshot.process == 'opencode' and opencode_empty(snapshot.cursor_line):
        # The turn ended and the composer went back to its idle placeholder.
        return 'finished'
    if classify(text)[0]:
        return 'finished'
    return 'unknown'


def outcome(snapshot):
    """Fingerprint the answer through its outcome, excluding mutable UI tips."""
    text = response(snapshot.text)
    matches = [m for pattern in (CAPACITY, COMPLETED, STOP, STEP_DONE_MARK, CONTINUE)
               for m in pattern.finditer(text)]
    return fingerprint(text[:max(m.end() for m in matches)]) if matches else None


def _missing_process(error):
    """A reptyr target left /proc. Other observation errors stay fatal to the poll."""
    if isinstance(error, (FileNotFoundError, ProcessLookupError)):
        return True
    filename = getattr(error, 'filename', None) or ''
    return isinstance(error, OSError) and str(filename).startswith('/proc/')


def _mark_stale(state, pane):
    """Mark the panes of a dead client. Report whether the notice is new.

    A dead client is a standing fact, so it is reported once rather than on
    every poll.
    """
    notices = state.setdefault('_stale_notices', {})
    prefix = f'{pane}:'
    for key, entry in state.items():
        if key.startswith(prefix) and isinstance(entry, dict):
            entry['queue_reason'] = 'dead or stale process'
    new = pane not in notices
    notices[pane] = True
    return new


def _resolutions(path):
    """Read the operator's model resolutions written by the CLI."""
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _adopt_resolutions(state, path):
    """Fold operator resolutions into the monitor's own decision records."""
    decisions = state.setdefault('_model_decisions', {})
    routes = state.setdefault('_routes', {})
    for pane, record in _resolutions(path.parent / RESOLUTIONS).items():
        if not isinstance(record, dict):
            continue
        pending = decisions.get(pane)
        if isinstance(pending, dict) and pending.get('key') == record.get('key'):
            pending['resolved'] = record
        moved = record.get('route')
        if isinstance(moved, dict) and moved.get('pane') and moved['pane'] not in routes:
            routes[moved['pane']] = {'resume': True, 'at': time.time(), 'from': pane}


def _record_decision(decisions, snapshot, failure, allowlist):
    """Record a pending model decision. Report whether it is new."""
    record = decisions.get(snapshot.pane)
    if isinstance(record, dict) and record.get('key') == failure.key \
            and record.get('client_pid') == snapshot.pid:
        return False
    decisions[snapshot.pane] = {
        'name': failure.name,
        'phrase': failure.phrase,
        'key': failure.key,
        'detail': failure.detail,
        'line': failure.line,
        'client_pid': snapshot.pid,
        'at': time.time(),
        'providers': [entry['id'] for entry in allowlist],
        'resolved': None,
    }
    return True


def _route_to(snapshot, provider, config, decisions, failure, routes):
    """Move a pane's work to another client. Report whether it worked."""
    try:
        moved = resolve_route(snapshot.pane, provider, config)
    except (RuntimeError, OSError, ValueError) as error:
        LOG.warning('%s routing to %s failed: %s', snapshot.pane, provider, error)
        return None
    moved.update({'at': time.time(), 'key': failure.key})
    decisions[snapshot.pane] = {
        'name': failure.name,
        'phrase': failure.phrase,
        'key': failure.key,
        'detail': failure.detail,
        'line': failure.line,
        'client_pid': snapshot.pid,
        'at': time.time(),
        'providers': [provider],
        'resolved': {'provider': provider, 'model': moved.get('model', 'default'),
                     'at': time.time(), 'route': moved},
    }
    routes[moved['pane']] = {'resume': True, 'at': time.time(), 'from': snapshot.pane}
    LOG.warning('%s routed to %s in %s (pane %s); the new session resumes the work',
                snapshot.pane, provider, moved['session'], moved['pane'])
    return moved


def tick_queue(backend, policy, state, config, path, now, save):
    fallback = config.get('reply', DEFAULT_REPLY)
    allowlist = providers(config)
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
                if _mark_stale(state, pane):
                    LOG.warning('%s queue observation skipped: dead or stale process: %s', pane, error)
                continue
            LOG.warning('%s queue observation failed: %s', pane, error)
            failed = True
    # Unobserved panes cannot be assumed gone if any observation failed.
    if failed:
        save(path, state)
        return
    _adopt_resolutions(state, path)
    model_decisions = state['_model_decisions']
    routes = state.setdefault('_routes', {})
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
        elif phases[key] == 'model_blocked':
            # A provider failure ends the turn. The pane is paused, not running.
            LOG.info('queue releases %s: provider failure, model decision pending', s.pane)
            queue['active'] = None
        elif phases[key] in {'finished', 'stopped', 'capacity'} and (
                active.get('observed_running') or outcome(s) != active.get('outcome')):
            LOG.info('queue releases %s: %s', s.pane, phases[key])
            queue['active'] = None
        else:
            if phases[key] != 'active' and now - active['at'] >= 120 and not active.get('warned'):
                LOG.warning('queue holds %s: delivery or completion remains unconfirmed; inspect this pane', s.pane)
                active['warned'] = True
    candidates = set()
    eligible_map = {}
    for key, s in snapshots.items():
        entry = state.setdefault(key, {})
        state.get('_stale_notices', {}).pop(s.pane, None)
        capacity = phases[key] == 'capacity'
        route_entry = routes.get(s.pane)
        resume = bool(isinstance(route_entry, dict) and route_entry.get('resume'))
        model_note = None
        entry['queue_kind'] = 'capacity' if capacity else 'continuation'
        if phases[key] == 'stopped':
            entry['queue_reason'] = 'client requested no further automatic continuation'
            continue
        if phases[key] == 'model_blocked':
            failure = model_failure(s)
            if failure is None:
                continue
            record = model_decisions.get(s.pane)
            resolved = (isinstance(record, dict) and record.get('key') == failure.key
                        and isinstance(record.get('resolved'), dict))
            entry['queue_kind'] = 'model_decision'
            if resolved:
                applied = record['resolved']
                if applied.get('route'):
                    # The work moved to another client. This pane stays paused.
                    entry['queue_reason'] = 'routed to %s (%s)' % (
                        applied.get('provider'), applied['route'].get('session'))
                    continue
                # The operator already chose for this exact failure.
                model_note = 'model decision applied: %s/%s' % (
                    applied.get('provider'), applied.get('model'))
                entry['queue_reason'] = model_note
                phases[key] = 'unknown'
            elif failure.name == 'credit_exhausted':
                hop = next_hop(config, failure.name, s.process)
                if hop and _route_to(s, hop, config, model_decisions, failure, routes):
                    entry['queue_reason'] = 'routed to %s' % hop
                    continue
                # The last tier is exhausted. Wait; do not retry and do not
                # fall back to a lower model.
                status = fallback_policy(config)['exhausted_status']
                entry['queue_reason'] = status
                if _record_decision(model_decisions, s, failure, allowlist):
                    LOG.warning('%s %s: %s (%s); waiting for the credits to reset',
                                s.pane, status, failure.detail, failure.name)
                continue
            else:
                entry['queue_reason'] = 'model decision pending: %s' % failure.name
                if _record_decision(model_decisions, s, failure, allowlist):
                    LOG.warning('%s model decision pending: %s (%s); choose with: '
                                'python3 -m overseer model-select %s',
                                s.pane, failure.name, failure.detail, s.pane)
                continue
        if phases[key] == 'active':
            entry['ran_turn'] = True
        if not s.ready or phases[key] == 'active':
            entry.pop('fingerprint', None)
            continue
        if phases[key] == 'finished':
            entry.pop('capacity_attempts', None)
        if capacity and entry.get('capacity_attempts', 0) >= config.get('capacity_max_retries', 3):
            entry['queue_reason'] = 'capacity retry limit reached; manual intervention needed'
            continue
        opencode_done = (s.process == 'opencode' and phases[key] == 'finished'
                         and bool(entry.get('ran_turn')))
        eligible, reason = policy.consider(entry, s.text, now, capacity=capacity,
                                           retry_seconds=config.get('capacity_retry_seconds', 120),
                                           resume=resume, completed=opencode_done)
        if not eligible:
            stopgate.review(entry, s.text, reason, config, now, s.pane)
        if eligible and not capacity and not resume:
            prompt, kind = stopgate.prompt_for(entry, s.text, lambda: next_prompt(s.text, fallback))
            if prompt is None:
                eligible = False
                reason = kind
                hold(entry, s.text, kind)
                LOG.info('%s skipped: %s', s.pane, kind)
        entry['queue_reason'] = reason
        if model_note:
            entry['queue_reason'] = model_note
        eligible_map[key] = eligible
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
    # Every branch that set a halting queue_reason is recorded here.
    for key, snapshot in snapshots.items():
        entry = state.get(key)
        if isinstance(entry, dict):
            note(entry, entry.get('queue_reason'), snapshot.text, snapshot.pane, now)
    save(path, state)
    if queue.get('active') or any(p == 'active' for p in phases.values()) or not waiting:
        return
    key = waiting[0]
    if not eligible_map.get(key):
        return
    s = snapshots[key]
    entry = state[key]
    if config['dry_run']:
        if entry.get('previewed') != entry['fingerprint']:
            _, kind = ('', 'routine continuation') if phases[key] == 'capacity' else stopgate.prompt_for(entry, s.text, lambda: next_prompt(s.text, fallback))
            if kind in {'report-based prompt', 'writer handoff prompt'}:
                LOG.info('%s would send %s in FIFO queue (dry run)', s.pane, kind)
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
    outgoing, kind = (fallback, 'routine continuation') if phases[key] == 'capacity' else stopgate.prompt_for(entry, s.text, lambda: next_prompt(s.text, fallback))
    route_entry = routes.get(s.pane)
    if isinstance(route_entry, dict) and route_entry.get('resume'):
        # A newly routed session gets the configured continuation to start.
        outgoing, kind = fallback, 'routed continuation'
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
    if isinstance(route_entry, dict) and route_entry.get('resume'):
        route_entry['resume'] = False
        route_entry['resumed_at'] = now
    save(path, state)
    try:
        backend.send(s, outgoing)
        clear(entry)
        if kind == stopgate.OVERRIDE_KIND:
            stopgate.sent(entry)
        if kind in {'report-based prompt', 'writer handoff prompt', stopgate.OVERRIDE_KIND}:
            LOG.info('%s sent %s', s.pane, kind)
        elif kind == 'routed continuation':
            LOG.info('%s dispatched the routed continuation', s.pane)
        else:
            LOG.info('%s dispatched from FIFO queue', s.pane)
    except (RuntimeError, OSError, ValueError) as error:
        # Retain the slot: an ambiguous send cannot safely be retried or overlapped.
        LOG.warning('%s queue delivery uncertain; reservation retained: %s', s.pane, error)
