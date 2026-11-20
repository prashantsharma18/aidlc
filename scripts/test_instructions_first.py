"""Plan 22: aidlc is instructions (ADR 0024). It ships no scripts and no CI workflows; the checks live in the
team's project; a verdict counts only from someone who did not write the change, at a named commit; and the words
need git, not a code host's features."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = sorted(p.name for p in (ROOT / "skills").iterdir() if p.name.startswith("aidlc-"))


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


AMENDED = ("0012-mechanical-recipe-commit", "0015-work-routes-and-the-part-model", "0016-greenfield-entry",
           "0017-feature-fast-path-and-build-modes", "0020-approved-documents-merge-first",
           "0021-several-repositories-at-least-tier-2", "0022-one-owner-per-fact-and-pinned-parts",
           "0023-people-decide-the-ai-records")


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    ADR = "docs/adr/0024-instructions-first.md"

    def test_adr_0024_is_proposed_and_supersedes_0019(self):
        text = read(self.ADR)
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("Supersedes: ADR 0019", "It ships no scripts and no CI workflows to teams",
                       "A rule that must hold every time lives in the team's project",
                       "counts only from someone who did not write it", "`plans/<KEY>/review-evidence.md`",
                       "They keep Read, Grep and Glob, and never run a command",
                       "aidlc depends on git and on no code-host feature", "the tag `checks-v1`",
                       "\"Change request\" stays the name of route C"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0024_holds_the_rule_table(self):
        text = read(self.ADR)
        self.assertIn("| Rule | Was enforced by | Now enforced by |", text)
        for rule in ("No deleted test, no changed assertion", "Plan complete before approval",
                     "Recipe commit is mechanical", "Contract version raised; breaking change raises MAJOR",
                     "Consumer copy matches the pinned version", "Secrets never read; push asks first"):
            self.assertIn(rule, text, rule)

    def test_adr_0019_is_superseded(self):
        self.assertIn("Status: Superseded by ADR 0024 (2026-11-20)", read("docs/adr/0019-gates-enforced-by-code.md"))

    def test_each_amended_adr_carries_a_dated_note(self):
        for name in AMENDED:
            text = read(f"docs/adr/{name}.md")
            self.assertIn("Amended by ADR 0024 (2026-11-20): see the last section.", text, name)
            self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"), name)
            self.assertIn("Status: Accepted", text, name)


if __name__ == "__main__":
    unittest.main()
