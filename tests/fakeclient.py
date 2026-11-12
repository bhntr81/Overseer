"""Fake worker clients for the tests: a program the host can start by name.

POSIX: a script with a shebang line. Windows runs no shebang script, so the fake is a real
`.exe`: pip's console-script launcher with a zipped `__main__.py` appended, which is how an
installed console script is built. It starts Python through CreateProcess and passes the
command line on unchanged; `cmd.exe` is not involved. `make_cmd_client` builds the other
Windows form, a `.cmd` starter, for the tests about that form.
"""
import io
import os
from pathlib import Path
import platform
import stat
import sys
import unittest
import zipfile


def _launcher():
    name = 't64-arm.exe' if platform.machine().upper() == 'ARM64' else 't64.exe'
    try:
        import pip._vendor.distlib as distlib
    except ImportError:
        raise unittest.SkipTest('no console-script launcher: pip is not installed') from None
    path = Path(distlib.__file__).with_name(name)
    if not path.is_file():
        raise unittest.SkipTest('no console-script launcher: pip ships no %s here' % name)
    return path.read_bytes()


def make_client(directory, name, body):
    """Write a client that runs the Python source `body`; return its path."""
    directory = Path(directory)
    if os.name != 'nt':
        path = directory / name
        path.write_text('#!%s\n%s' % (sys.executable, body), encoding='utf-8')
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as bundle:
        bundle.writestr('__main__.py', body)
    path = directory / (name + '.exe')
    path.write_bytes(_launcher() + ('#!"%s"\r\n' % sys.executable).encode('utf-8')
                     + archive.getvalue())
    return str(path)


def make_cmd_client(directory, name, body):
    """Windows only: write the client as a `.cmd` starter for a Python script; return its path."""
    directory = Path(directory)
    script = directory / (name + '-script.py')
    script.write_text(body, encoding='utf-8')
    path = directory / (name + '.cmd')
    path.write_text('@"%s" "%s" %%*\n' % (sys.executable, script), encoding='utf-8')
    return str(path)
