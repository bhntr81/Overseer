"""Host compatibility: the one module that branches on the operating system.

The factory, the loop, and the monitor need four things from the host: an
exclusive non-blocking file lock, a child started in a group of its own, a way
to tell whether that group still has a live process and to kill all of it, and
a bounded read of a child's output. POSIX supplies them with flock, sessions,
killpg, and select on a pipe. Native Windows supplies them with a byte-range
lock, a named job object (`overseer/winjob.py`), and a reader thread. Callers
use the functions here and never name fcntl or killpg themselves.

The tmux monitor and the pty single-program mode are not carried over: they
need tmux and POSIX terminals, and `require_posix` refuses them on Windows
with one line that names WSL2.
"""
import os
import queue
import re
import selectors
import signal
import subprocess
import threading
from types import SimpleNamespace

from overseer import winjob

WINDOWS = os.name == 'nt'

# Command-line actions that drive tmux or a pty.
TMUX_ACTIONS = frozenset({'run', 'status', 'watch', 'unwatch', 'start', 'here', 'model-select'})

# The gated launcher. The child cannot execute the task until its identity is
# durably saved; parent death before the one-byte release closes stdin and exits it.
_GATE = 'gate=sys.stdin.buffer.read(1); sys.exit(125) if gate != b"G" else None; '
_POSIX_LAUNCH = ('import os,sys; ' + _GATE +
                 'fd=os.open(os.devnull,os.O_RDONLY); os.dup2(fd,0); '
                 'os.execvpe(sys.argv[1],sys.argv[1:],os.environ)')
# Windows has no exec that keeps the process identity and exit status, so the
# launcher stays as the parent and passes the command's exit status through.
# It also opens the group's job by name: a job loses its name when its last
# handle closes, so this handle keeps the group findable after the controller dies.
# A launcher that cannot open it (the controller died first) refuses to run the task.
_WINDOWS_LAUNCH = ('import ctypes,os,subprocess,sys; ' + _GATE +
                   'held=ctypes.WinDLL("kernel32").OpenJobObjectW(4,0,"overseer-group-%d"%os.getpid()); '
                   'sys.exit(125) if not held else None; '
                   'sys.exit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))')
LAUNCH = _WINDOWS_LAUNCH if WINDOWS else _POSIX_LAUNCH


def require_posix(feature):
    """Refuse a tmux or pty feature on native Windows with one clear line."""
    if WINDOWS:
        raise RuntimeError('%s is not supported on native Windows (it needs tmux and a POSIX '
                           'terminal); run Overseer inside WSL2 for it' % feature)


# --- starting a command -----------------------------------------------------

# Windows starts a .cmd or .bat file through cmd.exe, which reads the command
# line by its own rules: a quote ends quoting, %NAME% is expanded even inside
# quotes, & | < > ^ ( ) ! are syntax, and a line break ends the line. No
# escaping makes arbitrary text safe there, so only arguments made of
# characters cmd.exe leaves alone are passed to such a file.
_BATCH = ('.cmd', '.bat')
_INERT = re.compile(r'[A-Za-z0-9 _./:\\=+@,~-]*')
_REFUSED, _MISSING = 126, 127


def prepare(argv, env, cwd):
    """Return (argv, refusal) for a command about to be started in `cwd` with `env`.

    POSIX: the command is returned as given. Windows: a program named without a
    directory is looked up on PATH with the PATHEXT extensions, as the shell
    does, and its full path replaces the name. `refusal` is None, or one line
    saying why nothing may be started: the program does not exist, or it is a
    .cmd or .bat file and an argument holds text cmd.exe would interpret.
    """
    if not WINDOWS:
        return argv, None
    program = _find(argv[0], env, cwd)
    if program is None:
        return argv, ('overseer: cannot start %r: no such program (looked on PATH with %s); '
                      'install it or give its full path' % (argv[0], _extensions(env)))
    argv = [program, *argv[1:]]
    if program.lower().endswith(_BATCH):
        for index, argument in enumerate(argv[1:], 1):
            if not _INERT.fullmatch(argument):
                return argv, ('overseer: refused to start %s: argument %d holds text that cmd.exe, '
                              'which runs a .cmd or .bat file, would interpret or cannot carry (a '
                              'quote, %%, &, a line break, or another character outside letters, '
                              'digits, spaces and _./:\\=+@,~-). Nothing was run. Install a native '
                              '.exe of this program, run it under WSL2, or name its interpreter and '
                              'script in the argument list.' % (program, index))
    return argv, None


def refusal_status(refusal):
    """The exit status recorded for a refusal: 127 not found, 126 not startable."""
    return _MISSING if 'no such program' in refusal else _REFUSED


def _extensions(env):
    return env.get('PATHEXT') or os.environ.get('PATHEXT') or '.COM;.EXE;.BAT;.CMD'


def _find(name, env, cwd):
    """Find a program as cmd.exe does: the directory given, else `cwd`, then PATH."""
    extensions = [item.lower() for item in _extensions(env).split(';') if item]
    if os.path.dirname(name):
        folders = [None]
    else:
        folders = [str(cwd)] + [item for item in (env.get('PATH') or '').split(os.pathsep) if item]
    for folder in folders:
        base = os.path.join(str(cwd), name) if folder is None else os.path.join(folder, name)
        exact = [base] if os.path.splitext(base)[1].lower() in extensions else []
        for candidate in exact + [base + extension for extension in extensions]:
            if os.path.isfile(candidate):
                return candidate
    return None


# --- the exclusive non-blocking lock ---------------------------------------

def lock(handle):
    """Take an exclusive lock on an open file, or raise BlockingIOError at once.

    The lock belongs to this open handle: a second handle, in this process or
    another, is refused until `unlock`, the handle's close, or the owner's death.
    """
    if WINDOWS:
        import msvcrt
        # A Windows lock covers a byte range, not the file. Byte 0 is the lock;
        # the range may lie past the end of an empty file.
        os.lseek(handle.fileno(), 0, os.SEEK_SET)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as error:
            raise BlockingIOError(error.errno, 'the lock is held') from None
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)


def unlock(handle):
    """Release a lock taken with `lock`."""
    if WINDOWS:
        import msvcrt
        os.lseek(handle.fileno(), 0, os.SEEK_SET)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_UN)


# --- process groups ---------------------------------------------------------

def popen_group(argv, **options):
    """Start a child in a group of its own, named by the child's pid.

    POSIX: a new session, so the pid is also the process group id. Windows: a
    job object named after the pid, which every descendant joins.
    """
    if not WINDOWS:
        return subprocess.Popen(argv, start_new_session=True, **options)
    child = subprocess.Popen(argv, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, **options)
    try:
        winjob.JOBS[child.pid] = winjob.adopt(child.pid)
    except OSError:
        child.kill()
        child.wait()
        raise
    return child


def group_alive(pid):
    """Report whether the group started as `pid` still has a live process."""
    if not WINDOWS:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    handle, owned = winjob.find(pid, winjob.QUERY)
    if not handle:
        return False
    try:
        return winjob.active(handle) > 0
    finally:
        if not owned:
            winjob.close(handle)


def kill_group(pid):
    """Kill every process of the group started as `pid`, grandchildren included.

    Raises ProcessLookupError when the group has no process left, as killpg does.
    """
    if not WINDOWS:
        os.killpg(pid, signal.SIGKILL)
        return
    handle, _ = winjob.find(pid, winjob.QUERY | winjob.TERMINATE)
    winjob.JOBS.pop(pid, None)
    if not handle:
        raise ProcessLookupError('no process group %d' % pid)
    try:
        active = winjob.active(handle)
        if active:
            winjob.terminate(handle)
    finally:
        winjob.close(handle)
    if not active:
        raise ProcessLookupError('no process group %d' % pid)


def terminate_group(pid):
    """Ask the group started as `pid` to stop: SIGTERM on POSIX, a kill on Windows."""
    if not WINDOWS:
        os.killpg(pid, signal.SIGTERM)
    elif pid in winjob.JOBS or group_alive(pid):
        kill_group(pid)
    else:
        # A child that was not started through popen_group has no job; end it alone.
        os.kill(pid, signal.SIGTERM)


# --- bounded reads of a child's output --------------------------------------

def output_selector(stream):
    """Return a selector with `stream` registered for reading.

    POSIX: the standard selector. Windows cannot select on a pipe, so a thread
    reads it and the same four calls (get_map, select, unregister, close) are
    served from a queue. Read a ready key with `read_ready`.
    """
    selector = _PipeSelector() if WINDOWS else selectors.DefaultSelector()
    selector.register(stream, selectors.EVENT_READ)
    return selector


def read_ready(key):
    """Return the bytes behind a ready key; empty bytes mean end of output."""
    chunk = getattr(key, 'chunk', None)
    return os.read(key.fileobj.fileno(), 65536) if chunk is None else chunk


class _PipeSelector:
    def __init__(self):
        self._chunks = queue.Queue(maxsize=16)
        self._streams = {}

    def register(self, stream, _events):
        self._streams[stream] = True
        threading.Thread(target=self._pump, args=(stream,), daemon=True).start()

    def _pump(self, stream):
        while True:
            try:
                chunk = os.read(stream.fileno(), 65536)
            except (OSError, ValueError):
                chunk = b''
            self._chunks.put((stream, chunk))
            if not chunk:
                return

    def get_map(self):
        return self._streams

    def select(self, timeout=None):
        try:
            stream, chunk = self._chunks.get(timeout=timeout)
        except queue.Empty:
            return []
        return [(SimpleNamespace(fileobj=stream, chunk=chunk), selectors.EVENT_READ)]

    def unregister(self, stream):
        self._streams.pop(stream, None)

    def close(self):
        # Unblock a reader thread that is waiting to hand over a chunk nobody wants.
        self._streams.clear()
        with self._chunks.mutex:
            self._chunks.queue.clear()
            self._chunks.not_full.notify_all()
