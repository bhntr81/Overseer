"""Provider failures and the operator's model choice.

The monitor never substitutes a model on its own. A client that reports an
unsupported model, exhausted credits, or a failed login pauses its pane and
leaves the choice to the operator.
"""
from dataclasses import dataclass
import re


UNSUPPORTED_MODEL = re.compile(
    r"model is not supported|unsupported model|invalid model|unknown model|model[ _]not[ _]found",
    re.IGNORECASE,
)
CREDIT_EXHAUSTED = re.compile(
    r"insufficient credit|out of credits|credit balance|quota exceeded|insufficient_quota|"
    r"usage limit reached|payment required|billing",
    re.IGNORECASE,
)
AUTH_FAILED = re.compile(
    r"unauthorized|authentication failed|not logged in|invalid api key|login required",
    re.IGNORECASE,
)

CLASSES = (
    ("unsupported_model", UNSUPPORTED_MODEL),
    ("credit_exhausted", CREDIT_EXHAUSTED),
    ("auth_failed", AUTH_FAILED),
)

# These phrases identify a provider failure without needing the word "error".
SELF_DESCRIBING = frozenset({
    "insufficient credit", "out of credits", "credit balance", "quota exceeded",
    "insufficient_quota", "usage limit reached", "payment required",
    "unauthorized", "authentication failed", "not logged in", "invalid api key",
    "login required",
})

QUOTED = re.compile(r"'([^']+)'")
SELECTED = re.compile(r"^[>❯»›]\s")
FOOTER = "default]"
RESOLUTIONS = "model-resolutions.json"
BOX = "┃"
PICKER_HEADER = "Select Model and Effort"
PICKER_FOOTER = "enter select"
EFFORT_HEADER = "Select Reasoning Level"
EXHAUSTED = "CREDITS_EXHAUSTED_WAITING"
DEFAULT_POLICY = {
    "primary": [],
    "zero_credit": [],
    "excluded_models": [],
    "exhausted_status": EXHAUSTED,
}


@dataclass(frozen=True)
class Failure:
    """One provider failure visible in a client's output."""

    name: str
    phrase: str
    line: str
    detail: str
    start: int
    end: int

    @property
    def key(self):
        """Decision identity. The line carries volatile text, so it is excluded."""
        return f"{self.name}:{self.phrase}"


def _detail(name, line, phrase):
    if name == "unsupported_model":
        quoted = QUOTED.search(line)
        if quoted:
            return quoted.group(1)
    return phrase


def detect(text):
    """Return the most recent provider failure in text, or None."""
    found = None
    for name, pattern in CLASSES:
        for match in pattern.finditer(text):
            start = text.rfind("\n", 0, match.start()) + 1
            end = text.find("\n", match.end())
            line = text[start:end if end != -1 else len(text)].strip()
            phrase = match.group(0).casefold()
            if "error" not in line.casefold() and phrase not in SELF_DESCRIBING:
                continue
            failure = Failure(name, phrase, line, _detail(name, line, phrase),
                              match.start(), match.end())
            if found is None or failure.end > found.end:
                found = failure
    return found


def normalize(text):
    """Fold case, spaces, dashes, and underscores for model matching."""
    return re.sub(r"[\s_-]+", " ", text or "").strip().casefold()


def model_id(model):
    """Return the identifier of a configured model entry."""
    return model.get("id") if isinstance(model, dict) else model


def model_label(model):
    """Return the display label of a configured model entry."""
    if isinstance(model, dict):
        return model.get("label") or model.get("id")
    return model


def provider_table(config):
    """Return the configured providers keyed by id."""
    table = config.get("model_providers")
    return table if isinstance(table, dict) else {}


def fallback_policy(config):
    """Return the credit fallback policy. A malformed policy is unusable, not fatal."""
    raw = config.get("fallback_policy")
    result = dict(DEFAULT_POLICY)
    if not isinstance(raw, dict):
        return result
    for field in ("primary", "zero_credit", "excluded_models"):
        value = raw.get(field)
        if isinstance(value, list):
            result[field] = [item for item in value if isinstance(item, str) and item.strip()]
    status = raw.get("exhausted_status")
    if isinstance(status, str) and status.strip():
        result["exhausted_status"] = status.strip()
    return result


def excluded_models(config):
    """Return the normalized model ids the policy excludes."""
    return {normalize(item) for item in fallback_policy(config)["excluded_models"]}


def permitted_models(config, provider_id):
    """Return a provider's models with the excluded ids removed."""
    entry = provider_table(config).get(provider_id)
    if not isinstance(entry, dict):
        return []
    excluded = excluded_models(config)
    models = [m for m in entry.get("models") or [] if isinstance(m, (str, dict))]
    return [m for m in models if normalize(model_id(m)) not in excluded]


def fallback_chain(config, failure_name):
    """Return the ordered provider chain for a failure class.

    A credit failure means the paid tier cannot serve the work, so the chain
    starts at the zero-credit tier. Any other failure keeps the paid tier.
    """
    rules = fallback_policy(config)
    if failure_name == "credit_exhausted":
        return list(rules["zero_credit"])
    return list(rules["primary"])


def next_hop(config, failure_name, client):
    """Return the next provider whose client differs from the pane's client."""
    table = provider_table(config)
    for provider_id in fallback_chain(config, failure_name):
        entry = table.get(provider_id)
        if isinstance(entry, dict) and entry.get("client") != client:
            return provider_id
    return None


def providers(config):
    """Return the ordered provider allowlist from a config dict."""
    table = config.get("model_providers")
    order = config.get("allowed_providers")
    if not isinstance(table, dict) or not isinstance(order, list):
        return []
    allowlist = []
    for name in order:
        entry = table.get(name)
        if not isinstance(entry, dict):
            continue
        client = entry.get("client")
        models = permitted_models(config, name)
        if not isinstance(client, str) or not client or not models:
            continue
        allowlist.append({"id": name, "client": client,
                          "label": entry.get("label") or name, "models": models})
    return allowlist


def find_entry(lines, model):
    """Return the index of the picker entry for model, or None."""
    wanted = normalize(model_id(model))
    label = normalize(model_label(model))
    for index, line in enumerate(lines):
        text = normalize(line)
        if not text:
            continue
        if wanted and wanted in text:
            return index
        if label and label in text:
            return index
    return None


def selected_index(lines):
    """Return the index of the highlighted picker entry, or None."""
    for index, line in enumerate(lines):
        if SELECTED.match(line.strip()):
            return index
    return None


def picker_block(lines):
    """Return the entries of a model picker, or an empty list.

    Only the block between the picker's own header and footer is searched, so
    a conversation line can never be mistaken for a picker entry.
    """
    start = None
    for index, line in enumerate(lines):
        if PICKER_HEADER in line:
            start = index
            break
    if start is None:
        return []
    for index in range(start + 1, len(lines)):
        if PICKER_FOOTER in lines[index]:
            return lines[start + 1:index]
    return lines[start + 1:]


def effort_screen(text):
    """Report whether a captured screen is the reasoning level step."""
    return EFFORT_HEADER in (text or "")


def navigation(target, highlighted):
    """Return the key and the number of presses that reach the target entry."""
    if target is None or highlighted is None:
        return "Down", 0
    delta = target - highlighted
    if delta == 0:
        return "Down", 0
    return ("Down" if delta > 0 else "Up"), abs(delta)


def footer_model(text):
    """Return the model segment of a client composer footer, or None."""
    for line in reversed(text.splitlines()):
        if "·" in line and FOOTER in line:
            return line.strip().split("·")[0].strip()
    return None


def footer_shows(text, model):
    """Report whether the composer footer names the expected model."""
    head = footer_model(text)
    if not head:
        return False
    return normalize(head).startswith(normalize(model_label(model)))


def opencode_composer(text):
    """Return the text of an OpenCode composer row, or None when it is not one."""
    stripped = (text or "").strip()
    if not stripped.startswith(BOX):
        return None
    return stripped[len(BOX):].strip()


def opencode_empty(text):
    """Report whether an OpenCode composer row shows an empty input."""
    body = opencode_composer(text)
    if body is None:
        return False
    return body == "" or body.startswith("Ask anything")
