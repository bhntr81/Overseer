"""Opt-in tmux transport. Never types into a desktop's focused window."""

from dataclasses import dataclass
import fnmatch
from pathlib import Path
import subprocess
import time

from .modelchoice import (
    effort_screen, find_entry, footer_model, footer_shows, model_id, navigation,
    opencode_empty, picker_block, selected_index,
)

CLIENTS = frozenset({"codex", "claude", "opencode"})


def command(*args):
    result = subprocess.run(["tmux", *args], text=True, capture_output=True, timeout=10)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "tmux command failed")
    return result.stdout


@dataclass(frozen=True)
class Snapshot:
    pane: str
    process: str
    pid: str
    text: str
    cursor_line: str
    mode: str
    dead: str
    cursor_x: int = -1

    @property
    def ready(self):
        if self.process not in CLIENTS or self.mode != "0" or self.dead != "0":
            return False
        if self.process == "opencode":
            # OpenCode draws a bordered box; the cursor sits on its text row.
            return opencode_empty(self.cursor_line)
        # Codex renders the composer as "›" or "»" depending on the build.
        return (self.cursor_line.strip() in {">", "❯", "›", "»"}
                or (self.cursor_line.strip() in {"› Ask Codex to do anything",
                                                "» Ask Codex to do anything"}
                    and self.cursor_x == 2))


def bridged_process(bridge_pid, binding):
    """Validate a live reptyr binding and the original tty's foreground client."""
    target_pid, start = binding.split(":")
    bridge = Path("/proc") / bridge_pid
    target = Path("/proc") / target_pid
    expected = Path.home() / ".local/share/overseer/vendor/usr/bin/reptyr"
    if bridge.joinpath("exe").resolve() != expected:
        raise RuntimeError("unrecognized terminal bridge")
    argv = bridge.joinpath("cmdline").read_bytes().decode().split("\0")
    if argv[1:3] != ["-T", target_pid]:
        raise RuntimeError("terminal bridge target mismatch")
    fields = target.joinpath("stat").read_text().rsplit(")", 1)[1].split()
    if fields[19] != start or fields[2] != fields[5] or fields[0] in {"T", "Z"}:
        raise RuntimeError("original client is no longer the foreground process")
    return target.joinpath("comm").read_text().strip(), binding


class Tmux:
    def __init__(self, exclusions=()):
        self.exclusions = exclusions

    def inventory(self):
        try:
            output = command("list-panes", "-a", "-F", "#{pane_id}\t#{@overseer}\t#{session_name}\t#{pane_title}")
        except RuntimeError as error:
            if "no server running" in str(error) or "error connecting" in str(error):
                return []
            raise
        result = []
        for line in output.splitlines():
            pane, enabled, session, title = line.split("\t", 3)
            excluded = any(matches(pattern, (pane, session, title)) for pattern in self.exclusions)
            result.append({"pane": pane, "enabled": enabled == "1", "session": session,
                           "title": title, "excluded": excluded})
        return result

    def panes(self):
        return [row["pane"] for row in self.inventory() if row["enabled"] and not row["excluded"]]

    def snapshot(self, pane, require_opt_in=True):
        metadata = command("display-message", "-p", "-t", pane,
                           "#{pane_id}\t#{pane_current_command}\t#{pane_pid}\t"
                           "#{cursor_y}\t#{pane_in_mode}\t#{pane_dead}\t#{@overseer}\t"
                           "#{cursor_x}\t#{@overseer_target}").rstrip("\n").split("\t")
        if len(metadata) != 9 or (require_opt_in and metadata[6] != "1"):
            raise RuntimeError("pane is no longer opted in")
        actual, process, pid, cursor_y, mode, dead, _, cursor_x, binding = metadata
        if binding:
            process, pid = bridged_process(pid, binding)
        text = command("capture-pane", "-p", "-t", actual)
        lines = text.splitlines()
        cursor = int(cursor_y)
        cursor_line = lines[cursor] if cursor < len(lines) else ""
        return Snapshot(actual, process, pid, text, cursor_line, mode, dead, int(cursor_x))

    def inspect(self, pane):
        """Read a pane without requiring the opt-in. Sending still requires it."""
        return self.snapshot(pane, require_opt_in=False)

    def _clear_picker(self, pane):
        """Leave any picker and clear a leftover command from the composer."""
        command("send-keys", "-t", pane, "Escape")
        time.sleep(0.3)
        if "/model" in command("capture-pane", "-p", "-t", pane):
            for _ in range(6):
                command("send-keys", "-t", pane, "BSpace")
            time.sleep(0.3)
        return command("capture-pane", "-p", "-t", pane)

    def select_model(self, pane, model):
        """Apply a model to a live client through the client's own picker."""
        current = self.inspect(pane)
        if not current.ready:
            raise RuntimeError("pane is not ready for a model change")
        command("send-keys", "-t", pane, "-l", "--", "/model")
        time.sleep(0.6)
        command("send-keys", "-t", pane, "Enter")
        time.sleep(1.0)
        screen = command("capture-pane", "-p", "-t", pane)
        block = picker_block(screen.splitlines())
        target = find_entry(block, model)
        highlighted = selected_index(block)
        if not block or target is None or highlighted is None:
            self._clear_picker(pane)
            raise RuntimeError("the client does not offer %s" % model_id(model))
        key, count = navigation(target, highlighted)
        for _ in range(count):
            command("send-keys", "-t", pane, key)
        time.sleep(0.2)
        command("send-keys", "-t", pane, "Enter")
        time.sleep(1.0)
        screen = command("capture-pane", "-p", "-t", pane)
        if not footer_shows(screen, model):
            if not effort_screen(screen):
                self._clear_picker(pane)
                raise RuntimeError("the client did not report %s" % model_id(model))
            # The scope key applies the change to this session only.
            command("send-keys", "-t", pane, "s")
            time.sleep(1.0)
            screen = command("capture-pane", "-p", "-t", pane)
        if not footer_shows(screen, model):
            self._clear_picker(pane)
            raise RuntimeError("the client did not report %s" % model_id(model))
        return footer_model(screen)

    def send(self, original, reply):
        if original.pane not in self.panes():
            raise RuntimeError("pane is excluded or no longer watched")
        current = self.snapshot(original.pane)
        if current != original or not current.ready:
            raise RuntimeError("pane changed before send; reply skipped")
        # Literal mode prevents reply text from being interpreted as tmux key names.
        command("send-keys", "-t", current.pane, "-l", "--", reply)
        # Codex batches rapid character input as paste; immediate Enter may be
        # absorbed into that paste instead of submitting the composer.
        time.sleep(0.5)
        after = self.snapshot(original.pane)
        if (after.process, after.pid, after.mode, after.dead) != (current.process, current.pid, "0", "0"):
            raise RuntimeError("client changed after typing; input left unsubmitted")
        command("send-keys", "-t", current.pane, "Enter")


def matches(pattern, values):
    pattern = pattern.casefold()
    if not any(char in pattern for char in "*?["):
        if pattern.startswith("%"):
            return pattern == values[0].casefold()
        return any(pattern in value.casefold() for value in values)
    return any(fnmatch.fnmatchcase(value.casefold(), pattern) for value in values)
