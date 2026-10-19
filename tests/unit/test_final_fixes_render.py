# tests/unit/test_final_fixes_render.py
"""Plan 2 final fix pass (final-fixes.md): render, harness data and doctor."""
import json
import os
import unittest
from datetime import date
from pathlib import Path

from aidlc.adapters import get_adapter
from aidlc.checks.doctor import run_doctor
from aidlc.harness import HarnessError, effective_permissions, harness_data
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git, run_cli
from tests.hook_loader import load_hook
from tests.unit.test_guard import GuardEnv

post = load_hook("post_check")


def which_all(_name):
    return "/usr/bin/x"


class Scaffold:
    """A committed package.json, then init-repo; optional extra tracked files."""

    def __init__(self, files=None):
        self.repo = TempRepo({"package.json": "{}\n", **(files or {})})

    def __enter__(self):
        self.root = self.repo.__enter__()
        init_repo(self.root, "svc", "team", "node", "purpose", date(2026, 10, 19))
        return self.root

    def __exit__(self, *exc):
        self.repo.__exit__(*exc)


def settings(root):
    [f] = get_adapter("claude-code").render_permissions(root)
    return json.loads(f.content)


def set_config(root, old, new):
    cfg = root / ".aidlc/config.yaml"
    text = cfg.read_text()
    assert old in text, old
    cfg.write_text(text.replace(old, new))


def doctor(root):
    return [str(f) for f in run_doctor(root, which=which_all, claude_version="2.1.296")]


class F2DenyWriteOnlyExistingTest(unittest.TestCase):
    def test_missing_literal_paths_are_not_rendered(self):
        with Scaffold() as root:
            dw = settings(root)["sandbox"]["filesystem"]["denyWrite"]
            for missing in ("./api", "./ci", "./.mcp.json", "./.github", "./architecture",
                            "./openwiki", "./test/allowed-skips.txt"):
                self.assertNotIn(missing, dw)
            for present in ("./.aidlc", "./AGENTS.md", "./plans", "./.openwikiignore",
                            "./CLAUDE.md", "./.claude", "./.git/hooks", "./.git/config", "~/.aidlc"):
                self.assertIn(present, dw)

    def test_tracked_api_file_renders_api(self):
        with Scaffold({"api/x.yaml": "openapi: 3.1.0\n"}) as root:
            self.assertIn("./api", settings(root)["sandbox"]["filesystem"]["denyWrite"])

    def test_untracked_not_ignored_literal_renders(self):
        with Scaffold() as root:
            (root / ".mcp.json").write_text("{}\n")
            self.assertIn("./.mcp.json", settings(root)["sandbox"]["filesystem"]["denyWrite"])

    def test_ignored_files_are_not_listed(self):
        with Scaffold() as root:
            (root / ".gitignore").write_text("CLAUDE.local.md\nb/\n.mcp.json\n")
            (root / "CLAUDE.local.md").write_text("mine\n")
            (root / "b").mkdir()
            (root / "b/AGENTS.md").write_text("ignored\n")
            (root / ".mcp.json").write_text("{}\n")
            dw = settings(root)["sandbox"]["filesystem"]["denyWrite"]
            for ignored in ("./CLAUDE.local.md", "./b/AGENTS.md", "./.mcp.json"):
                self.assertNotIn(ignored, dw)

    def test_first_render_is_stable(self):
        with Scaffold() as root:
            code, out, err = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 0, out + err)
            code, out, err = run_cli("render", "--tool", "claude-code", "--check", str(root))
            self.assertEqual(code, 0, out + err)
            self.assertEqual([m for m in doctor(root) if m.startswith("FAIL")], [])

    def test_d11_warn_names_the_post_check(self):
        with Scaffold() as root:
            run_cli("render", "--tool", "claude-code", str(root))
            warns = [m for m in doctor(root) if m.startswith("WARN") and "D11 " in m]
            self.assertTrue(warns)
            self.assertTrue(all("post-check" in w for w in warns), warns)


class F4BaseBranchRenderTest(unittest.TestCase):
    def test_harness_data_carries_base_branch(self):
        with Scaffold() as root:
            self.assertEqual(harness_data(root)["base_branch"], "main")
            set_config(root, "base_branch: main", "base_branch: master")
            self.assertEqual(harness_data(root)["base_branch"], "master")

    def test_invalid_base_branch_is_an_error(self):
        with Scaffold() as root:
            set_config(root, "base_branch: main", "base_branch: '-x y'")
            with self.assertRaises(HarnessError):
                harness_data(root)

    def test_missing_base_ref_fails_d12(self):
        with Scaffold() as root:
            set_config(root, "base_branch: main", "base_branch: develop")
            run_cli("render", "--tool", "claude-code", str(root))
            fails = [m for m in doctor(root) if m.startswith("FAIL") and "D12" in m]
            self.assertEqual(len(fails), 1, fails)
            self.assertIn("create it or set harness.base_branch", fails[0])

    def test_existing_base_ref_passes_d12(self):
        with Scaffold() as root:
            run_cli("render", "--tool", "claude-code", str(root))
            self.assertFalse([m for m in doctor(root) if "D12" in m])


class F5NoBytecodeInRepoTest(unittest.TestCase):
    def test_render_and_doctor_leave_no_pycache(self):
        with Scaffold() as root, GuardEnv(branch="feat/x") as env:
            os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
            code, out, err = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 0, out + err)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "install")
            git(root, "switch", "-q", "-c", "feat/x")
            run_cli("doctor", str(root))
            status = git(root, "status", "--porcelain", "--untracked-files=all")
            self.assertNotIn("__pycache__", status)
            os.environ["AIDLC_HARNESS_FILE"] = str(root / ".aidlc/hooks/harness.json")
            env.write_scope(root, ["src/**"])
            event = {"tool": "shell", "args": {}, "cwd": str(root), "output": ""}
            self.assertEqual(post.check(event)["decision"], "pass")


class F7SandboxLooseningTest(unittest.TestCase):
    def narrow(self, root, text):
        (root / ".aidlc/permissions.yaml").write_text(text)

    def test_entry_without_reason_is_a_schema_error(self):
        with Scaffold() as root:
            self.narrow(root, "sandbox_allow_write_add: [{value: ~/.cache/x, owner: '@team'}]\n")
            with self.assertRaises(HarnessError):
                effective_permissions(root)
            self.narrow(root, "network_allow_add: [example.com]\n")
            with self.assertRaises(HarnessError):
                effective_permissions(root)

    def test_dangerous_write_paths_refused(self):
        home = str(Path.home())
        for value in ("~", "/", "~/", "~/.claude", "~/.claude/x", "~/.aidlc/scopes", "~/.local/bin",
                      "~/bin", "/usr", "/usr/local/lib", "/bin", "~/x/../.claude", "../x",
                      "~/.local", f"{home}/.claude", f"{home}/.aidlc/logs", "~/.c*", "/*"):
            with self.subTest(value=value), Scaffold() as root:
                self.narrow(root, "sandbox_allow_write_add:\n"
                                  f"  - {{value: {json.dumps(value)}, reason: r, owner: o}}\n")
                with self.assertRaisesRegex(HarnessError, "refused"):
                    effective_permissions(root)

    def test_valid_entries_render_and_warn(self):
        with Scaffold() as root:
            self.narrow(root, "sandbox_allow_write_add:\n"
                              "  - {value: ~/.cache/playwright, reason: browser cache, owner: '@web'}\n"
                              "network_allow_add:\n"
                              "  - {value: cdn.example.com, reason: fonts, owner: '@web'}\n")
            s = settings(root)["sandbox"]
            self.assertIn("~/.cache/playwright", s["filesystem"]["allowWrite"])
            self.assertIn("cdn.example.com", s["network"]["allowedDomains"])
            run_cli("render", "--tool", "claude-code", str(root))
            warns = [m for m in doctor(root) if m.startswith("WARN") and "D6" in m]
            for value, reason in (("~/.cache/playwright", "browser cache"), ("cdn.example.com", "fonts")):
                self.assertTrue(any(value in w and reason in w and "@web" in w for w in warns), warns)

    def test_init_repo_template_stays_valid(self):
        with Scaffold() as root:
            self.assertEqual(effective_permissions(root)["sandbox_allow_write_add"], [])


class F9NestedEnvDenyReadTest(unittest.TestCase):
    def test_bare_names_rendered_at_any_depth(self):
        with Scaffold() as root:
            deny_read = settings(root)["sandbox"]["filesystem"]["denyRead"]
            for path in ("./.env", "./.env.*", "./**/.env", "./**/.env.*"):
                self.assertIn(path, deny_read)
            self.assertNotIn("./**/secrets/**", deny_read)

    def test_d2_expects_both_entries(self):
        with Scaffold() as root:
            run_cli("render", "--tool", "claude-code", str(root))
            path = root / ".claude/settings.json"
            s = json.loads(path.read_text())
            s["sandbox"]["filesystem"]["denyRead"].remove("./**/.env")
            path.write_text(json.dumps(s, indent=2) + "\n")
            self.assertTrue(any(m.startswith("FAIL") and "D2" in m and "./**/.env" in m
                                for m in doctor(root)))


if __name__ == "__main__":
    unittest.main()


class F2ClaudeLocalProtectedTest(unittest.TestCase):
    def test_policy_protects_claude_local_md(self):
        from aidlc.policy import load_policy
        base = load_policy("permissions")
        for entry in ("CLAUDE.local.md", "**/CLAUDE.local.md"):
            self.assertIn(entry, base["protected_paths"])
            self.assertIn(entry, base["deny"]["edit"])

    def test_rendered_harness_protects_claude_local_md(self):
        with Scaffold() as root:
            self.assertIn("CLAUDE.local.md", harness_data(root)["protected_paths"])
            self.assertIn("Edit(**/CLAUDE.local.md)", settings(root)["permissions"]["deny"])


class F3RiskInventoryTest(unittest.TestCase):
    def test_base_branch_risk_is_listed_with_its_controls(self):
        from aidlc.policy import load_policy
        risks = {r["id"]: r for r in load_policy("risk-inventory")["risks"]}
        risk = risks["move-base-branch"]
        self.assertEqual(set(risk["controls"]), {"hook-pre", "hook-post", "branch-protection"})
        self.assertIn("base branch", risk["action"])
