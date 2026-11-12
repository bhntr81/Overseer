"""The prompt-writing snapshot: what is copied, what is withheld, and the drift check."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'sync-promptwriting'
PUBLISHED = ['AGENTS.md', 'GUIDE.md', 'LESSONS.md', 'README.md', 'TEMPLATE.md']
LESSONS = ('# Outcomes\n\nHow to fill a row.\n\n'
           '| Date | Prompt | Project |\n|---|---|---|\n'
           '| 2026-01-01 | `prompts/private.md` | `SecretProject` |\n'
           '| 2026-01-02 | `prompts/other.md` | `SecretProject` |\n')


class SyncTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name) / 'canonical'
        self.snapshot = Path(temporary.name) / 'snapshot'
        (self.source / 'prompts').mkdir(parents=True)
        for name in ('AGENTS.md', 'GUIDE.md', 'README.md', 'TEMPLATE.md', 'DESIGN.md'):
            (self.source / name).write_bytes(('# %s\n\nbody of %s\n' % (name, name)).encode())
        (self.source / 'LESSONS.md').write_bytes(LESSONS.encode())
        (self.source / 'prompts' / 'private.md').write_bytes(b'private\n')

    def run_script(self, *arguments):
        return subprocess.run([sys.executable, str(SCRIPT), '--source', str(self.source),
                               '--snapshot', str(self.snapshot), *arguments],
                              capture_output=True, text=True, timeout=60)

    def test_it_copies_the_five_method_files_and_nothing_else(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(path.name for path in self.snapshot.iterdir()), PUBLISHED)
        for name in ('AGENTS.md', 'GUIDE.md', 'TEMPLATE.md'):
            self.assertEqual((self.snapshot / name).read_bytes(), (self.source / name).read_bytes())

    def test_the_lessons_table_keeps_its_header_and_loses_every_row(self):
        self.run_script()
        text = (self.snapshot / 'LESSONS.md').read_text(encoding='utf-8')
        self.assertTrue(text.endswith('| Date | Prompt | Project |\n|---|---|---|\n'))
        self.assertIn('How to fill a row.', text)
        self.assertNotIn('SecretProject', text)
        self.assertNotIn('private.md', text)

    def test_the_readme_says_what_is_withheld_and_why(self):
        self.run_script()
        text = (self.snapshot / 'README.md').read_text(encoding='utf-8')
        self.assertTrue(text.startswith((self.source / 'README.md').read_text(encoding='utf-8')))
        for word in ('DESIGN.md', 'prompts/', 'scripts/sync-promptwriting'):
            self.assertIn(word, text)

    def test_the_source_is_never_written(self):
        before = {path: path.read_bytes() for path in self.source.rglob('*') if path.is_file()}
        self.run_script()
        self.run_script('--check')
        after = {path: path.read_bytes() for path in self.source.rglob('*') if path.is_file()}
        self.assertEqual(before, after)

    def test_check_passes_on_a_fresh_snapshot_and_writes_nothing(self):
        self.assertEqual(self.run_script('--check').returncode, 1)
        self.assertFalse(self.snapshot.exists())
        self.run_script()
        self.assertEqual(self.run_script('--check').returncode, 0)

    def test_check_fails_when_the_canonical_file_moved_on(self):
        self.run_script()
        (self.source / 'GUIDE.md').write_bytes(b'# changed\n')
        result = self.run_script('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('GUIDE.md', result.stderr)

    def test_check_fails_on_an_edited_or_extra_snapshot_file(self):
        self.run_script()
        (self.snapshot / 'DESIGN.md').write_bytes(b'leaked\n')
        result = self.run_script('--check')
        self.assertEqual(result.returncode, 1)
        self.assertIn('DESIGN.md', result.stderr)

    def test_an_absent_canonical_project_is_a_note_for_check_and_an_error_for_a_write(self):
        self.source = self.source.with_name('absent')
        check = self.run_script('--check')
        self.assertEqual(check.returncode, 0)
        self.assertIn('absent', check.stdout)
        self.assertEqual(self.run_script().returncode, 2)
        self.assertFalse(self.snapshot.exists())


class CommittedSnapshotTest(unittest.TestCase):
    def test_the_repository_carries_the_five_files_without_rows_or_archive(self):
        folder = ROOT / 'promptwriting'
        self.assertEqual(sorted(path.name for path in folder.iterdir()), PUBLISHED)
        lessons = (folder / 'LESSONS.md').read_text(encoding='utf-8').rstrip('\n')
        self.assertRegex(lessons.splitlines()[-1], r'^\|\s*-{3}')

    def test_the_agent_instructions_name_the_snapshot_as_the_fallback(self):
        self.assertIn('promptwriting/GUIDE.md', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
