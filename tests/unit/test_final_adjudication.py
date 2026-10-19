# tests/unit/test_final_adjudication.py
"""Plan 2 final re-review residuals adjudicated by the controller (ledger "Final: Ruling N1/N2/N5")."""
import json
import subprocess
import sys
import unittest

from tests.helpers import git
from tests.hook_loader import HOOKS, load_hook
from tests.unit.test_guard import GuardEnv, repo_on_branch

guard = load_hook("guard")
post = load_hook("post_check")
shim = load_hook("claude_shim")

# Built-in tools of the pinned Claude Code version (2.1.296) that only read, track tasks or talk
# to other agents: they must not prompt on every call.
PINNED_READ = ("TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "TaskStop", "TaskOutput", "LSP",
               "SendMessage")
# Built-ins with side effects outside the edit/shell classes: deliberately unknown (ask a person).
PINNED_ASK = ("EnterWorktree", "ExitWorktree", "CronCreate", "Workflow", "Artifact")


def ev(root, tool="shell"):
    return {"session": "s", "call": "c", "tool": tool, "args": {}, "cwd": str(root), "output": ""}


class N1PinnedBuiltinsTest(unittest.TestCase):
    def test_task_and_lsp_tools_are_read(self):
        for name in PINNED_READ:
            with self.subTest(name=name), GuardEnv(extra_env={"AIDLC_UNATTENDED": "1"}):
                g = shim.to_generic({"tool_name": name, "tool_input": {}}, "pre")
                self.assertEqual(g["tool"], "read")
                self.assertEqual(guard.decide(g)["decision"], "allow")

    def test_side_effect_builtins_still_ask(self):
        for name in PINNED_ASK:
            with self.subTest(name=name), GuardEnv():
                g = shim.to_generic({"tool_name": name, "tool_input": {}}, "pre")
                self.assertEqual(guard.decide(g)["decision"], "ask")


class N5MissingToolNameTest(unittest.TestCase):
    def test_missing_or_non_string_tool_name_exits_2(self):
        for payload in ({"tool_input": {}}, {"tool_name": "", "tool_input": {}},
                        {"tool_name": ["Bash"], "tool_input": {}}, {"tool_name": 5}):
            with self.subTest(payload=payload), GuardEnv():
                out = subprocess.run([sys.executable, str(HOOKS / "claude_shim.py"), "pre"],
                                     input=json.dumps(payload), capture_output=True, text=True,
                                     timeout=5)
                self.assertEqual((out.returncode, out.stdout), (2, ""))


class N2BaseMovedHintTest(unittest.TestCase):
    def test_rebased_branch_flag_says_rescope(self):
        repo, root = repo_on_branch()
        try:
            old_base = git(root, "rev-parse", "main")
            with GuardEnv() as env:
                env.write_scope(root, [f"base: {old_base}", "src/**"])
                git(root, "checkout", "-q", "main")
                (root / "AGENTS.md").write_text("# team update\n")
                git(root, "add", "AGENTS.md")
                git(root, "commit", "-q", "-m", "teammate")
                git(root, "checkout", "-q", "-")
                git(root, "rebase", "-q", "main")
                r = post.check(ev(root))
                self.assertEqual((r["decision"], r["rule"]), ("flag", "protected-path"))
                self.assertIn("re-run aidlc scope", r["reason"])
        finally:
            repo.__exit__(None, None, None)

    def test_unmoved_base_has_no_rescope_hint(self):
        repo, root = repo_on_branch()
        try:
            base = git(root, "rev-parse", "main")
            with GuardEnv() as env:
                env.write_scope(root, [f"base: {base}", "src/**"])
                (root / "src" / "AGENTS.md").write_text("x\n")
                r = post.check(ev(root))
                self.assertEqual(r["rule"], "protected-path")
                self.assertNotIn("re-run aidlc scope", r["reason"])
                self.assertIn("commit it on the base branch", r["reason"])
        finally:
            repo.__exit__(None, None, None)


if __name__ == "__main__":
    unittest.main()
