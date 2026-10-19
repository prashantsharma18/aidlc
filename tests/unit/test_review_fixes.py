"""Regression tests for the final-review findings on plan 1 (Important 1-6)."""
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from aidlc.checks.context_drift import check_context_drift
from aidlc.repo import init_repo
from aidlc.scope import ScopeError, approved_ref, parse_may_change
from tests.helpers import TempRepo, git, run_cli

RULES = {"AGENTS.md": "# x\n", ".aidlc/rules/db.md": "---\npaths: [\"db/**\"]\n---\nRule.\n"}


class RenderLocationTest(unittest.TestCase):  # Important 1
    def test_render_from_subdirectory_writes_at_repo_root(self):
        with TempRepo({**RULES, "src/a.ts": "x\n"}) as root:
            code, out, _ = run_cli("render", "--tool", "claude-code", cwd=root / "src")
            self.assertEqual(code, 0, out)
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertFalse((root / "src" / "CLAUDE.md").exists())

    def test_render_outside_repo_is_usage_error_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = run_cli("render", "--tool", "claude-code", tmp)
            self.assertEqual(code, 2, out)
            self.assertFalse((Path(tmp) / "CLAUDE.md").exists())

    def test_render_requires_agents_md(self):
        with TempRepo({"README.md": "x\n"}) as root:
            code, out, _ = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 1, out)
            self.assertIn("AGENTS.md", out)
            self.assertFalse((root / "CLAUDE.md").exists())


class ScopeApprovalTest(unittest.TestCase):  # Important 2
    def test_moving_ref_in_approvals_is_rejected(self):
        approvals = "feat/SHIP-1-x HEAD:plans/b.md lead 2026-10-18\n"
        with TempRepo({"plans/approved-bundles.txt": approvals}) as root:
            with self.assertRaises(ScopeError):
                approved_ref(root, "feat/SHIP-1-x")

    def test_cli_has_no_bundle_or_approvals_ref_bypass(self):
        with TempRepo({"plans/b.md": "MAY CHANGE src/**\n"}) as root:
            out_file = str(Path(tempfile.mkdtemp()) / "scope")
            code, _, _ = run_cli("scope", "--repo", str(root), "--bundle", "HEAD:plans/b.md",
                                 "--out", out_file)
            self.assertEqual(code, 2)
            code, _, _ = run_cli("scope", "--repo", str(root), "--branch", "feat/x",
                                 "--approvals-ref", "feat/x", "--out", out_file)
            self.assertEqual(code, 2)

    def test_self_approval_on_feature_branch_is_ignored(self):
        with TempRepo({"plans/b.md": "MAY CHANGE src/**\n",
                       "plans/approved-bundles.txt": "# none\n"}) as root:
            sha = git(root, "rev-parse", "HEAD")
            git(root, "switch", "-q", "-c", "feat/x")
            (root / "plans/approved-bundles.txt").write_text(f"feat/x {sha}:plans/b.md me 2026-10-18\n",
                                                            encoding="utf-8")
            git(root, "commit", "-q", "-am", "self-approve")
            out_file = Path(tempfile.mkdtemp()) / "scope"
            code, out, _ = run_cli("scope", "--repo", str(root), "--branch", "feat/x",
                                   "--out", str(out_file))
            self.assertEqual(code, 1, out)
            self.assertFalse(out_file.exists())


class ScopeValidationTest(unittest.TestCase):  # Important 3
    def test_dangerous_patterns_are_refused(self):
        for bad in ("../../etc/passwd", "/home/u/.bashrc", ".git/hooks/pre-commit", "**", "*",
                    "src/../../x"):
            with self.subTest(bad=bad), self.assertRaises(ScopeError):
                parse_may_change(f"MAY CHANGE  src/**, {bad}\n")

    def test_normal_patterns_pass(self):
        self.assertEqual(parse_may_change("MAY CHANGE  src/**, test/a.ts\n"), ["src/**", "test/a.ts"])

    def test_out_inside_repository_is_refused(self):
        with TempRepo({"plans/b.md": "MAY CHANGE src/**\n"}) as root:
            sha = git(root, "rev-parse", "HEAD")
            (root / "plans/approved-bundles.txt").write_text(f"feat/x {sha}:plans/b.md lead 2026-10-18\n",
                                                            encoding="utf-8")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "approve")
            target = root / ".aidlc" / "scope.txt"
            code, out, _ = run_cli("scope", "--repo", str(root), "--branch", "feat/x",
                                   "--out", str(target))
            self.assertEqual(code, 1, out)
            self.assertFalse(target.exists())


class DriftFalsePositiveTest(unittest.TestCase):  # Important 4
    def _repo(self, agents):
        return TempRepo({"AGENTS.md": agents, ".gitignore": "dist/\n", "src/app/a.test.ts": "x\n",
                         "docs/codebase-map.md": "Owner: t · Last verified: 2026-10-18, against commit 0000000\n"})

    def _fails(self, root):
        sha = git(root, "rev-parse", "--short", "HEAD")
        (root / "docs/codebase-map.md").write_text(
            f"Owner: t · Last verified: 2026-10-18, against commit {sha}\n", encoding="utf-8")
        return [str(f) for f in check_context_drift(root, date(2026, 10, 18)) if f.level == "FAIL"]

    def test_common_non_paths_are_not_reported(self):
        agents = ("- `application/json`, `origin/main`, `HTTP/2`, `TCP/IP`, `and/or`, `owner/repo`\n"
                  "- tests are `*.test.ts`; never edit `dist/`\n")
        with self._repo(agents) as root:
            self.assertEqual(self._fails(root), [])

    def test_real_stale_paths_still_fail(self):
        agents = "- old code in `src/old/` and `src/legacy/handler` and `src/gone.ts`\n"
        with self._repo(agents) as root:
            fails = " ".join(self._fails(root))
            for stale in ("src/old/", "src/legacy/handler", "src/gone.ts"):
                self.assertIn(stale, fails)


class SymlinkEscapeTest(unittest.TestCase):  # Important 5
    def test_render_refuses_symlinked_output_dir(self):
        with TempRepo(RULES) as root, tempfile.TemporaryDirectory() as outside:
            os.symlink(outside, root / ".claude")
            code, out, _ = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 1, out)
            self.assertFalse((Path(outside) / "rules" / "db.md").exists())

    def test_render_refuses_symlinked_claude_extra(self):
        with TempRepo(RULES) as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "evil.md").write_text("injected\n", encoding="utf-8")
            os.symlink(Path(outside) / "evil.md", root / ".aidlc" / "claude.md")
            code, out, _ = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 1, out)
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_init_repo_does_not_write_through_dangling_symlink(self):
        with TempRepo() as root, tempfile.TemporaryDirectory() as outside:
            os.symlink(Path(outside) / "pwned.md", root / "AGENTS.md")
            report = dict(init_repo(root, "x", "o", "node", "p", date(2026, 10, 18)))
            self.assertNotEqual(report["AGENTS.md"], "created")
            self.assertFalse((Path(outside) / "pwned.md").exists())


class OrphanRuleTest(unittest.TestCase):  # Important 6
    def test_orphaned_generated_rule_is_reported_then_removed(self):
        with TempRepo(RULES) as root:
            self.assertEqual(run_cli("render", "--tool", "claude-code", str(root))[0], 0)
            (root / ".aidlc/rules/db.md").unlink()
            (root / ".claude/rules/mine.md").write_text("hand written\n", encoding="utf-8")
            code, out, _ = run_cli("render", "--tool", "claude-code", "--check", str(root))
            self.assertEqual(code, 1, out)
            self.assertIn("orphaned", out)
            run_cli("render", "--tool", "claude-code", str(root))
            self.assertFalse((root / ".claude/rules/db.md").exists())
            self.assertTrue((root / ".claude/rules/mine.md").exists())
