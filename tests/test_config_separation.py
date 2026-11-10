"""Public/local configuration separation, the Windows entry points, and the agent docs.

Written before the implementation and frozen (see docs/DEVELOPMENT.md). The live
config.json is local, ignored and never read here: the checked-in
config.example.json is the public configuration.
"""
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from overseer.__main__ import main, settings
from overseer.modelchoice import providers
from overseer.policy import BLOCKED

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "config.example.json"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def have_git():
    return shutil.which("git") is not None and (ROOT / ".git").exists()


class ExampleConfigTests(unittest.TestCase):
    def test_example_exists_and_loads_through_the_real_loader(self):
        config = settings(EXAMPLE)
        self.assertIs(config["dry_run"], True, "the example must not send anything by default")
        self.assertLessEqual(config["max_per_day"], 4)

    def test_example_has_no_machine_or_personal_details(self):
        text = EXAMPLE.read_text(encoding="utf-8")
        for needle in ("/home/", "kali", "john", "bhntr81", "@gmail", "clubwpt", "ollama/"):
            self.assertNotIn(needle, text.lower(), needle)
        config = json.loads(text)
        for path in config.get("target_paths", []):
            self.assertFalse(Path(path).is_absolute(), path)

    def test_example_watches_nothing_until_the_operator_chooses(self):
        config = settings(EXAMPLE)
        self.assertEqual(config.get("exclude"), [])
        self.assertEqual(config.get("targets"), [])
        self.assertEqual(config.get("target_paths"), [])

    def test_example_keeps_the_provider_allowlist_and_the_status_contract(self):
        config = settings(EXAMPLE)
        self.assertEqual([entry["id"] for entry in providers(config)],
                         ["claude", "openai", "opencode", "grok"])
        reply = config["reply"]
        self.assertIsNone(BLOCKED.search(reply))
        for marker in ("OVERSEER_REPORT", "OVERSEER_STEP_DONE", "OVERSEER_DONE",
                       "OVERSEER_NEEDS_INPUT", "SESSION_HANDOFF.md"):
            self.assertIn(marker, reply)

    def test_example_leaves_the_stop_agent_off(self):
        self.assertIs(settings(EXAMPLE)["stop_agent"]["enabled"], False)


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def test_a_missing_config_names_the_example_to_copy(self):
        with self.assertRaises(ValueError) as caught:
            settings(self.dir / "config.json")
        self.assertIn("config.example.json", str(caught.exception))
        self.assertFalse((self.dir / "config.json").exists(), "nothing may be created")

    def test_a_malformed_config_is_refused(self):
        path = self.dir / "config.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            settings(path)

    def test_a_fresh_install_runs_from_the_copied_example(self):
        path = self.dir / "config.json"
        shutil.copyfile(EXAMPLE, path)
        self.assertIs(settings(path)["dry_run"], True)

    def test_reading_an_existing_config_never_rewrites_it(self):
        path = self.dir / "config.json"
        shutil.copyfile(EXAMPLE, path)
        before = path.read_bytes()
        settings(path)
        self.assertEqual(path.read_bytes(), before)

    def test_the_cli_exits_one_and_explains_when_config_json_is_missing(self):
        errors = io.StringIO()
        argv = ["overseer", "status", "--state", str(self.dir / "state.json")]
        with patch("overseer.__main__.ROOT", self.dir), patch.object(sys, "argv", argv), \
                self.assertLogs(level="ERROR") as logs:
            self.assertEqual(main(), 1)
        self.assertIn("config.example.json", "\n".join(logs.output))
        self.assertFalse((self.dir / "config.json").exists())


@unittest.skipUnless(have_git(), "needs a git checkout")
class IgnoreRuleTests(unittest.TestCase):
    def test_local_config_and_backups_are_ignored(self):
        for name in ("config.json", "config.json.bak-20261030-061132",
                     "config.json.bak-before-anything", "state.sqlite3"):
            self.assertEqual(git("check-ignore", "-q", name).returncode, 0, name)

    def test_the_example_is_not_ignored(self):
        self.assertEqual(git("check-ignore", "-q", "config.example.json").returncode, 1)

    def test_no_local_config_or_backup_is_tracked(self):
        tracked = git("ls-files").stdout.splitlines()
        self.assertNotIn("config.json", tracked)
        self.assertEqual([name for name in tracked if ".bak" in name], [])


class WindowsEntryPointTests(unittest.TestCase):
    def test_the_powershell_scripts_exist(self):
        for name in ("check.ps1", "check-doc-references.ps1"):
            self.assertTrue((ROOT / "scripts" / name).is_file(), name)

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is not installed")
    def test_check_resolves_a_python_without_running_the_suite(self):
        result = subprocess.run(
            ["pwsh", "-NoProfile", "-File", str(ROOT / "scripts" / "check.ps1"), "-ResolveOnly"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"(?i)python")

    @unittest.skipUnless(shutil.which("pwsh"), "PowerShell is not installed")
    def test_doc_check_propagates_the_exit_codes(self):
        script = str(ROOT / "scripts" / "check-doc-references.ps1")
        good = subprocess.run(["pwsh", "-NoProfile", "-File", script], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        missing = subprocess.run(["pwsh", "-NoProfile", "-File", script, str(ROOT / "no-such.md")],
                                 capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)

    def test_the_python_doc_check_reports_a_missing_document_with_exit_two(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "check-doc-references"),
                                 str(ROOT / "no-such.md")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


class AgentDocumentationTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding="utf-8")

    def test_codex_and_claude_find_the_same_instructions(self):
        agents = self.read("AGENTS.md")
        self.assertIn("docs/DEVELOPMENT.md", agents)
        claude = self.read("CLAUDE.md")
        self.assertIn("AGENTS.md", claude)
        self.assertLess(len(claude), 600, "CLAUDE.md points at AGENTS.md; it must not duplicate it")

    def test_the_development_guide_covers_all_three_environments(self):
        guide = self.read("docs/DEVELOPMENT.md")
        for text in ("Linux", "PowerShell", "Codex", "Claude Code", "config.example.json",
                     "scripts/check", "scripts/check-doc-references", "fcntl", "tmux",
                     "Red-Green", "ledger", "approval", "epoch", "reconcile-handoff"):
            self.assertIn(text, guide, text)

    def test_the_readme_explains_configuration_and_the_development_guide(self):
        readme = self.read("README.md")
        self.assertIn("config.example.json", readme)
        self.assertIn("docs/DEVELOPMENT.md", readme)

    def test_every_committed_doc_link_to_a_repo_file_resolves(self):
        for name in ("README.md", "AGENTS.md", "CLAUDE.md", "docs/DEVELOPMENT.md"):
            for target in re.findall(r"\]\((?!https?:|#)([^)#\s]+)\)", self.read(name)):
                base = (ROOT / name).parent
                self.assertTrue((base / target).exists(), f"{name} links to missing {target}")


if __name__ == "__main__":
    unittest.main()
