"""Temporary measurement for CI round 1: what native Windows does today. Removed before merge."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from overseer.factory import Factory
from overseer.provider import build_task

try:
    from tests.fakeclient import make_cmd_client
    from tests.test_client_launch import TEXTS, RECORD
except ImportError:
    from fakeclient import make_cmd_client
    from test_client_launch import TEXTS, RECORD


@unittest.skipUnless(os.name == 'nt', 'measures Windows')
class Probe(unittest.TestCase):
    def test_measure(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'ws').mkdir()
            (base / 'bin').mkdir()
            received = base / 'argv.json'
            client = make_cmd_client(base / 'bin', 'probeclient', RECORD % str(received))
            factory = Factory(base / 'state' / 'jobs.sqlite3')
            try:
                cases = [(label, client, text) for label, text in TEXTS.items()]
                cases.append(('bare name', 'probeclient', 'plain words only'))
                path = str(base / 'bin') + os.pathsep + os.environ.get('PATH', '')
                for index, (label, program, text) in enumerate(cases):
                    if received.exists():
                        received.unlink()
                    spec, _ = build_task('p%d' % index, 'probe', str(base / 'ws'),
                                         checks=[[sys.executable, '-c', 'pass']], instruction=text,
                                         runner='opencode', env={}, opencode=program, timeout_seconds=60)
                    factory.submit(spec)
                    with patch.dict(os.environ, {'PATH': path}):
                        result = factory.run_one()
                    got = json.loads(received.read_text(encoding='utf-8'))[-1] if received.exists() else None
                    log = (Path(result['evidence']) / '00.log').read_text(encoding='utf-8', errors='replace')
                    print('PROBE %s | state=%s | client_ran=%s | exact=%s | received=%r | marker=%s | log_tail=%r'
                          % (label, result['state'], got is not None, got == text, got,
                             (base / 'ws' / 'marker.txt').exists(), log[-200:]), file=sys.stderr)
            finally:
                factory.close()
