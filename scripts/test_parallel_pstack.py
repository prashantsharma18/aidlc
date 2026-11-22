"""Plan 28: parallel work like pstack (ADR 0030). The throughput checkpoint, scheduling from the approved plan, the
queue branch, the watch pass and CI, `lane-run`, and `worker.md`."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR = "docs/adr/0030-the-agent-drafts-the-queue-and-a-lane-runs-to-the-next-decision.md"
DESIGN = "docs/design/2026-11-22-parallel-work-like-pstack.md"
PLAN = "docs/plans/2026-11-22-plan-28-parallel-like-pstack.md"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def skill(name: str) -> str:
    """The skill's SKILL.md, then its references/*.md in name order, whitespace-collapsed (Plan 26)."""
    files = sorted((ROOT / "skills" / name / "references").glob("*.md"))
    return " ".join([flat(skill_md(name))] + [flat(p.read_text(encoding="utf-8")) for p in files])


def section(text: str, heading: str) -> str:
    """One `## ` section of a text, whitespace-collapsed."""
    return flat(text).split(heading, 1)[1].split(" ## ", 1)[0]


def words(name: str) -> int:
    """The words of a skill's SKILL.md and its references, as scripts/test_references.py counts them."""
    files = [ROOT / "skills" / name / "SKILL.md"] + sorted((ROOT / "skills" / name / "references").glob("*.md"))
    return sum(len(p.read_text(encoding="utf-8").split()) for p in files)


class AdrTest(unittest.TestCase):
    """Task 1: ADR 0030 records the design's decisions; pstack's notice covers the new parts."""

    def test_adr_0030_records_the_decisions(self):
        text = flat(read(ADR))
        self.assertIn("Status: Proposed (2026-11-22).", text)
        for phrase in ("Amends: ADR 0025",
                       "BLOCKING, APART, SHARED and SPLIT, none dropped",
                       "a queue row whose plan marks its slices independent stands for each slice the plan gave its "
                       "own branch",
                       "on its own branch `docs/queue-<YYYY-MM-DD>`",
                       "The person opens and merges its pull request; that merge is the confirmation.",
                       "A lane is its own workflow skill, `lane-run`",
                       "A person starts a lane by hand with one message (`lane-run SHIP-12`)",
                       "never by the lane's own report",
                       "after two fixes for the same check the row stops for a person",
                       "The AI never merges.",
                       "`Read <absolute path>/skills/lane-run/references/worker.md before anything else.`",
                       "pstack (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan)"):
            self.assertIn(phrase, text, phrase)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, read(ADR), heading)

    def test_adr_0025_points_to_the_amendment(self):
        text = read("docs/adr/0025-parallel-lanes.md")
        self.assertIn("Amended by ADR 0030 (proposed, 2026-11-22): the coordinator schedules a plan's slices, drafts "
                      "the queue on its own branch for a person to merge, and watches lanes and CI; lane mode is "
                      "`lane-run`; see ADR 0030.", flat(text))
        self.assertLess(text.index("Amended by ADR 0030"), text.index("## Context"))

    def test_the_notice_credits_the_new_parts(self):
        notice = flat(read("skills/NOTICE"))
        for phrase in ("`skills/lane-run/references/worker.md`", "`lane-run`",
                       "the watch pass and the CI table in `parallel-lanes`", "the throughput checkpoint"):
            self.assertIn(phrase, notice, phrase)

    def test_the_research_order_moves_worker_md(self):
        order = read("docs/research/2026-11-22-pstack-review/README.md").split("## The order", 1)[1]
        row28 = next(line for line in order.splitlines() if line.startswith("| 28 |"))
        row32 = next(line for line in order.splitlines() if line.startswith("| 32 |"))
        self.assertIn("`worker.md`", row28)
        self.assertIn("`lane-run`", row28)
        self.assertNotIn("`worker.md`", row32)


if __name__ == "__main__":
    unittest.main()
