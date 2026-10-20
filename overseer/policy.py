"""Conservative, deterministic detection; terminal text is never executed.

A visible OVERSEER_REPORT line is parsed as data. It is never evaluated, and
its fields are copied into one bounded prompt. No model is asked to interpret it.
"""

import hashlib
import json
import re


DEFAULT_REPLY = "Yes, please continue with the next step of the current task."
CONTINUE = re.compile(
    r"(?:would you like me to|shall I|should I|may I|can I) "
    r"(?:continue|proceed|go ahead)(?:\s+with (?:the )?next step)?\s*\?"
    r"|(?:ready to continue|continue with the next step)\s*\?",
    re.IGNORECASE,
)
BLOCKED = re.compile(
    r"approve|approval|permission|allow (?:once|always)|sandbox|sudo|password|"
    r"api.?key|credential|delete|destroy|overwrite|deploy|publish|purchase|"
    r"payment|send (?:an? )?(?:email|message)|push to|git push|merge|"
    r"accept (?:these |the )?edits|trust (?:this|the)|\[y/n\]|\(y/n\)|"
    r"esc to (?:interrupt|cancel)|ctrl.c to (?:interrupt|cancel)|"
    r"thinking|working|running|generating",
    re.IGNORECASE,
)
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
STOP = re.compile(r"^\s*(?:[•*-]\s*)?OVERSEER_(?:DONE|NEEDS_INPUT)\b", re.MULTILINE)
COMPLETED = re.compile(r"Worked for .+ •", re.IGNORECASE)


def tail_text(text):
    return "\n".join(ANSI.sub("", text).splitlines()[-18:]).strip()


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


REPORT_MARK = "OVERSEER_REPORT"
MAX_PROMPT = 1000
_REPORT_TAIL = (
    "When that step is finished, print one visible line that starts with "
    "OVERSEER_REPORT and a JSON object with status, objective, remaining, done, and evidence. "
    "status must be continue, done, or needs_input. "
    "Put the next unfinished step in remaining. "
    "If authorized work is finished or cannot proceed, use done or needs_input and do not invent work."
)


def _controls(text):
    return any(ord(character) < 32 or ord(character) == 127 for character in text)


def _sendable(text):
    return isinstance(text, str) and bool(text.strip()) and len(text) <= MAX_PROMPT and not _controls(text)


def _report_state(text):
    """Return absent, invalid, stop, empty, or ready plus fields from the latest report."""
    cleaned = ANSI.sub("", text)
    found = False
    payload = None
    for line in cleaned.splitlines():
        body = line.strip()
        if not body.startswith(REPORT_MARK):
            continue
        rest = body[len(REPORT_MARK):].lstrip(" \t")
        if not rest.startswith("{"):
            continue
        found = True
        try:
            value, end = json.JSONDecoder().raw_decode(rest)
        except json.JSONDecodeError:
            payload = None
            continue
        if rest[end:].strip() or not isinstance(value, dict):
            payload = None
            continue
        payload = value
    if not found:
        return "absent", None
    if not isinstance(payload, dict):
        return "invalid", None
    status = payload.get("status")
    if status in {"done", "needs_input"}:
        return "stop", None
    if status != "continue":
        return "invalid", None
    fields = {}
    for name, required in (("objective", True), ("remaining", True), ("done", False), ("evidence", False)):
        if name not in payload or payload[name] in (None, ""):
            if required:
                return "empty", None
            fields[name] = ""
            continue
        value = payload[name]
        if not isinstance(value, str) or _controls(value):
            return "invalid", None
        collapsed = " ".join(value.split())
        if not collapsed:
            if required:
                return "empty", None
            fields[name] = ""
            continue
        fields[name] = collapsed
    return "ready", fields


def _compose(fields):
    objective = fields["objective"][:160]
    remaining = fields["remaining"][:220]
    done = fields["done"][:120]
    evidence = fields["evidence"][:120]
    while True:
        parts = [f"Automatic continuation. Objective: {objective}."]
        if done:
            parts.append(f"Done: {done}.")
        if evidence:
            parts.append(f"Evidence: {evidence}.")
        parts.append(f"Do only this next: {remaining}.")
        parts.append(_REPORT_TAIL)
        prompt = " ".join(parts)
        if _sendable(prompt):
            return prompt
        if len(remaining) > 40:
            remaining = remaining[:max(40, len(remaining) - 40)].rstrip()
        elif evidence:
            evidence = ""
        elif done:
            done = ""
        elif len(objective) > 20:
            objective = objective[:max(20, len(objective) - 20)].rstrip()
        else:
            return None


def next_prompt(text, fallback, *, capacity=False):
    """Choose the one line to submit, or withhold it.

    The reason is a fixed phrase. It never includes report text.
    """
    if capacity:
        if _sendable(fallback):
            return fallback, "routine continuation"
        return None, "invalid output report"
    kind, fields = _report_state(text)
    if kind == "absent":
        if _sendable(fallback):
            return fallback, "routine continuation"
        return None, "invalid output report"
    if kind == "invalid":
        return None, "invalid output report"
    if kind == "stop":
        return None, "output report requested no further continuation"
    if kind == "empty":
        return None, "report has no remaining work"
    prompt = _compose(fields)
    if prompt is None:
        return None, "invalid output report"
    return prompt, "report-based prompt"


def hold(state, text, reason):
    """Remember a screen that must not be answered again, without counting a reply."""
    state["held_fingerprint"] = fingerprint(text)
    state["held_reason"] = reason


def classify(text, continue_on_completion=False):
    tail = tail_text(text)
    if STOP.search(tail):
        return False, "client requested no further automatic continuation"
    if BLOCKED.search(tail):
        return False, "active generation, permission, or sensitive action visible"
    if continue_on_completion and COMPLETED.search(tail):
        return True, "completed turn with empty composer"
    if not CONTINUE.search(tail):
        return False, "no recognized routine continuation question"
    return True, "routine continuation question"


class Policy:
    def __init__(self, idle_seconds=180, cooldown_seconds=900, max_per_day=12, continue_on_completion=False):
        self.idle_seconds = idle_seconds
        self.cooldown_seconds = cooldown_seconds
        self.max_per_day = max_per_day
        self.continue_on_completion = continue_on_completion

    def consider(self, state, text, now, *, capacity=False, retry_seconds=120, resume=False):
        """Update observation state. Sending must be acknowledged separately."""
        digest = fingerprint(text)
        if state.get("fingerprint") != digest or now < state.get("stable_since", now):
            state.update(fingerprint=digest, stable_since=now)
        if capacity:
            eligible, reason = True, "model capacity retry"
        elif resume:
            eligible, reason = True, "routed session needs a continuation"
        else:
            eligible, reason = classify(text, self.continue_on_completion)
        if not eligible:
            return False, reason
        if now - state["stable_since"] < (retry_seconds if capacity else self.idle_seconds):
            return False, "waiting for idle threshold"
        if not capacity and state.get("sent_fingerprint") == digest:
            return False, "already replied to this screen"
        if not capacity and state.get("held_fingerprint") == digest:
            return False, state.get("held_reason") or "output report withheld"
        if now - state.get("last_sent", float("-inf")) < (retry_seconds if capacity else self.cooldown_seconds):
            return False, "cooldown"
        recent = [stamp for stamp in state.get("sent_times", []) if now - stamp < 86400]
        state["sent_times"] = recent
        if len(recent) >= self.max_per_day:
            return False, "daily reply limit"
        return True, reason

    @staticmethod
    def acknowledge(state, text, now):
        state.update(last_sent=now, sent_fingerprint=fingerprint(text))
        state.setdefault("sent_times", []).append(now)
