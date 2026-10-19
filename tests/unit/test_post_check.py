# tests/unit/test_post_check.py
import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests.helpers import git
from tests.hook_loader import load_hook
from tests.unit.test_guard import GuardEnv, repo_on_branch

post = load_hook("post_check")


def ev(root, tool="edit", output=""):
    return {"session": "s", "call": "c", "tool": tool, "args": {}, "cwd": str(root), "output": output}


def run_main(event):
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(out):
        post.main()
    return out.getvalue()


class PostCheckTest(unittest.TestCase):
    def setUp(self):
        self.repo, self.root = repo_on_branch()
        (self.root / "test").mkdir()
        (self.root / "test" / "a.test.ts").write_text("it('a', () => { expect(f()).toBe(1); });\n")
        (self.root / "test" / "ATests.cs").write_text("Assert.Equal(1, F());\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "tests")
        git(self.root, "branch", "-f", "main", "HEAD")      # base = this commit

    def tearDown(self):
        self.repo.__exit__(None, None, None)

    def test_clean_change_passes(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["src/**", "test/**"])
            (self.root / "src" / "a.ts").write_text("y\n")
            self.assertEqual(post.check(ev(self.root))["decision"], "pass")

    def test_write_outside_scope_flagged(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["src/**"])
            (self.root / "docs").mkdir()
            (self.root / "docs" / "x.md").write_text("x\n")
            r = post.check(ev(self.root, tool="shell"))
            self.assertEqual((r["decision"], r["rule"]), ("flag", "outside-scope"))

    def test_path_with_space_flagged_and_named(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["src/**"])
            (self.root / "docs").mkdir()
            (self.root / "docs" / "a b.md").write_text("x\n")
            r = post.check(ev(self.root, tool="shell"))
            self.assertEqual((r["decision"], r["rule"]), ("flag", "outside-scope"))
            self.assertIn("docs/a b.md", r["reason"])

    def test_changed_assertion_flagged_ts_and_cs(self):
        for path, new in (("test/a.test.ts", "it('a', () => { expect(f()).toBe(2); });\n"),
                          ("test/ATests.cs", "Assert.Equal(2, F());\n")):
            with self.subTest(path=path), GuardEnv() as env:
                env.write_scope(self.root, ["**"])
                (self.root / path).write_text(new)
                r = post.check(ev(self.root))
                self.assertEqual((r["decision"], r["rule"]), ("flag", "changed-assertion"))
                git(self.root, "checkout", "--", path)

    def test_added_assertion_passes(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            with (self.root / "test" / "a.test.ts").open("a") as fh:
                fh.write("it('b', () => { expect(g()).toBe(3); });\n")
            self.assertEqual(post.check(ev(self.root))["decision"], "pass")

    def test_secret_in_output_flagged(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            r = post.check(ev(self.root, tool="shell", output="key AKIAABCDEFGHIJKLMNOP"))
            self.assertEqual(r["rule"], "secret-in-output")

    def test_no_scope_flagged(self):
        with GuardEnv():
            self.assertEqual(post.check(ev(self.root))["rule"], "no-scope")

    def test_read_tools_skip_repository_checks(self):
        with GuardEnv():
            self.assertEqual(post.check(ev(self.root, tool="read"))["decision"], "pass")

    def test_inherited_git_env_does_not_leak(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            os.environ["GIT_DIR"] = "/nonexistent"
            try:
                self.assertEqual(post.check(ev(self.root))["decision"], "pass")
            finally:
                del os.environ["GIT_DIR"]

    def test_unattended_value_does_not_disable_scope(self):
        # guard._unattended() is the single source: "yes" counts as unattended
        with GuardEnv(extra_env={"AIDLC_SCOPE": "off", "AIDLC_UNATTENDED": "yes"}):
            self.assertEqual(post.check(ev(self.root))["rule"], "no-scope")

    def test_printed_result_and_log_redact_secrets(self):
        secret = "AKIAABCDEFGHIJKLMNOP"
        path = self.root / "test" / "a.test.ts"
        path.write_text(f"it('a', () => {{ expect(f()).toBe('{secret}'); }});\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "secret assertion")
        git(self.root, "branch", "-f", "main", "HEAD")
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            path.write_text("it('a', () => { expect(f()).toBe(2); });\n")
            printed = run_main(ev(self.root))
            self.assertEqual(json.loads(printed)["rule"], "changed-assertion")
            self.assertNotIn(secret, printed)
            log = (env.base / "logs" / "decisions.jsonl").read_text()
            self.assertNotIn(secret, log)

    def test_log_record_names_post_tool_check(self):
        with GuardEnv() as env:
            env.write_scope(self.root, ["**"])
            run_main(ev(self.root))
            record = json.loads((env.base / "logs" / "decisions.jsonl").read_text().splitlines()[-1])
            self.assertEqual(record["hook"], "post-tool-check")
