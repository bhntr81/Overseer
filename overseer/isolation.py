"""Bubblewrap boundary probes for one disposable worker runtime.

This does not make the trusted argv command runner a sandbox. A passing probe
shows only that this profile blocked the checked actions.
"""
import errno
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys

MEMORY_LIMIT_BYTES = 128 * 1024 * 1024
ALLOCATION_BYTES = 160 * 1024 * 1024
PROBE_TIMEOUT_SECONDS = 20
WALL_TIMEOUT_SECONDS = 3
PROTECTED = {
    'ledger': b'ledger\n',
    'other': b'other\n',
    'cred': b'cred\n',
}
PROBE_CODE = r'''
import os, socket, resource
from pathlib import Path
Path("/workspace/ok").write_text("yes\n")
for label, path in [("ledger","/ledger/ledger"),("other","/other/note"),("cred","/creds/auth")]:
    try:
        Path(path).write_text("pwned\n")
        print(label, "WRITE_OK")
    except OSError as e:
        print(label, "DENIED", e.errno)
host = os.environ.get("HOST_EVIDENCE", "")
print("HOST_HIDDEN" if host and not Path(host).exists() else "HOST_VISIBLE")
try:
    s = socket.socket()
    s.settimeout(1)
    s.connect(("192.0.2.1", 80))
    print("NET_OK")
except OSError as e:
    print("NET_DENIED", e.errno)
print("AS", *resource.getrlimit(resource.RLIMIT_AS))
try:
    resource.setrlimit(resource.RLIMIT_AS, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
    print("RAISE_OK")
except (ValueError, OSError):
    print("RAISE_DENIED")
try:
    blob = bytearray(int(os.environ["ALLOCATION_BYTES"]))
    print("ALLOC_OK", len(blob))
except MemoryError:
    print("ALLOC_DENIED")
'''


def _which(name):
    return shutil.which(name)


def _remove_group(pid):
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_group(argv, timeout):
    process = subprocess.Popen(
        argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        start_new_session=True, text=True,
    )
    try:
        output, _ = process.communicate(timeout=timeout)
        return process.returncode, output[:1024 * 1024], False
    except subprocess.TimeoutExpired:
        _remove_group(process.pid)
        output, _ = process.communicate()
        return process.returncode, output[:1024 * 1024], True
    finally:
        if process.poll() is None:
            _remove_group(process.pid)
            process.wait()


def _runtime_roots():
    interpreter = Path(sys.executable).resolve()
    if not str(interpreter).startswith('/usr/'):
        raise OSError('isolation probe requires the system Python under /usr')
    roots = [Path('/usr'), Path('/lib')]
    if Path('/lib64').exists():
        roots.append(Path('/lib64'))
    if Path('/bin').exists():
        roots.append(Path('/bin'))
    return interpreter, roots


def _bwrap_prefix(workspace, mounts, host_evidence):
    bwrap = _which('bwrap')
    prlimit = _which('prlimit')
    if not bwrap or not prlimit:
        raise OSError('bubblewrap or prlimit is unavailable; isolation route disabled')
    interpreter, roots = _runtime_roots()
    argv = [
        prlimit, f'--as={MEMORY_LIMIT_BYTES}', '--',
        bwrap, '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
        '--setenv', 'HOST_EVIDENCE', str(host_evidence),
        '--setenv', 'ALLOCATION_BYTES', str(ALLOCATION_BYTES),
    ]
    for root in roots:
        argv.extend(['--ro-bind', str(root), str(root)])
    argv.extend(['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp', '--bind', str(workspace), '/workspace'])
    for source, target in mounts:
        argv.extend(['--ro-bind', str(source), target])
    argv.extend(['--chdir', '/workspace', '--', str(interpreter), '-c', PROBE_CODE])
    return argv


def _prepare(root):
    root.mkdir(parents=True, mode=0o700)
    workspace = root / 'workspace'
    workspace.mkdir(mode=0o700)
    paths = {}
    for name, payload in PROTECTED.items():
        if name == 'ledger':
            directory, filename = root / 'ledger', 'ledger'
        elif name == 'other':
            directory, filename = root / 'other', 'note'
        else:
            directory, filename = root / 'creds', 'auth'
        directory.mkdir(mode=0o700)
        path = directory / filename
        path.write_bytes(payload)
        paths[name] = path
    return workspace, paths


def restrictions_held(output, before, after, workspace_ok, timed_out):
    """Judge a probe from host bytes and controller-owned output."""
    if timed_out:
        return False, 'boundary probe exceeded its wall-clock limit'
    lines = set(output.splitlines())
    for name in PROTECTED:
        if f'{name} WRITE_OK' in lines:
            return False, f'{name} write was reported as allowed'
        if not any(line.startswith(f'{name} DENIED ') for line in lines):
            return False, f'{name} write was not denied'
        if before[name] != after[name] or after[name] != PROTECTED[name]:
            return False, f'{name} bytes changed on the host'
    if 'HOST_HIDDEN' not in lines:
        return False, 'host evidence path was visible inside the probe'
    if f'NET_DENIED {errno.ENETUNREACH}' not in lines:
        return False, 'network connect was not unreachable'
    if 'NET_OK' in lines:
        return False, 'network connect succeeded'
    expected_limit = f'AS {MEMORY_LIMIT_BYTES} {MEMORY_LIMIT_BYTES}'
    if expected_limit not in lines or 'RAISE_DENIED' not in lines or 'ALLOC_DENIED' not in lines:
        return False, 'address-space limit was not enforced'
    if 'RAISE_OK' in lines or any(line.startswith('ALLOC_OK') for line in lines):
        return False, 'address-space limit was raised or exceeded'
    if workspace_ok != b'yes\n':
        return False, 'disposable workspace write did not succeed'
    return True, 'boundary probe restrictions held'


def run_isolation_probe(evidence):
    """Run the closed probe. Missing bubblewrap fails closed."""
    evidence = Path(evidence)
    root = evidence / 'probe-root'
    try:
        if not _which('bwrap') or not _which('prlimit'):
            raise OSError('bubblewrap or prlimit is unavailable; isolation route disabled')
        workspace, paths = _prepare(root)
        before = {name: path.read_bytes() for name, path in paths.items()}
        mounts = [
            (root / 'ledger', '/ledger'),
            (root / 'other', '/other'),
            (root / 'creds', '/creds'),
        ]
        code, output, timed_out = _run_group(
            _bwrap_prefix(workspace, mounts, evidence), PROBE_TIMEOUT_SECONDS,
        )
        (evidence / 'isolation.log').write_text(output)
        after = {name: path.read_bytes() for name, path in paths.items()}
        workspace_file = workspace / 'ok'
        workspace_ok = workspace_file.read_bytes() if workspace_file.is_file() else b''
        held, detail = restrictions_held(output, before, after, workspace_ok, timed_out)
        if held:
            sleep = _which('sleep')
            if not sleep:
                held, detail = False, 'sleep is unavailable; wall-clock limit was not tested'
            else:
                _, roots = _runtime_roots()
                timeout_argv = [
                    _which('bwrap'), '--unshare-all', '--die-with-parent', '--new-session', '--clearenv',
                ]
                for root_path in roots:
                    timeout_argv.extend(['--ro-bind', str(root_path), str(root_path)])
                timeout_argv.extend(['--chdir', '/', '--', sleep, '30'])
                killed_code, killed_output, killed = _run_group(timeout_argv, WALL_TIMEOUT_SECONDS)
                (evidence / 'timeout.log').write_text(killed_output)
                if not killed:
                    held, detail = False, 'wall-clock limit did not stop the sleep probe'
                else:
                    detail = 'boundary probe restrictions held; wall-clock limit stopped the sleep probe'
                    code = killed_code
        passed = held
    except OSError as error:
        passed = False
        detail = str(error)
        output = ''
        code = None
        timed_out = False
    result = {
        'stage': 'isolation_probe', 'exit_code': code, 'timed_out': timed_out,
        'passed': passed, 'detail': detail, 'log': str(evidence / 'isolation.log'),
    }
    (evidence / 'isolation-result.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n'
    )
    return {
        'state': 'passed' if passed else 'failed',
        'detail': detail,
        'results': [result],
    }
