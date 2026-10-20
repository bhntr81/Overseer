import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from overseer.factory import Factory
from overseer.isolation import MEMORY_LIMIT_BYTES, PROTECTED, restrictions_held, run_isolation_probe


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / 'state' / 'jobs.sqlite3'
        self.factory = Factory(self.db)
        self.addCleanup(self.factory.close)

    def test_verdict_requires_host_bytes_and_denials(self):
        output = '\n'.join([
            'ledger DENIED 30', 'other DENIED 30', 'cred DENIED 30', 'HOST_HIDDEN',
            'NET_DENIED 101', f'AS {MEMORY_LIMIT_BYTES} {MEMORY_LIMIT_BYTES}',
            'RAISE_DENIED', 'ALLOC_DENIED',
        ])
        before = dict(PROTECTED)
        self.assertTrue(restrictions_held(output, before, dict(PROTECTED), b'yes\n', False)[0])
        changed = dict(PROTECTED)
        changed['ledger'] = b'pwned\n'
        held, detail = restrictions_held(output, before, changed, b'yes\n', False)
        self.assertFalse(held)
        self.assertIn('ledger', detail)
        allowed = output.replace('ledger DENIED 30', 'ledger WRITE_OK')
        self.assertFalse(restrictions_held(allowed, before, dict(PROTECTED), b'yes\n', False)[0])

    def test_missing_bubblewrap_fails_closed(self):
        evidence = self.root / 'evidence'
        evidence.mkdir()
        with patch('overseer.isolation._which', return_value=None):
            outcome = run_isolation_probe(evidence)
        self.assertEqual(outcome['state'], 'failed')
        self.assertIn('unavailable', outcome['detail'])
        self.assertFalse(outcome['results'][0]['passed'])

    def test_probe_spec_rejects_commands_and_paths(self):
        spec = {'id': 'probe', 'objective': 'check the disposable runtime', 'mode': 'isolation_probe'}
        self.assertTrue(self.factory.submit(spec))
        for extra in ({'workspace': '/tmp'}, {'implementation': ['/bin/true']}, {'checks': [['/bin/true']]}):
            with self.assertRaises(ValueError):
                self.factory.submit({'id': 'other', 'objective': 'no', 'mode': 'isolation_probe', **extra})

    def test_live_probe_blocks_protected_paths_network_and_memory(self):
        self.factory.submit({
            'id': 'live-probe', 'objective': 'prove the disposable runtime restrictions',
            'mode': 'isolation_probe',
        })
        result = self.factory.run_one()
        self.assertEqual(result['state'], 'passed', result['detail'])
        evidence = Path(result['evidence'])
        saved = json.loads((evidence / 'isolation-result.json').read_text())
        self.assertTrue(saved['passed'])
        self.assertEqual((evidence / 'probe-root' / 'ledger' / 'ledger').read_bytes(), b'ledger\n')
        self.assertEqual((evidence / 'probe-root' / 'other' / 'note').read_bytes(), b'other\n')
        self.assertEqual((evidence / 'probe-root' / 'creds' / 'auth').read_bytes(), b'cred\n')
        self.assertEqual((evidence / 'probe-root' / 'workspace' / 'ok').read_text(), 'yes\n')
        log = (evidence / 'isolation.log').read_text()
        self.assertIn('NET_DENIED 101', log)
        self.assertIn('ALLOC_DENIED', log)
        self.assertTrue((evidence / 'timeout.log').is_file())
