"""The prompt-writing project in `promptwriting/`: what is published and what is withheld."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'promptwriting'
PUBLISHED = ['AGENTS.md', 'GUIDE.md', 'LESSONS.md', 'README.md', 'TEMPLATE.md']
WITHHELD = ('promptwriting/prompts/', 'promptwriting/DESIGN.md')


class PromptwritingLayoutTest(unittest.TestCase):
    def test_the_five_method_files_are_present(self):
        for name in PUBLISHED:
            self.assertTrue((FOLDER / name).is_file(), name)

    def test_the_private_parts_are_git_ignored(self):
        ignored = (ROOT / '.gitignore').read_text(encoding='utf-8').splitlines()
        for entry in WITHHELD:
            self.assertIn(entry, ignored)

    @unittest.skipUnless(shutil.which('git') and (ROOT / '.git').exists(), 'needs a git checkout')
    def test_git_tracks_the_five_files_and_nothing_else(self):
        listed = subprocess.run(['git', 'ls-files', 'promptwriting'], cwd=ROOT, capture_output=True,
                                text=True, check=True).stdout.split()
        self.assertEqual(sorted(listed), ['promptwriting/' + name for name in PUBLISHED])

    def test_the_published_lessons_rows_are_whole_and_do_not_need_the_archive(self):
        lines = (FOLDER / 'LESSONS.md').read_text(encoding='utf-8').splitlines()
        table = [line for line in lines if line.startswith('|')]
        self.assertGreaterEqual(len(table), 3)
        for line in table:
            self.assertEqual(line.count('|'), 14, line[:60])
        for row in table[2:]:
            self.assertNotIn('prompts/', row, row[:60])

    def test_the_readme_says_what_is_withheld_and_why(self):
        text = (FOLDER / 'README.md').read_text(encoding='utf-8')
        for word in ('DESIGN.md', 'prompts/', 'private'):
            self.assertIn(word, text)

    def test_the_agent_instructions_name_the_guide_in_this_repository(self):
        self.assertIn('promptwriting/GUIDE.md', (ROOT / 'AGENTS.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
