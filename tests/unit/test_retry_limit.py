# tests/unit/test_retry_limit.py
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest import mock
from datetime import date
from pathlib import Path

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


ORIGINAL_WRITABLE_ROOTS = guard.writable_roots


def repo_only_roots(cwd):
    """Writable roots for tests whose stub entry lives under /tmp: only the repository counts."""
    top = guard.repo_root(Path(cwd or os.getcwd()))
    return [os.path.realpath(top)] if top else []


def install_entry(base, name="real", case=None):
    """A stub `aidlc` (the framework's entry point) on PATH, recorded in cli.json. The ambient
    PATH is never relied on. Call inside GuardEnv (it sets AIDLC_HOME_DIR and restores the env)."""
    stub = Path(base) / name / "aidlc"
    stub.parent.mkdir(parents=True, exist_ok=True)
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    home = Path(os.environ["AIDLC_HOME_DIR"])
    home.mkdir(parents=True, exist_ok=True)
    (home / "cli.json").write_text(json.dumps({"entry": str(stub.resolve())}))
    os.environ["PATH"] = f"{stub.parent}{os.pathsep}/usr/bin{os.pathsep}/bin"
    if case is not None:                       # the stub is under /tmp, so keep only the repository writable
        for module in (guard, post.guard):      # post_check imports its own copy of guard
            patcher = mock.patch.object(module, "writable_roots", repo_only_roots)
            patcher.start()
            case.addCleanup(patcher.stop)
    return stub


def write_run(root, run):
    (root / ".check").mkdir(exist_ok=True)
    (root / ".check" / "result.json").write_text(json.dumps({"result": "FAIL", "run": run}))


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
        with GuardEnv(), tempfile.TemporaryDirectory() as tmp:
            stub = install_entry(tmp, case=self)
            (Path(tmp) / "bin").mkdir()
            (Path(tmp) / "bin" / "aidlc").symlink_to(stub)       # `bin/aidlc` relative to cwd
            for command, expected in self.CASES:
                with self.subTest(command=command):
                    self.assertEqual(guard.check_segments(command, tmp), expected)

    def test_named_checks_after_repo_are_not_the_one_check(self):
        for command in ("aidlc check --repo . context-drift", "aidlc check --repo=. openwiki",
                        "aidlc check context-drift --repo ."):
            with self.subTest(command=command):
                self.assertEqual(guard.check_segments(command), (False, False))
        self.assertEqual(guard.check_segments("aidlc check --repo context-drift")[0], True)

    def test_only_the_framework_entry_point_is_exact(self):
        with GuardEnv(), tempfile.TemporaryDirectory() as tmp:
            install_entry(tmp, case=self)
            fake = Path(tmp) / "fakebin" / "aidlc"
            fake.parent.mkdir()
            fake.write_text("#!/bin/sh\nexit 0\n")
            fake.chmod(0o755)
            self.assertEqual(guard.check_segments(f"{fake} check", tmp), (True, False))     # by path
            self.assertEqual(guard.check_segments("../fakebin/aidlc check", f"{tmp}/real"), (True, False))
            os.environ["PATH"] = f"{fake.parent}{os.pathsep}{os.environ['PATH']}"           # earlier on PATH
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, False))
            os.environ["PATH"] = f"{Path(tmp) / 'real'}{os.pathsep}{os.environ['PATH']}"
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, True))

    def test_missing_or_bad_cli_json_is_never_exact(self):
        with GuardEnv(), tempfile.TemporaryDirectory() as tmp:
            install_entry(tmp, case=self)
            cli = Path(os.environ["AIDLC_HOME_DIR"]) / "cli.json"
            cli.write_text(json.dumps({"entry": 5}))
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, False))
            cli.write_text("{nope")
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, False))
            cli.unlink()
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, False))
            elsewhere = Path(tmp) / "elsewhere.json"
            elsewhere.write_text(json.dumps({"entry": str((Path(tmp) / "real" / "aidlc").resolve())}))
            cli.symlink_to(elsewhere)                                                        # a symlinked cli.json
            self.assertEqual(guard.check_segments("aidlc check", tmp), (True, False))


class CounterTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = repo_on_branch()
        self.stubs = tempfile.TemporaryDirectory()
        install_entry(self.stubs.name, case=self)

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)
        self.stubs.cleanup()

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


class ArtefactCountingTest(unittest.TestCase):
    """Runs the command parser cannot see (python3 -m aidlc check, $A check, make) still count, once,
    from the new run id in the check's own record."""

    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = repo_on_branch()
        self.stubs = tempfile.TemporaryDirectory()
        install_entry(self.stubs.name, case=self)

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)
        self.stubs.cleanup()

    def failures(self):
        return guard.read_failures(self.root, "feat/SHIP-1-x")

    def adopt(self, run="r0"):
        write_run(self.root, run)                                 # the first sight of a run is not counted
        self.assertIsNone(post.record_check(ran(self.root, "ls", "", 0)))

    def test_unseen_run_counts_once(self):
        self.adopt()
        for command in ("python3 -m aidlc check", "A=aidlc; $A check"):
            with self.subTest(command=command):
                before = self.failures()
                write_run(self.root, uuid.uuid4().hex)
                r = post.record_check(ran(self.root, command, "", 1))
                self.assertEqual(r["rule"], "check-recorded")
                self.assertEqual(self.failures(), before + 1)
                self.assertIsNone(post.record_check(ran(self.root, "ls", "", 0)))   # same run: not again
                self.assertEqual(self.failures(), before + 1)

    def test_post_phase_counts_too(self):
        self.adopt()
        write_run(self.root, "r1")
        post.record_check(ran(self.root, "make check", "", 0))
        self.assertEqual(self.failures(), 1)

    def test_canonical_pass_stores_the_run(self):
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        write_run(self.root, "r2")
        post.record_check(ran(self.root, "aidlc check", pass_text(self.root), 0))
        self.assertEqual(self.failures(), 0)
        self.assertIsNone(post.record_check(ran(self.root, "ls", "", 0)))
        self.assertEqual(self.failures(), 0)

    def test_bad_artefacts_are_no_signal(self):
        (self.root / ".check").mkdir(exist_ok=True)
        result = self.root / ".check" / "result.json"
        self.adopt()
        for body in ("{nope", json.dumps({"run": 5}), json.dumps([1]), json.dumps({"x": "y" * (1 << 21), "run": "a"})):
            result.write_text(body)
            self.assertIsNone(post.record_check(ran(self.root, "ls", "", 0)))
        result.unlink()
        other = self.root / "other.json"
        other.write_text(json.dumps({"run": "linked"}))
        result.symlink_to(other)
        self.assertIsNone(post.record_check(ran(self.root, "ls", "", 0)))
        self.assertEqual(self.failures(), 0)

    def test_forged_pass_from_a_fake_entry_point_is_a_failure(self):
        fake = Path(self.stubs.name) / "fakebin" / "aidlc"
        fake.parent.mkdir()
        fake.write_text("#!/bin/sh\nexit 0\n")
        fake.chmod(0o755)
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        post.record_check(ran(self.root, f"{fake} check", pass_text(self.root), 0))
        self.assertEqual(self.failures(), 2)


class RecordIntegrityTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = repo_on_branch()
        self.path = guard.attempts_file(self.root, "feat/SHIP-1-x")

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def test_symlinked_lock_or_directory_is_at_the_limit(self):
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(guard.read_failures(self.root, "feat/SHIP-1-x"), 1)
        lock = self.path.parent / ".lock"
        lock.unlink()
        lock.symlink_to(self.root / "src" / "a.ts")
        self.assertIsNone(guard.read_failures(self.root, "feat/SHIP-1-x"))
        r = post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(r["rule"], "retry-limit")
        self.assertEqual((self.root / "src" / "a.ts").read_text(), "x\n")

    def test_symlinked_attempts_directory_is_at_the_limit_and_never_written(self):
        real = Path(tempfile.mkdtemp())
        home = Path(os.environ["AIDLC_HOME_DIR"])
        home.mkdir(parents=True, exist_ok=True)
        (home / "attempts").symlink_to(real)
        self.assertIsNone(guard.read_failures(self.root, "feat/SHIP-1-x"))
        r = post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        self.assertEqual(r["rule"], "retry-limit")
        self.assertEqual(list(real.iterdir()), [])

    def test_symlinked_repository_directory_is_at_the_limit(self):
        real = Path(tempfile.mkdtemp())
        self.path.parent.parent.mkdir(parents=True)
        self.path.parent.symlink_to(real)
        self.assertIsNone(guard.read_failures(self.root, "feat/SHIP-1-x"))


class CliEntryTest(unittest.TestCase):
    def test_render_records_the_entry_point(self):
        with TempRepo({"package.json": "{}\n"}) as root, tempfile.TemporaryDirectory() as home:
            init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
            saved = dict(os.environ)
            os.environ["AIDLC_HOME_DIR"] = home
            try:
                self.assertEqual(run_cli("render", "--tool", "claude-code", str(root))[0], 0)
                entry = json.loads((Path(home) / "cli.json").read_text())["entry"]
                self.assertEqual(entry, str((Path(__file__).resolve().parents[2] / "bin" / "aidlc").resolve()))
                self.assertEqual(guard.cli_entry(), entry)
            finally:
                os.environ.clear()
                os.environ.update(saved)

    def test_check_record_carries_a_run_id(self):
        from aidlc.checks.onecheck import CheckResult
        rec = CheckResult([]).record(type("C", (), {"branch": "b", "base": "x"})())
        self.assertRegex(rec["run"], r"^[0-9a-f]{32}$")


class _Both:
    def __init__(self, *patches):
        self.patches = patches

    def __enter__(self):
        for patch in self.patches:
            patch.start()

    def __exit__(self, *exc):
        for patch in self.patches:
            patch.stop()


class EntryPointLocationTest(unittest.TestCase):
    """The entry point must be where the agent cannot write (guard.trusted_entry), and it must stay
    there: a fake that links itself to the entry after running is not credited."""

    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = repo_on_branch()
        self.safe = tempfile.TemporaryDirectory()               # stands for a directory outside every writable root
        self.stub = install_entry(self.safe.name)               # the real, unpatched writable roots stay in force
        self.entry = str(self.stub.resolve())
        os.environ["TMPDIR"] = "/nonexistent-tmpdir"

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)
        self.safe.cleanup()

    def test_with_the_real_rule_a_tmp_entry_is_not_trusted(self):
        self.assertFalse(guard.trusted_entry(self.entry, str(self.root), self.entry))

    def outside(self):
        roots = lambda cwd: [os.path.realpath(self.root)]  # noqa: E731
        stack = mock.patch.object(guard, "writable_roots", roots)
        stack2 = mock.patch.object(post.guard, "writable_roots", roots)
        return _Both(stack, stack2)

    def test_entry_by_absolute_path_and_a_link_outside_the_roots_pass(self):
        link_dir = Path(self.safe.name) / "bin"
        link_dir.mkdir()
        (link_dir / "aidlc").symlink_to(self.entry)
        with self.outside():
            self.assertTrue(guard.trusted_entry(self.entry, str(self.root), self.entry))
            self.assertTrue(guard.trusted_entry(str(link_dir / "aidlc"), str(self.root), self.entry))

    def test_a_link_inside_the_repository_or_tmp_is_not_trusted(self):
        (self.root / ".check").mkdir()
        inside = self.root / ".check" / "aidlc"
        inside.symlink_to(self.entry)
        with self.outside():
            self.assertFalse(guard.trusted_entry(".check/aidlc", str(self.root), self.entry))
        with tempfile.TemporaryDirectory() as tmp:               # /tmp is writable under the real rule
            linked = Path(tmp) / "aidlc"
            linked.symlink_to(self.entry)
            self.assertFalse(guard.trusted_entry(str(linked), str(self.root), self.entry))

    def test_a_chain_through_a_writable_hop_is_not_trusted(self):
        hop = self.root / "hop"
        hop.symlink_to(self.entry)
        outer = Path(self.safe.name) / "bin"
        outer.mkdir()
        (outer / "aidlc").symlink_to(hop)                        # safe link -> link in the repository -> entry
        with self.outside():
            self.assertFalse(guard.trusted_entry(str(outer / "aidlc"), str(self.root), self.entry))

    def test_a_link_loop_is_not_trusted(self):
        a, b = Path(self.safe.name) / "a", Path(self.safe.name) / "b"
        a.symlink_to(b)
        b.symlink_to(a)
        with self.outside():
            self.assertFalse(guard.trusted_entry(str(a), str(self.root), self.entry))

    def test_a_relative_path_entry_is_never_trusted(self):
        bin_dir = Path(self.safe.name) / "bin"
        bin_dir.mkdir()
        (bin_dir / "aidlc").symlink_to(self.entry)
        os.environ["PATH"] = os.path.relpath(bin_dir, self.root)
        with self.outside():
            self.assertFalse(guard.trusted_entry("aidlc", str(self.root), self.entry))
            os.environ["PATH"] = str(bin_dir)
            self.assertTrue(guard.trusted_entry("aidlc", str(self.root), self.entry))

    def test_self_replacing_fake_gets_no_pass(self):
        fake = self.root / ".check" / "aidlc"
        fake.parent.mkdir()
        fake.write_text("#!/bin/sh\nexit 0\n")
        post.record_check(ran(self.root, "aidlc check", FAIL_TEXT, 1))
        fake.unlink()
        fake.symlink_to(self.entry)                              # what `ln -sf <entry> "$0"` leaves behind
        with self.outside():
            post.record_check(ran(self.root, ".check/aidlc check", pass_text(self.root), 0))
        self.assertEqual(guard.read_failures(self.root, "feat/SHIP-1-x"), 2)


class SafePathLauncherTest(unittest.TestCase):
    def test_a_planted_package_in_the_cwd_does_not_replace_the_cli(self):
        framework = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "aidlc").mkdir()
            (Path(tmp) / "aidlc" / "__init__.py").write_text("")
            (Path(tmp) / "aidlc" / "__main__.py").write_text("print('PLANTED-CLI')\n")
            out = subprocess.run([str(framework / "bin" / "aidlc"), "--help"], cwd=tmp, capture_output=True,
                                 text=True, timeout=30)
        self.assertNotIn("PLANTED-CLI", out.stdout)
        self.assertIn("usage: aidlc", out.stdout)


class MinorsTest(unittest.TestCase):
    def test_abbreviated_option_on_check_is_a_usage_error(self):
        with TempRepo({"package.json": "{}\n"}) as root:
            code, _, _ = run_cli("check", "--re", str(root), "context-drift")
            self.assertEqual(code, 2)

    def test_reset_keeps_the_current_run_so_the_next_call_counts_nothing(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv():
                for _ in range(3):
                    post.record_check(ran(root, "aidlc check", FAIL_TEXT, 1))
                write_run(root, "on-disk")
                self.assertEqual(run_cli("attempts", "--repo", str(root), "--reset")[0], 0)
                self.assertIsNone(post.record_check(ran(root, "ls", "", 0)))
                self.assertEqual(guard.read_failures(root, "feat/SHIP-1-x"), 0)
                write_run(root, "newer")
                post.record_check(ran(root, "make check", "", 1))
                self.assertEqual(guard.read_failures(root, "feat/SHIP-1-x"), 1)
        finally:
            repo.__exit__(None, None, None)

    def test_render_warns_when_the_entry_point_is_missing(self):
        with TempRepo({"package.json": "{}\n"}) as root:
            init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
            with mock.patch("aidlc.cliinfo.entry_point", return_value=None):
                code, _, err = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 0)
            self.assertIn("aidlc render: warning: framework entry point not found; the retry limit "
                          "will never credit a PASS", err)
