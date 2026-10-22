"""Wind the worker down to a clean stop before its account usage runs out.

Claude Code prints a usage line in the pane, e.g. "You've used 75% of your
weekly limit". When almost nothing is left, a hard cut can interrupt the worker
in the middle of an edit, leaving a half-written change and no commit. This
module reads that line out of bounded pane text and decides whether the monitor
should send a one-time wind-down instruction — finish the current change,
commit and push loose ends, update the handoff, and stop — instead of a routine
continuation. Stopping a few percent early trades a little unused budget for not
being cut off mid-change.

Several limits can be shown at once (weekly, session, a rolling window); the
most-constrained one wins, so the guard fires on whichever runs out first. ANSI
escapes are stripped and only the last 64 KiB is read, matching the status-block
reader. This module reads nothing and runs nothing; it returns data and a prompt
string the monitor sends, never code to evaluate.
"""
import re

from overseer.policy import ANSI

# Wind down once only this many percent of a limit remains. The user asked for a
# stop at about 5% left, so the worker wraps up before the hard cut.
DEFAULT_THRESHOLD_PERCENT = 5

# Only the last 64 KiB of pane text is read, as the status-block reader does, so
# an old usage line scrolled far up the pane cannot decide a live cycle.
MAX_TEXT_BYTES = 64 * 1024

# "You've used 75% of your weekly limit" / "used 97% of your 5-hour limit", with
# or without the leading "You've". The percent is captured; the limit kind is
# matched loosely so a new phrasing of "... of your <kind> limit" still counts.
_USAGE = re.compile(r"used\s+(\d{1,3})%\s+of\s+your\s+[\w .-]*?limit",
                    re.IGNORECASE)


def _tail(text):
    """Return the ANSI-stripped last MAX_TEXT_BYTES of text, or '' for non-text."""
    if not isinstance(text, str):
        return ""
    if len(text) > MAX_TEXT_BYTES:
        text = text[-MAX_TEXT_BYTES:]
    return ANSI.sub("", text)


def used_percent(text):
    """Return the highest usage percent shown in text, clamped to 100, or None.

    None means no usage line was found, which is treated as unknown — never as
    "plenty left", so a missing line can never by itself trigger a wind-down.
    """
    found = [int(match.group(1)) for match in _USAGE.finditer(_tail(text))]
    if not found:
        return None
    return min(100, max(found))


def remaining_percent(text):
    """Return how many percent of the most-constrained limit remain, or None."""
    used = used_percent(text)
    if used is None:
        return None
    return 100 - used


def should_wind_down(text, threshold_percent=DEFAULT_THRESHOLD_PERCENT):
    """Whether the worker should wind down: a usage line is present and at most
    ``threshold_percent`` of its most-constrained limit remains. Unknown usage
    (no line) never winds down."""
    remaining = remaining_percent(text)
    return remaining is not None and remaining <= threshold_percent


def winddown_prompt():
    """The one-time instruction to send when usage is nearly exhausted.

    A single line (the monitor sends one line), telling the worker to reach a
    clean stopping point and stop, rather than begin new work that a hard cut
    would interrupt.
    """
    return ("Your account usage is nearly exhausted, so wind down now: finish only "
            "the change in progress, commit and push loose ends, update the handoff/NOW "
            "with exactly where things stand and the next step, then stop. Do not start "
            "any new task or step — reach a clean stopping point and stop there.")
