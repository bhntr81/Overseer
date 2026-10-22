"""The monitor's explicit halted status.

An intentional halt — the client asked to stop, the turn needs input, the
escalation gate holds the pane, a model decision is pending — is recorded in
the monitor's own state file, announced once, and shown by ``overseer status``.
Nothing here changes when the monitor sends: a halted pane still receives no
automated reply. This module records, announces and renders only.

The record lives in the monitor's JSON state file, inside the pane's own
entry, so it outlives the tmux session that produced it and the operator can
still see why the automatic replies stopped. The factory's sqlite ledger and
its repair-lineage freeze are a different store and never see this one.

A reason is a fixed phrase. It never carries report text, and it is never
interpreted.
"""
import json
import logging
import time
from pathlib import Path

from .escalation import HOLD_ESCALATION, HOLD_STRIKES
from .policy import INVALID_REPORT, NEEDS_INPUT_MARK, STOP_REASON, current_turn
from .route import session_name

LOG = logging.getLogger("overseer")

HALTED = "HALTED"
PAUSED = "PAUSED"
NEEDS_INPUT = "OVERSEER_NEEDS_INPUT"
REPORT_STOP = "output report requested no further continuation"
MODEL_PENDING = "model decision pending: "
ROUTED = "routed to "
EXHAUSTED = "CREDITS_EXHAUSTED"
CAPACITY_LIMIT = "capacity retry limit reached; manual intervention needed"

ANSWER_IN_PANE = "answer it in the pane to resume"
UNFREEZE = "python3 -m overseer unfreeze <pane>"
MODEL_SELECT = "python3 -m overseer model-select <pane>"

# The exact reason, its kind, and the action that resumes the automatic turns.
REASONS = {
    STOP_REASON: (HALTED, "the client asked to stop; " + ANSWER_IN_PANE),
    NEEDS_INPUT: (HALTED, "the client is waiting for an answer; " + ANSWER_IN_PANE),
    REPORT_STOP: (HALTED, "the report ended the automatic continuation; "
                 + ANSWER_IN_PANE),
    HOLD_ESCALATION: (HALTED, UNFREEZE),
    HOLD_STRIKES: (HALTED, UNFREEZE),
    MODEL_PENDING: (PAUSED, MODEL_SELECT),
    CAPACITY_LIMIT: (PAUSED, "manual intervention needed; the pane is not retried"),
    INVALID_REPORT: (PAUSED, "print the OVERSEER_REPORT again with its JSON on one line"),
}


def classify_reason(reason):
    """Return the (kind, resume action) of an intentional halt, or None.

    The default is transient: a reason that is not named here is not a halt,
    so it is neither recorded nor written over an existing record.
    """
    if not isinstance(reason, str) or not reason:
        return None
    if reason in REASONS:
        return REASONS[reason]
    if reason.startswith(MODEL_PENDING):
        return (PAUSED, MODEL_SELECT)
    if reason.startswith(ROUTED):
        return (PAUSED, "the work moved to another session; this pane stays paused")
    if reason.startswith(EXHAUSTED):
        return (PAUSED, "wait for the credits to reset")
    return None


def exact_reason(reason, text):
    """Return the reason to record, naming the marker when the turn carries one.

    The policy returns one reason for two situations, so the current turn is
    read to tell a client that needs input from a client that stopped. A marker
    in an earlier turn is not part of the current turn and does not count.
    """
    if reason == STOP_REASON and isinstance(text, str):
        if NEEDS_INPUT_MARK.search(current_turn(text)):
            return NEEDS_INPUT
    return reason


def session_of(pane):
    """Return the session name of a pane, or the pane id when it is gone."""
    try:
        return session_name(pane) or pane
    except (RuntimeError, OSError, ValueError):
        return pane


def note(entry, reason, text=None, pane=None, now=None, session=None):
    """Record an intentional halt and announce it once.

    Returns the new record when the transition is new, and None otherwise: the
    same reason is never announced twice, and a transient reason never records,
    replaces or clears anything.
    """
    kind = classify_reason(reason)
    if kind is None:
        return None
    exact = exact_reason(reason, text)
    previous = entry.get("halt")
    if isinstance(previous, dict) and previous.get("reason") == exact:
        return None
    if session:
        name = session
    elif pane:
        name = session_of(pane)
    else:
        name = ""
    record = {"reason": exact, "kind": kind[0], "resume": kind[1], "session": name,
              "pane": pane or "", "at": now if now is not None else time.time()}
    entry["halt"] = record
    LOG.info("[OVERSEER] Session %s paused automatic turns: %s", name, exact)
    LOG.info("[OVERSEER] Session %s resumes when: %s", name, kind[1])
    return record


def clear(entry):
    """Remove the pane's halt record after a successful send."""
    entry.pop("halt", None)


def read_state(path):
    """Read the monitor's state file tolerantly. A broken file is an empty state."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def render(state):
    """Return the lines of the halted status section for a whole state dict.

    The section is read from the state file, so a pane whose tmux session has
    closed is still listed with the reason it stopped for.
    """
    lines = []
    for key, entry in sorted(state.items()):
        if not isinstance(entry, dict):
            continue
        record = entry.get("halt")
        if not isinstance(record, dict):
            continue
        lines.append("  %s session=%s %s" % (record.get("pane") or key.split(":")[0],
                                              record.get("session") or "unknown",
                                              record.get("kind") or HALTED))
        lines.append("    Reason: %s" % (record.get("reason") or "unknown"))
        lines.append("    Resume: %s" % (record.get("resume") or "unknown"))
    if not lines:
        return []
    return ["HALTED / PAUSED SESSIONS:"] + lines
