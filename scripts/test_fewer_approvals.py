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
        self.assertEqual(decision_rows(TIERS_COPIES[0]), {
            "**Ready**: the work, its acceptance criteria and its tier": [
                "product owner; the tier with whoever owns the risk (on F0, D1 and route S, the engineer who confirms "
                "the brief)", "yes", "yes", "yes, with a specialist's spec review",
                "Tier 1: the decider's word in the session or their own tracker entry, checked (ADR 0023). Tier 2 and "
                "3: the approval of the spec's pull request, which merges first (ADR 0020)"],
            "**Design + plan**": [
                "tech lead or architect", "no", "yes: one pull request approval that merges design and plan first",
                "yes, with the specialists", "the pull request approval"],
            "**Merge**": [
                "a code owner who did not write the change, after a non-author PASS",
                "yes; the code owner sees spec, plan and code together", "yes; every affected area",
                "yes; the security specialist when the change touches secrets, permissions, tool calls, dependencies "
                "or prompts", "the pull request"],
            "**Release**": [
                "release approver", "only when users see the change", "only when users see the change",
                "always; a named approver and a rehearsed rollback",
                "change management, cited in the readiness record"],
            "**Restatement** of a hands-on build": [
                "the engineer", "no: stated", "no: stated", "yes, per slice",
                "the progress note's `restatement confirmed by` line"]})

    def test_tier_1_releases_only_when_users_see_the_change_everywhere(self):
        for rel in TIERS_COPIES + (TIERS_DOCS,):
            text = flat(rel)
            self.assertIn("its release has a release approver. That approver decides only when users see the change.",
                          text, rel)
            self.assertIn("no plan approval (except a plan with independent slices, ADR 0025)", text, rel)
            self.assertIn("The flag rule applies at Tier 1 and 2; at Tier 3 both the deploy and turning the flag on "
                          "are decided.", text, rel)
        for rel in ("docs/operating-model/tiers.md", "docs/adr/0026-decisions-by-tier-and-standard-changes.md",
                    "docs/design/2026-11-21-fewer-approvals.md"):
            self.assertIn("Ready and Merge, and Release only when users see the change", flat(rel), rel)

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


LANE = "In a lane, release at your gate as `parallel-lanes` says."


def assert_gate_line(case: unittest.TestCase, name: str) -> None:
    """The Gate line is in the stage's Gate, once in the whole file, and sits just before the lane line (or, for a
    stage with no lane line, just before "You draft; you never approve.")."""
    raw = read(f"skills/{name}/SKILL.md")
    case.assertEqual(raw.count(DECIDE), 1, name)
    after = LANE if LANE in raw else "You draft; you never approve."
    case.assertIn(DECIDE + " " + after, gate(name), name)


class ReadyTest(unittest.TestCase):
    """Task 3: the intent's acceptance and the spec's approval are one decision, Ready."""

    def test_both_gates_carry_the_line(self):
        for name in ("aidlc-intent", "aidlc-specify"):
            assert_gate_line(self, name)

    def test_the_intent_states_its_draft_and_goes_on(self):
        text = gate("aidlc-intent")
        self.assertIn("That acceptance is part of Ready, which the product owner decides with the spec (the tiers "
                      "file's decisions table): state the draft and its provisional tier in the session, and go on to "
                      "`aidlc-specify`; there is no separate stop here.", text)
        block = flat("skills/aidlc-intent/assets/intent.md").split("## For the reviewer", 1)[1]
        self.assertIn("part of Ready, which the product owner decides with the spec", block)
        self.assertIn("and hands it to the spec, where the product owner decides Ready.", skill("aidlc-intent"))

    def test_the_spec_approval_is_ready_and_its_pull_request_is_the_record(self):
        text = gate("aidlc-specify")
        for phrase in ("That approval is Ready (the tiers file's decisions table): the work, its acceptance criteria "
                       "and its tier, in one decision with the intent's acceptance.",
                       "At Tier 1 the record is the approval with the spec's version on the work item",
                       "That pull request's approval is the record: check it in the review tool (when you cannot, the "
                       "spec owner confirms it in this session), then write the spec's Approval record and the work "
                       "item's entry from it, with how it was confirmed, and ask before posting (ADR 0026)."):
            self.assertIn(phrase, text, phrase)
        specify = skill("aidlc-specify")
        self.assertIn("Use when the intent is drafted", specify)
        self.assertIn("**Draft mode.** The intent is drafted (its acceptance is decided with the spec, as Ready)", specify)
        self.assertNotIn("The accepted intent", specify)

    def test_ready_is_recorded_once(self):
        text = gate("aidlc-intent")
        self.assertIn("At Tier 1 you record the acceptance", text)
        self.assertIn("At Tier 2 and 3 it is recorded with Ready, in the spec's pull request, with no separate "
                      "tracker acceptance.", text)
        spec = gate("aidlc-specify")
        self.assertIn("That sentence applies at Tier 1.", spec)
        self.assertIn("At Tier 2 and 3 the pull request's approval is the record and takes precedence", spec)
        self.assertIn("and stops for the spec owner's Ready decision.", skill("aidlc-specify"))
        for name in ("aidlc-intent", "aidlc-specify"):
            self.assertNotIn("The accepted intent lives in the work item", skill(name), name)
        self.assertNotIn("Only the product owner accepts work, in the tracker.", skill("aidlc-intent"))
        record = next(l for l in read("skills/aidlc-intent/assets/intent.md").splitlines() if "**Record it:**" in l)
        self.assertIn("Tier 1", record)
        self.assertIn("spec's pull request", record)
        for name in ("aidlc-intent", "aidlc-specify"):
            for sentence in skill(name).replace("\n", " ").split(". "):
                if "Tier 2" in sentence and "tracker" in sentence and "approv" in sentence:
                    self.assertTrue("pull request" in sentence and ("record" in sentence or "no separate" in sentence
                                    or "precedence" in sentence or "ask before" in sentence), sentence)


class DesignPlanTest(unittest.TestCase):
    """Task 4: design and plan are one decision at Tier 2 and 3, and none at Tier 1."""

    def test_the_three_gates_carry_the_line(self):
        for name in ("aidlc-discover", "aidlc-design", "aidlc-plan"):
            assert_gate_line(self, name)

    def test_discover_proceeds_with_the_design_and_waits_only_for_a_tier_change(self):
        text = gate("aidlc-discover")
        self.assertIn("To proceed is not a separate stop: at Tier 2 and 3 it is decided with the design and the plan, "
                      "in their one pull request, and at Tier 1 the code owner sees the evidence pack at Merge.", text)
        self.assertIn("To escalate, or to raise the tier, changes Ready, so it waits for the tech lead and whoever owns "
                      "the risk.", text)
        self.assertIn("8. Draft the decision for the tech lead: proceed, escalate, or raise the tier.",
                      skill("aidlc-discover"))
        self.assertNotIn("the accepted intent", skill("aidlc-discover"))

    def test_design_is_stated_at_tier_1_and_approved_with_the_plan_above_it(self):
        text = gate("aidlc-design")
        for phrase in ("The tech lead or architect approves the design with the plan",
                       "At Tier 1 the design is not a separate decision (the tiers file's decisions table): state "
                       "\"none needed\" and its reason in the session and in the plan, and go on; the code owner sees "
                       "it at Merge.",
                       "A design question answered yes at Tier 1 raises the tier, which is a Ready decision: stop and "
                       "say so.",
                       "merges to the default branch first, in its own pull request, together with the plan, which "
                       "the tech lead or architect approves once (ADR 0020, as ADR 0026 amends it): state the design "
                       "and go on to `aidlc-plan`, because the decision comes once, on that pull request"):
            self.assertIn(phrase, text, phrase)
        step = skill("aidlc-design").split(" 1. Ask the three questions", 1)[1].split(" 2. When the change adds", 1)[0]
        self.assertIn("At Tier 1 it is not a stop: state it in the session, write the RECORDED BY line as `stated at "
                      "Tier 1; the code owner sees it at Merge`, and go on.", step)
        note = read("skills/aidlc-design/assets/design-note.md")
        self.assertIn("RECORDED BY  <tech lead or architect>, <YYYY-MM-DD>, <how it was confirmed> | stated at Tier 1; "
                      "the code owner sees it at Merge", note)

    def test_the_plan_waits_for_no_one_at_tier_1(self):
        text = gate("aidlc-plan")
        for phrase in ("At Tier 2 and 3, the tech lead reviews the plan against its checklist and decides, with the "
                       "design, once (Design + plan in the tiers file's decisions table)",
                       "That pull request approval is the record: the work item's entry is written from it (ADR 0026).",
                       "At Tier 1 no one approves the plan: state it in the session, with its slices, their MODE and "
                       "the design's \"none needed\", and go on",
                       "where the code owner sees spec, plan and code together at Merge",
                       "This is why at Tier 1 a plan with independent slices is the one plan that waits for the tech lead.",
                       "At Tier 1 a bundle is built as the plan stated it, and a changed bundle is stated again.",
                       "the engineer confirms the brief (`fix.md` or `brief.md`) and its tier, which is Ready on routes "
                       "D1 and F0"):
            self.assertIn(phrase, text, phrase)
        plan = skill("aidlc-plan")
        self.assertIn("State the restatement in the session and go on: it is not a stop (the tiers file's decisions "
                      "table), and the person may correct it at any time.", plan)
        self.assertNotIn("Wait for the person to confirm.", plan)
        self.assertIn("at Tier 1 it states the plan and goes on", plan)
        self.assertIn("at Tier 1 a \"none needed\" is stated", skill("aidlc-design"))
        self.assertNotIn("Wait for the person. |", plan)
        self.assertIn("You are waiting for a plan approval at Tier 1, where the tiers file's decisions table lists none.",
                      section(plan, "## Red flags"))
        self.assertEqual(plan.count("The engineer confirms its TIER with it: that is Ready on route"), 2)

    def test_the_templates_say_who_decides_at_each_tier(self):
        plan = flat("skills/aidlc-plan/assets/plan.md").split("## For the reviewer", 1)[1].split(" ## ", 1)[0]
        self.assertIn("at Tier 1 no one: the plan is stated, and the code owner reads it at Merge", plan)
        self.assertIn("At Tier 1: `none: stated at Tier 1, the code owner reads it at Merge`",
                      flat("skills/aidlc-plan/assets/plan.md"))
        bundle = flat("skills/aidlc-plan/assets/task-bundle.md")
        self.assertIn("at Tier 1 the bundle is stated with the plan, and the code owner reads it at Merge", bundle)
        self.assertIn("approved with the bundle at Tier 2 and 3)", bundle)
        self.assertIn("0 Restate the goal and criteria with file references; at Tier 3 (hands-on) wait for "
                      "confirmation; otherwise write it to the progress note and go on.", bundle)
        for name in ("fix-brief", "feature-brief"):
            text = flat(f"skills/aidlc-plan/assets/{name}.md")
            self.assertIn("to confirm the brief, its TIER and its MODE", text, name)
            self.assertIn("written by the AI when the engineer confirms the brief and its TIER", text, name)

    def test_one_pull_request_is_the_single_repository_case(self):
        across = ("For a story across several repositories, Decision 2 is still one decision, taken by the same tech "
                  "lead on the home design pull request and on each part's plan pull request, each approval recorded "
                  "on its own pull request, never as a separate tracker approval.")
        for name in ("aidlc-design", "aidlc-plan"):
            text = gate(name)
            self.assertIn("In a single repository, ", text, name)
            self.assertIn(across, text, name)
        step = skill("aidlc-design").split(" 1. Ask the three questions", 1)[1].split(" 2. When the change adds", 1)[0]
        self.assertIn("state the note and go on: the approval comes with the plan, on the combined pull request "
                      "(across repositories, as Decision 2)", step)


class BuildReviewTest(unittest.TestCase):
    """Task 5: one restatement wait (Tier 3), one diff review (the findings), one code-owner approval (Merge)."""

    def test_the_three_gates_carry_the_line(self):
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            assert_gate_line(self, name)

    def test_the_restatement_waits_only_at_tier_3(self):
        step = skill("aidlc-build").split(" 2. Read the bundle's TIER", 1)[1].split(" 3. Load every skill", 1)[0]
        order = [step.index(p) for p in (
            "At Tier 3, where every slice is hands-on, the restatement is a person's decision, per slice (the tiers "
            "file's decisions table).",
            "Hands-on: wait for the person to confirm.",
            "A confirmation given before you have stated the restatement does not count at Tier 3: state it, then wait.",
            "At Tier 1 and 2 the restatement is stated, not waited on, in every mode: say it in the session, write it "
            "under Restatement in the progress note (step 4) and go on without waiting; the person may correct it at "
            "any time, and reads it with the diff.",
            "Checkpoints still stop where the bundle's MODE puts them (step 7).")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("Delegate with checkpoints or delegate: write the restatement", step)
        self.assertIn("after the slice's task bundle is approved (at Tier 1, once the plan has stated it",
                      skill("aidlc-build"))
        self.assertIn("Use when a slice's task bundle is approved, or at Tier 1 stated with its plan.", skill("aidlc-build"))

    def test_the_diff_is_reviewed_once_as_the_findings(self):
        build = gate("aidlc-build")
        self.assertNotIn("the person reviews the diff before pushing", build)
        self.assertIn("and the person pushes: you hold no push credential.", build)
        self.assertIn("The engineer's review of the diff is their decision on each review finding, once, in "
                      "`aidlc-review`: not a separate stop before the push (ADR 0026).", build)
        self.assertIn("Deciding the findings is the engineer's review of the diff, once: there is no separate review "
                      "of the diff before the push (ADR 0026).", skill("aidlc-review"))

    def test_the_code_owner_approves_once_at_merge(self):
        verify = gate("aidlc-verify")
        self.assertNotIn("a code owner who did not write the change approves it", verify)
        self.assertIn("The code owner's approval is one decision, Merge, taken once at `aidlc-review`'s gate (ADR "
                      "0026): this stage asks for no approval of its own.", verify)
        review = gate("aidlc-review")
        self.assertIn("This is Merge (the tiers file's decisions table), the one code-owner approval of the change: at "
                      "Tier 1 the code owner sees spec, plan and code together, and at Tier 3 the security specialist "
                      "decides when the change touches secrets, permissions, tool calls, dependencies or prompts.",
                      review)
        self.assertIn("A code owner who is neither the author nor the pusher approves, after a non-author PASS", review)
        approving = [name for name in ("aidlc-build", "aidlc-verify", "aidlc-review")
                     if re.search(r"code owner[^.;]* approves", gate(name))]
        self.assertEqual(approving, ["aidlc-review"])


if __name__ == "__main__":
    unittest.main()
