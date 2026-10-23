# tests/unit/test_adopt_import.py
import subprocess
import unittest
from datetime import date

from aidlc import adopt
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git


class ImportPatchTest(unittest.TestCase):
    FILES = {"CLAUDE.md": "Run pytest before you push.\n",
             ".cursor/rules/api.mdc": "---\nglobs: src/api/**, src/routes/**\nalwaysApply: false\n---\nKeep handlers thin.\n",
             ".github/instructions/db.instructions.md": "---\napplyTo: 'db/**'\n---\nNo raw SQL.\n",
             ".github/copilot-instructions.md": "Prefer small functions.\n"}

    def test_refuses_before_init_repo(self):
        with TempRepo(self.FILES) as root, self.assertRaises(adopt.AdoptError):
            adopt.import_patch(root)

    def test_the_patch_applies_and_never_overwrites(self):
        with TempRepo(self.FILES) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            (root / ".aidlc/rules/db.md").write_text("---\npaths: [db/**]\n---\nPerson's rule.\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "init")
            patch, problems = adopt.import_patch(root)
            self.assertEqual(len(problems), 1)
            self.assertIn(".aidlc/rules/db.md", problems[0])
            (root / "adopt.patch").write_text(patch, encoding="utf-8")
            done = subprocess.run(["git", "apply", "--check", "adopt.patch"], cwd=root, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            git(root, "apply", "adopt.patch")
            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            for needle in ("## Imported from CLAUDE.md", "Run pytest before you push.",
                           "## Imported from .github/copilot-instructions.md"):
                self.assertIn(needle, agents)
            api = (root / ".aidlc/rules/api.md").read_text(encoding="utf-8")
            self.assertIn('  - "src/api/**"', api)
            self.assertIn('  - "src/routes/**"', api)
            self.assertIn("Keep handlers thin.", api)
            self.assertFalse((root / "CLAUDE.md").exists())
            self.assertFalse((root / ".cursor/rules/api.mdc").exists())
            self.assertTrue((root / ".github/instructions/db.instructions.md").exists())   # left: its target exists
            self.assertEqual((root / ".aidlc/rules/db.md").read_text(encoding="utf-8"),
                             "---\npaths: [db/**]\n---\nPerson's rule.\n")

    def test_nothing_to_import_is_an_empty_patch(self):
        with TempRepo({"README.md": "x\n"}) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            self.assertEqual(adopt.import_patch(root), ("", []))


class ImportReviewFixesTest(unittest.TestCase):
    """Final review of Plan 5.1."""

    def patched(self, files, init=True):
        with TempRepo(files) as root:
            if init:
                init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
                git(root, "add", "-A")
                git(root, "commit", "-qm", "init")
            patch, problems = adopt.import_patch(root)
            (root / "adopt.patch").write_bytes(patch.encode("utf-8"))
            done = subprocess.run(["git", "apply", "--check", "adopt.patch"], cwd=root, capture_output=True, text=True)
            return patch, problems, done

    def test_two_sources_for_one_target_keep_the_second(self):
        patch, problems, done = self.patched({
            ".cursor/rules/api.mdc": "---\nglobs: src/**\n---\nCursor rule.\n",
            ".github/instructions/api.instructions.md": "---\napplyTo: 'lib/**'\n---\nCopilot rule.\n"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(patch.count("+++ b/.aidlc/rules/api.md"), 1)
        self.assertEqual(len(problems), 1)
        self.assertIn(".aidlc/rules/api.md", problems[0])

    def test_crlf_files_import(self):
        patch, problems, done = self.patched({
            "CLAUDE.md": "Line one.\r\nLine two.\r\n",
            ".cursor/rules/db.mdc": "---\r\nglobs: db/**\r\n---\r\nNo raw SQL.\r\n"})
        self.assertEqual((done.returncode, problems), (0, []), done.stderr)

    def test_brace_globs_and_manual_rules_are_left_for_a_person(self):
        patch, problems, done = self.patched({
            ".cursor/rules/web.mdc": "---\nglobs: src/**/*.{ts,tsx}\n---\nTyped.\n",
            ".cursor/rules/ask.mdc": "---\ndescription: use when asked\nalwaysApply: false\n---\nManual.\n"})
        self.assertEqual(patch, "")                       # both left for a person: nothing to apply
        self.assertEqual(len(problems), 2)
        self.assertNotIn("web.mdc", patch)
        self.assertNotIn("ask.mdc", patch)

    def test_unreadable_and_badly_named_sources_are_left_for_a_person(self):
        with TempRepo({"README.md": "x\n"}) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            (root / "CLAUDE.md").write_bytes(b"caf\xe9\n")
            (root / ".cursor" / "rules").mkdir(parents=True)
            (root / ".cursor" / "rules" / "bad\nname.mdc").write_text("---\nglobs: x/**\n---\nx\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "init")
            patch, problems = adopt.import_patch(root)
            self.assertEqual(patch, "")
            self.assertTrue(any("CLAUDE.md" in p and "UTF-8" in p for p in problems), problems)
            self.assertTrue(any("control character" in p for p in problems), problems)

    def test_a_missing_agents_md_is_a_clear_error(self):
        with TempRepo({"CLAUDE.md": "x\n"}) as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            (root / "AGENTS.md").unlink()
            with self.assertRaises(adopt.AdoptError):
                adopt.import_patch(root)
