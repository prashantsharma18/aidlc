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
