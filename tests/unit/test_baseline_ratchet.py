# tests/unit/test_baseline_ratchet.py
import os
import unittest

import yaml
from datetime import date, timedelta

from aidlc import ci
from aidlc.baseline import BASELINE
from aidlc.checks.onecheck import FAIL, OK, local_context
from aidlc.repo import CONFIG, load_config
from tests.unit.test_baseline import FUTURE, PAST, entry
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed, py


class RatchetTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({"lint": py("pass"), "format": py("pass")}, ["lint"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def judge(self, base_text, head_text, head_steps=None):
        if head_text is not None:
            (self.root / BASELINE).write_text(head_text, encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))      # the base's configuration
        ctx.steering = {} if base_text is None else {BASELINE: base_text}
        if head_steps is not None:                                   # the change's configuration
            data = yaml.safe_load((self.root / CONFIG).read_text(encoding="utf-8"))
            data["check_steps"] = head_steps
            (self.root / CONFIG).write_text(yaml.safe_dump(data), encoding="utf-8")
        return ci.step_baseline(ctx)

    def test_runs_in_ci_before_config_policy(self):
        names = [n for n, _ in ci.JUDGE_STEPS]
        self.assertEqual(names[-2:], ["baseline", "config-policy"])

    def test_no_baseline_anywhere_passes(self):
        self.assertEqual(self.judge(None, None).status, OK)

    def test_shrinking_passes(self):
        both = entry() + entry("skips", "pkg.A skip")
        step = self.judge(both, entry())
        self.assertEqual(step.status, OK)
        self.assertIn("1 paid off", step.detail)

    def test_a_new_entry_fails_the_ratchet(self):
        for head in (entry(), entry("skips", "pkg.A skip")):
            with self.subTest(head=head):
                step = self.judge("", head)
                self.assertEqual(step.status, FAIL)
                self.assertIn("may only shrink", step.detail)

    def test_a_new_step_may_start_report_only(self):
        # format is not in the base's check_steps, and the change adds it
        self.assertEqual(self.judge("", entry(key="format"), head_steps=["lint", "format"]).status, OK)

    def test_a_new_report_only_step_must_be_added_by_the_change(self):
        step = self.judge("", entry(key="lint-v2"))                  # in neither configuration: pre-seeding
        self.assertEqual(step.status, FAIL)
        self.assertIn("may only shrink", step.detail)

    def test_a_date_moved_later_is_named(self):
        later = (date.today() + timedelta(days=90)).isoformat()
        step = self.judge(entry(), entry(when=later))
        self.assertEqual(step.status, OK)
        self.assertIn(f"lint: {FUTURE} -> {later}", step.detail)

    def test_ci_reads_the_head_baseline_from_git_objects(self):
        from tests.helpers import git
        (self.root / BASELINE).write_text(entry(), encoding="utf-8")
        git(self.root, "add", BASELINE)
        git(self.root, "commit", "-qm", "baseline")
        head = git(self.root, "rev-parse", "HEAD")
        (self.root / BASELINE).write_text(entry() + entry("skips", "pkg.A new")[len(""):], encoding="utf-8")
        ctx = local_context(self.root, load_config(self.root))
        ctx.steering, ctx.head = {BASELINE: entry()}, head
        self.assertEqual(ci.step_baseline(ctx).status, OK)          # the uncommitted skip is not the change

    def test_an_expired_entry_fails(self):
        step = self.judge(entry(when=PAST), entry(when=PAST))
        self.assertEqual(step.status, FAIL)
        self.assertIn("review date", step.detail)

    def test_moving_a_date_is_a_reviewed_decision_not_growth(self):
        later = (date.today() + timedelta(days=90)).isoformat()
        self.assertEqual(self.judge(entry(), entry(when=later)).status, OK)

    def test_a_linked_head_baseline_fails(self):
        target = self.root / "elsewhere.yaml"
        target.write_text(entry(), encoding="utf-8")
        os.symlink(target, self.root / BASELINE)
        self.assertEqual(self.judge(entry(), None).status, FAIL)

    def test_a_malformed_head_baseline_fails(self):
        self.assertEqual(self.judge("", "report_only: nope\n").status, FAIL)
