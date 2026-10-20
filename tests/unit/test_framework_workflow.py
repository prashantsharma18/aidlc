import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/framework-ci.yml"
PINNED = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")


class FrameworkWorkflowTest(unittest.TestCase):
    """The framework's own CI (ADR 0002): public repository, so a read-only token and no secrets."""

    def setUp(self):
        self.wf = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.on = self.wf.get("on", self.wf.get(True))      # YAML 1.1 reads a bare `on` as True

    def test_framework_workflow_is_read_only_and_pinned(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        self.assertNotIn("secrets.", text)
        self.assertNotIn("pull_request_target", text)
        for job in self.wf["jobs"].values():
            self.assertNotIn("permissions", job)
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], PINNED)
                if "actions/checkout" in step.get("uses", ""):
                    self.assertFalse(step["with"]["persist-credentials"])
                self.assertNotIn("${{", step.get("run", ""))

    def test_jobs_and_triggers(self):
        self.assertEqual(set(self.wf["jobs"]), {"unit", "sandbox", "policy"})
        self.assertEqual(set(self.on), {"push", "pull_request"})
        self.assertEqual(self.on["push"]["branches"], ["main"])

    def test_every_job_has_a_timeout(self):
        # A hung job would otherwise run for GitHub's 6-hour maximum (Plan 3.5 review, minor 10).
        for name, job in self.wf["jobs"].items():
            with self.subTest(job=name):
                self.assertIn("timeout-minutes", job)
                self.assertLessEqual(job["timeout-minutes"], 30)
