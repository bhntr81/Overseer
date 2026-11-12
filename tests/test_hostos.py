"""The host compatibility layer: the lock, process groups, and the POSIX-only gate.

Every test here runs on Linux and on native Windows; none is skipped by platform.
"""
import contextlib
import io
import logging
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from overseer import hostos

ROOT = Path(__file__).resolve().parents[1]
ENV = dict(os.environ, PYTHONPATH=str(ROOT))

TRY_LOCK = '''
import sys
from overseer import hostos
with open(sys.argv[1], 'a') as handle:
    try:
        hostos.lock(handle)
    except BlockingIOError:
        print('busy')
    else:
        print('held')
        hostos.unlock(handle)
'''

HOLD_LOCK = '''
import sys, time
from overseer import hostos
handle = open(sys.argv[1], 'a')
hostos.lock(handle)
print('held', flush=True)
time.sleep(120)
'''

# The child starts a grandchild that shares its stdout, reports, then waits or leaves.
FAMILY = '''
import subprocess, sys, time
subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], stdout=sys.stdout)
print('ready', flush=True)
if sys.argv[1] == 'stay':
    time.sleep(120)
'''


# A controller starts a gated task in its own group, releases it, reports, and waits to be killed.
CONTROLLER = '''
import subprocess, sys, time
from overseer import hostos
child = hostos.popen_group([sys.executable, '-c', hostos.LAUNCH, sys.executable, '-c',
                            'import time; print("task", flush=True); time.sleep(120)'],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE)
child.stdin.write(b'G')
child.stdin.flush()
child.stdout.readline()
print(child.pid, flush=True)
time.sleep(120)
'''


def python(code, *args, **kwargs):
    return subprocess.run([sys.executable, '-c', code, *args], cwd=ROOT, env=ENV,
                          capture_output=True, text=True, timeout=60, **kwargs)


def closes_within(stream, seconds):
    """True when every holder of the pipe is gone, so a read reaches end of file."""
    done = threading.Event()

    def drain():
        with contextlib.suppress(OSError, ValueError):
            while stream.read(4096):
                pass
        done.set()

    threading.Thread(target=drain, daemon=True).start()
    return done.wait(seconds)


class LockTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = str(Path(self.temporary.name) / 'ledger.lock')

    def test_a_second_process_cannot_take_a_held_lock_and_can_after_release(self):
        with open(self.path, 'a') as handle:
            hostos.lock(handle)
            self.assertEqual(python(TRY_LOCK, self.path).stdout.strip(), 'busy')
            hostos.unlock(handle)
            self.assertEqual(python(TRY_LOCK, self.path).stdout.strip(), 'held')

    def test_a_second_handle_in_the_same_process_cannot_take_a_held_lock(self):
        with open(self.path, 'a') as first, open(self.path, 'a') as second:
            hostos.lock(first)
            with self.assertRaises(BlockingIOError):
                hostos.lock(second)
            hostos.unlock(first)
            hostos.lock(second)
            hostos.unlock(second)

    def test_closing_the_handle_releases_the_lock(self):
        with open(self.path, 'a') as handle:
            hostos.lock(handle)
        self.assertEqual(python(TRY_LOCK, self.path).stdout.strip(), 'held')

    def test_the_death_of_the_owner_releases_the_lock(self):
        owner = subprocess.Popen([sys.executable, '-c', HOLD_LOCK, self.path], cwd=ROOT, env=ENV,
                                 stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(owner.stdout.readline().strip(), 'held')
            self.assertEqual(python(TRY_LOCK, self.path).stdout.strip(), 'busy')
        finally:
            owner.kill()
            owner.wait()
            owner.stdout.close()
        deadline = time.monotonic() + 10
        result = 'busy'
        while result == 'busy' and time.monotonic() < deadline:
            result = python(TRY_LOCK, self.path).stdout.strip()
        self.assertEqual(result, 'held')


class GroupTest(unittest.TestCase):
    def family(self, mode):
        child = hostos.popen_group([sys.executable, '-c', FAMILY, mode], stdout=subprocess.PIPE)
        self.addCleanup(child.stdout.close)
        self.addCleanup(child.wait)
        self.addCleanup(self.quiet_kill, child.pid)
        self.assertEqual(child.stdout.readline().strip(), b'ready')
        return child

    @staticmethod
    def quiet_kill(pid):
        with contextlib.suppress(ProcessLookupError):
            hostos.kill_group(pid)

    def wait_until_gone(self, pid):
        deadline = time.monotonic() + 10
        while hostos.group_alive(pid) and time.monotonic() < deadline:
            time.sleep(.05)
        return not hostos.group_alive(pid)

    def test_killing_a_group_leaves_no_surviving_grandchild(self):
        child = self.family('stay')
        self.assertTrue(hostos.group_alive(child.pid))
        hostos.kill_group(child.pid)
        child.wait(timeout=10)
        self.assertTrue(closes_within(child.stdout, 10), 'a grandchild still holds the pipe')
        self.assertTrue(self.wait_until_gone(child.pid))

    def test_a_group_whose_leader_exited_is_still_alive_and_still_killed(self):
        child = self.family('leave')
        child.wait(timeout=10)
        self.assertTrue(hostos.group_alive(child.pid), 'the grandchild keeps the group alive')
        hostos.kill_group(child.pid)
        self.assertTrue(closes_within(child.stdout, 10), 'a grandchild still holds the pipe')
        self.assertTrue(self.wait_until_gone(child.pid))

    def test_a_group_is_found_and_killed_after_its_controller_died(self):
        controller = subprocess.Popen([sys.executable, '-c', CONTROLLER], cwd=ROOT, env=ENV,
                                      stdout=subprocess.PIPE, text=True)
        try:
            group = int(controller.stdout.readline())
        finally:
            controller.kill()
            controller.wait()
            controller.stdout.close()
        self.addCleanup(self.quiet_kill, group)
        self.assertTrue(hostos.group_alive(group), self.diagnosis(group))
        hostos.kill_group(group)
        self.assertTrue(self.wait_until_gone(group))

    @staticmethod
    def diagnosis(group):
        if not hostos.WINDOWS:
            return 'group %d' % group
        import ctypes
        handle = hostos._kernel().OpenJobObjectW(4, False, hostos._job_name(group))
        return 'job %r open=%r error=%r' % (hostos._job_name(group), handle, ctypes.get_last_error())

    def test_a_finished_group_is_not_alive_and_killing_it_reports_that(self):
        child = hostos.popen_group([sys.executable, '-c', 'pass'])
        child.wait(timeout=10)
        self.assertTrue(self.wait_until_gone(child.pid))
        with self.assertRaises(ProcessLookupError):
            hostos.kill_group(child.pid)


class OutputTest(unittest.TestCase):
    def test_a_childs_output_is_read_through_the_selector_until_it_ends(self):
        code = 'import sys; sys.stdout.write("x" * 200000); sys.stdout.flush()'
        child = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE)
        selector = hostos.output_selector(child.stdout)
        received = 0
        deadline = time.monotonic() + 30
        try:
            while selector.get_map() and time.monotonic() < deadline:
                for key, _ in selector.select(timeout=.1):
                    chunk = hostos.read_ready(key)
                    if chunk:
                        received += len(chunk)
                    else:
                        selector.unregister(key.fileobj)
        finally:
            selector.close()
            child.wait()
            child.stdout.close()
        self.assertEqual(received, 200000)

    def test_a_silent_child_yields_nothing_within_the_timeout(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'],
                                 stdout=subprocess.PIPE)
        selector = hostos.output_selector(child.stdout)
        try:
            started = time.monotonic()
            self.assertEqual(list(selector.select(timeout=.2)), [])
            self.assertLess(time.monotonic() - started, 5)
            self.assertTrue(selector.get_map())
        finally:
            child.kill()
            child.wait()
            selector.close()
            child.stdout.close()

    def test_the_gated_launcher_runs_the_command_and_returns_its_exit_code(self):
        child = subprocess.Popen([sys.executable, '-c', hostos.LAUNCH, sys.executable, '-c',
                                  'import sys; print("ran"); sys.exit(7)'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output, _ = child.communicate(b'G', timeout=60)
        self.assertEqual(output.strip(), b'ran')
        self.assertEqual(child.returncode, 7)

    def test_the_gated_launcher_refuses_without_the_release_byte(self):
        child = subprocess.Popen([sys.executable, '-c', hostos.LAUNCH, sys.executable, '-c',
                                  'print("ran")'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output, _ = child.communicate(b'', timeout=60)
        self.assertEqual(output, b'')
        self.assertEqual(child.returncode, 125)


class ImportTest(unittest.TestCase):
    def test_the_package_imports_without_the_posix_only_modules(self):
        code = ('import sys\n'
                'for name in ("fcntl", "termios", "pty", "tty", "resource", "pwd", "grp"):\n'
                '    sys.modules[name] = None\n'
                'import overseer.hostos, overseer.factory, overseer.__main__, overseer.orchestrate\n'
                'print("imported")\n')
        result = python(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'imported')

    def test_no_module_but_the_layer_and_the_pty_mode_names_fcntl(self):
        offenders = [path.name for path in sorted((ROOT / 'overseer').glob('*.py'))
                     if path.name not in ('hostos.py', 'local.py')
                     and 'fcntl' in path.read_text(encoding='utf-8')]
        self.assertEqual(offenders, [])


class PosixOnlyTest(unittest.TestCase):
    def test_require_posix_passes_here_unless_this_is_windows(self):
        if hostos.WINDOWS:
            with self.assertRaises(RuntimeError):
                hostos.require_posix('the tmux monitor')
        else:
            hostos.require_posix('the tmux monitor')

    def test_on_windows_the_refusal_is_one_line_that_names_wsl2(self):
        with patch.object(hostos, 'WINDOWS', True):
            with self.assertRaises(RuntimeError) as raised:
                hostos.require_posix('the tmux monitor')
        message = str(raised.exception)
        self.assertIn('WSL2', message)
        self.assertIn('the tmux monitor', message)
        self.assertNotIn('\n', message)

    def test_on_windows_the_monitor_and_pty_entry_points_exit_nonzero_naming_wsl2(self):
        from overseer import __main__ as cli
        with tempfile.TemporaryDirectory() as directory:
            state = str(Path(directory) / 'state.json')
            for argv in (['run', '--once', '--state', state], ['here', '--state', state],
                         ['start', 'name'], ['watch', '%0'], ['unwatch', '%0'],
                         ['model-select', '%0', '--state', state]):
                with self.subTest(argv=argv), patch.object(hostos, 'WINDOWS', True), \
                        patch.object(sys, 'argv', ['overseer', *argv]), \
                        self.assertLogs(cli.LOG, logging.ERROR) as logs, \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cli.main(), 1)
                self.assertEqual(len(logs.records), 1)
                self.assertIn('WSL2', logs.records[0].getMessage())
                self.assertFalse(Path(state).exists())

    def test_a_real_windows_host_gives_the_same_refusal_from_the_command_line(self):
        if not hostos.WINDOWS:
            self.skipTest('the refusal is exercised by patching on this host; this runs on Windows')
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([sys.executable, '-m', 'overseer', 'run', '--once', '--state',
                                     str(Path(directory) / 'state.json')], cwd=ROOT, env=ENV,
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn('WSL2', result.stderr)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
