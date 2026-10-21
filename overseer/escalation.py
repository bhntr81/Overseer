"""The monitor's escalation hold and its pane 3-strike freeze.

The monitor stops sending to a pane when the current turn carries a valid
AGENTS.md status block whose STATUS is STUCK_NEEDS_ESCALATION, and when three
consecutive step reports of that pane show TESTS_PASSED: FALSE or an unchanged
remaining fingerprint. A held pane is never sent to again: not a continuation,
not a report prompt, not a handoff, not a capacity retry, not a routed resume.

The hold lives in the monitor's own JSON state file, inside that pane's own
entry, a store the factory's sqlite ledger never sees. Only the operator
releases a pane, with ``python3 -m overseer unfreeze <pane>``. Report text is
data: it is parsed, never evaluated.
"""
import json
import logging
import time
from pathlib import Path

from .policy import _report_state, current_turn, fingerprint
from .statusblock import STATUS_STUCK, parse

LOG = logging.getLogger("overseer")
RELEASES = "escalation-releases.json"
HOLD_ESCALATION = "status block reports STUCK_NEEDS_ESCALATION"
HOLD_STRIKES = "three consecutive failed or unchanged step reports"
STRIKE_LIMIT = 3
ENTRY = {"held": None, "strikes": 0, "last_remaining": None, "last_report": None}


def _held(entry):
    """Return the recorded hold of a pane entry, or None."""
    escalation = entry.get("escalation")
    if not isinstance(escalation, dict):
        return None
    held = escalation.get("held")
    return held if isinstance(held, dict) else None


def _turn(text):
    """Return the current turn's report fields and its valid status block."""
    turn = current_turn(text)
    kind, fields = _report_state(turn)
    block = parse(turn)
    return (fields if kind in ("ready", "handoff") else None,
            block if block["valid"] else None)


def _freeze(state, reason, screen):
    """Record the hold of a pane with the id a release record must name."""
    entry = state.setdefault("escalation", dict(ENTRY))
    stamp = time.time()
    entry["held"] = {"reason": reason, "at": stamp, "screen": screen,
                     "id": fingerprint("%s|%.6f" % (reason, stamp))}


def classify(state, text):
    """Return the hold reason of one pane and screen, or None."""
    # The entry is the pane's own state. Without one the text is still read:
    # a stuck status block holds the pane, but nothing can be recorded.
    entry = state.get("escalation") if isinstance(state, dict) else None
    if not isinstance(entry, dict):
        entry = {}
    if entry.get("held"):
        return entry["held"]["reason"]
    screen = fingerprint(text)
    if entry.get("last_report") == screen:
        # The same screen, already observed: one report counts once.
        return None
    report, status = _turn(text)
    if status is not None and status["status"] == STATUS_STUCK:
        if state is None:
            return HOLD_ESCALATION
        _freeze(state, HOLD_ESCALATION, screen)
        return HOLD_ESCALATION
    if state is None or (report is None and status is None):
        # Without evidence the counter neither advances nor resets.
        return None
    remaining = report.get("remaining") if report else None
    if remaining is None and status is not None:
        remaining = status.get("next_instruction")
    previous = entry.get("last_remaining")
    entry = state.setdefault("escalation", dict(ENTRY))
    entry["last_report"] = screen
    if remaining is not None:
        remaining = fingerprint(remaining)
        entry["last_remaining"] = remaining
    failed = status is not None and status["tests_passed"] is False
    if failed or (remaining is not None and remaining == previous):
        entry["strikes"] = entry.get("strikes", 0) + 1
    else:
        entry["strikes"] = 0
    if entry["strikes"] >= STRIKE_LIMIT:
        _freeze(state, HOLD_STRIKES, screen)
        return HOLD_STRIKES
    return None


def _read(path):
    """Read the release records beside the state file, or nothing."""
    target = Path(path).parent / RELEASES
    try:
        data = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(path, data):
    """Write the release records beside the state file."""
    target = Path(path).parent / RELEASES
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(target)


def release(state, pane, path):
    """Record the operator's release of one pane. Return the released ids."""
    # The state file belongs to the running monitor, so the release is written
    # to the sidecar beside it and the monitor folds it into its own state.
    prefix = pane + ":"
    ids = []
    for key, entry in state.items():
        if not key.startswith(prefix) or not isinstance(entry, dict):
            continue
        held = _held(entry)
        if held and held.get("id"):
            ids.append(held["id"])
    if not ids:
        return []
    data = _read(path)
    data[pane] = {"ids": ids, "at": time.time()}
    _write(path, data)
    return ids


def adopt(state, path):
    """Apply the operator's releases to the monitor's state. Return the keys."""
    # A release names the id of the freeze it releases. A record left behind by
    # an earlier release never matches a later freeze, so it releases nothing.
    released = []
    for pane, record in _read(path).items():
        ids = record.get("ids") if isinstance(record, dict) else None
        if not isinstance(ids, list):
            continue
        for key, entry in state.items():
            if not key.startswith(pane + ":") or not isinstance(entry, dict):
                continue
            held = _held(entry)
            if not held or held.get("id") not in ids:
                continue
            escalation = entry["escalation"]
            escalation["held"] = None
            escalation["strikes"] = 0
            escalation["last_remaining"] = None
            if isinstance(held.get("screen"), str):
                escalation["last_report"] = held["screen"]
            released.append(key)
            LOG.info("%s released by the operator", key)
    return released
