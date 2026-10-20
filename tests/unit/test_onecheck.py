# tests/unit/test_onecheck.py
import json
import os
import re
import sys
import time
import unittest
from datetime import date

import yaml

from aidlc.checks import onecheck
from aidlc.checks.onecheck import FAIL, OK, SKIPPED, local_context, run_check
from aidlc.repo import init_repo, load_config
from tests.helpers import TempRepo, git, run_cli
from tests.unit.test_guard import GuardEnv

PY = sys.executable
RESULT_LINE = re.compile(r"^check  result (PASS|FAIL)  \((\d+) of (\d+) steps failed\)$")


def py(code):
    """A shell command that runs Python code (double quotes are not allowed in `code`)."""
    return f'"{PY}" -c "{code}"'


def installed(commands, steps, files=None):
    """An installed repository on branch feat/SHIP-1-x with the given commands and check steps."""
    repo = TempRepo({"src/app.txt": "a\n", **(files or {})})
    root = repo.__enter__()
    init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 19))
    cfg_path = root / ".aidlc/config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    cfg["commands"], cfg["check_steps"] = commands, steps
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "install")
    git(root, "checkout", "-q", "-b", "feat/SHIP-1-x")
    return repo, root


class EngineTest(unittest.TestCase):
    """The engine with only the scope step as a built-in, so counts are exact."""

    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("print('lint fine')"),
                                          "test": py("import sys; print('boom line'); sys.exit(3)")},
                                         ["lint", "test"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def ctx(self, **kw):
        ctx = local_context(self.root, load_config(self.root))
        for key, value in kw.items():
            setattr(ctx, key, value)
        return ctx

    def run_scope_only(self, ctx):
        return run_check(ctx, builtins=[("scope", onecheck.step_scope)])

    def test_every_step_runs_after_a_failure(self):
        self.env.write_scope(self.root, ["src/**"])
        result = self.run_scope_only(self.ctx())
        self.assertEqual([(s.name, s.status) for s in result.steps],
                         [("lint", OK), ("test", FAIL), ("scope", OK)])
        self.assertEqual(result.summary(), "result FAIL  (1 of 3 steps failed)")
        self.assertEqual(result.steps[1].log, ".check/test.log")
        self.assertIn("boom line", (self.root / ".check/test.log").read_text())

    def test_printed_output_is_one_line_per_step_plus_failing_tail(self):
        self.env.write_scope(self.root, ["src/**"])
        result = self.run_scope_only(self.ctx())
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            onecheck.print_result(result, self.root)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], f"check  {'lint':<16}ok")
        self.assertEqual(lines[1], f"check  {'test':<16}FAIL  exit 3  (full log: .check/test.log)")
        self.assertIn("        | boom line", lines)
        self.assertEqual(lines[-1], "check  result FAIL  (1 of 3 steps failed)")

    def test_missing_scope_fails_closed(self):
        result = self.run_scope_only(self.ctx())
        self.assertEqual(result.steps[-1].status, FAIL)
        self.assertIn("aidlc scope", result.steps[-1].detail)

    def test_write_outside_scope_is_listed(self):
        self.env.write_scope(self.root, ["src/**"])
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs/x.md").write_text("x\n")
        step = self.run_scope_only(self.ctx()).steps[-1]
        self.assertEqual(step.status, FAIL)
        self.assertIn("docs/x.md", step.detail)

    def test_check_scope_skip_is_loud_and_ignored_when_unattended(self):
        os.environ["CHECK_SCOPE"] = "skip"
        try:
            step = self.run_scope_only(self.ctx()).steps[-1]
            self.assertEqual(step.status, SKIPPED)
            self.assertIn("never set by the harness or CI", step.detail)
            os.environ["AIDLC_UNATTENDED"] = "1"
            step = self.run_scope_only(self.ctx()).steps[-1]
            self.assertNotEqual(step.status, SKIPPED)
        finally:
            os.environ.pop("CHECK_SCOPE", None)
            os.environ.pop("AIDLC_UNATTENDED", None)

    def test_unknown_step_fails(self):
        ctx = self.ctx()
        ctx.config.check_steps = ["typecheck"]
        step = run_check(ctx, builtins=[]).steps[0]
        self.assertEqual((step.name, step.status), ("typecheck", FAIL))
        self.assertIn("no command 'typecheck'", step.detail)

    def test_hanging_command_times_out_and_its_children_die(self):
        pidfile = self.root / "child.pid"
        hang = py("import subprocess,sys,time; "
                  f"p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
                  f"open(r'{pidfile}','w').write(str(p.pid)); time.sleep(60)")
        ctx = self.ctx(timeout_s=1)
        ctx.config.commands["test"] = hang
        ctx.config.check_steps = ["test"]
        started = time.monotonic()
        step = run_check(ctx, builtins=[]).steps[0]
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(step.status, FAIL)
        self.assertIn("timed out after 1 s", step.detail)
        child = int(pidfile.read_text())
        time.sleep(0.2)
        with self.assertRaises(ProcessLookupError):
            os.kill(child, 0)

    def test_command_reading_stdin_does_not_hang(self):
        ctx = self.ctx(timeout_s=20)
        ctx.config.commands["test"] = py("input()")
        ctx.config.check_steps = ["test"]
        started = time.monotonic()
        step = run_check(ctx, builtins=[]).steps[0]
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(step.status, FAIL)

    def test_a_step_that_raises_is_a_failure(self):
        def boom(_ctx):
            raise RuntimeError("cannot read")
        step = run_check(self.ctx(), builtins=[("scope", boom)]).steps[-1]
        self.assertEqual(step.status, FAIL)
        self.assertIn("could not run (RuntimeError: cannot read)", step.detail)

    def test_objects_mode_ignores_the_working_tree(self):
        self.env.write_scope(self.root, ["src/**"])
        (self.root / "src/app.txt").write_text("b\n")
        git(self.root, "commit", "-qam", "in scope")
        (self.root / "docs").mkdir(exist_ok=True)
        (self.root / "docs/x.md").write_text("x\n")            # untracked, outside the scope
        head = git(self.root, "rev-parse", "HEAD")
        self.assertEqual(onecheck.changed_paths(self.root, self.ctx().base, head), ["src/app.txt"])
        self.assertEqual(self.run_scope_only(self.ctx(head=head)).steps[-1].status, OK)

    def test_printed_tail_never_follows_a_replaced_log(self):
        secret = self.root.parent / "host-secret.txt"
        secret.write_text("HOST-SECRET-LINE\n")
        ctx = self.ctx()
        ctx.config.commands["test"] = py("import os,sys; os.remove('.check/test.log'); "
                                         f"os.symlink(r'{secret}', '.check/test.log'); print('own line'); sys.exit(1)")
        ctx.config.check_steps = ["test"]
        result = run_check(ctx, builtins=[])
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            onecheck.print_result(result, self.root)
        self.assertNotIn("HOST-SECRET-LINE", out.getvalue())
        self.assertNotIn("tail", result.record(ctx)["steps"][0])

    def test_symlinked_check_dir_is_refused(self):
        (self.root / ".check").symlink_to(self.root.parent)
        with self.assertRaises(onecheck.CheckError):
            run_check(self.ctx(), builtins=[])

    def test_symlinked_gitignore_never_clobbers_its_target(self):
        victim = self.root.parent / "victim.txt"
        victim.write_text("precious\n")
        (self.root / ".check").mkdir()
        (self.root / ".check" / ".gitignore").symlink_to(victim)
        with self.assertRaises(onecheck.CheckError):
            run_check(self.ctx(), builtins=[])
        self.assertEqual(victim.read_text(), "precious\n")

    def test_check_dir_never_shows_as_a_change(self):
        self.env.write_scope(self.root, ["src/**"])
        self.run_scope_only(self.ctx())
        self.assertNotIn(".check", git(self.root, "status", "--porcelain"))

    def test_failing_log_tail_is_redacted(self):
        ctx = self.ctx()
        ctx.config.commands["test"] = py("import sys; print('key AKIA' + 'ABCDEFGHIJKLMNOP'); sys.exit(1)")
        ctx.config.check_steps = ["test"]
        result = run_check(ctx, builtins=[])
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            onecheck.print_result(result, self.root)
        self.assertNotIn("AKIAABCDEFGHIJKLMNOP", out.getvalue())


class CliTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("print(1)")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def test_cli_runs_every_step_and_ends_with_the_contract_line(self):
        self.env.write_scope(self.root, ["src/**"])
        code, out, _ = run_cli("check", "--repo", str(self.root))
        last = out.splitlines()[-1]
        match = RESULT_LINE.match(last)
        self.assertIsNotNone(match, last)
        self.assertEqual(code, 0 if match.group(1) == "PASS" else 1)
        lines = out.splitlines()
        self.assertRegex(lines[0], r"^check  context  repo=\S+  base=[0-9a-f]{40}  scope=\S+  mode=require$")
        names = [line.split()[1] for line in lines[1:-1] if line.startswith("check  ")]
        self.assertEqual(names[:2], ["lint", "scope"])        # command steps first, then built-ins
        self.assertIn("context-drift", names)

    def test_cli_writes_the_record(self):
        self.env.write_scope(self.root, ["src/**"])
        run_cli("check", "--repo", str(self.root))
        record = json.loads((self.root / ".check/result.json").read_text())
        self.assertIn(record["result"], ("PASS", "FAIL"))
        self.assertEqual(record["branch"], "feat/SHIP-1-x")
        self.assertEqual(record["steps"][0]["name"], "lint")

    def test_not_an_installed_repository_exits_2(self):
        with TempRepo({"a.txt": "a\n"}) as root:
            code, out, err = run_cli("check", "--repo", str(root))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("not an installed repository", err)

    def test_named_checks_still_work(self):
        code, out, _ = run_cli("check", "context-drift", str(self.root))
        self.assertIn(code, (0, 1))
        self.assertIn("context-drift:", out)


class SetupErrorTest(unittest.TestCase):
    """Every problem before or after the steps run exits 2 with a message, never a traceback."""

    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("print(1)")}, ["lint"])
        self.env.write_scope(self.root, ["src/**"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def assert_exit_2(self):
        code, out, err = run_cli("check", "--repo", str(self.root))
        self.assertEqual(code, 2, (out, err))
        self.assertNotIn("Traceback", err)
        self.assertIn("aidlc check:", err)

    def test_regular_file_at_check_dir(self):
        (self.root / ".check").write_text("x\n")
        self.assert_exit_2()

    def test_directory_at_check_gitignore(self):
        (self.root / ".check").mkdir()
        (self.root / ".check/.gitignore").mkdir()
        self.assert_exit_2()

    def test_step_plants_result_symlink(self):
        outside = self.root.parent / "outside-record.txt"
        outside.write_text("untouched\n")
        cfg_path = self.root / ".aidlc/config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        cfg["commands"]["lint"] = py(f"import os; os.symlink(r'{outside}', '.check/result.json')")
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        self.assert_exit_2()
        self.assertEqual(outside.read_text(), "untouched\n")


class LongStepNameTest(unittest.TestCase):
    def test_long_names_keep_a_separator(self):
        name = "dependency-audit-xyz1"                      # 21 characters
        result = onecheck.CheckResult([onecheck.StepResult(name, FAIL, "exit 1"),
                                       onecheck.StepResult("lint", OK)])
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            onecheck.print_result(result, None)
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], f"check  {name} FAIL  exit 1")
        self.assertEqual(lines[1], f"check  {'lint':<16}ok")
