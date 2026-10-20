"""Moving work from one client to another.

A route creates a new session for a different client in the same working
directory and enrolls it. It never sends keys to, restarts, kills, or
re-creates an existing session, pane, bridge, or client.
"""
import os
from pathlib import Path
import shlex

from .modelchoice import provider_table
from .tmux import command

# Clients that take the initial prompt as a positional argument.
POSITIONAL = ("codex", "claude", "grok")


def pane_binding(pane):
    """Return the reptyr binding of a pane, or an empty string."""
    return command("display-message", "-p", "-t", pane, "#{@overseer_target}").strip()


def working_directory(pane):
    """Return the working directory of the client that runs in a pane.

    A reptyr-bridged pane reports the bridge's directory, so the client's own
    directory is read from the bridged process instead.
    """
    binding = pane_binding(pane)
    if binding:
        target = binding.split(":")[0]
        try:
            return os.readlink("/proc/%s/cwd" % target)
        except OSError:
            pass
    return command("display-message", "-p", "-t", pane, "#{pane_current_path}").strip()


def session_name(pane):
    """Return the session name of a pane."""
    return command("display-message", "-p", "-t", pane, "#{session_name}").strip()


def client_argv(client, prompt=None):
    """Build the client command, with the initial prompt in the client's own form."""
    if not prompt:
        return [client]
    if client in POSITIONAL:
        return [client, prompt]
    return [client, "--prompt", prompt]


def start_session(name, client, directory, prompt=None):
    """Start a session for a client and enroll its pane. Return the pane id."""
    shell_command = shlex.join(client_argv(client, prompt))
    pane = command("new-session", "-d", "-P", "-F", "#{pane_id}", "-s", name,
                   "-c", str(Path(directory)), shell_command).strip()
    command("set-option", "-p", "-t", pane, "@overseer", "1")
    return pane


def route(pane, client, directory, prompt=None, suffix=None):
    """Move a pane's work to a new session running another client.

    The new session is named after the old one, enrolls itself, and is
    returned with its pane id. The original pane is left untouched.
    """
    base = session_name(pane) or "overseer"
    name = "%s-%s" % (base, suffix or client)
    new_pane = start_session(name, client, directory, prompt)
    return {"pane": new_pane, "session": name, "client": client}


def resolve_route(pane, provider, config):
    """Move a pane's work to the client of a provider and describe the move."""
    entry = provider_table(config).get(provider)
    if not isinstance(entry, dict):
        raise ValueError("provider %s is not configured" % provider)
    client = entry.get("client")
    if not isinstance(client, str) or not client:
        raise ValueError("provider %s has no client" % provider)
    directory = working_directory(pane)
    if not directory:
        raise ValueError("cannot read the working directory of %s" % pane)
    moved = route(pane, client, directory)
    moved.update({"provider": provider, "directory": directory, "model": "default"})
    return moved
