import json
import sys
import unittest
from datetime import date

from aidlc.checks.doctor import run_doctor
from aidlc.repo import init_repo
from tests.helpers import TempRepo, run_cli


def ready_repo():
    repo = TempRepo({"package.json": "{}\n"})
    root = repo.__enter__()
    init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
    run_cli("render", "--tool", "claude-code", str(root))
    return repo, root


def which_all(_name):
    return "/usr/bin/x"


class DoctorTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.root = ready_repo()

    def tearDown(self):
        self.repo.__exit__(None, None, None)

    def all(self, **kw):
        return [f for f in run_doctor(self.root, which=which_all, claude_version="2.1.296", **kw)]

    def fails(self, **kw):
        return [str(f) for f in self.all(**kw) if f.level == "FAIL"]

    def warns(self):
        return [str(f) for f in self.all() if f.level == "WARN"]

    def edit_settings(self, fn):
        path = self.root / ".claude/settings.json"
        s = json.loads(path.read_text())
        fn(s)
        path.write_text(json.dumps(s, indent=2) + "\n")

    def test_healthy_repo_has_no_fail(self):
        self.assertEqual(self.fails(), [])
        self.assertFalse(any("D11" in m for m in self.fails()))

    def test_missing_sandbox_deps_fail(self):
        msgs = [str(f) for f in run_doctor(self.root, which=lambda n: None, claude_version="2.1.296")]
        self.assertTrue(any("D5" in m and "bwrap" in m for m in msgs))

    def test_old_claude_fails(self):
        self.assertTrue(any("D10" in m for m in
                            [str(f) for f in run_doctor(self.root, which=which_all, claude_version="2.1.282")]))

    def test_unknown_claude_version_warns(self):
        msgs = [str(f) for f in run_doctor(self.root, which=which_all, claude_version=None)]
        self.assertTrue(any(m.startswith("WARN") and "D10" in m for m in msgs))

    def test_planted_weakened_settings_fail(self):
        def weaken(s):
            s["sandbox"]["allowUnsandboxedCommands"] = True
            s["permissions"]["deny"].remove("Read(.env)")
        self.edit_settings(weaken)
        msgs = " ".join(self.fails())
        for code in ("D1", "D2", "D3"):
            self.assertIn(code, msgs)

    def test_missing_sandbox_denyread_entry_fails_d2(self):
        def drop(s):
            s["sandbox"]["filesystem"]["denyRead"].pop()
        self.edit_settings(drop)
        self.assertTrue(any("D2" in m for m in self.fails()))

    def test_allow_add_and_unmapped_tools_warn(self):
        (self.root / ".aidlc/permissions.yaml").write_text(
            "allow_add: [{kind: shell, pattern: 'docker build*', reason: images, owner: '@team'}]\n")
        run_cli("render", "--tool", "claude-code", str(self.root))
        warns = [str(f) for f in run_doctor(self.root, which=which_all, claude_version="2.1.296")
                 if f.level == "WARN"]
        self.assertTrue(any("D6" in w and "docker build*" in w for w in warns))
        self.assertTrue(any("D7" in w and "tracker." in w for w in warns))

    def test_dropped_deny_rule_names_its_list(self):
        warns = self.warns()
        self.assertTrue(any("D7" in w and "tracker.transition_issue" in w and "deny" in w for w in warns))
        self.assertTrue(any("D7" in w and "tracker.read_issue" in w and "allow" in w for w in warns))
        self.assertTrue(any("D7" in w and "tracker.add_comment" in w and "ask" in w for w in warns))

    def test_long_import_fails(self):
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs/big.md").write_text("x\n" * 250)
        (self.root / ".aidlc/claude.md").write_text("@docs/big.md\n")
        run_cli("render", "--tool", "claude-code", str(self.root))
        self.assertTrue(any("D8" in m for m in self.fails()))

    def test_medium_import_warns(self):
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs/mid.md").write_text("x\n" * 100)
        (self.root / ".aidlc/claude.md").write_text("@docs/mid.md\n")
        run_cli("render", "--tool", "claude-code", str(self.root))
        self.assertEqual([m for m in self.fails() if "D8" in m], [])
        self.assertTrue(any("D8" in w for w in self.warns()))

    def test_import_outside_repo_fails(self):
        (self.root / ".aidlc/claude.md").write_text("@../outside.md\n")
        run_cli("render", "--tool", "claude-code", str(self.root))
        self.assertTrue(any("D8" in m for m in self.fails()))

    def test_unknown_mcp_server_warns(self):
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {"mystery": {}, "lab-jira": {}}}))
        warns = self.warns()
        self.assertTrue(any("D9" in w and "mystery" in w for w in warns))
        self.assertFalse(any("D9" in w and "lab-jira" in w for w in warns))

    def test_widened_matcher_fails_d4(self):
        self.edit_settings(lambda s: s["hooks"]["PreToolUse"][0].update(matcher=".*"))
        self.assertTrue(any("D4" in m and "matcher" in m for m in self.fails()))

    def test_missing_hook_file_fails_d4(self):
        (self.root / ".aidlc/hooks/guard.py").unlink()
        self.assertTrue(any("D4" in m for m in self.fails()))

    def test_selftest_leaves_no_trace(self):
        import os
        before_path, before_mods = list(sys.path), set(sys.modules)
        before_env = os.environ.get("AIDLC_HARNESS_FILE")
        self.fails()
        self.assertEqual(sys.path, before_path)
        self.assertEqual(set(sys.modules) - before_mods, set())
        self.assertEqual(os.environ.get("AIDLC_HARNESS_FILE"), before_env)

    def test_protected_path_missing_denywrite_fails_d11(self):
        self.edit_settings(lambda s: s["sandbox"]["filesystem"]["denyWrite"].remove("./AGENTS.md"))
        self.assertTrue(any("D11" in m for m in self.fails()))

    def test_protected_path_missing_edit_rule_fails_d11(self):
        def drop(s):
            s["permissions"]["deny"] = [r for r in s["permissions"]["deny"] if not r.startswith("Edit(")]
        self.edit_settings(drop)
        self.assertTrue(any("D11" in m for m in self.fails()))

    def test_glob_protected_path_warns_d11(self):
        self.assertTrue(any(w.startswith("WARN") and "D11 " in w and "sandbox denyWrite covers only files "
                            "tracked at render time" in w for w in self.warns()))

    def test_cli(self):
        code, out, _ = run_cli("doctor", str(self.root))
        self.assertIn("doctor:", out)


class DoctorFrameworkRepoTest(unittest.TestCase):
    def test_uninstalled_repository_exits_2_cleanly(self):
        with TempRepo({"README.md": "x\n"}) as root:
            code, out, err = run_cli("doctor", str(root))
        self.assertEqual(code, 2)
        self.assertIn("not an installed repository; run aidlc init-repo", out + err)
        self.assertNotIn("Traceback", out + err)
