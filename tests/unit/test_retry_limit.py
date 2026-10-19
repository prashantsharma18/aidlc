# tests/unit/test_retry_limit.py
import json
import re
import subprocess
import sys
import unittest
from datetime import date

from aidlc.adapters import get_adapter
from aidlc.checks.doctor import run_doctor
from aidlc.harness import harness_data
from aidlc.policy import load_policy
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git, run_cli
from tests.hook_loader import HOOKS, load_hook
from tests.unit.test_guard import GuardEnv, edit, repo_on_branch, shell

guard = load_hook("guard")
post = load_hook("post_check")
shim = load_hook("claude_shim")

FAIL_TEXT = "check  test            FAIL  exit 1\ncheck  result FAIL  (1 of 6 steps failed)\n"


def context(root, branch="feat/SHIP-1-x", base=None, mode="require", scope=None):
    """The context line `aidlc check` prints for this repository (Task 1)."""
    base = base or git(root, "merge-base", "main", "HEAD")
    scope = scope or guard.scope_file(root, branch)
    return f"check  context  repo={root}  base={base}  scope={scope}  mode={mode}\n"


def pass_text(root, **kw):
    return context(root, **kw) + "check  lint            ok\ncheck  result PASS  (0 of 6 steps failed)\n"


def ran(root, command, text, exit_code):
    return {"session": "s", "call": "c", "tool": "shell", "args": {"command": command},
            "cwd": str(root), "output": text, "text": text, "exit_code": exit_code}


class CheckSegmentsTest(unittest.TestCase):
    CASES = [
        ("aidlc check", (True, True)),
        ("bin/aidlc check --repo .", (True, True)),
        ("env X=1 aidlc check", (True, False)),               # wrappers and assignments are not exact
        ("PATH=/tmp/fake:$PATH aidlc check", (True, False)),
        ("env -i aidlc check", (True, False)),
        ("aidlc check > log.txt", (True, True)),               # exact, but its output is hidden
        ("aidlc check || true", (True, False)),
        ("aidlc check; echo 'check  result PASS  (0 of 1 steps failed)'", (True, False)),
        ("bash -c 'aidlc check'", (True, False)),
        ("echo $(aidlc check)", (True, False)),
        ("aidlc check context-drift .", (False, False)),
        ("echo aidlc check", (False, False)),
        ("npm test", (False, False)),
        ("", (False, False)),
    ]

    def test_cases(self):
        for command, expected in self.CASES:
            with self.subTest(command=command):
                self.assertEqual(guard.check_segments(command), expected)


class CounterTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = repo_on_branch()

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def failures(self):
        return guard.read_failures(self.root, "feat/SHIP-1-x")

    def test_fail_counts_and_pass_resets(self):
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(self.failures(), 2)
        r = post.record_check(ran(self.root, "aidlc check", pass_text(self.root), 0))
        self.assertEqual((r["decision"], r["rule"]), ("pass", "check-recorded"))
        self.assertEqual(self.failures(), 0)

    def test_third_failure_flags_and_guard_denies(self):
        for _ in range(2):
            post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        r = post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual((r["decision"], r["rule"]), ("flag", "retry-limit"))
        self.env.write_scope(self.root, ["src/**"])
        for event in (edit(self.root, "src/a.ts"), shell("npm test", self.root)):
            with self.subTest(tool=event["tool"]):
                d = guard.decide(event)
                self.assertEqual((d["decision"], d["rule"]), ("deny", "retry-limit"))
                self.assertIn("aidlc attempts --reset", d["reason"])
        read = guard.decide({"tool": "read", "args": {"path": "src/a.ts"}, "cwd": str(self.root)})
        self.assertEqual(read["decision"], "allow")

    def test_gaming_shapes_count_as_failures(self):
        (self.root / "src" / "b.ts").write_text("b\n")           # a commit on the branch, so HEAD differs
        git(self.root, "add", "-A")                                # from the merge base the hooks compute
        git(self.root, "commit", "-qm", "branch work")
        good = pass_text(self.root)
        other = self.root.parent / "elsewhere"
        for command, text in (("aidlc check || true", good), ("aidlc check > log.txt", ""),
                              ("aidlc check; echo 'check  result PASS  (0 of 1 steps failed)'", good),
                              ("bash -c 'aidlc check'", good), ("echo $(aidlc check)", good),
                              ("CHECK_SCOPE=skip aidlc check", pass_text(self.root, mode="skip")),
                              ("PATH=/tmp/fake:$PATH aidlc check", good), ("env -i aidlc check", good),
                              ("AIDLC_BASE_REF=HEAD aidlc check",
                               pass_text(self.root, base=git(self.root, "rev-parse", "HEAD"))),
                              ("AIDLC_SCOPE_FILE=/tmp/any.scope aidlc check", pass_text(self.root, scope="/tmp/any.scope")),
                              ("aidlc check --repo ../elsewhere",
                               good.replace(f"repo={self.root}", f"repo={other}")),
                              ("aidlc check", good.replace("check  lint            ok",
                                                           "check  scope           SKIPPED  CHECK_SCOPE=skip"))):
            with self.subTest(command=command):
                before = self.failures()
                post.record_check(ran(self.root, command, text, 0))
                self.assertEqual(self.failures(), before + 1)

    def test_passing_text_with_nonzero_exit_is_a_failure(self):
        post.record_check(ran(self.root, "aidlc check", pass_text(self.root), 1))
        self.assertEqual(self.failures(), 1)

    def test_detached_head_is_counted_and_limited(self):
        git(self.root, "checkout", "-q", "--detach")
        for _ in range(3):
            post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(guard.read_failures(self.root, None), 3)
        d = guard.decide(shell("npm test", self.root))
        self.assertEqual((d["decision"], d["rule"]), ("deny", "retry-limit"))

    def test_counts_survive_parallel_updates(self):
        import threading
        threads = [threading.Thread(target=post.record_check, args=(ran(self.root, "aidlc check", FAIL_TEXT, 1),))
                   for _ in range(8)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(self.failures(), 8)

    def test_unrelated_commands_are_not_counted(self):
        self.assertIsNone(post.record_check(ran(self.root, "npm test", FAIL_TEXT, 1)))
        self.assertEqual(self.failures(), 0)

    def test_unreadable_record_fails_closed(self):
        path = guard.attempts_file(self.root, "feat/SHIP-1-x")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json")
        self.env.write_scope(self.root, ["src/**"])
        self.assertEqual(guard.decide(edit(self.root, "src/a.ts"))["rule"], "retry-limit")
        r = post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(r["rule"], "retry-limit")

    def test_attempts_file_name_is_safe_and_unique_per_repository(self):
        path = guard.attempts_file(self.root, "feat/a.b/c")
        self.assertEqual(path.name, "feat__a.b__c.json")
        self.assertRegex(path.parent.name, rf"^{re.escape(self.root.name)}-[0-9a-f]{{8}}$")
        self.assertEqual(path.parent.parent.name, "attempts")
        twin = self.root.parent / "twin" / self.root.name
        self.assertNotEqual(guard.attempts_file(twin, "feat/a.b/c").parent, path.parent)
        self.assertEqual(guard.attempts_file(self.root, None).name, "__detached__.json")


class ShimPostFailureTest(unittest.TestCase):
    def run_shim(self, phase, payload):
        return subprocess.run([sys.executable, str(HOOKS / "claude_shim.py"), phase],
                              input=json.dumps(payload), capture_output=True, text=True, timeout=10)

    def test_post_failure_event_carries_exit_code_and_text(self):
        g = shim.to_generic({"tool_name": "Bash", "tool_input": {"command": "aidlc check"},
                             "error": "Exit code 1\n" + FAIL_TEXT}, "post-failure")
        self.assertEqual((g["exit_code"], g["hook"]), (1, "post-tool-check"))
        self.assertIn("check  result FAIL", g["text"])

    def test_post_event_text_is_stdout_and_stderr(self):
        g = shim.to_generic({"tool_name": "Bash", "tool_input": {"command": "x"},
                             "tool_response": {"stdout": "out", "stderr": "err"}}, "post")
        self.assertEqual((g["exit_code"], g["text"]), (0, "out\nerr"))

    def test_three_failing_checks_block_through_the_shim(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                env.write_scope(root, ["**"])
                payload = {"tool_name": "Bash", "tool_input": {"command": "aidlc check"}, "cwd": str(root),
                           "error": "Exit code 1\n" + FAIL_TEXT}
                outs = [self.run_shim("post-failure", payload) for _ in range(3)]
                self.assertEqual([o.returncode for o in outs], [0, 0, 0])
                self.assertEqual(outs[0].stdout, "")
                body = json.loads(outs[2].stdout)
                self.assertEqual(body["decision"], "block")
                self.assertIn("[aidlc retry-limit]", body["reason"])
        finally:
            repo.__exit__(None, None, None)

    def test_failed_shell_write_of_a_protected_file_is_flagged(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                env.write_scope(root, ["src/**"])
                (root / "src" / "AGENTS.md").write_text("x\n")
                out = self.run_shim("post-failure", {"tool_name": "Bash", "cwd": str(root),
                                                     "tool_input": {"command": "echo x > src/AGENTS.md; exit 1"},
                                                     "error": "Exit code 1\n"})
                self.assertIn("[aidlc protected-path]", json.loads(out.stdout)["reason"])
        finally:
            repo.__exit__(None, None, None)


class WiringTest(unittest.TestCase):
    def test_harness_data_and_policy(self):
        with TempRepo({"package.json": "{}\n"}) as root:
            init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
            self.assertEqual(harness_data(root)["retry_cap"], 3)
            [settings] = get_adapter("claude-code").render_permissions(root)
            entry = json.loads(settings.content)["hooks"]["PostToolUseFailure"][0]
            self.assertEqual(entry["hooks"][0]["onFailure"], "block")
            self.assertTrue(entry["hooks"][0]["command"].endswith('claude_shim.py" post-failure'))
        self.assertIn("aidlc attempts*--reset*", load_policy("permissions")["deny"]["shell"])
        risk = {r["id"]: r for r in load_policy("risk-inventory")["risks"]}["runaway-loop"]
        self.assertTrue({"retry-limit", "hook-pre", "hook-post"} <= set(risk["controls"]))

    def test_doctor_requires_the_failure_hook(self):
        with TempRepo({"package.json": "{}\n"}) as root:
            init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
            run_cli("render", "--tool", "claude-code", str(root))
            path = root / ".claude/settings.json"
            s = json.loads(path.read_text())
            del s["hooks"]["PostToolUseFailure"]
            path.write_text(json.dumps(s, indent=2) + "\n")
            msgs = [str(f) for f in run_doctor(root, which=lambda n: "/usr/bin/x", claude_version="2.1.296")]
            self.assertTrue(any("D4 PostToolUseFailure" in m for m in msgs))

    def test_attempts_cli_status_and_reset(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv():
                for _ in range(3):
                    post.record_check(ran(root, "aidlc check", FAIL_TEXT, 1))
                code, out, _ = run_cli("attempts", "--repo", str(root))
                self.assertEqual(code, 1)
                self.assertIn("3 failing check(s) in a row on feat/SHIP-1-x (limit 3)", out)
                code, out, _ = run_cli("attempts", "--repo", str(root), "--reset")
                self.assertEqual(code, 0)
                self.assertEqual(guard.read_failures(root, "feat/SHIP-1-x"), 0)
                code, _, _ = run_cli("attempts", "--repo", str(root), "--rese")   # no abbreviations
                self.assertEqual(code, 2)
        finally:
            repo.__exit__(None, None, None)


class SymlinkedRecordTest(unittest.TestCase):
    def test_symlinked_record_is_never_written_through_and_counts_as_the_limit(self):
        with GuardEnv():
            repo, root = repo_on_branch()
            try:
                path = guard.attempts_file(root, "feat/SHIP-1-x")
                path.parent.mkdir(parents=True, exist_ok=True)
                target = root.parent / "victim.json"
                target.write_text('{"failures": 0}')
                path.symlink_to(target)
                self.assertIsNone(guard.read_failures(root, "feat/SHIP-1-x"))
                r = post.record_check(ran(root, "aidlc check", FAIL_TEXT, 1))
                self.assertEqual(r["rule"], "retry-limit")
                self.assertEqual(target.read_text(), '{"failures": 0}')
            finally:
                repo.__exit__(None, None, None)
