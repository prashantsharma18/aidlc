# tests/unit/test_baseline.py
import unittest
from datetime import date, timedelta

from aidlc import baseline
from aidlc.baseline import BaselineError, active, parse
from aidlc.checks import onecheck
from aidlc.checks.onecheck import FAIL, OK, REPORTED, StepResult, local_context, report_only, run_check
from aidlc.repo import load_config
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed, py
from tests.unit.test_onecheck_skips import REPORT, write_report

FUTURE = (date.today() + timedelta(days=30)).isoformat()
PAST = (date.today() - timedelta(days=1)).isoformat()


def entry(kind="report_only", key="lint", when=FUTURE):
    field = "step" if kind == "report_only" else "test"
    return f"{kind}:\n  - {{{field}: {key!r}, owner: '@team', review_by: '{when}', reason: 'existing debt'}}\n"


class ParseTest(unittest.TestCase):
    def test_empty_means_no_entries(self):
        self.assertEqual(parse(""), [])

    def test_both_kinds(self):
        entries = parse(entry() + entry("skips", "pkg.A skip"))
        self.assertEqual({(e.kind, e.key) for e in entries}, {("report_only", "lint"), ("skips", "pkg.A skip")})

    def test_test_and_build_can_never_be_report_only(self):
        for step in ("test", "build", "install", "restore"):
            with self.subTest(step=step), self.assertRaises(BaselineError):
                parse(entry(key=step))

    def test_a_malformed_baseline_fails_closed(self):
        for text in ("[1, 2]", "report_only: x\n", "secrets: []\n", "report_only:\n  - {step: lint}\n",
                     entry().replace("'@team'", "''"), entry(when="soon"), entry() + entry()[len("report_only:\n"):]):
            with self.subTest(text=text), self.assertRaises(BaselineError):
                parse(text)

    def test_active_drops_expired_entries(self):
        entries = parse(entry(when=PAST))
        self.assertEqual(active(entries, "report_only"), {})


class ReportOnlyTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("raise SystemExit(1)")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def lint(self, text=None):
        if text is not None:
            (self.root / baseline.BASELINE).write_text(text, encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        return run_check(ctx, builtins=[]).steps[0]

    def test_a_failing_step_fails_without_a_baseline(self):
        self.assertEqual(self.lint().status, FAIL)

    def test_a_baselined_step_is_reported_not_failed(self):
        step = self.lint(entry())
        self.assertEqual(step.status, REPORTED)
        self.assertIn("report-only until", step.detail)

    def test_an_expired_report_only_entry_fails_again(self):
        self.assertEqual(self.lint(entry(when=PAST)).status, FAIL)

    def test_a_passing_step_stays_ok(self):
        ctx = local_context(self.root, load_config(self.root))
        self.assertEqual(report_only(ctx, StepResult("lint", OK, "")).status, OK)

    def test_ci_reads_the_base_baseline_not_the_change(self):
        (self.root / baseline.BASELINE).write_text(entry(), encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        ctx.steering = {}                                  # the base has no baseline
        self.assertEqual(report_only(ctx, StepResult("lint", FAIL, "x")).status, FAIL)

    def test_a_malformed_baseline_fails_the_step(self):
        self.assertEqual(self.lint("report_only: nope\n").status, FAIL)


class BaselineSkipsTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        cmd = write_report("<testsuite><testcase classname='pkg.A' name='ok'/>"
                           "<testcase classname='pkg.A' name='skip'><skipped/></testcase></testsuite>")
        self.repo, self.root = installed({"test": cmd}, ["test"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def skips(self):
        ctx = local_context(self.root, load_config(self.root))
        ctx.config.test_reports = [REPORT]
        return run_check(ctx, builtins=[("skips", onecheck.step_skips)]).steps[-1]

    def test_a_baselined_skip_is_accepted_until_its_date(self):
        self.assertEqual(self.skips().status, FAIL)
        (self.root / baseline.BASELINE).write_text(entry("skips", "pkg.A skip"), encoding="utf-8")
        self.assertEqual(self.skips().status, OK)
        (self.root / baseline.BASELINE).write_text(entry("skips", "pkg.A skip", PAST), encoding="utf-8")
        self.assertEqual(self.skips().status, FAIL)

    def test_reported_does_not_count_as_a_failure(self):
        result = onecheck.CheckResult([StepResult("lint", REPORTED, "")])
        self.assertTrue(result.passed)


class ReviewFixesTest(unittest.TestCase):
    """Final review of Plan 5.1."""

    def test_whitespace_cannot_smuggle_a_never_report_only_step(self):
        for key in (" test", "test ", "compile", "Lint", "lint step"):
            with self.subTest(key=key), self.assertRaises(BaselineError):
                parse(entry(key=key))

    def test_step_names_follow_the_check(self):
        self.assertEqual(baseline.STEP_NAME.pattern, onecheck.STEP_NAME.pattern)

    def test_review_by_is_a_plain_date(self):
        for when in ("2027-01-31 10:00:00", "20270131", "2027-W05-1"):
            text = f"report_only:\n  - {{step: lint, owner: '@t', review_by: {when}, reason: r}}\n"
            with self.subTest(when=when), self.assertRaises(BaselineError):
                parse(text)


class BadBaselineKeepsTheFailureTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("raise SystemExit(1)")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def test_a_bad_baseline_keeps_the_original_failure(self):
        (self.root / baseline.BASELINE).write_text("report_only: nope\n", encoding="utf-8")
        step = run_check(local_context(self.root, load_config(self.root)), builtins=[]).steps[0]
        self.assertEqual(step.status, FAIL)
        self.assertIn("exit 1", step.detail)
        self.assertIn("baseline not applied", step.detail)
        self.assertTrue(step.log)

    def test_a_reported_step_still_points_to_its_log(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            onecheck.print_result(onecheck.CheckResult([StepResult("lint", REPORTED, "x", log=".check/lint.log")]),
                                  self.root)
        self.assertIn("(full log: .check/lint.log)", out.getvalue())
