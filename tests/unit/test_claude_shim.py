# tests/unit/test_claude_shim.py
import json
import os
import subprocess
import sys
import unittest

from tests.helpers import git
from tests.hook_loader import HOOKS, load_hook
from tests.unit.test_guard import GuardEnv, repo_on_branch

shim = load_hook("claude_shim")


def run(phase, payload, env_extra=None):
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, str(HOOKS / "claude_shim.py"), phase], input=stdin,
                          capture_output=True, text=True, env={**os.environ, **(env_extra or {})}, timeout=5)


class TranslationTest(unittest.TestCase):
    def test_classes_and_args(self):
        cases = [("Edit", {"file_path": "a"}, "edit", {"path": "a"}),
                 ("MultiEdit", {"file_path": "a"}, "edit", {"path": "a"}),
                 ("NotebookEdit", {"notebook_path": "n.ipynb"}, "edit", {"path": "n.ipynb"}),
                 ("Bash", {"command": "ls", "run_in_background": True}, "shell", {"command": "ls"}),
                 ("WebFetch", {"url": "https://x"}, "external", {"url": "https://x"}),
                 ("mcp__lab-jira__atlassian-rovo-getjiraissue", {"issueIdOrKey": "A-1"}, "mcp",
                  {"name": "mcp__lab-jira__atlassian-rovo-getjiraissue"}),
                 ("Teleport", {}, "unknown", {})]
        for tool, inp, cls, args in cases:
            with self.subTest(tool=tool):
                g = shim.to_generic({"tool_name": tool, "tool_input": inp, "session_id": "s",
                                     "tool_use_id": "t", "cwd": "/tmp"}, "pre")
                self.assertEqual((g["tool"], g["args"]), (cls, args))

    def test_missing_tool_input_is_unknown_safe(self):
        g = shim.to_generic({"tool_name": "Edit"}, "pre")
        self.assertEqual(g["args"], {"path": None})


class ProcessTest(unittest.TestCase):
    def test_allow_is_silent(self):
        with GuardEnv():
            out = run("pre", {"tool_name": "Bash", "tool_input": {"command": "npm run check"}, "cwd": "/tmp"})
            self.assertEqual((out.returncode, out.stdout), (0, ""))

    def test_deny_is_json_with_reason(self):
        with GuardEnv():
            out = run("pre", {"tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": "/tmp"})
            body = json.loads(out.stdout)["hookSpecificOutput"]
            self.assertEqual(body["permissionDecision"], "deny")
            self.assertIn("[aidlc shell-deny]", body["permissionDecisionReason"])

    def test_ask_passes_through(self):
        with GuardEnv():
            out = run("pre", {"tool_name": "WebFetch", "tool_input": {"url": "https://x"}, "cwd": "/tmp"})
            self.assertEqual(json.loads(out.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

    def test_malformed_payload_exits_2(self):
        with GuardEnv():
            out = run("pre", "not json")
            self.assertEqual(out.returncode, 2)

    def test_bad_phase_exits_2(self):
        out = run("sideways", {"tool_name": "Bash"})
        self.assertEqual(out.returncode, 2)

    def test_post_flag_is_block_json(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv():
                out = run("post", {"tool_name": "Bash", "tool_input": {"command": "x"}, "cwd": str(root),
                                   "tool_response": {"stdout": "AKIAABCDEFGHIJKLMNOP"}})
                body = json.loads(out.stdout)
                self.assertEqual(body["decision"], "block")
                self.assertIn("secret-in-output", body["reason"])
        finally:
            repo.__exit__(None, None, None)


class RulingTest(unittest.TestCase):
    def test_non_object_tool_input_exits_2(self):
        with GuardEnv():
            for bad in (["x"], "x", 5):
                with self.subTest(bad=bad):
                    out = run("pre", {"tool_name": "Edit", "tool_input": bad, "cwd": "/tmp"})
                    self.assertEqual(out.returncode, 2)
                    self.assertEqual(out.stdout, "")

    def test_post_reason_is_redacted(self):
        key = "AKIAABCDEFGHIJKLMNOP"
        repo, root = repo_on_branch()
        try:
            (root / "test").mkdir()
            tf = root / "test" / "a.test.ts"
            tf.write_text(f"it('a', () => {{\n  expect(k()).toBe('{key}');\n}});\n")
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "tests")
            git(root, "branch", "-f", "main", "HEAD")
            tf.write_text("it('a', () => {\n});\n")
            with GuardEnv() as env:
                env.write_scope(root, ["src/**", "test/**"])
                out = run("post", {"tool_name": "Edit", "tool_input": {"file_path": str(tf)},
                                   "cwd": str(root), "tool_response": {"ok": True}})
            body = json.loads(out.stdout)
            self.assertEqual(body["decision"], "block")
            self.assertIn("changed-assertion", body["reason"])
            self.assertNotIn(key, out.stdout)
        finally:
            repo.__exit__(None, None, None)

    def test_shim_redacts_unredacted_check_reason_in_process(self):
        # post_check.check() returns unredacted text; the shim must redact what it prints.
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        key = "AKIAABCDEFGHIJKLMNOP"
        fake = {"decision": "flag", "rule": "changed-assertion", "reason": f"line: {key}"}
        post = load_hook("post_check")
        out = io.StringIO()
        with GuardEnv(), mock.patch.object(post, "check", return_value=fake), \
                mock.patch("sys.stdin", io.StringIO(json.dumps({"tool_name": "Edit", "cwd": "/tmp"}))), \
                mock.patch.dict(sys.modules, {"post_check": post}), redirect_stdout(out):
            rc = shim.main(["claude_shim.py", "post"])
        self.assertEqual(rc, 0)
        self.assertNotIn(key, out.getvalue())
        self.assertIn("[REDACTED]", out.getvalue())
