# tests/unit/test_final_fixes.py
"""Plan 2 final fix pass (final-fixes.md F1-F11, M1, M4): hook-level behaviour."""
import json
import os
import subprocess
import sys
import unittest

from tests.helpers import git
from tests.hook_loader import HOOKS, load_hook
from tests.unit.test_guard import HARNESS, GuardEnv, edit, repo_on_branch, shell

guard = load_hook("guard")
post = load_hook("post_check")
shim = load_hook("claude_shim")

READ_CONTROL = ("Read", "Glob", "Grep", "LS", "NotebookRead", "TodoWrite", "Task", "Agent",
                "ToolSearch", "BashOutput", "KillShell", "KillBash", "ExitPlanMode", "EnterPlanMode",
                "Skill", "SlashCommand", "AskUserQuestion", "ListMcpResourcesTool",
                "ReadMcpResourceTool")


def ev(root, tool="edit", output=""):
    return {"session": "s", "call": "c", "tool": tool, "args": {}, "cwd": str(root), "output": output}


class F1ToolClassesTest(unittest.TestCase):
    def test_read_and_control_tools_are_class_read(self):
        for name in READ_CONTROL:
            with self.subTest(name=name):
                self.assertEqual(shim.CLASSES.get(name), "read")

    def test_monitor_is_shell_with_its_command(self):
        g = shim.to_generic({"tool_name": "Monitor", "tool_input": {"command": "git push"}}, "pre")
        self.assertEqual((g["tool"], g["args"]), ("shell", {"command": "git push"}))
        with GuardEnv():
            self.assertEqual(guard.decide(g)["decision"], "deny")

    def test_unknown_tool_asks_interactive_denies_unattended(self):
        with GuardEnv():
            r = guard.decide({"tool": "unknown", "args": {}})
            self.assertEqual((r["decision"], r["rule"]), ("ask", "unknown-tool"))
        with GuardEnv(extra_env={"AIDLC_UNATTENDED": "1"}):
            r = guard.decide({"tool": "unknown", "args": {}})
            self.assertEqual((r["decision"], r["rule"]), ("deny", "unknown-tool"))

    def test_bash_output_post_only_scans_for_secrets(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv():                       # no scope: a modifying tool would flag no-scope
                g = shim.to_generic({"tool_name": "BashOutput", "tool_input": {"bash_id": "1"},
                                     "cwd": str(root), "tool_response": {"stdout": "ok"}}, "post")
                self.assertEqual(post.check(g)["decision"], "pass")
                g = shim.to_generic({"tool_name": "BashOutput", "tool_input": {"bash_id": "1"},
                                     "cwd": str(root),
                                     "tool_response": {"stdout": "AKIAABCDEFGHIJKLMNOP"}}, "post")
                self.assertEqual(post.check(g)["rule"], "secret-in-output")
        finally:
            repo.__exit__(None, None, None)


class F2ProtectedCreationTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.root = repo_on_branch()
        git(self.root, "branch", "-f", "main", "HEAD")

    def tearDown(self):
        self.repo.__exit__(None, None, None)

    def test_in_scope_shell_created_agents_md_flagged(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["src/feature/**"])
            (self.root / "src/feature").mkdir(parents=True)
            (self.root / "src/feature/AGENTS.md").write_text("x\n")
            r = post.check(ev(self.root, tool="shell"))
            self.assertEqual((r["decision"], r["rule"]), ("flag", "protected-path"))
            self.assertIn("src/feature/AGENTS.md", r["reason"])
            self.assertIn("commit it, gitignore it, or stop and ask if you did not create it", r["reason"])

    def test_new_claude_local_md_flagged(self):
        harness = dict(HARNESS, protected_paths=HARNESS["protected_paths"] + ["CLAUDE.local.md",
                                                                            "**/CLAUDE.local.md"])
        with GuardEnv() as env:
            (env.base / "harness.json").write_text(json.dumps(harness))
            env.write_scope(self.root, ["**"])
            (self.root / "CLAUDE.local.md").write_text("x\n")
            self.assertEqual(post.check(ev(self.root, tool="shell"))["rule"], "protected-path")

    def test_case_variant_flagged(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            (self.root / "src/Agents.MD").write_text("x\n")
            self.assertEqual(post.check(ev(self.root, tool="shell"))["rule"], "protected-path")

    def test_gitignored_protected_file_not_flagged(self):
        harness = dict(HARNESS, protected_paths=HARNESS["protected_paths"] + ["CLAUDE.local.md"])
        with GuardEnv() as env:
            (env.base / "harness.json").write_text(json.dumps(harness))
            env.write_scope(self.root, ["src/**", ".gitignore"])
            (self.root / ".gitignore").write_text("CLAUDE.local.md\n")
            (self.root / "CLAUDE.local.md").write_text("x\n")
            self.assertEqual(post.check(ev(self.root, tool="shell"))["decision"], "pass")


class F3BaseRefTest(unittest.TestCase):
    def test_base_moving_commands_denied(self):
        with GuardEnv():
            for cmd in ("git branch -f main HEAD", "git branch -D main", "git branch -d main",
                        "git branch -M main", "git branch -m main old", "git branch -m feat/x main",
                        "git branch --force main HEAD", "git update-ref refs/heads/main HEAD",
                        "git update-ref -d refs/heads/main", "git update-ref main HEAD",
                        "git checkout -B main", "git checkout -b main", "git switch -C main",
                        "git switch -c main", "git fetch . HEAD:main", "git fetch . HEAD:refs/heads/main",
                        "git push . HEAD:main", "git -C . branch -f main HEAD",
                        "echo ok && git branch -f main HEAD"):
                with self.subTest(cmd=cmd):
                    r = guard.decide(shell(cmd))
                    self.assertEqual((r["decision"], r["rule"]), ("deny", "base-ref"))

    def test_base_from_harness_data(self):
        with GuardEnv() as env:
            (env.base / "harness.json").write_text(json.dumps(dict(HARNESS, base_branch="master")))
            self.assertEqual(guard.decide(shell("git branch -f master HEAD"))["rule"], "base-ref")
            self.assertEqual(guard.decide(shell("git branch -f main HEAD"))["decision"], "allow")

    def test_ordinary_branch_commands_allowed(self):
        with GuardEnv():
            for cmd in ("git branch feat/y", "git checkout -b feat/y", "git switch -c feat/y",
                        "git checkout main", "git symbolic-ref HEAD refs/heads/main",
                        "git branch -f feat/y main", "git log main"):
                with self.subTest(cmd=cmd):
                    self.assertEqual(guard.decide(shell(cmd))["decision"], "allow")

    def test_invalid_base_branch_fails_closed(self):
        with GuardEnv() as env:
            (env.base / "harness.json").write_text(json.dumps(dict(HARNESS, base_branch=5)))
            self.assertEqual(guard.decide(shell("ls"))["decision"], "deny")

    def test_post_check_uses_recorded_base_after_main_moves(self):
        repo, root = repo_on_branch()
        try:
            base = git(root, "rev-parse", "main")
            with GuardEnv() as env:
                env.write_scope(root, [f"base: {base}", "src/**"])
                (root / "docs").mkdir()
                (root / "docs/x.md").write_text("x\n")
                git(root, "add", "docs/x.md")
                git(root, "commit", "-q", "-m", "out of scope")
                git(root, "branch", "-f", "main", "HEAD")
                r = post.check(ev(root, tool="shell"))
                self.assertEqual((r["decision"], r["rule"]), ("flag", "outside-scope"))
        finally:
            repo.__exit__(None, None, None)

    def test_malformed_base_line_is_no_scope(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                env.write_scope(root, ["base: not-a-sha", "src/**"])
                self.assertEqual(guard.decide(edit(root, "src/a.ts"))["rule"], "no-scope")
        finally:
            repo.__exit__(None, None, None)

    def test_base_line_is_not_a_pattern(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                env.write_scope(root, ["base: " + "a" * 40, "src/**"])
                self.assertEqual(guard.load_scope(root), ["src/**"])
                self.assertEqual(guard.scope_base(root), "a" * 40)
        finally:
            repo.__exit__(None, None, None)


class F4BaseBranchTest(unittest.TestCase):
    def test_post_check_uses_harness_base_branch(self):
        repo, root = repo_on_branch()
        try:
            git(root, "branch", "-m", "main", "master")
            with GuardEnv() as env:
                (env.base / "harness.json").write_text(json.dumps(dict(HARNESS, base_branch="master")))
                env.write_scope(root, ["src/**"])
                (root / "src/a.ts").write_text("y\n")
                self.assertEqual(post.check(ev(root))["decision"], "pass")
        finally:
            repo.__exit__(None, None, None)


class F6CredentialRegexTest(unittest.TestCase):
    def test_ordinary_code_not_blocked(self):
        for text in ("password: string;", "const token = getToken();", "apiKey: process.env.X",
                     'password = "${PASSWORD}"', 'token = "my_token_name2"',
                     'secret: "process.env.SECRET_1"', 'api_key = os.environ["API_KEY_2"]'):
            with self.subTest(text=text):
                self.assertIsNone(guard.BLOCK_SECRET_RE.search(text))
                self.assertIsNone(guard.BLOCK_SECRET_RE.search(json.dumps({"stdout": text})))

    def test_credentials_blocked(self):
        for text in ("AKIAABCDEFGHIJKLMNOP", "-----BEGIN PRIVATE KEY-----",
                     "-----BEGIN RSA PRIVATE KEY-----", 'api_key = "sk9f8a7d6s5a4f3d2s1a"',
                     "Authorization: Bearer abcdefghijklmnopqrstuvwxyz0123",
                     "glpat-abcdefghij0123456789", "AIza" + "a1B2c3D4e5" * 3 + "abcde",
                     "ghp_" + "a" * 36, "sk-ant-" + "a1" * 12, "xoxb-1234567890-abc"):
            with self.subTest(text=text):
                self.assertTrue(guard.BLOCK_SECRET_RE.search(text))
                self.assertTrue(guard.BLOCK_SECRET_RE.search(json.dumps({"stdout": text})))

    def test_post_check_does_not_block_ordinary_code(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                env.write_scope(root, ["src/**"])
                out = json.dumps({"stdout": "const token = getToken();\npassword: string;"})
                self.assertEqual(post.check(ev(root, tool="read", output=out))["decision"], "pass")
                out = json.dumps({"stdout": 'api_key = "sk9f8a7d6s5a4f3d2s1a"'})
                self.assertEqual(post.check(ev(root, tool="read", output=out))["rule"], "secret-in-output")
        finally:
            repo.__exit__(None, None, None)


class F8ShimFailureLoggedTest(unittest.TestCase):
    def test_malformed_stdin_logs_one_fail_safe_record(self):
        for phase, hook, decision in (("pre", "pre-tool-guard", "deny"), ("post", "post-tool-check", "flag")):
            with self.subTest(phase=phase), GuardEnv() as env:
                out = subprocess.run([sys.executable, str(HOOKS / "claude_shim.py"), phase],
                                     input="not json", capture_output=True, text=True, timeout=5)
                self.assertEqual(out.returncode, 2)
                lines = (env.base / "logs" / "decisions.jsonl").read_text().splitlines()
                self.assertEqual(len(lines), 1)
                record = json.loads(lines[0])
                self.assertEqual((record["hook"], record["decision"], record["rule"]),
                                 (hook, decision, "fail-safe"))
                self.assertIsNone(record["tool"])

    def test_logging_failure_never_raises(self):
        with GuardEnv(extra_env={"AIDLC_LOG_DIR": "/proc/aidlc-cannot-write"}):
            out = subprocess.run([sys.executable, str(HOOKS / "claude_shim.py"), "pre"],
                                 input="not json", capture_output=True, text=True, timeout=5,
                                 env=dict(os.environ))
            self.assertEqual(out.returncode, 2)
            self.assertNotIn("Traceback", out.stderr)


if __name__ == "__main__":
    unittest.main()
