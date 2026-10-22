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


AI_GATES = ROOT / ".github/workflows/ai-gates.yml"
ACTION = "anthropics/claude-code-action@6fed3ca145920b639991cb756090506e1bcaf515"


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
                    self.assertNotIn(":*)", tool)             # no wildcard command rules (Plan 4b review)
                    self.assertNotIn(tool, ("Read", "Glob", "Grep", "Bash"))
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
        self.assertIn('git diff --quiet --no-renames "$BASE" "$HEAD" -- . \':(exclude)docs/\'', scope["run"])
        later = self.steps("agent-config-evals")[self.steps("agent-config-evals").index(scope) + 1:]
        for step in later:
            self.assertIn("steps.scope.outputs.changed == 'true'", step.get("if", ""))

    def test_the_suite_comes_from_the_base_commit(self):
        runs = "\n".join(s.get("run", "") for s in self.steps("agent-config-evals"))
        self.assertIn('git checkout --no-overlay "$BASE" -- tests/harness_live', runs)
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


def scope_script() -> str:
    wf = yaml.safe_load(AI_GATES.read_text(encoding="utf-8"))
    [step] = [s for s in wf["jobs"]["agent-config-evals"]["steps"] if s.get("id") == "scope"]
    return step["run"]


class AiGatesReviewFixesTest(unittest.TestCase):
    """Final review of Plan 4b: detection that cannot miss a change, a judge the change cannot alter,
    tools that cannot read the key, and a report that never publishes it."""

    def detect(self, change) -> tuple[int, str]:
        from tests.helpers import TempRepo, git
        files = {"core/hooks/guard.py": "g\n", "cli/aidlc/scope.py": "s\n", "docs/a.md": "a\n"}
        with TempRepo(files) as root, tempfile.TemporaryDirectory() as tmp:
            base = git(root, "rev-parse", "HEAD")
            change(root, git)
            git(root, "add", "-A")
            git(root, "commit", "-qm", "head")
            head = git(root, "rev-parse", "HEAD").strip()
            out = Path(tmp) / "out"
            out.write_text("")
            env = {"PATH": "/usr/bin:/bin", "HOME": tmp, "BASE": base, "HEAD": head,
                   "GITHUB_OUTPUT": str(out), "GIT_CONFIG_NOSYSTEM": "1"}
            if getattr(change, "bad_base", False):
                env["BASE"] = "0" * 40
            done = subprocess.run(["bash", "-c", scope_script()], cwd=root, env=env, capture_output=True, text=True)
            return done.returncode, out.read_text()

    def test_a_rename_out_of_the_harness_is_a_change(self):
        code, out = self.detect(lambda root, git: git(root, "mv", "core/hooks/guard.py", "tools_guard.py"))
        self.assertEqual((code, out.strip()), (0, "changed=true"))

    def test_any_code_change_outside_docs_is_a_change(self):
        code, out = self.detect(lambda root, git: (root / "cli/aidlc/scope.py").write_text("t\n"))
        self.assertEqual((code, out.strip()), (0, "changed=true"))

    def test_a_docs_only_change_skips_the_suite(self):
        code, out = self.detect(lambda root, git: (root / "docs/a.md").write_text("b\n"))
        self.assertEqual((code, out.strip()), (0, "changed=false"))

    def test_an_unknown_base_fails_the_job(self):
        def change(root, git):
            (root / "docs/a.md").write_text("b\n")
        change.bad_base = True
        code, out = self.detect(change)
        self.assertNotEqual(code, 0)
        self.assertNotIn("changed=", out)

    def test_the_judge_is_restored_exactly_and_runs_isolated(self):
        runs = "\n".join(s.get("run", "") for s in yaml.safe_load(AI_GATES.read_text())["jobs"]["agent-config-evals"]["steps"])
        self.assertIn('git checkout --no-overlay "$BASE" -- tests/harness_live tests/helpers.py tests/__init__.py', runs)
        self.assertIn("python3 -I tests/harness_live/run_attacks.py", runs)
        suite = (ROOT / "tests/harness_live/run_attacks.py").read_text()
        self.assertNotIn("sys.path.insert(0", suite)
        self.assertIn("sys.path.append(str(ROOT))", suite)

    def test_review_steps_scrub_the_key_from_subprocesses(self):
        wf = yaml.safe_load(AI_GATES.read_text())
        for step in wf["jobs"]["ai-review"]["steps"]:
            if step.get("uses", "").startswith("anthropics/claude-code-action@"):
                self.assertEqual(step["env"]["CLAUDE_CODE_SUBPROCESS_ENV_SCRUB"], "1")

    def test_security_pass_tools_are_exact(self):
        wf = yaml.safe_load(AI_GATES.read_text())
        security = wf["jobs"]["ai-review"]["steps"][2]
        tools = re.search(r'--allowedTools "([^"]+)"', security["with"]["claude_args"]).group(1).split(",")
        self.assertEqual(tools, ["Read(./**)",
                                 "Bash(git diff ${{ github.event.pull_request.base.sha }}...${{ github.event.pull_request.head.sha }})",
                                 "mcp__github_inline_comment__create_inline_comment"])

    def test_the_report_is_uploaded_only_without_the_key(self):
        steps = yaml.safe_load(AI_GATES.read_text())["jobs"]["agent-config-evals"]["steps"]
        [check] = [s for s in steps if s.get("id") == "keycheck"]
        self.assertIn('grep -qF -- "$KEY"', check["run"])
        self.assertEqual(check["env"]["KEY"], "${{ secrets.ANTHROPIC_API_KEY }}")
        [upload] = [s for s in steps if "upload-artifact" in s.get("uses", "")]
        self.assertIn("steps.keycheck.outcome == 'success'", upload["if"])
        self.assertLess(steps.index(check), steps.index(upload))
