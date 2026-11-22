"""Plan 27: connect the flow. A person starts `story-run` once per decision, and it runs the stages until the next
person's decision; the AI may push its own feature branch (ADR 0028); tests first when a test is practical
(ADR 0029); eight playbooks; every hand-off between stages defined (docs/design/2026-11-22-connect-the-flow.md)."""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DESIGN = "docs/design/2026-11-22-connect-the-flow.md"
ADR_RUN = "docs/adr/0028-story-run-the-ai-push-and-the-hand-offs.md"
ADR_TESTS = "docs/adr/0029-tests-first-when-practical.md"
DECIDE = ("A person decides here only where the tiers file's decisions table lists this decision; otherwise state "
          "what you did and go on.")
APPROVE = "You draft; you never approve."
TIERS_COPIES = tuple(f"skills/{s}/assets/tiers.md" for s in
                     ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review"))
TIERS_DOCS = "docs/operating-model/tiers-table.md"
RULES_FILES = ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md")
# The stages that mark a row of a story's index, in the order a route runs them.
ROW_STAGES = ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan",
              "aidlc-build", "aidlc-verify", "aidlc-review", "aidlc-release")
STORY_LEVEL = ("aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-release")
PART_LEVEL = ("aidlc-plan", "aidlc-build", "aidlc-verify", "aidlc-review")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def words(name: str) -> int:
    """The words in a skill's SKILL.md, front matter included, as `wc -w` counts them."""
    return len(skill_md(name).split())


def section(text: str, heading: str) -> str:
    """One `## ` section of a raw text, from its heading to the next `## ` heading."""
    start = text.index("\n" + heading + "\n")
    end = text.find("\n## ", start + len(heading) + 2)
    return text[start:] if end < 0 else text[start:end]


class AdrTest(unittest.TestCase):
    """Task 1: ADR 0028 and ADR 0029 record the design's decisions, and pstack's licence is in skills/NOTICE."""

    def test_adr_0028_records_the_run_the_push_and_the_hand_offs(self):
        adr = flat(read(ADR_RUN))
        for phrase in ("# 0028 · story-run, the AI's push, and every hand-off defined",
                       "Design: `docs/design/2026-11-22-connect-the-flow.md`",
                       "Amends: ADR 0026 (the kept rule \"the person pushes\"), ADR 0025",
                       "A person's start of `story-run` is the go-ahead for the stages up to the next person's "
                       "decision, as a person's start of a lane is (ADR 0025).",
                       "The AI may push its own feature branch: the story's code branch, a slice's branch, or a "
                       "document pull request's branch, as the index's BRANCH lines name them.",
                       "It never force-pushes, never pushes the default branch or a tag, and never merges, approves, or "
                       "opens or closes a pull request.",
                       "Without both, the person pushes, as before, and `story-run` stops at the push.",
                       "Moving a stacked slice with `git rebase --onto` needs a force-push, so it still asks the person",
                       "The verdict rule is unchanged",
                       "G1: `aidlc-start` writes BRANCH lines in the index.", "G2: `aidlc-specify` at Tier 2 and 3",
                       "G3: a document that merges first is not edited after its approval.",
                       "G4: `aidlc-start` writes a `merged` row on every route.",
                       "the stage that found it ends there, and build, verify and review run again.",
                       "It pushes only a branch whose pull request is the next person's action",
                       "Approved but not merged is a stop for the person's merge.",
                       "One rule for a wait: a document's decision (Ready, Design + plan, a brief's confirmation) waits "
                       "in that document's own row, in place of done,",
                       "G10, G11: every stage that marks a row ends with a short hand-off",
                       "The table in `using-aidlc` is the one source of which stages each route runs.",
                       "A playbook, like a stage's reference, never holds or lifts a gate.",
                       "the AI never approves or merges (ADR 0023)", "\"where your AI tool has one\""):
            self.assertIn(phrase, adr, phrase)
        self.assertIn("and Release only when users see the change (a plan with independent slices is still approved)",
                      adr)

    def test_adr_0029_records_tests_first_when_practical(self):
        adr = flat(read(ADR_TESTS))
        for phrase in ("# 0029 · Tests first, when a test is practical",
                       "Write the failing test first whenever the change has a cheap local test. A cheap local test is "
                       "always written.",
                       "This case is called \"no test for <criterion>\", never \"a skipped test\": a test marked skip or "
                       "disabled is still the Quality bar's stop.",
                       "the test path is unclear, the test is expensive to build",
                       "or there is nothing sensible to assert.",
                       "one row in the decision log (ADR 0027), `no test for <criterion>`, with why a test is impractical "
                       "and the proof it used instead, before it writes the code.",
                       "For a defect, the reproduction still comes first and still fails first",
                       "The tests reviewer lists every criterion with no test, with its reason.",
                       "`aidlc-verify` lists the criterion under Unproved, with its proof, accepted at Merge by the code "
                       "owner.",
                       "a row adds no new stop and no new approval.",
                       "Never editing an existing assertion; no new dependency without asking; every Stop if.",
                       "pstack's `tdd` skill (MIT, Lauren Tan)"):
            self.assertIn(phrase, adr, phrase)

    def test_the_amended_adrs_name_adr_0028(self):
        for rel in ("docs/adr/0026-decisions-by-tier-and-standard-changes.md", "docs/adr/0025-parallel-lanes.md"):
            text = read(rel)
            self.assertIn("Amended by ADR 0028 (proposed, 2026-11-22)", text, rel)
            self.assertLess(text.index("Amended by ADR 0028"), text.index("## Context"), rel)

    def test_notice_holds_pstacks_licence_beside_the_first(self):
        notice = read("skills/NOTICE")
        self.assertTrue(notice.startswith("Third-party licence for portions of the practice skills in this folder."))
        self.assertIn("Copyright (c) 2025 Addy Osmani", notice)
        self.assertIn("Third-party licence for portions of `story-run` (its SKILL.md and its playbooks in "
                      "`story-run/references/`) and of\nthe tests-first wording (ADR 0029, `writing-tests`), adapted from "
                      "pstack (`cursor/plugins`, folder `pstack`), as ADRs\n0028 and 0029 record.", notice)
        self.assertIn("Copyright (c) 2026 Lauren Tan", notice)
        self.assertEqual(notice.count("Permission is hereby granted, free of charge"), 2)


if __name__ == "__main__":
    unittest.main()
