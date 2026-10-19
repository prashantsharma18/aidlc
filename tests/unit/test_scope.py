import os
import stat
import tempfile
import unittest
from pathlib import Path

from aidlc.scope import ScopeError, approved_ref, bundle_at, parse_may_change, write_scope
from tests.helpers import TempRepo, git, run_cli

BUNDLE = ("TASK BUNDLE · SHIP-1 · slice 2\r\n"
          "GOAL        Do the thing\r\n"
          "MAY CHANGE  src/shipments/**, src/flags.ts (new),\r\n"
          "            test/**,\r\n"
          "            api/openapi.yaml\r\n"
          "MUST NOT    anything else\r\n")


class ScopeTest(unittest.TestCase):
    def test_parse_multiline_crlf_and_notes(self):
        self.assertEqual(parse_may_change(BUNDLE),
                         ["src/shipments/**", "src/flags.ts", "test/**", "api/openapi.yaml"])

    def test_missing_field_fails_closed(self):
        with self.assertRaises(ScopeError):
            parse_may_change("GOAL x\nMUST NOT y\n")

    def test_empty_field_fails_closed(self):
        with self.assertRaises(ScopeError):
            parse_may_change("MAY CHANGE\nMUST NOT y\n")

    def test_bundle_read_from_commit_not_working_tree(self):
        with TempRepo({"plans/SHIP-1/slice-2.md": BUNDLE}) as root:
            sha = git(root, "rev-parse", "HEAD")
            (root / "plans/SHIP-1/slice-2.md").write_text("MAY CHANGE **\n", encoding="utf-8")
            text = bundle_at(root, f"{sha}:plans/SHIP-1/slice-2.md")
            self.assertIn("src/shipments/**", text)

    def test_approved_ref_last_line_wins_and_unknown_branch_fails(self):
        approvals = ("# header\n"
                     "feat/SHIP-1-x aaa111:plans/a.md lead 2026-10-01\n"
                     "feat/SHIP-1-x bbb222:plans/b.md lead 2026-10-02\n")
        with TempRepo({"plans/approved-bundles.txt": approvals}) as root:
            self.assertEqual(approved_ref(root, "feat/SHIP-1-x"), "bbb222:plans/b.md")
            with self.assertRaises(ScopeError):
                approved_ref(root, "feat/OTHER-2-y")

    def test_write_scope_read_only_and_replaceable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "scope"
            write_scope(["a/**"], out)
            write_scope(["b/**"], out)
            self.assertEqual(out.read_text(encoding="utf-8"), "b/**\n")
            self.assertFalse(os.stat(out).st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))

    def test_cli_branch_mode(self):
        with TempRepo({"plans/SHIP-1/slice-2.md": BUNDLE}) as root:
            sha = git(root, "rev-parse", "HEAD")
            (root / "plans/approved-bundles.txt").write_text(
                f"feat/SHIP-1-x {sha}:plans/SHIP-1/slice-2.md lead 2026-10-18\n", encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "approve")
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "scope"
                code, text, _ = run_cli("scope", "--repo", str(root), "--branch", "feat/SHIP-1-x",
                                        "--out", str(out))
                self.assertEqual(code, 0, text)
                self.assertIn("api/openapi.yaml", out.read_text(encoding="utf-8"))
