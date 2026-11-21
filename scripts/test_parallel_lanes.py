"""Plan 23: parallel lanes (ADR 0025). A third kind of skill, workflow, and its first skill, `parallel-lanes`; one
release line at the tracked stages' gates; independent slices as sibling pull requests; the stacked-slice update; and
the behaviour cases that prove a lane holds at a person's decision."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402
from test_validate import package  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DESIGN = "docs/design/2026-11-21-parallel-lanes.md"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def section(text: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed text."""
    return text.split(heading, 1)[1].split(" ## ", 1)[0]


def clean_env() -> dict:
    """The environment with every GIT_ variable removed, so a throwaway repository never reaches an outer one, and
    with no user or system configuration, so no global hook runs."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return dict(env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
                GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                PYTHONDONTWRITEBYTECODE="1")


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run git in a throwaway repository."""
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, env=clean_env(), check=check,
                          capture_output=True, text=True)


def sh(command: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run one command line from a skill, its placeholders already filled, in a throwaway repository."""
    return subprocess.run(command, shell=True, cwd=cwd, env=clean_env(), capture_output=True, text=True)


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    ADR = "docs/adr/0025-parallel-lanes.md"

    def test_adr_0025_is_proposed_with_a_decider(self):
        text = read(self.ADR)
        self.assertIn("Status: Proposed (2026-11-21)", text)
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = flat(self.ADR)
        for phrase in ("Amends: ADR 0015", "a third kind of skill, workflow (`metadata.kind: workflow`)", "`QUEUE.md`",
                       "git refuses to check out a branch that another worktree already has",
                       "Lanes for one repository start from one clone on one machine",
                       "`waiting: <decision> by <who>`", "sibling pull requests", "`git rebase --onto`",
                       "`plans/<KEY>/slice-<n>/`", "keeps `disable-model-invocation: true`, and so does `parallel-lanes`",
                       "`Read <absolute path>/skills/parallel-lanes/SKILL.md before anything else.`",
                       "`pstack/skills/poteto-mode/SKILL.md`",
                       "only load from a slash command, so they reach another agent no other way",
                       "aidlc borrows pstack's way of passing instructions, not its autonomy",
                       "aidlc still ships no script and no workflow, and needs no code-host feature"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0015_points_to_the_amendment_and_keeps_its_last_section(self):
        text = read("docs/adr/0015-work-routes-and-the-part-model.md")
        self.assertIn("Amended by ADR 0025 (proposed, 2026-11-21): one pull request per independent slice", text)
        self.assertLess(text.index("Amended by ADR 0025"), text.index("## Context"))
        self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"))


WORKFLOW_BODY = """# Title

## When to use
x
## Inputs
x
## Steps
1. x
## Stop if
x
## Common excuses
x
## Red flags
x
## Rules
- You draft; you never approve.
"""


def workflow(name: str, body: str = WORKFLOW_BODY, kind: str = "workflow") -> str:
    return (f"---\nname: {name}\ndescription: Runs work across sessions. Use when needed.\nmetadata:\n  kind: {kind}\n"
            f"  invocation: auto\n---\n{body}")


class WorkflowKindTest(unittest.TestCase):
    """Task 2: a third kind of skill, workflow, with its own sections and two naming rules (ADR 0025)."""

    def check(self, skills: dict) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            package(Path(tmp), skills, assets=())
            return validate.validate(Path(tmp))

    def test_a_workflow_in_the_workflow_format_has_no_problems(self):
        self.assertEqual(self.check({"parallel-lanes": workflow("parallel-lanes")}), [])
        self.assertEqual(validate.WORKFLOW_SECTIONS, ("## When to use", "## Inputs", "## Steps", "## Stop if",
                                                      "## Common excuses", "## Red flags", "## Rules"))

    def test_a_workflow_needs_every_workflow_section(self):
        body = WORKFLOW_BODY.replace("## Inputs\nx\n", "")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("missing section '## Inputs'" in p for p in problems), problems)

    def test_a_workflow_keeps_the_sections_in_order(self):
        body = WORKFLOW_BODY.replace("## Inputs\nx\n## Steps\n1. x\n", "## Steps\n1. x\n## Inputs\nx\n")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("out of order" in p for p in problems), problems)

    def test_a_workflow_ends_its_rules_with_the_gate_line(self):
        body = WORKFLOW_BODY.replace("- You draft; you never approve.", "- ok")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("You draft; you never approve." in p for p in problems), problems)

    def test_a_workflow_name_never_starts_with_aidlc(self):
        problems = self.check({"aidlc-lanes": workflow("aidlc-lanes")})
        self.assertTrue(any("a workflow name never starts with 'aidlc-'" in p for p in problems), problems)
        self.assertFalse(any("'## Produces'" in p for p in problems), problems)

    def test_a_workflow_name_never_starts_with_an_ing_word(self):
        for name in ("running-lanes", "queueing"):
            problems = self.check({name: workflow(name)})
            self.assertTrue(any("a workflow name never starts with an '-ing' word" in p for p in problems),
                            (name, problems))

    def test_a_quoted_workflow_kind_or_one_with_a_comment_is_still_a_workflow(self):
        for kind in ("'workflow'", "workflow  # see ADR 0025"):
            problems = self.check({"parallel-lanes": workflow("parallel-lanes", "# Essay\n", kind)})
            self.assertTrue(any("missing section '## Inputs'" in p for p in problems), (kind, problems))

    def test_the_rules_file_names_the_workflow_kind(self):
        standards = flat("AGENTS.md").split("## Standards", 1)[1].split(" ## ", 1)[0]
        self.assertIn("Workflow skills (`metadata.kind: workflow`, ADR 0025) run work across sessions and keep: When "
                      "to use, Inputs, Steps, Stop if, Common excuses, Red flags, Rules", standards)
        self.assertIn("a workflow name never starts with `aidlc-` or with an \"-ing\" word", standards)
        self.assertIn("`using-aidlc` (`metadata.kind: map`) keeps the open format", standards)

    def test_a_workflow_name_may_start_with_a_noun_that_ends_in_ing(self):
        for name in ("ring-buffer", "thing-map", "string-tools", "spring-lanes", "ingest-queue"):
            self.assertEqual(self.check({name: workflow(name)}), [], name)

    def test_the_other_kinds_are_unaffected_next_to_a_workflow(self):
        stage_body = WORKFLOW_BODY.replace("## Steps\n1. x\n", "## Steps\n1. x\n## Produces\nx\n## Gate\nx\n")
        practice_body = WORKFLOW_BODY.replace("## Inputs\nx\n", "").replace("## Stop if", "## Checks\nx\n## Stop if")
        skills = {"parallel-lanes": workflow("parallel-lanes"),
                  "aidlc-stage": workflow("aidlc-stage", stage_body, "stage"),
                  "doing-checks": workflow("doing-checks", practice_body, "practice")}
        self.assertEqual(self.check(skills), [])
        broken = dict(skills, **{"aidlc-stage": workflow("aidlc-stage", WORKFLOW_BODY, "stage")})
        self.assertTrue(any("missing section '## Produces'" in p for p in self.check(broken)))

    def test_a_workflow_kind_in_the_body_or_unindented_is_not_a_workflow(self):
        in_body = workflow("parallel-lanes", "# Essay\n  kind: workflow\n", "other")
        top_level = ("---\nname: parallel-lanes\ndescription: Runs work. Use when needed.\nkind: workflow\n---\n"
                     "# Essay\n")
        self.assertEqual(self.check({"parallel-lanes": in_body}), [])
        self.assertEqual(self.check({"parallel-lanes": top_level}), [])


if __name__ == "__main__":
    unittest.main()
