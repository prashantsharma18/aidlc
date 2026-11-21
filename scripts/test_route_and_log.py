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


class SpecifyTest(unittest.TestCase):
    """Task 4: the spec shows the route apart from the product owner's approval."""

    def test_the_spec_template_shows_the_route(self):
        spec = read("skills/aidlc-specify/assets/spec.md")
        self.assertIn("Spec owner: {{OWNER}} · Tier: {{TIER}} · Route: {{ROUTE, from the story index's ROUTE line; "
                      "shown, the tech lead owns it}} · Version: v1", spec)
        self.assertIn("Spec {{version}} approved by {{owner}} on {{YYYY-MM-DD}}, {{how it was confirmed: checked on the "
                      "work item, or in the session}} · route {{ROUTE}} (shown; the tech lead owns it). Reviewed by "
                      "{{specialist}}.", spec)
        block = flat("skills/aidlc-specify/assets/spec.md").split("## For the reviewer", 1)[1].split(" ## ", 1)[0]
        self.assertIn("a specialist reviews at Tier 3; the route is shown with the spec, and the tech lead owns it "
                      "(ADR 0027)", block)
        self.assertIn("On the work item: \"Spec vN approved by name · route F1 (shown; the tech lead owns it)\"", block)

    def test_specify_writes_the_route_and_never_decides_it(self):
        specify = skill("aidlc-specify")
        self.assertIn("Copy the route from the index's ROUTE line into the spec's header: Ready shows it, and the tech "
                      "lead owns it (ADR 0027).", section(specify, "## Steps"))
        text = gate("aidlc-specify")
        for phrase in ("Ready shows the route apart from the approval: write the Approval record as \"Spec vN approved "
                       "by … · route F1 (shown; the tech lead owns it)\", and at Tier 1, where the spec may be a few "
                       "lines on the work item, write the work item's entry the same way (ADR 0027).",
                       "The spec owner sees the route and does not decide it: when they disagree with it, the work "
                       "goes back to `aidlc-start`, and the tech lead decides; their Ready still covers the work, its "
                       "criteria and its tier.",
                       DECIDE + " " + LANE + " You draft; you never approve."):
            self.assertIn(phrase, text, phrase)
        self.assertIn("You are recording the route as the spec owner's decision, or changing the route yourself: the "
                      "tech lead owns it.", section(specify, "## Red flags"))
        self.assertIn("Keep the header's route equal to the index's ROUTE line.", section(specify, "## Steps"))


class RouteCheckTest(unittest.TestCase):
    """Task 5: a technical person checks the route at the first technical decision the table lists for it."""

    BRIEFS = {"fix-brief": ("ACTUAL ", "D1 (<why: a defect; Tier 1; one repository; a reproduction; the expected "
                                       "behaviour written in SOURCE>)", "Ready on route D1, ADR 0026"),
              "feature-brief": ("OWNER ", "F0 (<why: a new feature; Tier 1; one repository; criteria written on the "
                                          "work item by OWNER>)", "Ready on route F0, ADR 0026")}

    def test_the_engineer_checks_it_in_the_brief_at_ready(self):
        for name, (before, value, ready) in self.BRIEFS.items():
            text = read(f"skills/aidlc-plan/assets/{name}.md")
            fields = text.split("```text\n", 1)[1].split("\n```", 1)[0].splitlines()
            route = next(l for l in fields if l.startswith("ROUTE "))
            self.assertTrue(route.startswith("ROUTE       " + value), name)
            self.assertIn("the engineer's confirmation covers the route, as it covers the TIER; the tech lead owns the "
                          "route, ADR 0027", route, name)
            at = fields.index(route)
            self.assertTrue(fields[at - 1].startswith(before), name)
            self.assertTrue(fields[at + 1].startswith("TIER "), name)
            self.assertIn(f"({ready}), which covers its ROUTE line (ADR 0027)", flat(f"skills/aidlc-plan/assets/{name}.md"))
        plan = skill("aidlc-plan")
        self.assertEqual(plan.count("It covers the brief's ROUTE line too: the engineer checks the route's facts, "
                                    "which the tech lead owns (ADR 0027)."), 2)
        self.assertEqual(plan.count("The engineer confirms its TIER with it: that is Ready on route"), 2)

    def test_the_tech_lead_checks_it_at_design_and_plan(self):
        plan = gate("aidlc-plan")
        self.assertIn("At Tier 2 and 3, and at Tier 1 for a plan with independent slices, the tech lead or architect "
                      "also checks the route with this decision: the facts "
                      "on the story index's ROUTE line, in the same pull request (for a story across several "
                      "repositories, on the home design pull request). A fact that does not hold goes back to "
                      "`aidlc-start`, which re-routes the work (ADR 0027). " + DECIDE + " " + LANE, plan)
        design = gate("aidlc-design")
        self.assertIn("At Tier 2 and 3 the tech lead or architect also checks the route here, with the design: the "
                      "facts on the story index's ROUTE line, in the same pull request (on the home design pull "
                      "request for a story across several repositories); on route G, they check it when they approve "
                      "`new-system.md`. A fact that does not hold goes back to `aidlc-start` (ADR 0027). " + DECIDE,
                      design)

    def test_the_code_owner_checks_it_at_merge_on_the_other_tier_1_routes(self):
        review = skill("aidlc-review")
        self.assertIn("the tier, the route (the story index's ROUTE line, with its facts) and the rollback;",
                      section(review, "## Steps"))
        self.assertIn("At Tier 1 on F1, D2 and C, the code owner also checks the route here: the facts on the ROUTE "
                      "line the description shows. A fact that does not hold goes back to `aidlc-start` before the "
                      "merge, which re-routes the work (ADR 0027).", gate("aidlc-review"))
        trace = flat("skills/aidlc-review/assets/pr-description.md").split("## Traceability", 1)[1]
        self.assertIn("- **Work item:** {{key, title}} · Tier {{n}} - **Route:** {{the story index's ROUTE line, with "
                      "its facts}} (shown at Ready; the tech lead owns it; at Tier 1 on F1, D2 and C, the code owner "
                      "checks it here, ADR 0027)", trace)


class BuildLogTest(unittest.TestCase):
    """Task 6: the build logs each judgement call when it makes it, and never logs a stop."""

    NOTE = "skills/aidlc-build/assets/progress-note.md"

    def test_the_progress_note_holds_the_row(self):
        text = read(self.NOTE)
        log = text.split("## Decisions made while working (for the PR)\n", 1)[1].split("\n## ", 1)[0]
        self.assertTrue(log.rstrip().endswith(ROW), log)
        flat_log = " ".join(log.split())
        for phrase in ("The decision log (ADR 0027): one row per judgement call, written when the call is made, and "
                       "one per Deviation and per Assumption below.",
                       "A judgement call is a choice the spec, the plan and the bundle left open, settled inside MAY "
                       "CHANGE; anything a stop names is a stop, never a row.",
                       "`owner` is who owns the area and should see the row, never an approval: no row waits.",
                       "Write `- none` when the slice made no judgement call."):
            self.assertIn(phrase, flat_log, phrase)
        self.assertNotIn("confirm with", text)
        self.assertEqual(re.findall(r"<(?!!--)[^<>\n]+>", outside_code(text)), [])
        self.assertNotRegex(outside_code(text), r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S")

    def test_step_7_writes_the_row_when_the_call_is_made(self):
        step = skill("aidlc-build").split(" 7. Implement one step at a time.", 1)[1].split(" 8. Run the full test", 1)[0]
        for phrase in ("the message also gives the step number and any judgement call the step settled.",
                       "**Log each judgement call** (ADR 0027): a choice the spec, the plan and the bundle left open, "
                       "which you settle inside MAY CHANGE (a name, one of two ways to write something, a test's "
                       "shape, how to handle an edge case the criteria already allow).",
                       "Write its row under \"Decisions made while working (for the PR)\" in the progress note when you "
                       "make the call, not at the end, and name the step's commit once it is committed:",
                       "`- <commit> · <decision> · <why> · <evidence: file:line, a test or a command> · owner <who owns "
                       "the area>`",
                       "the code owner of the path for a choice in code, the tech lead for a choice of approach, the "
                       "criterion's owner for an edge case a criterion allows.",
                       "It is a pointer, never a gate: no row waits, and no one approves a row.",
                       "Each Deviation and each Assumption the note lists gets a row too.",
                       "A slice with no judgement call writes `- none`.",
                       "Anything this skill says stops the work is never a row: an unclear criterion, a new "
                       "dependency, a file outside MAY CHANGE, a contract change, a changed assertion and every STOP "
                       "IF still stop.",
                       "When you believe you need someone's yes before going on, it is not a judgement call: it is a "
                       "stop, and you ask."):
            self.assertIn(phrase, step, phrase)
        self.assertNotIn("who must confirm it", skill("aidlc-build"))

    def test_the_report_red_flag_excuse_and_gate(self):
        build = skill("aidlc-build")
        self.assertIn("and what you did not know. Point to the decision log: the rows under \"Decisions made while "
                      "working (for the PR)\" in the progress note, or `none`.", section(build, "## Steps"))
        self.assertIn("You are logging a choice a stop names (an unclear criterion, a new dependency, a file outside "
                      "MAY CHANGE, a contract change, a changed assertion, a STOP IF) instead of stopping, or writing a "
                      "row that waits for someone's yes.", section(build, "## Red flags"))
        self.assertIn("| \"The criterion is unclear, but I will pick the sensible reading and log it for the "
                      "reviewer.\" | An unclear criterion is a stop, not a judgement call. The log holds only choices "
                      "the documents left open: stop, and ask the criterion's owner. |", section(build, "## Common excuses"))
        text = gate("aidlc-build")
        self.assertIn("The code owner reads the decision log at Merge, with the spec, the plan and the code; no row "
                      "waits, and no one approves a row (ADR 0027). " + DECIDE, text)
        self.assertIsNone(re.search(r"code owner[^.;]* approves", text))


if __name__ == "__main__":
    unittest.main()
