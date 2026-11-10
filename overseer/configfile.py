"""Reading the local configuration file.

`config.json` is the operator's local, git-ignored configuration. The public,
checked-in `config.example.json` is the template for it. This module only
reads: it never creates, copies, or rewrites a configuration file, so an
existing `config.json` is never replaced.
"""
import os
from pathlib import Path


def default_path(root):
    """The configuration file: $OVERSEER_CONFIG when set and not empty, else <root>/config.json."""
    chosen = os.environ.get("OVERSEER_CONFIG")
    return Path(chosen) if chosen else Path(root) / "config.json"


def read_text(path):
    """Return the configuration file's text, or explain how to create it."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise ValueError(
            "configuration file not found: %s. Create it from the public example "
            "(copy config.example.json to config.json, then edit it); Overseer "
            "never creates or overwrites config.json itself." % path) from None
