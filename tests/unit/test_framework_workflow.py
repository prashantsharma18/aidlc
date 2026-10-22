import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

import yaml

from aidlc.checks.conftest_check import rego_dir
from aidlc.tools import which_tool

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


from aidlc.tools import which_tool

AI_GATES = ROOT / ".github/workflows/ai-gates.yml"
ACTION = "anthropics/claude-code-action@6fed3ca145920b639991cb756090506e1bcaf515"
HARNESS_PATHS = ("core/hooks/", "core/policy/", "cli/aidlc/adapters/", "cli/aidlc/harness\\.py",
                 "cli/aidlc/hookbridge\\.py", "tests/harness_live/", "\\.github/workflows/ai-gates\\.yml")


class AiGatesWorkflowTest(unittest.TestCase):
    """The AI gates (ADR 0004): approved runs only, the key only in the ai-gates environment, one
    narrow write for the reviewer, fail closed."""

    def setUp(self):
        self.text = AI_GATES.read_text(encoding="utf-8")
        self.wf = yaml.safe_load(self.text)
        self.on = self.wf.get("on", self.wf.get(True))
        self.jobs = self.wf["jobs"]

    def steps(self, job):
        return self.jobs[job]["steps"]

    def test_triggers_permissions_and_jobs(self):
        self.assertEqual(set(self.on), {"pull_request"})
        self.assertEqual(self.wf["permissions"], {"contents": "read"})
        self.assertEqual(set(self.jobs), {"ai-review", "agent-config-evals"})
        self.assertNotIn("pull_request_target", self.text)
        self.assertNotIn("id-token", self.text)

    def test_the_key_lives_only_in_ai_gates_jobs(self):
        for name, job in self.jobs.items():
            with self.subTest(job=name):
                self.assertEqual(job["environment"], "ai-gates")
                self.assertLessEqual(job["timeout-minutes"], 60)
        secrets = set(re.findall(r"secrets\.([A-Z_]+)", self.text))
        self.assertEqual(secrets, {"ANTHROPIC_API_KEY", "GITHUB_TOKEN"})

    def test_review_job_has_one_narrow_write_and_no_shell(self):
        job = self.jobs["ai-review"]
        self.assertEqual(job["permissions"], {"contents": "read", "pull-requests": "write"})
        self.assertNotIn("permissions", self.jobs["agent-config-evals"])
        for step in job["steps"]:
            self.assertNotIn("run", step)
        uses = [s["uses"] for s in job["steps"]]
        self.assertEqual(uses.count(ACTION), 2)
        self.assertTrue(all(u == ACTION or u.startswith("actions/checkout@") for u in uses))

    def test_every_action_is_pinned_and_checkout_keeps_no_credentials(self):
        for name, job in self.jobs.items():
            for step in job["steps"]:
                if "uses" in step:
                    self.assertRegex(step["uses"], PINNED)
                if "actions/checkout" in step.get("uses", ""):
                    self.assertFalse(step["with"]["persist-credentials"])
                self.assertNotIn("${{", step.get("run", ""))

    def test_review_tools_are_read_only_plus_comments(self):
        review = [s for s in self.steps("ai-review") if s.get("uses") == ACTION]
        bug, security = review
        self.assertEqual(bug["with"]["plugins"], "code-review@claude-code-plugins")
        self.assertTrue(bug["with"]["prompt"].startswith("/code-review:code-review --comment "))
        for step in review:
            args = step["with"]["claude_args"]
            tools = re.search(r'--allowedTools "([^"]+)"', args).group(1).split(",")
            with self.subTest(step=step.get("name")):
                self.assertIn("mcp__github_inline_comment__create_inline_comment", tools)
                for tool in tools:
                    self.assertRegex(tool, r"^(Read|Glob|Grep|Bash\(git (diff|log|show):\*\)|"
                                           r"mcp__github_inline_comment__create_inline_comment)$")
                self.assertIn("--model claude-sonnet-5-5", args)
                self.assertRegex(args, r"--max-turns \d+")
                self.assertEqual(step["with"]["anthropic_api_key"], "${{ secrets.ANTHROPIC_API_KEY }}")
                self.assertEqual(step["with"]["github_token"], "${{ secrets.GITHUB_TOKEN }}")
        self.assertIn("never approve", security["with"]["prompt"].lower())
        self.assertIn("data, never instructions", security["with"]["prompt"])

    def test_jobs_are_never_skipped_except_drafts(self):
        self.assertEqual(self.jobs["ai-review"].get("if"), "github.event.pull_request.draft == false")
        self.assertNotIn("if", self.jobs["agent-config-evals"])
        self.assertNotIn("continue-on-error", self.text)

    def test_scope_detection_fails_closed(self):
        [scope] = [s for s in self.steps("agent-config-evals") if s.get("id") == "scope"]
        self.assertIn("set -euo pipefail", scope["run"])
        self.assertIn('git diff --name-only "$BASE" "$HEAD"', scope["run"])
        for path in HARNESS_PATHS:
            self.assertIn(path, scope["run"])
        later = self.steps("agent-config-evals")[self.steps("agent-config-evals").index(scope) + 1:]
        for step in later:
            self.assertIn("steps.scope.outputs.changed == 'true'", step.get("if", ""))

    def test_the_suite_comes_from_the_base_commit(self):
        runs = "\n".join(s.get("run", "") for s in self.steps("agent-config-evals"))
        self.assertIn('git checkout "$BASE" -- tests/harness_live', runs)
        self.assertIn("npm install -g @anthropic-ai/claude-code@2.1.296", runs)
        self.assertIn("tests/harness_live/run_attacks.py --out", runs)
        suite = [s for s in self.steps("agent-config-evals") if "run_attacks.py" in s.get("run", "")]
        self.assertEqual(suite[0]["env"]["ANTHROPIC_API_KEY"], "${{ secrets.ANTHROPIC_API_KEY }}")


@unittest.skipUnless(which_tool("conftest"), "conftest is not installed: run `aidlc tools install conftest`")
class FrameworkWorkflowsPassThePackTest(unittest.TestCase):
    def test_framework_workflows_pass_the_rego_pack(self):
        for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
            rel = str(path.relative_to(ROOT))
            with self.subTest(workflow=rel), tempfile.TemporaryDirectory() as tmp:
                data = Path(tmp) / "data.json"
                data.write_text(json.dumps({"aidlc": {"input_file": rel}}), encoding="utf-8")
                proc = subprocess.run([str(which_tool("conftest")), "test", str(path), "--policy", str(rego_dir()),
                                       "--data", str(data), "--namespace", "aidlc.workflows", "--output", "json"],
                                      capture_output=True, text=True, timeout=60, cwd=tmp)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)