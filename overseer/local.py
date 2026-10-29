"""Run one client in this terminal and monitor it without tmux.

Overseer's tmux transport reads a pane and types into it. Single-program mode
keeps the same contract -- ``panes()``, ``snapshot()``, ``send()`` over
``tmux.Snapshot`` -- but the "pane" is the client this process started in the
user's own terminal. The client gets a pseudo-terminal, the driver relays the
user's bytes to it and its output back, and a screen model in
``overseer.terminal`` keeps what the monitor reads.

The wrapper owns the client: when it exits, the client exits. It is one
program, one terminal, with no tmux server, no project menu, and no routing.
"""

import atexit
import codecs
import errno
import fcntl
import json
import logging
import os
from pathlib import Path
import pty
import select
import signal
import struct
import sys
import termios
import threading
import time
import tty

from .policy import Policy
from .terminal import Screen
from .tmux import Snapshot


LOG = logging.getLogger("overseer")
PANE = "local"
POLL_GRACE = 0.2


def log_path():
    return Path.home() / ".local/state/overseer/local.log"


class PtyBackend:
    """One client process behind a pseudo-terminal, seen as a single pane."""

    def __init__(self, process, pid, master, screen, screen_lock, write_lock):
        self.process = process
        self.pid = pid
        self.master = master
        self.screen = screen
        self.screen_lock = screen_lock
        self.write_lock = write_lock
        self.exited = False

    def panes(self):
        return [] if self.exited else [PANE]

    def snapshot(self, pane=PANE):
        with self.screen_lock:
            text = self.screen.text()
            cursor_line = self.screen.cursor_line()
            cursor_x = self.screen.cursor_x
        return Snapshot(PANE, self.process, str(self.pid), text, cursor_line,
                        "0", "1" if self.exited else "0", cursor_x)

    def send(self, original, reply):
        if self.exited:
            raise RuntimeError("client has exited; nothing was sent")
        with self.write_lock:
            current = self.snapshot()
            if current != original or not current.ready:
                raise RuntimeError("screen changed before send; reply skipped")
            os.write(self.master, reply.encode("utf-8"))
            # A client that batches fast input as paste absorbs an immediate
            # Enter into that paste, so submit separately, as the tmux path does.
            time.sleep(0.5)
            after = self.snapshot()
            if (after.process, after.pid, after.mode, after.dead) != (
                    current.process, current.pid, "0", "0"):
                raise RuntimeError("client changed after typing; input left unsubmitted")
            os.write(self.master, b"\r")


def _load_state(path):
    if not path.exists():
        return {}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or any(not isinstance(value, dict) for value in state.values()):
        raise ValueError("invalid state file; inspect it before restarting")
    return state


def _configure_logging():
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, force=True, filename=str(path),
                        format="%(asctime)s %(levelname)s %(message)s")
    return path


def _monitor(backend, config_path, state_path, state, settings, tick, save, stop):
    """Poll the screen and apply the same policy the tmux monitor applies."""
    while not stop.is_set():
        try:
            config = dict(settings(config_path))
            # Single-program mode has one pane in this process, so the durable
            # FIFO and its routing (which reaches tmux) do not apply here.
            config["serial_queue"] = False
            policy = Policy(config["idle_seconds"], config["cooldown_seconds"],
                            config["max_per_day"], config.get("continue_on_completion", False))
            tick(backend, policy, state, config, state_path, time.time())
        except (RuntimeError, OSError, ValueError) as error:
            LOG.warning("monitor cycle: %s", error)
        stop.wait(max(1, _poll_seconds(config_path, settings)))


def _poll_seconds(config_path, settings):
    try:
        return settings(config_path)["poll_seconds"]
    except (OSError, ValueError):
        return 30


def _relay(stdin, master, screen, screen_lock, write_lock, stop, resize):
    """Copy the user's bytes to the client and its output back to the terminal.

    The client's queries reach the real terminal unchanged and its replies come
    back through the same path, so no query is answered here.
    """
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    wake = signal.set_wakeup_fd(-1)
    wake_r, wake_w = os.pipe()
    os.set_blocking(wake_r, False)
    os.set_blocking(wake_w, False)
    previous_wakeup = wake
    signal.set_wakeup_fd(wake_w)
    try:
        while not stop.is_set():
            try:
                readable, _, _ = select.select([stdin, master, wake_r], [], [], 1.0)
            except InterruptedError:
                continue
            if wake_r in readable:
                try:
                    while os.read(wake_r, 4096):
                        pass
                except BlockingIOError:
                    pass
            if resize.is_set():
                resize.clear()
                _resize(stdin, master, screen, screen_lock)
            if stdin in readable:
                try:
                    data = os.read(stdin, 4096)
                except OSError:
                    data = b""
                if not data:
                    stop.set()
                    break
                with write_lock:
                    os.write(master, data)
            if master in readable:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno not in {errno.EIO, errno.EBADF}:
                        raise
                    data = b""
                if not data:
                    break
                view = memoryview(data)
                while view:
                    written = os.write(1, view)
                    view = view[written:]
                with screen_lock:
                    screen.feed(decoder.decode(data))
    finally:
        signal.set_wakeup_fd(previous_wakeup)
        os.close(wake_r)
        os.close(wake_w)


def _resize(stdin, master, screen, screen_lock):
    try:
        size = os.get_terminal_size(stdin)
    except OSError:
        return
    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ,
                    struct.pack("HHHH", size.lines, size.columns, 0, 0))
    except OSError:
        return
    with screen_lock:
        screen.resize(size.columns, size.lines)


def run_attached(client, client_args, config_path, state_path, cwd, settings, tick, save):
    """Run `client` in this terminal under the monitor. Return its exit status."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("single-program mode needs a terminal on stdin and stdout")
    process = Path(client).name
    if process not in {"codex", "claude", "opencode"}:
        raise RuntimeError("single-program mode watches codex, claude, or opencode")
    config = settings(config_path)
    if config.get("dry_run"):
        LOG.info("single-program mode is a dry run; no prompt is typed")
    directory = Path(cwd).resolve()
    if not directory.is_dir():
        raise RuntimeError("not a directory: %s" % directory)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    lock = state_path.with_suffix(".lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise RuntimeError("another monitor is already using this state file")
    state = _load_state(state_path)
    logfile = _configure_logging()

    size = os.get_terminal_size(0)
    columns, rows = size.columns, size.lines
    screen = Screen(columns, rows)
    screen_lock = threading.Lock()
    write_lock = threading.Lock()
    stop = threading.Event()
    resize = threading.Event()

    pid, master = pty.fork()
    if pid == 0:
        try:
            fcntl.ioctl(0, termios.TIOCSWINSZ,
                        struct.pack("HHHH", rows, columns, 0, 0))
            os.chdir(directory)
            os.execvpe(client, [client, *client_args], os.environ)
        except BaseException as error:
            try:
                os.write(2, ("overseer: cannot start %s: %s\r\n" % (client, error)).encode())
            finally:
                os._exit(127)

    backend = PtyBackend(process, pid, master, screen, screen_lock, write_lock)
    original = termios.tcgetattr(0)
    restored = threading.Event()

    def restore():
        if restored.is_set():
            return
        restored.set()
        try:
            termios.tcsetattr(0, termios.TCSADRAIN, original)
        except OSError:
            pass

    def terminate(signum, frame):
        stop.set()
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    def resized(signum, frame):
        resize.set()

    atexit.register(restore)
    signal.signal(signal.SIGWINCH, resized)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGHUP, terminate)
    monitor = threading.Thread(target=_monitor, name="overseer-monitor", daemon=True,
                               args=(backend, config_path, state_path, state, settings,
                                     tick, save, stop))
    exit_status = None
    try:
        tty.setraw(0)
        monitor.start()
        LOG.info("single-program monitor started; client=%s pid=%s state=%s",
                 process, pid, state_path)
        _relay(0, master, screen, screen_lock, write_lock, stop, resize)
        while True:
            done, status = os.waitpid(pid, 0)
            if done == pid:
                exit_status = os.waitstatus_to_exitcode(status)
                break
    finally:
        stop.set()
        backend.exited = True
        restore()
        atexit.unregister(restore)
        try:
            os.close(master)
        except OSError:
            pass
        monitor.join(timeout=5)
        if exit_status is None:
            try:
                _, status = os.waitpid(pid, 0)
                exit_status = os.waitstatus_to_exitcode(status)
            except ChildProcessError:
                exit_status = 0
        lock.close()
        sys.stdout.write("\r\n")
        sys.stdout.flush()
        print("Overseer attached session ended (exit %s); log: %s; state: %s"
              % (exit_status, logfile, state_path))
    return exit_status
