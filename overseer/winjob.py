"""Windows job objects: the process group of a factory task on native Windows.

Used only by `overseer.hostos`, and only on Windows; importing it elsewhere is
harmless because every Windows call is made inside a function.

Windows job objects. A job lives while it has a process or an open handle, and
it keeps its name only while a handle is open. The controller holds one and the
gated launcher holds another, so a group whose controller died is found again
by name for as long as its launcher runs.
"""

JOBS = {}
TERMINATE = 0x0008
QUERY = 0x0004
_PROCESS_TERMINATE = 0x0001
_PROCESS_SET_QUOTA = 0x0100
_BASIC_ACCOUNTING = 1
_KERNEL = None


def _kernel():
    global _KERNEL
    if _KERNEL is None:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        signatures = {
            'CreateJobObjectW': (wintypes.HANDLE, [ctypes.c_void_p, wintypes.LPCWSTR]),
            'OpenJobObjectW': (wintypes.HANDLE, [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]),
            'OpenProcess': (wintypes.HANDLE, [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]),
            'AssignProcessToJobObject': (wintypes.BOOL, [wintypes.HANDLE, wintypes.HANDLE]),
            'TerminateJobObject': (wintypes.BOOL, [wintypes.HANDLE, wintypes.UINT]),
            'QueryInformationJobObject': (wintypes.BOOL, [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                                         wintypes.DWORD, ctypes.c_void_p]),
            'CloseHandle': (wintypes.BOOL, [wintypes.HANDLE]),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(kernel, name)
            function.restype = result
            function.argtypes = arguments
        _KERNEL = kernel
    return _KERNEL


def _last_error(call):
    import ctypes
    code = ctypes.get_last_error()
    return OSError(code, '%s failed: %s' % (call, ctypes.FormatError(code)))


def name(pid):
    return 'overseer-group-%d' % pid


def adopt(pid):
    """Create the job for a new child and put the child in it; return the job handle."""
    kernel = _kernel()
    job = kernel.CreateJobObjectW(None, name(pid))
    if not job:
        raise _last_error('CreateJobObjectW')
    process = kernel.OpenProcess(_PROCESS_TERMINATE | _PROCESS_SET_QUOTA, False, pid)
    if not process:
        error = _last_error('OpenProcess')
        kernel.CloseHandle(job)
        raise error
    try:
        if not kernel.AssignProcessToJobObject(job, process):
            error = _last_error('AssignProcessToJobObject')
            kernel.CloseHandle(job)
            raise error
    finally:
        kernel.CloseHandle(process)
    return job


def find(pid, access):
    """Return (handle, owned): this process's own handle, or one opened by name."""
    if pid in JOBS:
        return JOBS[pid], True
    return _kernel().OpenJobObjectW(access, False, name(pid)), False


def active(handle):
    """The number of live processes in a job."""
    import ctypes
    from ctypes import wintypes

    class Accounting(ctypes.Structure):
        _fields_ = [('TotalUserTime', ctypes.c_int64), ('TotalKernelTime', ctypes.c_int64),
                    ('ThisPeriodTotalUserTime', ctypes.c_int64),
                    ('ThisPeriodTotalKernelTime', ctypes.c_int64),
                    ('TotalPageFaultCount', wintypes.DWORD), ('TotalProcesses', wintypes.DWORD),
                    ('ActiveProcesses', wintypes.DWORD),
                    ('TotalTerminatedProcesses', wintypes.DWORD)]

    record = Accounting()
    if not _kernel().QueryInformationJobObject(handle, _BASIC_ACCOUNTING, ctypes.byref(record),
                                               ctypes.sizeof(record), None):
        raise _last_error('QueryInformationJobObject')
    return record.ActiveProcesses


def terminate(handle):
    """End every process in a job."""
    if not _kernel().TerminateJobObject(handle, 1):
        raise _last_error('TerminateJobObject')


def close(handle):
    _kernel().CloseHandle(handle)
