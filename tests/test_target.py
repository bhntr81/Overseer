import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from overseer.factory import Factory
from overseer.target import TargetError, init as target_init


def contract(checks):
    return {'role': 'implementation', 'risk_tier': 'low', 'external_effects': [],
            'protected_paths': [], 'approval_requirements': [],
            'acceptance_ids': ['A%d' % (i + 1) for i in range(len(checks))],
            'required_capabilities': [], 'project_constraints': [],
            'measured_evidence': None, 'provider_availability': None,
            'budget': {'wall_time_seconds': 600, 'token_limit': None,
                       'cost_limit_usd': None, 'resource_limits': None,
                       'repair_allowance': 1}}


class TargetScaffoldTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()

    def test_init_creates_a_repository_with_one_commit(self):
        target = self.base / 'fresh'
        result = target_init(str(target))
        self.assertTrue((target / '.git').is_dir())
        self.assertEqual(len(result['head']), 40)
        count = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], cwd=target,
                               capture_output=True, text=True).stdout.strip()
        self.assertEqual(count, '1')
        self.assertFalse(result['spec_copied'])

    def test_init_refuses_a_non_empty_directory(self):
        target = self.base / 'used'
        target.mkdir()
        (target / 'file.txt').write_text('x')
        with self.assertRaises(TargetError):
            target_init(str(target))

    def test_init_refuses_a_path_inside_a_work_tree(self):
        repo = self.base / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '--quiet'], cwd=repo, check=True)
        with self.assertRaises(TargetError):
            target_init(str(repo / 'inside'))

    def test_init_copies_the_spec(self):
        spec = self.base / 'SPEC_SOURCE.md'
        spec.write_text('# Build the thing\n')
        target = self.base / 'withspec'
        result = target_init(str(target), spec=str(spec))
        self.assertTrue(result['spec_copied'])
        self.assertEqual((target / 'SPEC.md').read_text(), '# Build the thing\n')
        tracked = subprocess.run(['git', 'ls-files'], cwd=target,
                                 capture_output=True, text=True).stdout.split()
        self.assertIn('SPEC.md', tracked)

    def test_a_scaffolded_target_runs_builds_and_tests_from_scratch(self):
        target = self.base / 'project'
        target_init(str(target))
        impl_code = (
            "from pathlib import Path\n"
            "Path('mod.py').write_text('def add(a, b):\\n    return a + b\\n')\n"
            "Path('test_mod.py').write_text("
            "'import unittest, mod\\n"
            "class T(unittest.TestCase):\\n"
            "    def test_add(self):\\n"
            "        self.assertEqual(mod.add(2, 3), 5)\\n')\n"
        )
        checks = [[sys.executable, '-m', 'unittest', 'test_mod']]
        spec = {'id': 'scaffolded', 'objective': 'build and test a brand-new repo',
                'workspace': str(target), 'timeout_seconds': 30,
                'implementation': [sys.executable, '-c', impl_code],
                'checks': checks, 'contract': contract(checks)}
        f = Factory(self.base / 'state' / 'jobs.sqlite3')
        self.addCleanup(f.close)
        self.assertTrue(f.submit(spec))
        result = f.run_one()
        self.assertEqual(result['state'], 'passed')
        record = json.loads((Path(result['evidence']) / 'handoff.json').read_text())
        self.assertIsNotNone(record['base_revision']['value'])
        report = f.reconcile_handoff('scaffolded')
        self.assertEqual(report['verdict'], 'agree')
        self.assertEqual(report['unverifiable'], [])


if __name__ == '__main__':
    unittest.main()
