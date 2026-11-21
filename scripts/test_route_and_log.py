"""Plan 25: the route inside Ready, and a log of the AI's judgement calls (ADR 0027). Ready shows the route, which the
tech lead owns and a technical person checks at the first technical decision; a route change after Ready that touches
the tier, the scope, the criteria or the controls is decided again; the AI logs each judgement call in the progress
note, with its evidence and the area's owner, and the compliance reviewer and the code owner read the log."""
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = "docs/design/2026-11-21-route-in-ready-and-decision-log.md"
ADR = "docs/adr/0027-the-route-inside-ready-and-the-decision-log.md"
ADR_0026 = "docs/adr/0026-decisions-by-tier-and-standard-changes.md"
TIERS_COPIES = tuple(f"skills/{s}/assets/tiers.md" for s in
                     ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review"))
TIERS_DOCS = "docs/operating-model/tiers-table.md"
DECIDE = ("A person decides here only where the tiers file's decisions table lists this decision; otherwise state "
          "what you did and go on.")
LANE = "In a lane, release at your gate as `parallel-lanes` says."
ROW = ("- {{commit}} · {{decision}} · {{why}} · {{evidence: file:line, a test or a command}} · owner "
       "{{who owns the area}}")


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


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


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

    def test_adr_0027_is_proposed_with_a_decider(self):
        text = read(ADR)
        self.assertTrue(text.startswith("# 0027 · The route inside Ready, and the decision log\n"))
        self.assertIn("Status: Proposed (2026-11-21)", text)
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = flat(ADR)
        for phrase in ("Amends: ADR 0026 (the Ready row of the decisions table)",
                       "\"the work, its acceptance criteria, its tier and its route\"",
                       "The product owner sees the route and does not decide it; the tech lead owns it",
                       "\"Spec vN approved by … · route F1 (shown; the tech lead owns it)\"",
                       "the kind of work, the tier, the repositories it changes, and whether its criteria are "
                       "already written",
                       "On F0, D1 and S, the engineer who confirms the brief, at Ready.",
                       "On F1, D2 and C at Tier 1, the code owner, at Merge",
                       "At Tier 2 and 3, the tech lead or architect, at Design + plan, in the same pull request.",
                       "A route that would lose controls is not allowed after Ready",
                       "A judgement call is a choice the spec, the plan and the bundle left open",
                       "Anything a skill says stops the work is a stop, never a row.",
                       "`owner` is a pointer, never a gate: no row waits, and no one approves a row.",
                       "a row that should have been a stop is high",
                       "The code owner reads the log with the spec, the plan and the code, inside Merge.",
                       "No decision is added or removed, and no stop",
                       "the AI never approves or merges (ADR 0023)",
                       "the tech lead or architect who approves `new-system.md`",
                       "for a plan with independent slices, first the tech lead who approves it",
                       "A tier change, up or down, needs a new Ready",
                       "aidlc still ships no code and needs no code-host feature (ADR 0024)"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0026_points_to_the_amendment(self):
        text = read(ADR_0026)
        self.assertIn("Amended by ADR 0027 (proposed, 2026-11-21): the Ready row also shows the route",
                      flat(ADR_0026))
        self.assertLess(text.index("Amended by ADR 0027"), text.index("## Context"))
        self.assertIn("Status: Proposed (2026-11-21). Accepted (2026-11-21; confirmed by the framework owner in the "
                      "session).", text)


def decision_rows(rel: str) -> dict:
    """The decisions table's rows, by their first cell."""
    table = read(rel).split("## Decisions by tier", 1)[1]
    return {cells[0]: cells[1:] for cells in
            ([c.strip() for c in line.strip().strip("|").split(" | ")] for line in table.splitlines()
             if line.startswith("| **"))}


class TiersTest(unittest.TestCase):
    """Task 2: Ready shows the route and Merge reads the log, in every tiers copy."""

    def test_every_copy_shows_the_route_in_ready_and_the_log_at_merge(self):
        texts = {read(rel) for rel in TIERS_COPIES}
        self.assertEqual(len(texts), 1)
        self.assertEqual(read(TIERS_DOCS).split("\n", 1)[1], texts.pop())
        rows = decision_rows(TIERS_COPIES[0])
        self.assertNotIn("**Ready**: the work, its acceptance criteria and its tier", rows)
        ready = rows["**Ready**: the work, its acceptance criteria, its tier and its route"]
        self.assertEqual(ready[0], "product owner; the tier with whoever owns the risk (on F0, D1 and route S, the "
                                   "engineer who confirms the brief); the route is shown, and the tech lead owns it")
        self.assertEqual(ready[1:4], ["yes", "yes", "yes, with a specialist's spec review"])
        merge = rows["**Merge**"]
        self.assertEqual(merge[0], "a code owner who did not write the change, after a non-author PASS, who reads the "
                                   "decision log with spec, plan and code")
        self.assertEqual(merge[1], "yes; the code owner sees spec, plan and code together")

    def test_the_rules_say_who_checks_the_route_and_that_no_row_waits(self):
        text = flat(TIERS_COPIES[0]).split("## Decisions by tier", 1)[1]
        for phrase in ("The route (ADR 0027): Ready shows it, and the tech lead owns it; the product owner sees it and "
                       "does not decide it.",
                       "the kind of work, the tier, the repositories the work changes, and whether its criteria are "
                       "written",
                       "on F0, D1 and route S, the engineer who confirms the brief, at Ready;",
                       "on F1, D2 and C at Tier 1, the code owner, at Merge, where the pull request description shows "
                       "the ROUTE line (for a plan with independent slices, first the tech lead who approves it);",
                       "at Tier 2 and 3, the tech lead or architect, at Design + plan, in the same pull request;",
                       "on route G, the tech lead or architect who approves `new-system.md`.",
                       "A route change after Ready that touches the tier, the scope, the criteria or the controls is "
                       "decided again, as `aidlc-start` says; a tier change, up or down, needs a new Ready; a lighter route is "
                       "chosen only at the start.",
                       "one row each in the progress note, and a row for each Deviation and Assumption; anything a "
                       "skill says stops the work is a stop, never a row",
                       "The decision log (ADR 0027):", "No row waits, and no one approves a row."):
            self.assertIn(phrase, text, phrase)
        self.assertLess(text.index("The route (ADR 0027)"), text.index("Where a pull request approval is the record"))

    def test_the_operating_model_says_it(self):
        tiers = flat("docs/operating-model/tiers.md").split("## Who decides at each tier", 1)[1]
        self.assertIn("Ready shows the route, which the tech lead owns, and a technical person checks it at the first "
                      "technical decision; the code owner reads the AI's decision log at Merge", tiers)
        self.assertIn("Ready and Merge, and Release only when users see the change; a plan with independent slices is "
                      "still approved", tiers)


if __name__ == "__main__":
    unittest.main()
