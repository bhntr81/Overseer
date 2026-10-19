import argparse
import fcntl
import json
import logging
import os
from pathlib import Path
import shlex
import signal
import sys
import time

from .policy import DEFAULT_REPLY, Policy
from .tmux import Tmux, command


ROOT = Path(__file__).resolve().parents[1]
STATE = Path.home() / ".local/state/overseer/state.json"
LOG = logging.getLogger("overseer")


def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        os.chmod(temporary, 0o600)
        json.dump(state, handle)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def settings(path):
    config = json.loads(path.read_text(encoding="utf-8"))
    for field in ("poll_seconds", "idle_seconds", "cooldown_seconds", "max_per_day"):
        if type(config.get(field)) is not int or config[field] < 1:
            raise ValueError(f"{field} must be a positive integer")
    if type(config.get("dry_run")) is not bool:
        raise ValueError("dry_run must be a boolean")
    if type(config.get("continue_on_completion", False)) is not bool:
        raise ValueError("continue_on_completion must be a boolean")
    if type(config.get("serial_queue", False)) is not bool:
        raise ValueError("serial_queue must be a boolean")
    for field, default in (("capacity_retry_seconds", 120), ("capacity_max_retries", 3)):
        if type(config.get(field, default)) is not int or config.get(field, default) < 1:
            raise ValueError(f"{field} must be a positive integer")
    if not isinstance(config.get("exclude", []), list) or any(not isinstance(v, str) or not v.strip() for v in config.get("exclude", [])):
        raise ValueError("exclude must be a list of nonempty patterns")
    reply = config.get("reply", DEFAULT_REPLY)
    if not isinstance(reply, str) or not reply.strip() or len(reply) > 1000 or any(ord(c) < 32 or ord(c) == 127 for c in reply):
        raise ValueError("reply must be one nonempty line, at most 1000 characters")
    config["reply"] = reply
    return config


def tick(backend, policy, state, config, path, now):
    if config.get("serial_queue", False):
        from .scheduler import tick_queue
        return tick_queue(backend, policy, state, config, path, now, save)
    for pane in backend.panes():
        try:
            snapshot = backend.snapshot(pane)
            # Include pane process identity, so a replacement session starts fresh.
            key = f"{pane}:{snapshot.pid}"
            entry = state.setdefault(key, {})
            if not snapshot.ready:
                entry.pop("fingerprint", None)
                continue
            eligible, reason = policy.consider(entry, snapshot.text, now)
            if not eligible:
                LOG.debug("%s skipped: %s", pane, reason)
                continue
            if config["dry_run"]:
                if entry.get("previewed") != entry["fingerprint"]:
                    LOG.info("%s would send routine continuation (dry run)", pane)
                    entry["previewed"] = entry["fingerprint"]
                continue
            # Reserve before interacting. An interrupted/failed send is not retried
            # automatically, because delivery may have happened before a crash.
            policy.acknowledge(entry, snapshot.text, now)
            save(path, state)
            backend.send(snapshot, config["reply"])
            LOG.info("%s sent routine continuation", pane)
        except (RuntimeError, OSError, ValueError) as error:
            LOG.warning("%s: %s", pane, error)
    save(path, state)


def run(args):
    config = settings(args.config)
    args.state.parent.mkdir(parents=True, exist_ok=True)
    with args.state.with_suffix(".lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("another monitor is already using this state file")
        # Fail closed on corrupt state instead of losing duplicate-send history.
        state = json.loads(args.state.read_text()) if args.state.exists() else {}
        if not isinstance(state, dict) or any(not isinstance(v, dict) for v in state.values()):
            raise ValueError("invalid state file; inspect it before restarting")
        policy = Policy(config["idle_seconds"], config["cooldown_seconds"], config["max_per_day"], config.get("continue_on_completion", False))
        backend = Tmux(config.get("exclude", []))
        stopped = False

        def stop(signum, frame):
            nonlocal stopped
            stopped = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        LOG.info("monitor started; dry_run=%s; poll=%ss", config["dry_run"], config["poll_seconds"])
        while not stopped:
            try:
                config = settings(args.config)
                backend.exclusions = config.get("exclude", [])
                policy = Policy(config["idle_seconds"], config["cooldown_seconds"], config["max_per_day"], config.get("continue_on_completion", False))
                tick(backend, policy, state, config, args.state, time.time())
            except (RuntimeError, OSError, ValueError) as error:
                LOG.warning("monitor cycle: %s", error)
            if args.once:
                break
            for _ in range(config["poll_seconds"]):
                if stopped:
                    break
                time.sleep(1)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Watch opted-in tmux LLM panes for routine continuation prompts.")
    sub = parser.add_subparsers(dest="action", required=True)
    monitor = sub.add_parser("run")
    monitor.add_argument("--config", type=Path, default=ROOT / "config.json")
    monitor.add_argument("--state", type=Path, default=STATE)
    monitor.add_argument("--once", action="store_true")
    sub.add_parser("status")
    for name in ("exclude", "include"):
        exclusion = sub.add_parser(name)
        exclusion.add_argument("pattern", help="pane ID, session/title substring, or quoted glob")
    for name in ("watch", "unwatch"):
        target = sub.add_parser(name)
        target.add_argument("pane", help="tmux pane ID, e.g. %%0")
    start = sub.add_parser("start")
    start.add_argument("name", help="new tmux session name")
    start.add_argument("--cwd", type=Path, default=Path.cwd())
    start.add_argument("client", choices=["codex", "claude"])
    start.add_argument("client_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.action == "run":
            return run(args)
        if args.action == "status":
            config = settings(ROOT / "config.json")
            print("Mode: " + ("dry run" if config["dry_run"] else "automatic replies"))
            print("Exclusions: " + ", ".join(config.get("exclude", [])))
            print("FIFO queue: " + ("enabled" if config.get("serial_queue", False) else "disabled"))
            if config.get("serial_queue", False):
                state = json.loads(STATE.read_text()) if STATE.exists() else {}
                queue = state.get("_queue", {})
                active = queue.get("active")
                print("Active reservation: " + (active['key'] if active else "none"))
                for index, key in enumerate(queue.get("waiting", []), 1):
                    entry = state.get(key, {})
                    timing = ''
                    if entry.get('queue_kind') == 'capacity':
                        retry_at = max(entry.get('stable_since', 0), entry.get('last_sent', 0)) + config.get('capacity_retry_seconds', 120)
                        timing = f"; retry delay remaining {max(0, int(retry_at - time.time()))}s"
                    print(f"Queue {index}: {key} — {entry.get('queue_reason', 'waiting')}{timing}")
                for key, entry in state.items():
                    if entry.get('queue_reason', '').startswith('capacity retry limit'):
                        print(f"Blocked {key}: {entry['queue_reason']}")
            for row in Tmux(config.get("exclude", [])).inventory():
                status = "EXCLUDED" if row["excluded"] else "WATCHED" if row["enabled"] else "OFF"
                print(f"{row['pane']} {status}: {row['session']} — {row['title']}")
        elif args.action in {"exclude", "include"}:
            path = ROOT / "config.json"
            config = settings(path)
            patterns = config.setdefault("exclude", [])
            if args.action == "exclude" and args.pattern not in patterns:
                patterns.append(args.pattern)
            elif args.action == "include":
                config["exclude"] = [v for v in patterns if v.casefold() != args.pattern.casefold()]
            save(path, config)
            print(f"{args.action}: {args.pattern}; applied at the next poll (within {config['poll_seconds']} seconds)")
        elif args.action in {"watch", "unwatch"}:
            pane = command("display-message", "-p", "-t", args.pane, "#{pane_id}").strip()
            command("set-option", "-p", "-t", pane, "@overseer", "1" if args.action == "watch" else "0")
            print(f"{args.action}: {pane}")
        elif args.action == "start":
            shell_command = shlex.join([args.client, *args.client_args])
            pane = command("new-session", "-d", "-P", "-F", "#{pane_id}", "-s", args.name,
                           "-c", str(args.cwd.resolve()), shell_command).strip()
            command("set-option", "-p", "-t", pane, "@overseer", "1")
            print(f"Started and watching {pane}. Attach: tmux attach-session -t {shlex.quote(args.name)}")
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        LOG.error("%s", error)
        return 1


if __name__ == "__main__":
    sys.exit(main())
