"""Conservative, deterministic detection; terminal text is never executed."""

import hashlib
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

    def consider(self, state, text, now, *, capacity=False, retry_seconds=120):
        """Update observation state. Sending must be acknowledged separately."""
        digest = fingerprint(text)
        if state.get("fingerprint") != digest or now < state.get("stable_since", now):
            state.update(fingerprint=digest, stable_since=now)
        eligible, reason = ((True, "model capacity retry") if capacity
                            else classify(text, self.continue_on_completion))
        if not eligible:
            return False, reason
        if now - state["stable_since"] < (retry_seconds if capacity else self.idle_seconds):
            return False, "waiting for idle threshold"
        if not capacity and state.get("sent_fingerprint") == digest:
            return False, "already replied to this screen"
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
