"""Plan 24: fewer approvals (ADR 0026). One decisions-by-tier table in the tiers file decides where a person stops; a
decision is asked once; at Tier 1 a person decides only Ready and Merge; teams list their standard changes in
`AGENTS.md`, and `aidlc-start` routes them as route S."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = "docs/design/2026-11-21-fewer-approvals.md"
ADR = "docs/adr/0026-decisions-by-tier-and-standard-changes.md"
TIERS_COPIES = tuple(f"skills/{s}/assets/tiers.md" for s in
                     ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review"))
DECIDE = ("A person decides here only where the tiers file's decisions table lists this decision; otherwise state "
          "what you did and go on.")


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


def gate(name: str) -> str:
    """A stage skill's Gate section, whitespace-collapsed."""
    return section(skill(name), "## Gate")


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


def front(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---") else ""


def scaffold(case: str, folder: Path) -> None:
    """Build a case's scaffold in an empty folder, as the eval runner does."""
    subprocess.run(["bash", str(ROOT / "evals" / case / "setup.sh")], cwd=folder, env=clean_env(), check=True,
                   capture_output=True, text=True)


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    AMENDED = {"0012-mechanical-recipe-commit": "the recipe pause is lifted for a recipe class",
               "0015-work-routes-and-the-part-model": "route S, for the standard changes a team lists",
               "0020-approved-documents-merge-first": "each pull request approval is the record"}

    def test_adr_0026_is_proposed_with_a_decider(self):
        text = read(ADR)
        self.assertIn("Status: Proposed (2026-11-21)", text)
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = flat(ADR)
        for phrase in ("Amends: ADR 0012", "ADR 0015", "ADR 0020",
                       "One decisions-by-tier table, in the tiers file every stage reads",
                       "Tier 1: two blocking decisions, Ready and Merge",
                       "Ready is the work, its acceptance criteria and its tier",
                       "the engineer who confirms the brief confirms its tier",
                       "No decision is asked twice", "the pull request approval is the record",
                       "the AI writes the work item's entry from it, with how it was confirmed, and asks before posting",
                       "The code owner approves once, at Merge", "deciding the findings is the diff review",
                       "The readiness record's Decision cites the change-management record",
                       "A \"Standard changes\" section in the team's `AGENTS.md`", "route S",
                       "It never stretches a class",
                       "the build's separate recipe-review pause is lifted",
                       "aidlc still ships no code and needs no code-host feature (ADR 0024)"):
            self.assertIn(phrase, body, phrase)

    def test_each_amended_adr_points_to_the_amendment_and_keeps_its_last_section(self):
        for name, phrase in self.AMENDED.items():
            text = read(f"docs/adr/{name}.md")
            line = f"Amended by ADR 0026 (proposed, 2026-11-21): {phrase}"
            self.assertIn(line, " ".join(text.split()), name)
            self.assertLess(text.index("Amended by ADR 0026"), text.index("## Context"), name)
            self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"), name)


TIERS_DOCS = "docs/operating-model/tiers-table.md"


def decision_rows(rel: str) -> dict:
    """The decisions table's rows, by their first cell."""
    table = read(rel).split("## Decisions by tier", 1)[1]
    return {cells[0]: cells[1:] for cells in
            ([c.strip() for c in line.strip().strip("|").split(" | ")] for line in table.splitlines()
             if line.startswith("| **"))}


class TiersTest(unittest.TestCase):
    """Task 2: one decisions-by-tier table, identical in the six copies and in the operating model's copy."""

    def test_the_six_copies_are_identical_and_the_docs_copy_matches(self):
        texts = {read(rel) for rel in TIERS_COPIES}
        self.assertEqual(len(texts), 1)
        text = texts.pop()
        self.assertTrue(text.startswith("# Risk tiers\n\n"))
        first, rest = read(TIERS_DOCS).split("\n", 1)
        self.assertTrue(first.startswith("<!-- ") and first.endswith(" -->"), first)
        self.assertIn("change all seven together", first)
        self.assertEqual(rest, text)

    def test_the_table_says_who_stops_at_each_tier(self):
        self.assertIn("| Decision | Who | Tier 1 | Tier 2 | Tier 3 | Recorded |", read(TIERS_COPIES[0]))
        rows = decision_rows(TIERS_COPIES[0])
        self.assertEqual(list(rows), ["**Ready**: the work, its acceptance criteria and its tier", "**Design + plan**",
                                      "**Merge**", "**Release**", "**Restatement** of a hands-on build"])
        ready, plan, merge, release, restate = rows.values()
        self.assertIn("on F0, D1 and route S, the engineer who confirms the brief", ready[0])
        self.assertEqual(ready[1:4], ["yes", "yes", "yes, with a specialist's spec review"])
        self.assertIn("Tier 2 and 3: the approval of the spec's pull request, which merges first (ADR 0020)", ready[4])
        self.assertEqual(plan[1:5], ["no", "yes: one pull request approval that merges design and plan first",
                                     "yes, with the specialists", "the pull request approval"])
        self.assertEqual(merge[0], "a code owner who did not write the change, after a non-author PASS")
        self.assertEqual(merge[1], "yes; the code owner sees spec, plan and code together")
        self.assertIn("the security specialist when the change touches secrets, permissions, tool calls, dependencies "
                      "or prompts", merge[3])
        self.assertEqual(release[1:3], ["only when users see the change", "only when users see the change"])
        self.assertEqual(release[3], "always; a named approver and a rehearsed rollback")
        self.assertEqual(release[4], "change management, cited in the readiness record")
        self.assertEqual(restate[1:4], ["no: stated", "no: stated", "yes, per slice"])

    def test_the_rules_under_the_table(self):
        text = flat(TIERS_COPIES[0]).split("## Decisions by tier", 1)[1]
        for phrase in ("A person stops only where this section says so (ADR 0026).",
                       "A stage that is not a decision for its tier still runs and still writes its document.",
                       "A person who disagrees says so, and the stage revises.",
                       "a change behind a flag that is still off needs no release decision until the flag goes on; "
                       "turning a flag on is the release.",
                       "Where a pull request approval is the record, the AI writes the tracker entry from it, with how "
                       "it was confirmed, and asks before posting (ADR 0023). When the AI cannot read the review tool, "
                       "the decider confirms in the session.",
                       "Kept at every tier, unchanged:",
                       "A new dependency, a quality-bar exception, and an assertion change (the criterion's owner "
                       "decides).", "Checkpoints where the bundle's MODE puts them.",
                       "a contract change (its consumers), a wireframe for a new screen (the product owner)",
                       "The person pushes: the AI holds no push credential.",
                       "Every decision in operate, feedback and onboard, and every `parallel-lanes` person action.",
                       "The AI never approves or merges (ADR 0023).",
                       "A change of tier, up or down, is a Ready decision at every tier",
                       "A plan that marks its slices independent merges first at every tier (ADR 0025)"):
            self.assertIn(phrase, text, phrase)

    def test_the_old_rows_name_no_plan_approval_at_tier_1(self):
        for rel in TIERS_COPIES + (TIERS_DOCS,):
            lines = read(rel).splitlines()
            approvals = next(line for line in lines if line.startswith("| Approvals")).split("|")
            self.assertIn("no plan approval", approvals[2], rel)
            self.assertIn("the engineer confirms a fast-path or standard brief, with its tier", approvals[2], rel)
            self.assertNotIn("tech lead approves the plan", approvals[2], rel)
            self.assertIn("design and plan, approved by the tech lead in one pull request", approvals[3], rel)
            design = next(line for line in lines if line.startswith("| Design |")).split("|")
            self.assertIn("which the AI states in the plan; the code owner sees it at Merge", design[2], rel)
            plan = next(line for line in lines if line.startswith("| Plan |")).split("|")
            self.assertIn("`standard.md`, route S", plan[2], rel)

    def test_the_operating_model_points_to_the_table(self):
        tiers = flat("docs/operating-model/tiers.md")
        self.assertIn("## Who decides at each tier", tiers)
        self.assertIn("[the decisions table](tiers-table.md#decisions-by-tier)", tiers)
        self.assertIn("At Tier 1 that is Ready and Merge", tiers)


if __name__ == "__main__":
    unittest.main()
