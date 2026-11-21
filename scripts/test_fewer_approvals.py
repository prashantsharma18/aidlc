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


if __name__ == "__main__":
    unittest.main()
