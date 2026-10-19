# tests/unit/test_onecheck_skips.py
import base64
import os
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path

import yaml

from aidlc.checks import onecheck
from aidlc.checks.onecheck import FAIL, NA, OK, local_context, run_check
from aidlc.repo import init_repo, load_config
from tests.helpers import TempRepo
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed, py
from tests.unit.test_test_reports import JUNIT

REPORT = ".check/junit.xml"


def write_report(text):
    """A test command that writes `text` to .check/junit.xml (as a test runner would). The text is
    passed as base64, so quotes in it never meet the shell."""
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    return py("import base64,pathlib; pathlib.Path('.check').mkdir(exist_ok=True); "
              f"pathlib.Path('{REPORT}').write_bytes(base64.b64decode('{b64}'))")


class SkipStepTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"test": write_report("<testsuite><testcase name='a'/></testsuite>")},
                                         ["test"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def skips(self, reports=(REPORT,), command=None):
        ctx = local_context(self.root, load_config(self.root))
        ctx.config.test_reports = list(reports)
        if command:
            ctx.config.commands["test"] = command
        return run_check(ctx, builtins=[("skips", onecheck.step_skips)]).steps[-1]

    def test_builtins_order(self):
        self.assertEqual([n for n, _ in onecheck.BUILTINS],
                         ["scope", "protected-tests", "skips", "context-drift", "secrets"])

    def test_all_tests_ran(self):
        step = self.skips()
        self.assertEqual(step.status, OK)
        self.assertEqual(step.detail, "1 tests, 0 not run, 0 unexpected")

    def test_unexpected_skip_fails(self):
        step = self.skips(command=write_report(JUNIT))
        self.assertEqual(step.status, FAIL)
        self.assertIn("1 unexpected", step.detail)
        self.assertIn("pkg.A skip", step.detail)

    def test_declared_skip_passes(self):
        (self.root / "test").mkdir(exist_ok=True)
        (self.root / onecheck.ALLOWED_SKIPS).write_text("pkg.A skip # needs the carrier sandbox; CI runs it\n")
        cmd = write_report("<testsuite><testcase classname='pkg.A' name='ok'/>"
                           "<testcase classname='pkg.A' name='skip'><skipped/></testcase></testsuite>")
        self.assertEqual(self.skips(command=cmd).status, OK)

    def test_declared_skip_without_reason_does_not_count(self):
        (self.root / "test").mkdir(exist_ok=True)
        (self.root / onecheck.ALLOWED_SKIPS).write_text("pkg.A skip\n")
        self.assertEqual(self.skips(command=write_report(JUNIT)).status, FAIL)

    def test_stale_report_never_passes_even_if_just_written(self):
        (self.root / ".check").mkdir(exist_ok=True)
        (self.root / REPORT).write_text("<testsuite><testcase name='a'/></testsuite>")   # a moment ago
        step = self.skips(command=py("print('tests did not write a report')"))
        self.assertEqual(step.status, FAIL)
        self.assertIn("did the tests run?", step.detail)

    def test_ci_reads_the_allow_list_from_the_trusted_checkout(self):
        (self.root / "test").mkdir(exist_ok=True)
        (self.root / onecheck.ALLOWED_SKIPS).write_text("pkg.A skip # the change declares its own skip\n")
        ctx = local_context(self.root, load_config(self.root))
        ctx.config.test_reports = [REPORT]
        ctx.config.commands["test"] = write_report(JUNIT)
        ctx.steering = {}                                            # the base has no such declaration
        step = run_check(ctx, builtins=[("skips", onecheck.step_skips)]).steps[-1]
        self.assertEqual(step.status, FAIL)

    def test_no_report_configured_fails(self):
        step = self.skips(reports=())
        self.assertEqual(step.status, FAIL)
        self.assertIn("test_reports is empty", step.detail)

    def test_empty_report_fails(self):
        step = self.skips(command=write_report("<testsuite></testsuite>"))
        self.assertEqual(step.status, FAIL)
        self.assertIn("lists no tests", step.detail)

    def test_unparseable_report_fails(self):
        self.assertEqual(self.skips(command=write_report("<oops")).status, FAIL)

    def test_no_test_step_is_not_applicable(self):
        ctx = local_context(self.root, load_config(self.root))
        ctx.config.check_steps = []
        step = run_check(ctx, builtins=[("skips", onecheck.step_skips)]).steps[-1]
        self.assertEqual(step.status, NA)

    def test_report_outside_the_checkout_is_ignored(self):
        outside = Path(tempfile.mkdtemp())
        (self.root / "link").symlink_to(outside)
        text = "<testsuite><testcase name='a'/></testsuite>"
        cmd = py(f"open('{outside}/r.xml','w').write('{text}')")
        step = self.skips(reports=("link/r.xml",), command=cmd)
        self.assertEqual(step.status, FAIL)
        self.assertIn("did the tests run?", step.detail)


class ConfigTest(unittest.TestCase):
    def test_bad_test_reports_rejected(self):
        for bad in ("x.xml", ["../x.xml"], ["/tmp/x.xml"], ["~/x.xml"], [5], [""]):
            with self.subTest(bad=bad), TempRepo({"a": "a\n"}) as root:
                init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 19))
                cfg_path = root / ".aidlc/config.yaml"
                cfg = yaml.safe_load(cfg_path.read_text())
                cfg["test_reports"] = bad
                cfg_path.write_text(yaml.safe_dump(cfg))
                with self.assertRaises(ValueError):
                    load_config(root)

    def test_init_repo_writes_profile_test_reports(self):
        with TempRepo({"package.json": "{}\n"}) as root:
            init_repo(root, "svc", "team", "node", "purpose", date(2026, 10, 19))
            self.assertEqual(load_config(root).test_reports, [".check/test-report.json"])

