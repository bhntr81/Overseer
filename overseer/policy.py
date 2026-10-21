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
DONE_MARK = re.compile(r"^\s*(?:[•*-]\s*)?OVERSEER_DONE\b", re.MULTILINE)
NEEDS_INPUT_MARK = re.compile(r"^\s*(?:[•*-]\s*)?OVERSEER_NEEDS_INPUT\b", re.MULTILINE)
# A finished step of a larger objective. Its stopping condition ended that
# prompt, not the objective.
STEP_DONE_MARK = re.compile(r"^\s*(?:[•*-]\s*)?OVERSEER_STEP_DONE\b", re.MULTILINE)
STOP_REASON = "client requested no further automatic continuation"
HANDOFF_REASON = "finished step; writer handoff due"
COMPLETED = re.compile(r"Worked for .+ •", re.IGNORECASE)


def current_turn(text):
    """Return the current answer: the text after the last submitted prompt line.

    A report or a marker of an earlier turn belongs to that turn. The answer
    above an empty composer is kept.
    """
    lines = ANSI.sub("", text).splitlines()
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index].strip()
        if line.startswith(("› ", "❯ ", "> ")) and line not in {"› Ask Codex to do anything"}:
            return "\n".join(lines[index + 1:])
    return "\n".join(lines)


def tail_text(text):
    return "\n".join(ANSI.sub("", text).splitlines()[-18:]).strip()


def fingerprint(text):
    return hashlib.sha256(text.encode()).hexdigest()


REPORT_MARK = "OVERSEER_REPORT"
MAX_PROMPT = 1000
_REPORT_TAIL = (
    "When that step is finished, print one visible line starting OVERSEER_REPORT "
    "and a JSON object with status, objective, remaining, done, and evidence. "
    "status is continue, step_done, done, or needs_input. "
    "A prompt's stopping condition ends that prompt, not the objective: if a next step "
    "remains, use step_done, put it in remaining, and end with \"OVERSEER_STEP_DONE\". "
    "Use done only when the objective has no actionable next step; do not invent work."
)


def _controls(text):
    return any(ord(character) < 32 or ord(character) == 127 for character in text)


def _sendable(text):
    return isinstance(text, str) and bool(text.strip()) and len(text) <= MAX_PROMPT and not _controls(text)


def _report_state(text):
    """Return absent, invalid, stop, empty, ready, or handoff plus fields from the latest report.

    A step_done report is a finished step of an objective that still has a
    named next step, so it becomes a writer handoff. A done report means the
    objective is finished and is taken at its word, whatever its remaining says.
    """
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
    if status not in {"continue", "step_done"}:
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
    return ("handoff" if status == "step_done" else "ready"), fields


def _done_follows_step_report(turn):
    """Return whether the last OVERSEER_DONE of a turn directly follows a step report.

    A bare OVERSEER_DONE ends only the step when the line above it, blank lines
    aside, is the turn's latest report and that report is step_done. A report
    quoted earlier in the answer, with prose after it, does not override the
    marker.
    """
    if _report_state(turn)[0] != "handoff":
        return False
    lines = turn.splitlines()
    marks = [index for index, line in enumerate(lines) if DONE_MARK.match(line)]
    if not marks:
        return False
    index = marks[-1] - 1
    while index >= 0 and not lines[index].strip():
        index -= 1
    return index >= 0 and _report_state(lines[index])[0] == "handoff"


def handoff_due(text, markers):
    """Return whether a finished step of the current turn asks for a writer handoff.

    The step report must belong to the current turn. OVERSEER_STEP_DONE under
    it is enough; a bare OVERSEER_DONE must directly follow it.
    """
    turn = current_turn(text)
    if _report_state(turn)[0] != "handoff":
        return False
    if STEP_DONE_MARK.search(markers) and STEP_DONE_MARK.search(turn):
        return True
    return bool(DONE_MARK.search(markers)) and _done_follows_step_report(turn)


def stop_requested(text, tail_only=True):
    """Return the fixed reason the screen asks Overseer to stop, or None.

    OVERSEER_NEEDS_INPUT anywhere in the current turn always stops, whatever
    the tail shows. OVERSEER_DONE stops unless it directly follows a step_done
    report of the current turn: the structured report names the next step and
    the bare marker does not, so the more specific statement decides.
    """
    turn = current_turn(text)
    markers = tail_text(text) if tail_only else ANSI.sub("", text)
    if NEEDS_INPUT_MARK.search(markers) or NEEDS_INPUT_MARK.search(turn):
        return STOP_REASON
    if DONE_MARK.search(markers) and not _done_follows_step_report(turn):
        return STOP_REASON
    return None


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


def _compose_handoff(fields):
    """Return the writer-handoff prompt for a finished step, or None.

    Overseer instructs the handoff. It cannot see or verify that a separate
    prompt-writing agent ran, wrote the next prompt, or that the prompt was
    executed; it reads only the next report.
    """
    objective = fields["objective"][:160]
    remaining = fields["remaining"][:220]
    done = fields["done"][:120]
    evidence = fields["evidence"][:120]
    while True:
        parts = ["Automatic continuation. The last step is finished; its stopping condition "
                 "ended that prompt, not the objective.", f"Objective: {objective}."]
        if done:
            parts.append(f"Step done: {done}.")
        if evidence:
            parts.append(f"Evidence: {evidence}.")
        parts.append("Give these results to the dedicated prompt-writing agent and have it "
                     f"write one bounded next prompt for: {remaining}.")
        parts.append("Then execute that prompt, verify it, and report. "
                     "If no separate writer can be used, report needs_input.")
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
    if kind == "handoff":
        if _report_state(current_turn(text))[0] != "handoff":
            # A step report of an earlier turn names a step that was already
            # handed over, or overtaken.
            return None, "step report belongs to an earlier turn"
        prompt = _compose_handoff(fields)
        if prompt is None:
            return None, "invalid output report"
        return prompt, "writer handoff prompt"
    prompt = _compose(fields)
    if prompt is None:
        return None, "invalid output report"
    return prompt, "report-based prompt"


def hold(state, text, reason):
    """Remember a screen that must not be answered again, without counting a reply."""
    state["held_fingerprint"] = fingerprint(text)
    state["held_reason"] = reason


def classify(text, continue_on_completion=False, completed=False, entry=None):
    tail = tail_text(text)
    stop = stop_requested(text)
    if stop:
        return False, stop
    # Imported here, not at module level: escalation reads the status block,
    # which reads this module, so a module-level import would close the cycle.
    from .escalation import classify as escalation_classify
    held = escalation_classify(entry, text)
    if held:
        return False, held
    if BLOCKED.search(tail):
        return False, "active generation, permission, or sensitive action visible"
    if handoff_due(text, tail):
        return True, HANDOFF_REASON
    if continue_on_completion and (COMPLETED.search(tail) or completed):
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

    def consider(self, state, text, now, *, capacity=False, retry_seconds=120, resume=False,
                 completed=False):
        """Update observation state. Sending must be acknowledged separately."""
        digest = fingerprint(text)
        if state.get("fingerprint") != digest or now < state.get("stable_since", now):
            state.update(fingerprint=digest, stable_since=now)
        eligible, reason = classify(text, self.continue_on_completion, completed, entry=state)
        holds = state.get("escalation")
        if reason == STOP_REASON or (isinstance(holds, dict) and holds.get("held")):
            # A stopped or held pane is never sent to, not even a capacity retry.
            return False, reason
        if capacity:
            eligible, reason = True, "model capacity retry"
        elif resume:
            eligible, reason = True, "routed session needs a continuation"
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
