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

from . import blueprint, configfile
from . import provider
from . import sizing
from . import usageguard
from .escalation import adopt, release
from .halt import clear, note, read_state, render
from .modelchoice import RESOLUTIONS, model_id, opencode_empty, providers, running_marker
from .policy import DEFAULT_REPLY, Policy, hold, next_prompt
from . import stopgate
from .route import resolve_route
from .tmux import CLIENTS, Tmux, command


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
    config = json.loads(configfile.read_text(path))
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
    if not isinstance(config.get("targets", []), list) or any(not isinstance(v, str) or not v.strip() for v in config.get("targets", [])):
        raise ValueError("targets must be a list of nonempty patterns")
    if not isinstance(config.get("target_paths", []), list) or any(not isinstance(v, str) or not v.strip() for v in config.get("target_paths", [])):
        raise ValueError("target_paths must be a list of nonempty paths")
    # A relative target path is resolved against the workspace that holds the
    # configuration, so "." means this project.
    config["target_paths"] = [str((path.parent / item).resolve()) if not Path(item).is_absolute() else item
                              for item in config.get("target_paths", [])]
    reply = config.get("reply", DEFAULT_REPLY)
    if not isinstance(reply, str) or not reply.strip() or len(reply) > 1000 or any(ord(c) < 32 or ord(c) == 127 for c in reply):
        raise ValueError("reply must be one nonempty line, at most 1000 characters")
    config["reply"] = reply
    return config


def decisions(path):
    """Read the monitor's model decision records."""
    try:
        data = json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        return {}
    records = data.get("_model_decisions")
    return records if isinstance(records, dict) else {}


def pending_decisions(path):
    """Return the decisions that still need an operator choice."""
    return {pane: record for pane, record in decisions(path).items()
            if isinstance(record, dict) and not isinstance(record.get("resolved"), dict)}


def resolve_decision(path, pane, record, provider, model, moved=None):
    """Record the operator's choice where the monitor will read it."""
    target = path.parent / RESOLUTIONS
    data = {}
    if target.exists():
        try:
            data = json.loads(target.read_text())
        except (OSError, ValueError):
            data = {}
    if not isinstance(data, dict):
        data = {}
    data[pane] = {"key": record.get("key"), "provider": provider, "model": model, "at": time.time()}
    if moved:
        data[pane]["route"] = moved
    save(target, data)


def ask_provider(allowlist, record):
    """Ask the operator which permitted provider to use."""
    print("Model decision pending: %s (%s)" % (record.get("name"), record.get("detail")))
    print("Permitted providers:")
    for index, entry in enumerate(allowlist, 1):
        models = [model_id(model) for model in entry["models"]]
        summary = ", ".join(models) if len(models) <= 6 else "%d models" % len(models)
        print("  %d) %s (%s) - %s" % (index, entry["id"], entry["label"], summary))
    print("Choose a provider (number or id). Press enter to cancel:")
    line = sys.stdin.readline()
    answer = line.strip() if line else ""
    if not answer:
        return None
    if answer.isdigit():
        number = int(answer)
        if 1 <= number <= len(allowlist):
            return allowlist[number - 1]["id"]
        print("no such provider", file=sys.stderr)
        return None
    return answer


def ask_model(entry):
    """Ask the operator which model of the chosen provider to use."""
    print("Models for %s:" % entry["id"])
    for index, model in enumerate(entry["models"], 1):
        print("  %d) %s" % (index, model_id(model)))
    print("Choose a model (number or id). Press enter for %s:" % model_id(entry["models"][0]))
    line = sys.stdin.readline()
    answer = line.strip() if line else ""
    if not answer:
        return model_id(entry["models"][0])
    if answer.isdigit():
        number = int(answer)
        if 1 <= number <= len(entry["models"]):
            return model_id(entry["models"][number - 1])
        print("no such model", file=sys.stderr)
        return None
    return answer


def model_select(args):
    """Show a pending model decision and apply the operator's choice."""
    config = settings(configfile.default_path(ROOT))
    allowlist = providers(config)
    pending = pending_decisions(args.state)
    if not args.pane:
        if not pending:
            print("No model decision is pending.")
            return 0
        for pane, record in sorted(pending.items()):
            print("%s: %s (%s) - providers: %s" % (
                pane, record.get("name"), record.get("detail"),
                ", ".join(record.get("providers") or [])))
            print("  resolve with: python3 -m overseer model-select %s" % pane)
        return 0
    record = pending.get(args.pane)
    if record is None:
        print("No model decision is pending for %s." % args.pane, file=sys.stderr)
        return 1
    choice = args.provider
    if not choice:
        choice = ask_provider(allowlist, record)
        if not choice:
            print("cancelled; nothing was changed")
            return 1
    entry = next((item for item in allowlist if item["id"] == choice), None)
    if entry is None:
        print("Provider %s is not permitted." % choice, file=sys.stderr)
        return 1
    backend = Tmux(config.get("exclude", []), config.get("targets", []),
                  config.get("target_paths", []))
    try:
        snapshot = backend.inspect(args.pane)
    except (RuntimeError, OSError, ValueError) as error:
        print("Cannot read %s: %s" % (args.pane, error), file=sys.stderr)
        return 1
    if snapshot.process != entry["client"]:
        # The client differs, so the work moves instead of the model changing.
        if entry["client"] not in CLIENTS:
            print("The monitor cannot watch %s sessions yet, so %s cannot be used here." % (
                entry["client"], entry["id"]))
            return 1
        try:
            moved = resolve_route(args.pane, entry["id"], config)
        except (RuntimeError, OSError, ValueError) as error:
            print("Routing failed: %s" % error, file=sys.stderr)
            return 1
        resolve_decision(args.state, args.pane, record, entry["id"],
                         moved.get("model", "default"), moved)
        print("Routed %s to %s in session %s (pane %s) at %s." % (
            args.pane, entry["id"], moved["session"], moved["pane"], moved.get("directory")))
        return 0
    model = args.model
    if not model:
        model = ask_model(entry)
    if not model:
        print("cancelled; nothing was changed")
        return 1
    if model not in [model_id(item) for item in entry["models"]]:
        print("Model %s is not in the permitted list for %s." % (model, entry["id"]), file=sys.stderr)
        return 1
    try:
        reported = backend.select_model(args.pane, model)
    except (RuntimeError, OSError, ValueError) as error:
        print("Model change failed: %s" % error, file=sys.stderr)
        return 1
    resolve_decision(args.state, args.pane, record, entry["id"], model)
    print("Applied %s/%s to %s. The client now reports %s." % (
        entry["id"], model, args.pane, reported))
    return 0


def tick(backend, policy, state, config, path, now):
    adopt(state, path)
    if config.get("serial_queue", False):
        from .scheduler import tick_queue
        return tick_queue(backend, policy, state, config, path, now, save)
    for pane in backend.panes():
        try:
            snapshot = backend.snapshot(pane)
            # Include pane process identity, so a replacement session starts fresh.
            key = f"{pane}:{snapshot.pid}"
            entry = state.setdefault(key, {})
            if running_marker(snapshot.text):
                # A running turn is never answered, and it proves a turn ran.
                entry["ran_turn"] = True
                entry.pop("fingerprint", None)
                continue
            if not snapshot.ready:
                entry.pop("fingerprint", None)
                continue
            # Usage guard: when the account's most-constrained limit is nearly
            # spent, send one wind-down instruction and then hold, so the worker
            # reaches a clean stop instead of being cut off mid-change. The flag
            # is per pane-process (the key carries the pid), so a fresh session
            # starts ungated.
            winddown_at = config.get("usage_winddown_percent", usageguard.DEFAULT_THRESHOLD_PERCENT)
            if usageguard.should_wind_down(snapshot.text, winddown_at):
                if entry.get("wound_down"):
                    note(entry, "usage wind-down already sent; holding", snapshot.text, pane, now)
                    continue
                if config["dry_run"]:
                    LOG.info("%s would send usage wind-down (dry run)", pane)
                    entry["wound_down"] = True
                    continue
                policy.acknowledge(entry, snapshot.text, now)
                entry["wound_down"] = True
                save(path, state)
                backend.send(snapshot, usageguard.winddown_prompt())
                clear(entry)
                LOG.info("%s sent usage wind-down (<= %d%% remaining)", pane, winddown_at)
                continue
            completed = (snapshot.process == "opencode" and opencode_empty(snapshot.cursor_line)
                         and bool(entry.get("ran_turn")))
            eligible, reason = policy.consider(entry, snapshot.text, now, completed=completed)
            if not eligible:
                stopgate.review(entry, snapshot.text, reason, config, now, pane)
                note(entry, reason, snapshot.text, pane, now)
                LOG.debug("%s skipped: %s", pane, reason)
                continue
            prompt, kind = stopgate.prompt_for(
                entry, snapshot.text, lambda: next_prompt(snapshot.text, config.get("reply", DEFAULT_REPLY)))
            if prompt is None:
                hold(entry, snapshot.text, kind)
                note(entry, kind, snapshot.text, pane, now)
                LOG.info("%s skipped: %s", pane, kind)
                continue
            if config["dry_run"]:
                if entry.get("previewed") != entry["fingerprint"]:
                    action = kind if kind in {"report-based prompt", "writer handoff prompt"} else "routine continuation"
                    LOG.info("%s would send %s (dry run)", pane, action)
                    entry["previewed"] = entry["fingerprint"]
                continue
            # Reserve before interacting. An interrupted/failed send is not retried
            # automatically, because delivery may have happened before a crash.
            policy.acknowledge(entry, snapshot.text, now)
            save(path, state)
            backend.send(snapshot, prompt)
            clear(entry)
            if kind == stopgate.OVERRIDE_KIND:
                stopgate.sent(entry)
            if kind in {"report-based prompt", "writer handoff prompt", stopgate.OVERRIDE_KIND}:
                LOG.info("%s sent %s", pane, kind)
            else:
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
        backend = Tmux(config.get("exclude", []), config.get("targets", []),
                      config.get("target_paths", []))
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
                backend.targets = config.get("targets", [])
                backend.target_paths = config.get("target_paths", [])
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
    parser = argparse.ArgumentParser(description="Watch opted-in tmux LLM panes, read output reports, and submit the next prompt.")
    sub = parser.add_subparsers(dest="action", required=True)
    monitor = sub.add_parser("run")
    monitor.add_argument("--config", type=Path, default=configfile.default_path(ROOT))
    monitor.add_argument("--state", type=Path, default=STATE)
    monitor.add_argument("--once", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--state", type=Path, default=STATE)
    for name in ("exclude", "include"):
        exclusion = sub.add_parser(name)
        exclusion.add_argument("pattern", help="pane ID, session/title substring, or quoted glob")
    for name in ("watch", "unwatch"):
        target = sub.add_parser(name)
        target.add_argument("pane", help="tmux pane ID, e.g. %%0")
    start = sub.add_parser("start")
    start.add_argument("name", help="new tmux session name")
    start.add_argument("--cwd", type=Path, default=Path.cwd())
    start.add_argument("client", nargs="?", choices=["codex", "claude", "opencode"],
                       default=None, help="client to run; defaults to the launching LLM session")
    start.add_argument("client_args", nargs=argparse.REMAINDER)
    here = sub.add_parser("here", help="run one client in this terminal, without tmux")
    here.add_argument("--config", type=Path, default=configfile.default_path(ROOT))
    here.add_argument("--state", type=Path, default=None,
                      help="state file (default: ~/.local/state/overseer/local-<pid>.json)")
    here.add_argument("--cwd", type=Path, default=Path.cwd())
    here.add_argument("client", nargs="?", choices=["codex", "claude", "opencode"],
                      default=None, help="client to run; defaults to the launching LLM session")
    here.add_argument("client_args", nargs=argparse.REMAINDER)
    select = sub.add_parser("model-select")
    select.add_argument("pane", nargs="?", help="tmux pane ID, e.g. %%0")
    select.add_argument("--provider", help="permitted provider id")
    select.add_argument("--model", help="model id within that provider")
    select.add_argument("--state", type=Path, default=STATE)
    unfreeze = sub.add_parser("unfreeze")
    unfreeze.add_argument("pane", help="tmux pane ID, e.g. %%0")
    unfreeze.add_argument("--state", type=Path, default=STATE)
    size = sub.add_parser("assess", help="size an objective: tier, steps, repairs, model, budget")
    size.add_argument("description", help="the objective in plain words")
    size.add_argument("--set", action="append", default=[], metavar="DIMENSION=N",
                      help="override a dimension (%s) with 0 to 3" % ", ".join(sizing.DIMENSIONS))
    size.add_argument("--json", action="store_true")
    size.add_argument("--plan", action="store_true", help="also write out the steps and their iterations")
    size.add_argument("--steps", help="comma-separated step names to use instead of the tier's template")
    progress = sub.add_parser("progress", help="evaluate a saved step plan (the .plan.json beside the ledger)")
    progress.add_argument("plan_file", type=Path)
    progress.add_argument("--json", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if args.action == "run":
            return run(args)
        if args.action == "status":
            config = settings(configfile.default_path(ROOT))
            state = read_state(args.state)
            print("Mode: " + ("dry run" if config["dry_run"] else "automatic replies"))
            print("Exclusions: " + ", ".join(config.get("exclude", [])))
            print("FIFO queue: " + ("enabled" if config.get("serial_queue", False) else "disabled"))
            if config.get("serial_queue", False):
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
            backend = Tmux(config.get("exclude", []), config.get("targets", []),
                           config.get("target_paths", []))
            for row in backend.inventory():
                print(f"{row['pane']} {backend.scope(row)}: {row['session']} — {row['title']}")
            for pane, record in sorted(pending_decisions(args.state).items()):
                print(f"{pane} MODEL DECISION PENDING: {record.get('name')} "
                      f"({record.get('detail')}) — providers: "
                      f"{', '.join(record.get('providers') or [])}")
                print(f"  resolve with: python3 -m overseer model-select {pane}")
            for line in render(state):
                print(line)
        elif args.action in {"exclude", "include"}:
            path = configfile.default_path(ROOT)
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
        elif args.action == "assess":
            overrides = {}
            for item in args.set:
                name, _, value = item.partition("=")
                if not value.isdigit():
                    raise ValueError("--set takes DIMENSION=N, got %r" % item)
                overrides[name] = int(value)
            result = sizing.assess(args.description, overrides)
            steps = None
            if args.plan or args.steps:
                names = [n.strip() for n in args.steps.split(",")] if args.steps else None
                steps = blueprint.make_plan(result, names)
            if args.json:
                data = result.as_dict()
                if steps:
                    data["plan"] = steps
                print(json.dumps(data, indent=2))
            else:
                print(sizing.render(result))
                if steps:
                    print(blueprint.render_plan(steps))
        elif args.action == "progress":
            saved = json.loads(args.plan_file.read_text())["plan"]
            evaluation = blueprint.evaluate(saved)
            print(json.dumps(evaluation, indent=2) if args.json else
                  blueprint.render_plan(saved) + "\n" + blueprint.render_evaluation(evaluation))
        elif args.action == "model-select":
            return model_select(args)
        elif args.action == "unfreeze":
            data = json.loads(args.state.read_text()) if args.state.exists() else {}
            if isinstance(data, dict) and release(data, args.pane, args.state):
                print("unfreeze: %s; applied at the next poll (within %d seconds)"
                      % (args.pane, settings(configfile.default_path(ROOT))["poll_seconds"]))
                return 0
            print("No hold is recorded for %s." % args.pane, file=sys.stderr)
            return 1
        elif args.action == "here":
            from .local import run_attached
            client = args.client or provider.default_runner()
            state = args.state or (Path.home() / ".local/state/overseer"
                                   / ("local-%d.json" % os.getpid()))
            return run_attached(client, args.client_args, args.config, state,
                                args.cwd, settings, tick, save)
        elif args.action == "start":
            # Default to the client of the LLM session that launched Overseer, so
            # running it from Claude Code starts a claude worker; free OpenCode
            # only when no session is detected.
            client = args.client or provider.default_runner()
            shell_command = shlex.join([client, *args.client_args])
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
