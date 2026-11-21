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


class StartTest(unittest.TestCase):
    """Task 3: the ROUTE line carries its facts; a technical person checks the route; a re-route after Ready is decided
    again, and never to a lighter route."""

    CHANGES = (
        "| The tier changes, up or down | A new Ready: the tier is part of Ready. A lower tier drops controls, so it is "
        "decided too |",
        "| The criteria change | The criterion's owner decides the amendment (`aidlc-specify`, amendment mode), as "
        "today |",
        "| The scope grows: a repository, a part or a contract is added (for example F1 to F2) | A new Ready, then the "
        "decisions the tiers file's decisions table lists for the new route |",
        "| The route gains controls (for example F0 to F1, D1 to D2, S to its normal route) | The new route's Ready, by "
        "that route's decider (the product owner for F1 and D2) |",
        "| The route would lose controls (for example F1 to F0, a normal route to S) | Not allowed after Ready: the "
        "work stays on its route. A lighter route is chosen only at the start |",
        "| None of the above: the same tier, repositories, criteria and controls (for example, the kind of work was "
        "mislabelled) | No new decision: state the change, and it is shown at the next decision the table lists |")

    def test_the_index_route_line_carries_its_facts(self):
        start, plan = (read(f"skills/{s}/assets/story-index.md") for s in ("aidlc-start", "aidlc-plan"))
        self.assertEqual(start, plan)
        line = next(l for l in start.splitlines() if l.startswith("ROUTE "))
        self.assertTrue(line.startswith("ROUTE      <F0 | F1 | F2 | C | D1 | D2 | G>   (or S: a standard change that "
                                        "AGENTS.md lists, ADR 0026)"), line)
        self.assertIn("(<kind of work>; Tier <n>; <one repository | n repositories>; <criteria written by owner | "
                      "criteria not yet written>, ADR 0027)", line)
        self.assertIn("The ROUTE line names the facts its route follows from; Ready shows the route, the tech lead "
                      "owns it, and a technical person checks the facts at the first technical decision (ADR 0027).",
                      flat("skills/aidlc-start/assets/story-index.md"))

    def test_start_writes_the_facts_and_says_who_checks_them(self):
        steps = section(skill("aidlc-start"), "## Steps")
        self.assertIn("S (a standard change). After the route, write in brackets the facts it follows from: the kind "
                      "of work, the tier, the repositories the work changes, and whether its criteria are already "
                      "written (for example `ROUTE F1 (new feature; Tier 1; one repository; criteria not yet "
                      "written)`).", steps)
        self.assertIn("a stage that finds one does not hold stops, and the work comes back here to be re-routed.", steps)
        self.assertIn("The brief's ROUTE line names route S with its facts (the class, Tier 1, one repository, every "
                      "limit held); the engineer's confirmation covers it, as it covers the tier (ADR 0027).", steps)
        text = gate("aidlc-start")
        for phrase in ("The product owner owns the story and its acceptance criteria; the tech lead owns the route.",
                       "Ready shows the route (the tiers file's decisions table): the product owner sees it and does "
                       "not decide it.",
                       "the engineer who confirms the brief on F0, D1 and S, at Ready;",
                       "the code owner on F1, D2 and C at Tier 1, at Merge (for a plan with independent slices, first "
                       "the tech lead who approves it);",
                       "the tech lead or architect at Tier 2 and 3, and on route G, at Design + plan (ADR 0027).",
                       "When the product owner disagrees with the route at Ready, the work comes back here, and the "
                       "tech lead decides; the product owner's Ready still covers the work, its criteria and its tier.",
                       DECIDE + " You draft; you never approve."):
            self.assertIn(phrase, text, phrase)
        self.assertNotIn("agrees the route", skill("aidlc-start"))
        self.assertEqual(read("skills/aidlc-start/SKILL.md").count(DECIDE), 1)

    def test_a_re_route_after_ready_is_decided_again(self):
        start = skill("aidlc-start")
        block = section(start, "## Steps").split("**An index for this key already exists**", 1)[1]
        self.assertIn("a re-route after Ready (ADR 0027): what the change touches decides what it needs before the "
                      "work goes on.", block)
        self.assertIn("| The change | What it needs before the work goes on |", block)
        for row in self.CHANGES:
            self.assertIn(row, block, row)
        self.assertIn("After Ready, it also says what the change needs (step 7).", section(start, "## When to use"))
        self.assertIn("Moving work to a lighter route after Ready (F1 to F0, a normal route to S), or re-routing after "
                      "Ready without saying what the change needs.", section(start, "## Red flags"))
        self.assertIn("| \"The tier dropped after discovery, so I will move the story to the fast path.\" | A lighter "
                      "route is chosen only at the start. After Ready the work stays on its route; a lower tier is a "
                      "new Ready. |", section(start, "## Common excuses"))

    def test_the_standard_brief_shows_the_route(self):
        text = read("skills/aidlc-start/assets/standard-brief.md")
        block = flat("skills/aidlc-start/assets/standard-brief.md").split("## For the reviewer", 1)[1]
        self.assertIn("The engineer, to confirm the brief, its TIER and its MODE (Ready on route S, ADR 0026), which "
                      "covers its ROUTE line (ADR 0027); the code owner approves it with the change", block)
        fields = text.split("```text\n", 1)[1].split("\n```", 1)[0].splitlines()
        route = next(l for l in fields if l.startswith("ROUTE "))
        self.assertTrue(route.startswith("ROUTE       S (<why: the class CLASS names; Tier 1; one repository; every "
                                         "limit of the class holds>)"), route)
        self.assertLess(fields.index(route), next(n for n, l in enumerate(fields) if l.startswith("TIER ")))
        self.assertEqual(re.findall(r"<(?!!--)[^<>\n]+>", outside_code(text)), [])


if __name__ == "__main__":
    unittest.main()
