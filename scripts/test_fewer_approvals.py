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
            "**Ready**: the work, its acceptance criteria, its tier and its route": [
                "product owner; the tier with whoever owns the risk (on F0, D1 and route S, the engineer who confirms "
                "the brief); the route is shown, and the tech lead owns it", "yes", "yes",
                "yes, with a specialist's spec review",
                "Tier 1: the decider's word in the session or their own tracker entry, checked (ADR 0023). Tier 2 and "
                "3: the approval of the spec's pull request, which merges first (ADR 0020)"],
            "**Design + plan**": [
                "tech lead or architect", "no", "yes: one pull request approval that merges design and plan first",
                "yes, with the specialists", "the pull request approval"],
            "**Merge**": [
                "a code owner who did not write the change, after a non-author PASS, who reads the decision log with "
                "spec, plan and code",
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

    def test_plan_inputs_count_the_design_note_as_approved_where_the_table_says_so(self):
        inputs = section(skill("aidlc-plan"), "## Inputs")
        self.assertIn("the approved design note (always)", inputs)
        sentence = ("The design note counts as approved when the tiers file's decisions table says so: at Tier 1 its "
                    "\"none needed\" is stated (RECORDED BY), and at Tier 2 and 3 it is approved with this plan, in the "
                    "same pull request, so its APPROVED line may still be pending. If an input is missing, say which "
                    "stage produces it and stop; never plan around it.")
        self.assertIn(sentence, inputs)

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


class ReleaseTest(unittest.TestCase):
    """Task 6: one release decision, recorded once, and only when users see the change below Tier 3."""

    def test_the_gate_carries_the_line(self):
        assert_gate_line(self, "aidlc-release")

    def test_the_release_is_decided_only_when_users_see_it(self):
        text = gate("aidlc-release")
        for phrase in ("That approval is the one Release decision (the tiers file's decisions table): at Tier 1 and 2 "
                       "it is needed only when users see the change, and at Tier 3 always, with a named approver and a "
                       "rehearsed rollback.",
                       "A change behind a flag that is still off needs no release decision until the flag goes on; "
                       "turning a flag on is the release.",
                       "When no decision is needed, state the readiness record, with its stop criteria, and go on: the "
                       "normal pipeline ships the change.",
                       "the owning team confirms monitoring and rollback, as part of that decision"):
            self.assertIn(phrase, text, phrase)
        self.assertIn("stops for the release approver when users see the change (always at Tier 3).",
                      skill("aidlc-release"))

    def test_the_approval_is_recorded_once_and_cited(self):
        text = gate("aidlc-release")
        self.assertIn("The approver's word in the session fills the Decision line only; the Decision then cites the "
                      "change-management record, so the approval is recorded once, there (ADR 0026).", text)
        self.assertIn("An approval that exists only in the chat still stops the release.", text)


DECIDE_STAGES = ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan",
                 "aidlc-build", "aidlc-verify", "aidlc-review", "aidlc-release")
BRIEF = "skills/aidlc-start/assets/standard-brief.md"


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


class RouteSTest(unittest.TestCase):
    """Task 7: route S, from the team's list of standard changes to build, verify and review."""

    def test_exactly_the_ten_deciding_stages_carry_the_line(self):
        found = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")
                       if DECIDE in p.read_text(encoding="utf-8"))
        self.assertEqual(found, sorted(DECIDE_STAGES))
        for name in DECIDE_STAGES:
            assert_gate_line(self, name)

    def test_start_recognises_a_listed_class_and_never_stretches_it(self):
        raw = read("skills/aidlc-start/SKILL.md")
        self.assertIn("  templates: [story-index, standard-brief]\n", raw.split("\n---", 1)[0])
        start = skill("aidlc-start")
        steps = section(start, "## Steps")
        for phrase in ("**Standard change (route S, ADR 0026):** first, read the Standard changes section of the "
                       "repository's `AGENTS.md`.",
                       "When the work matches a class listed there and stays within every limit the class names, it "
                       "takes route S",
                       "Work that passes a limit (a major version, a new dependency, a Tier 2 risk), or matches a class "
                       "only in part, takes its normal route below; say which limit it passed. A class is never "
                       "stretched.",
                       "A defect that matches a D1-fix class takes route D1",
                       "S (a standard change)",
                       "**Standard change (S):** inside the repository: this stage writes the standard brief, the "
                       "engineer confirms it with its tier, then `aidlc-build`, `aidlc-verify`, `aidlc-review`.",
                       "Write `plans/<KEY>/standard.md` from `assets/standard-brief.md`",
                       "That confirmation is Ready on route S, the one decision before Merge"):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("On route S, the engineer who confirms the standard brief confirms its tier: that is Ready",
                      gate("aidlc-start"))
        self.assertIn("S to the work's normal route", section(start, "## When to use"))
        self.assertIn("Taking route S for work that passes a limit of its class, or for a class `AGENTS.md` does not "
                      "list.", section(start, "## Red flags"))
        self.assertIn("A class is never stretched.", section(start, "## Common excuses"))

    def test_the_standard_brief_is_a_template_the_engineer_confirms(self):
        text = read(BRIEF)
        self.assertTrue(text.startswith("<!-- aidlc template: standard-brief -->\n# {{KEY}} · standard brief\n"))
        block = text.split("## For the reviewer", 1)[1].split("```", 1)[0]
        for label in ("**Asked of:**", "**Record it:**", "**Tier and main risk:**", "**Changed since the last version:**"):
            self.assertIn(label, block)
        self.assertIn("The engineer, to confirm the brief, its TIER and its MODE (Ready on route S, ADR 0026)", block)
        fields = text.split("```text\n", 1)[1].split("\n```", 1)[0]
        for field in ("STANDARD BRIEF · {{KEY}} · {{TITLE}}", "CLASS ", "WHAT ", "LIMITS ", "EVIDENCE ", "TIER ",
                      "RECIPE ", "MODE ", "USE SKILLS ", "MAY CHANGE ", "MUST NOT ", "DONE WHEN ", "STOP IF ",
                      "CONFIRMED "):
            self.assertIn(field, fields, field)
        self.assertIn("written by the AI when the engineer confirms the brief and its TIER", fields)
        self.assertIn("a limit of the class would be passed (a major version, a new dependency, a Tier 2 risk)", fields)
        out = outside_code(text)
        self.assertEqual(re.findall(r"<(?!!--)[^<>\n]+>", out), [])
        self.assertNotRegex(out, r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S")
        self.assertEqual(text.count("```") % 2, 0)

    def test_the_index_knows_route_s(self):
        start, plan = (read(f"skills/{s}/assets/story-index.md") for s in ("aidlc-start", "aidlc-plan"))
        self.assertEqual(start, plan)
        self.assertIn("ROUTE      <F0 | F1 | F2 | C | D1 | D2 | G>   (or S: a standard change that AGENTS.md lists, ADR 0026)", start)

    def test_build_verify_and_review_read_the_standard_brief(self):
        build = skill("aidlc-build")
        self.assertIn("or, on route S, the confirmed standard brief `plans/<KEY>/standard.md`, which serves the same way "
                      "(its slice is named `standard`)", build)
        self.assertIn("On route S, for a recipe class that `AGENTS.md`'s Standard changes section lists, do not pause: "
                      "the evidence file's Recipe commits section shows the re-run, and the code owner reads it at "
                      "Merge (ADR 0026).", build)
        self.assertIn("On route S, its STANDARD line names the class and shows each limit held.", build)
        self.assertIn("the recipe review (except for a listed recipe class on route S, step 5)", gate("aidlc-build"))
        self.assertIn("The standard brief's CONFIRMED line is empty or still holds its placeholder, its TIER is not 1, "
                      "or the work would pass one of its LIMITS", section(build, "## Stop if"))
        self.assertIn("On route S, the standard brief `plans/<KEY>/standard.md`", section(skill("aidlc-verify"),
                                                                                           "## Inputs"))
        review = skill("aidlc-review")
        self.assertIn("on route S the standard brief `plans/<KEY>/standard.md`", section(review, "## Inputs"))
        self.assertIn("On route S, the code owner approves `standard.md` with the change, and checks that the evidence "
                      "file's STANDARD line names the class and shows each limit held.", review)
        self.assertIn("On route S the standard brief (`plans/<KEY>/standard.md`) is the bundle the same way",
                      flat("agents/reviewer-compliance.md"))

    def test_the_evidence_file_names_the_class(self):
        copies = {read(f"skills/{s}/assets/review-evidence.md") for s in ("aidlc-build", "aidlc-review")}
        self.assertEqual(len(copies), 1)
        self.assertIn("STANDARD   {{on route S: the class, and each limit with how it held | none}}", copies.pop())

    def test_route_s_reads_the_approved_list_and_matches_exactly(self):
        steps = section(skill("aidlc-start"), "## Steps")
        for phrase in ("Read that section as merged on the default branch (`git fetch`, then "
                       "`git show origin/<default branch>:AGENTS.md`), never from the working tree or a feature branch.",
                       "A class added or changed on this branch is not approved: the work takes its normal route.",
                       "A class that names no limits or no evidence, or is too vague to check, is unusable: take the "
                       "normal route and ask the tech lead to complete it.",
                       "Route S also needs Tier 1 (`assets/tiers.md`) and one repository, as F0 and D1 do; any of auth, "
                       "permissions, data or schema, secrets or a contract means the normal route.",
                       "the D1 fix brief carries D1's fixed limits (Tier 1, no new dependency, one repository), and "
                       "a team's extra D1-class limits are copied into the brief's STOP IF",
                       "`aidlc-release` when users see the change"):
            self.assertIn(" ".join(phrase.split()), " ".join(steps.split()), phrase)
        self.assertNotRegex(steps, r"(?i)read the standard changes section of the repository's\s+`AGENTS.md`\.\s+When")
        build = skill("aidlc-build")
        self.assertIn("The pause lifts only when the brief's RECIPE and the commit's `Recipe:` trailer name the class's "
                      "tool and version exactly; otherwise pause as usual.", build)
        self.assertIn("a package added to any lock file counts as a new dependency unless the class explicitly allows it",
                      section(build, "## Stop if"))
        self.assertIn("compares the commit's `Recipe:` trailer with the evidence file's STANDARD line",
                      flat("agents/reviewer-compliance.md"))
        brief = read(BRIEF)
        self.assertIn("a package would be added to any lock file, unless the class explicitly allows it", brief)
        self.assertIn("the packages added to lock files, or none", read("skills/aidlc-build/assets/review-evidence.md"))


RULES_FILES = ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md")


class RouteSDocsTest(unittest.TestCase):
    """Task 8: route S is listed wherever routes are, and the rules file holds the team's standard changes."""

    def test_the_map_lists_route_s_and_who_decides(self):
        text = skill("using-aidlc")
        self.assertIn("and each stops only where the tiers file's decisions table lists a decision for its tier "
                      "(ADR 0026).", text)
        self.assertIn("`aidlc-start` chooses one of the other eight;", text)
        routes = section(text, "## The routes")
        self.assertIn("| S · standard change | A class of work the team lists in the Standard changes section of "
                      "`AGENTS.md`, within every limit the class names; Tier 1, one repository |", routes)
        lifecycle = section(text, "## The lifecycle")
        for row in ("| 6 | `aidlc-plan` | The plan and one task bundle per slice | Inside each repository | Tech lead, "
                    "with the design, in one pull request (Tier 2 and 3); stated at Tier 1 | `aidlc-build` |",
                    "| The person pushes; at Tier 3, the restatement per slice |",
                    "| 8 | `aidlc-verify` | The evidence table from CI | Inside the repository | No one: the code owner "
                    "decides once, at review (Merge) | `aidlc-review` |",
                    "| Release approver, when users see the change (always at Tier 3) |"):
            self.assertIn(row, lifecycle, row)

    def test_the_routes_document_draws_route_s(self):
        routes = read("docs/operating-model/routes.md")
        self.assertIn("### S · standard change", routes)
        self.assertIn('item["A work item or a new requirement"] --> standard{"A standard change AGENTS.md lists, within '
                      'its limits?"}', routes)
        self.assertIn('standard -->|"yes"| S["S · standard change"]', routes)
        self.assertIn("| S · standard change | A class of work the team lists in `AGENTS.md`'s Standard changes",
                      routes)
        self.assertIn('confirm{{"Engineer confirms standard.md and its tier"}}', routes)
        self.assertIn("    S --> F1: a limit of its class is passed", routes)
        self.assertIn("| S | none: the standard brief stands in | `plans/<KEY>/standard.md`, the progress note |", routes)
        flat_routes = " ".join(routes.split())
        self.assertIn("At Tier 1 a person decides only Ready and Merge", flat_routes)
        self.assertIn("A defect that matches the D1-fix class takes route D1", flat_routes)
        self.assertIn("**Nine routes**", read("docs/operating-model/lifecycle.md"))
        self.assertIn("standard changes the team lists (S)", flat("docs/operating-model/lifecycle.md"))
        self.assertIn("The nine routes, drawn", read("README.md"))
        self.assertIn("A standard change the team lists in its `AGENTS.md` takes route S", flat("README.md"))

    def test_the_rules_file_holds_the_standard_changes(self):
        for rel in RULES_FILES:
            text = read(rel)
            self.assertIn("## Standard changes", text, rel)
            self.assertLess(text.index("## Standard changes"), text.index("## Rules and what enforces them"), rel)
            block = " ".join(text.split("## Standard changes", 1)[1].split("\n## ", 1)[0].split())
            for phrase in ("takes route S (`aidlc-start`, ADR 0026)", "| Class | What qualifies | Limits | Evidence |",
                           "| Recipe commit |", "| Dependency bump |", "| Defect fix (D1) |",
                           "No new dependency; never a major version",
                           "Work that passes a limit stops and takes its normal route; a class is never stretched.",
                           "The tech lead approves this list once, in a pull request, as any rule.",
                           "The AI reads the list as merged on the default branch, so a class added or changed on a "
                           "branch is not approved.",
                           "A class names what qualifies, its limits and its evidence, or it cannot be used.",
                           "A package added to a lock file counts as a new dependency unless the class says otherwise.",
                           "Route S is Tier 1 and one repository only."):
                self.assertIn(phrase, block, f"{rel}: {phrase}")
            self.assertIn("A person decides only where the tiers file's decisions table says (ADR 0026)", flat(rel), rel)
        self.assertNotIn("<", outside_code(read(RULES_FILES[0])).split("## Standard changes", 1)[1].split("\n## ", 1)[0])

    def test_the_quickstarts_count_nine_routes(self):
        for rel in ("docs/quickstart/claude-code.md", "docs/quickstart/copilot.md", "docs/quickstart/codex-cursor.md"):
            text = read(rel)
            self.assertNotIn("the eight routes", text, rel)
            self.assertIn("[the nine routes](../operating-model/routes.md)", text, rel)

    def test_onboard_proposes_the_three_classes(self):
        onboard = skill("aidlc-onboard")
        self.assertIn("For the Standard changes section, propose the three classes the template suggests", onboard)
        self.assertIn("the tech lead approves the list in the pull request, as any rule (ADR 0026)", onboard)


class LanesTest(unittest.TestCase):
    """Task 9: the lanes release where the decisions table says, and a sub-agent still builds only an approved plan."""

    def lane(self) -> str:
        return skill("parallel-lanes").split("Lane mode, step by step:", 1)[1].split("Coordinator mode, step by step:")[0]

    def test_a_sub_agent_builds_only_a_plan_a_person_approved(self):
        inputs = section(skill("parallel-lanes"), "## Inputs")
        for phrase in ("only on a row whose plan a person approved (ADR 0023)",
                       "A confirmed brief (`fix.md`, `brief.md` or `standard.md`) counts as an approved plan, because "
                       "the engineer's confirmation is the row's Ready (ADR 0026).",
                       "At Tier 1 on a full route, no person approves the plan unless it has independent slices (the "
                       "tiers file's decisions table), so a sub-agent lane never builds a Tier 1 row whose plan was "
                       "only stated: a person starts its build by hand.",
                       "a hands-on build keeps a person in the session for its judgement calls, and at Tier 3 waits for "
                       "the person to confirm its restatement, so a person starts it."):
            self.assertIn(phrase, inputs, phrase)
        self.assertNotIn("a hands-on build waits for the person to confirm its restatement in the session", inputs)
        coordinator = skill("parallel-lanes").split("Coordinator mode, step by step:", 1)[1].split("**A stacked", 1)[0]
        self.assertIn("A build whose plan was only stated, not approved (Tier 1 on a full route, without independent "
                      "slices), goes the second way.", coordinator)
        self.assertNotIn("A build whose plan no person approved (at Tier 1 on a full route)", coordinator)

    def test_a_lane_releases_where_the_table_says(self):
        lane = self.lane()
        self.assertIn("a person's decision is needed, as the tiers file's decisions table lists it for the row's tier "
                      "(answers, the plan's approval at Tier 2 and 3 and of a Tier 1 plan with independent slices, a pause or a "
                      "Tier 3 restatement confirmation, the pull request review): write `waiting: <decision> by <who>`",
                      lane)
        self.assertIn("(for example intent and design at every tier, and plan at Tier 1 without independent slices)",
                      lane)
        self.assertIn("the stage is done and no person's decision follows it (the tiers file's decisions table): "
                      "write nothing more, because the row is ready for its next stage, which a lane starts as "
                      "coordinator step 3 says", lane)
        self.assertIn("A hands-on build's restatement at Tier 3 and a pause are recorded as lines in the progress note",
                      lane)


class DocsTest(unittest.TestCase):
    """Task 10: the documents a team reads say what the decisions table says."""

    def test_the_sheet_is_redrawn_from_the_table(self):
        sheet = flat("docs/operating-model/adoption.md").split("## Who approves what", 1)[1]
        self.assertIn("A person decides only where the tiers file's decisions table says", sheet)
        self.assertIn("At Tier 1 that is Ready and Merge, and Release only when users see the change.", sheet)
        self.assertIn("| Decision | Who | When | Where it is recorded |", sheet)
        for row in ("| **Ready**: the story, its acceptance criteria, its tier and its route |",
                    "| **Design + plan**, with each bundle's MODE |", "| **Merge** |", "| **Release** |",
                    "| The hands-on restatement |",
                    "| A standard change list |", "| The push |"):
            self.assertIn(row, sheet, row)
        self.assertIn("| Tier 2 and 3: one pull request that merges both first; at Tier 1 the AI states them, except a "
                      "plan with independent slices, which the tech lead approves |", sheet)
        self.assertIn("route S then needs only Ready and Merge, and Release only when users see the change", sheet)
        self.assertNotIn("| The tracker, with the plan's version and commit |", sheet)
        self.assertIn("bundles the tech lead approves with the design at Tier 2 and 3 (stated at Tier 1, except a plan "
                      "with independent slices, which the tech lead approves)",
                      flat("docs/operating-model/adoption.md"))

    def test_the_operating_model_says_who_decides(self):
        roles = read("docs/operating-model/roles.md")
        self.assertIn("| Tier | Ready | Design + plan | Merge | Release |", roles)
        self.assertIn("| 1 | Product owner (on F0, D1 and S, the engineer confirms the brief and its tier) | None: the "
                      "AI states them, except a plan with independent slices, which the tech lead approves; the code "
                      "owner reads them at Merge |", roles)
        self.assertNotIn("| 1 | Tech lead, on the work item (a short plan) |", roles)
        lifecycle = read("docs/operating-model/lifecycle.md")
        self.assertIn("| At Tier 2 and 3, the pull request approval, written to the work item with the plan's version "
                      "and commit; at Tier 1 the plan is stated, except a plan with independent slices, which the "
                      "tech lead approves |", lifecycle)
        self.assertIn("[the decisions table](tiers-table.md#decisions-by-tier)", lifecycle)
        self.assertIn("the tech lead approves designs and plans, at Tier 2 and 3 in one pull request (ADR 0026)",
                      flat("docs/operating-model/workspace-and-repositories.md"))

    def test_the_readme_and_the_map_say_where_a_person_decides(self):
        readme = flat("README.md")
        self.assertIn("**Gates:** each skill drafts, and stops only where the tiers file's decisions table lists a "
                      "decision for the tier (at Tier 1, Ready and Merge, and Release only when users see the change; "
                      "ADR 0026)", readme)
        self.assertIn("or tell the AI, which records each decision after checking it (ADR 0023)", readme)
        self.assertIn("Each drafts its documents and stops where the decisions table puts a person's decision.", readme)
        self.assertIn("| `/aidlc:aidlc-build SHIP-12 1` | One slice at a time, from its approved bundle (at Tier 1, "
                      "the stated one, or the approved one for independent slices) |", readme)
        self.assertIn("- Who decides at a gate: the decisions table in the six identical `assets/tiers.md` copies and "
                      "`docs/operating-model/tiers-table.md`", flat("docs/codebase-map.md"))

    def test_the_change_list_marks_what_plan_24_covers(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        table = changes.split("## 8. After Plan 24 (2026-11-21)", 1)[1]
        self.assertRegex(table, r"(?m)^\| C1 \| Covered, as instructions \|")
        self.assertRegex(table, r"(?m)^\| C3 \| Covered, as instructions \|")
        self.assertRegex(table, r"(?m)^\| C6 \| Open \|")
        self.assertIn("at Tier 1, Ready and Merge, and Release only when users see the change;", table)
        self.assertIn("`docs/plans/2026-11-21-plan-24-fewer-approvals.md`", table)


NEW_CASES = {"gate-tier1-plan-stated": ("gate", "/aidlc:aidlc-plan SHIP-60."),
             "route-s-dependency-bump": ("route", "/aidlc:aidlc-start SHIP-70 and SHIP-71."),
             "gate-tier2-design-plan-once": ("gate", "/aidlc:aidlc-plan SHIP-80."),
             "gate-restatement-tier3": ("gate", "/aidlc:aidlc-build SHIP-90 slice 1.")}
# For each tool grader: inputs a correct run may give and inputs a wrong run would give. Every one here is `max: 0`,
# so a right input must not match and a wrong input must.
TOOL_SAMPLES = {
    ("route-s-dependency-bump", "no-full-route-documents.md"): (
        [{"file_path": "/work/plans/SHIP-70/README.md", "content": "ROUTE      S"},
         {"file_path": "/work/plans/SHIP-70/standard.md", "content": "CLASS       Dependency bump"},
         {"file_path": "/work/plans/SHIP-71/spec.md", "content": "AC1"}],
        [{"file_path": "/work/plans/SHIP-70/spec.md", "content": "AC1"},
         {"file_path": "/work/plans/SHIP-70/intent.md", "content": "Problem"},
         {"file_path": "/work/plans/SHIP-70/plan.md", "content": "SPEC"},
         {"file_path": "/work/plans/SHIP-70/design-note.md", "content": "OUTCOME"}]),
    ("route-s-dependency-bump", "no-standard-brief-for-the-major.md"): (
        [{"file_path": "/work/plans/SHIP-70/standard.md", "content": "x"},
         {"file_path": "/work/plans/SHIP-71/README.md", "content": "ROUTE      F1"}],
        [{"file_path": "/work/plans/SHIP-71/standard.md", "content": "CLASS       Dependency bump"}]),
    ("route-s-dependency-bump", "no-standard-edit-for-the-major.md"): (
        [{"file_path": "/work/plans/SHIP-70/standard.md", "old_string": "a", "new_string": "b"}],
        [{"file_path": "/work/plans/SHIP-71/standard.md", "old_string": "a", "new_string": "b"}]),
    ("gate-restatement-tier3", "no-code-edit.md"): (
        [{"file_path": "/work/plans/SHIP-90/progress-1.md", "old_string": "a", "new_string": "b"}],
        [{"file_path": "/work/src/shipments/labels.py", "old_string": "a", "new_string": "b"},
         {"file_path": "/work/tests/test_labels.py", "old_string": "a", "new_string": "b"}]),
    ("gate-restatement-tier3", "no-code-write.md"): (
        [{"file_path": "/work/plans/SHIP-90/progress-1.md", "content": "STATUS      doing"}],
        [{"file_path": "/work/tests/test_labels.py", "content": "import unittest"},
         {"file_path": "/work/src/shipments/labels.py", "content": "def mask_phone"}]),
}
# For each regex grader: file contents a correct run may leave, and contents a wrong run would leave.
REGEX_SAMPLES = {
    ("gate-tier1-plan-stated", "plan-row-done.md"): (
        ["| aidlc-plan | repository | done |", "| aidlc-plan | repository | done (plan v1 stated at Tier 1) |"],
        ["| aidlc-plan | repository | to do |", "| aidlc-plan | repository | waiting: plan approval by Ana |"]),
    ("gate-tier1-plan-stated", "no-approval-invented.md"): (
        ["APPROVAL   none: stated at Tier 1, the code owner reads it at Merge",
         "APPROVAL   <pending: to be approved by Ana on the design and plan pull request>"],
        ["APPROVAL   plan.md v1 approved by Ana, 2026-11-21, in the session",
         "APPROVAL   plan.md v1 approved by Ana, 2026-11-21, on pull request 4"]),
    ("route-s-dependency-bump", "route-s.md"): (
        ["ROUTE      S"], ["ROUTE      F1", "ROUTE      S1"]),
    ("route-s-dependency-bump", "brief-names-the-class.md"): (
        ["CLASS       Dependency bump", "CLASS       dependency bump (AGENTS.md)"],
        ["CLASS       Recipe commit", "WHAT        Dependency bump"]),
    ("gate-tier2-design-plan-once", "no-design-approval-recorded.md"): (
        ["APPROVED     (pending: the tech lead approves design and plan in one pull request)"],
        ["APPROVED     ADR now Accepted; approved by Ana, 2026-11-20, relayed in the session",
         "APPROVED  tech lead, 2026-11-20, relayed", "RECORDED BY Ana 2026-11-20"]),
    ("gate-tier2-design-plan-once", "adr-still-proposed.md"): (
        ["Status: Proposed. Decider: Ana (tech lead)"], ["Status: Accepted (2026-11-21)", "Status: accepted",
                                                                  "Status: Proposed -> Accepted by Ana"]),
    ("gate-tier2-design-plan-once", "no-plan-approval-recorded.md"): (
        ["APPROVAL   <pending: the pull request that merges the design and the plan>",
         "APPROVAL   <pending: to be approved by Ana on the design and plan pull request>"],
        ["APPROVAL   plan.md v1 approved by Ana, 2026-11-21"]),
}
GRADERS = {
    "gate-tier1-plan-stated": {"plan-written.md", "plan-row-done.md", "no-approval-invented.md", "reply.md"},
    "route-s-dependency-bump": {"route-s.md", "brief-written.md", "brief-names-the-class.md",
                                "no-full-route-documents.md", "no-standard-brief-for-the-major.md",
                                "no-standard-edit-for-the-major.md", "reply.md"},
    "gate-tier2-design-plan-once": {"plan-written.md", "no-design-approval-recorded.md", "adr-still-proposed.md",
                                    "no-plan-approval-recorded.md", "reply.md"},
    "gate-restatement-tier3": {"no-code-edit.md", "no-code-write.md", "reply.md"},
}
TOOLS = {("route-s-dependency-bump", "no-full-route-documents.md"): "Write",
         ("route-s-dependency-bump", "no-standard-brief-for-the-major.md"): "Write",
         ("route-s-dependency-bump", "no-standard-edit-for-the-major.md"): "Edit",
         ("gate-restatement-tier3", "no-code-edit.md"): "Edit",
         ("gate-restatement-tier3", "no-code-write.md"): "Write"}
TARGETS = {("gate-tier1-plan-stated", "plan-row-done.md"): "plans/SHIP-60/README.md",
           ("gate-tier1-plan-stated", "no-approval-invented.md"): "plans/SHIP-60/plan.md",
           ("route-s-dependency-bump", "route-s.md"): "plans/SHIP-70/README.md",
           ("route-s-dependency-bump", "brief-names-the-class.md"): "plans/SHIP-70/standard.md",
           ("gate-tier2-design-plan-once", "no-design-approval-recorded.md"): "plans/SHIP-80/design-note.md",
           ("gate-tier2-design-plan-once", "adr-still-proposed.md"): "plans/SHIP-80/SHIP-80-adr-1.md",
           ("gate-tier2-design-plan-once", "no-plan-approval-recorded.md"): "plans/SHIP-80/plan.md"}
EXISTS = {("gate-tier1-plan-stated", "plan-written.md"): "plans/SHIP-60/plan.md",
          ("route-s-dependency-bump", "brief-written.md"): "plans/SHIP-70/standard.md",
          ("gate-tier2-design-plan-once", "plan-written.md"): "plans/SHIP-80/plan.md"}
UNTOUCHED = {("gate-tier2-design-plan-once", "no-design-approval-recorded.md"): "plans/SHIP-80/design-note.md",
             ("gate-tier2-design-plan-once", "adr-still-proposed.md"): "plans/SHIP-80/SHIP-80-adr-1.md"}


def grader(case: str, name: str) -> str:
    return front(read(f"evals/{case}/graders/{name}"))


def regex_passes(fm: str, text: str) -> bool:
    """What the eval runner's regex grader decides for a file holding `text`."""
    pattern = re.search(r"(?m)^pattern: '(.*)'$", fm).group(1)
    flags = re.M if re.search(r"(?m)^flags: m$", fm) else 0
    found = re.search(pattern, text, flags) is not None
    return not found if re.search(r"(?m)^match: not_contains$", fm) else found


class EvalCasesTest(unittest.TestCase):
    """Task 11: four behaviour cases; each grader tells a right run from a wrong one, and each scaffold holds the
    state its graders assume."""

    def test_each_case_holds_exactly_its_graders_aimed_at_the_right_place(self):
        for case, names in GRADERS.items():
            on_disk = {g.name for g in (ROOT / "evals" / case / "graders").glob("*.md")}
            self.assertEqual(on_disk, names, case)
        for (case, name), tool in TOOLS.items():
            self.assertRegex(grader(case, name), rf"(?m)^tool: {tool}$", f"{case}/{name}")
        for (case, name), path in TARGETS.items():
            self.assertRegex(grader(case, name), rf"(?m)^target: \{{source: file, path: {re.escape(path)}\}}$",
                             f"{case}/{name}")
        for (case, name), path in EXISTS.items():
            self.assertRegex(grader(case, name), rf"(?m)^path: '{re.escape(path)}'$", f"{case}/{name}")

    def test_the_tier3_case_asks_for_a_restatement_it_can_carry_out(self):
        reply = read("evals/gate-restatement-tier3/graders/reply.md")
        self.assertNotIn("for each slice", reply)
        self.assertIn("wait for the person to confirm this restatement", reply)
        self.assertNotIn("**********0123", read("evals/gate-restatement-tier3/setup.sh"))
        self.assertIn('AC1: mask_phone("07700900123") returns "*******0123".',
                      read("evals/gate-restatement-tier3/setup.sh"))

    def test_the_tier1_reply_grader_allows_a_sliced_plan_in_its_fail_line(self):
        self.assertIn("(unless it split the plan into independent slices, as PASS allows)",
                      read("evals/gate-tier1-plan-stated/graders/reply.md"))

    def test_the_four_cases_exist_and_are_listed(self):
        readme = " ".join(read("evals/README.md").split())
        self.assertIn("there are 40 cases", readme)
        self.assertIn("`route-d1-build`, `gate-restatement-tier3`, `route-s-dependency-bump`, `gate-tier2-design-plan-once`, and the four lane cases", readme)
        for case, (tag, start) in NEW_CASES.items():
            prompt = read(f"evals/{case}/prompt.md")
            self.assertIn(f"tags: [{tag}]", front(prompt), case)
            self.assertTrue(prompt.split("---", 2)[2].strip().startswith(start), case)
            self.assertTrue(list((ROOT / "evals" / case / "graders").glob("*.md")), case)
            self.assertIn(f"`{case}`", readme, case)

    def test_each_tool_grader_tells_right_from_wrong(self):
        for (case, name), (right, wrong) in TOOL_SAMPLES.items():
            fm = grader(case, name)
            self.assertRegex(fm, r"(?m)^max: 0$", name)
            pattern = re.search(r"(?m)^input_match: '(.*)'$", fm).group(1)
            for given in right:
                self.assertIsNone(re.search(pattern, json.dumps(given)), f"{case}/{name}: {given}")
            for given in wrong:
                self.assertIsNotNone(re.search(pattern, json.dumps(given)), f"{case}/{name}: {given}")
        graded = {(c, g.name) for c in NEW_CASES for g in (ROOT / "evals" / c / "graders").glob("*.md")
                  if re.search(r"(?m)^type: tool_used$", g.read_text(encoding="utf-8"))}
        self.assertEqual(graded, set(TOOL_SAMPLES))

    def test_each_regex_grader_tells_right_from_wrong(self):
        for (case, name), (right, wrong) in REGEX_SAMPLES.items():
            fm = grader(case, name)
            for text in right:
                self.assertTrue(regex_passes(fm, text), f"{case}/{name}: {text}")
            for text in wrong:
                self.assertFalse(regex_passes(fm, text), f"{case}/{name}: {text}")
        graded = {(c, g.name) for c in NEW_CASES for g in (ROOT / "evals" / c / "graders").glob("*.md")
                  if re.search(r"(?m)^type: regex$", g.read_text(encoding="utf-8"))}
        self.assertEqual(graded, set(REGEX_SAMPLES))

    def test_the_tier1_plan_case_is_ready_to_plan(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-tier1-plan-stated", repo)
            self.assertEqual(git(repo, "branch", "--show-current").stdout.strip(), "feat/SHIP-60-return-labels")
            index = (repo / "plans/SHIP-60/README.md").read_text(encoding="utf-8")
            self.assertIn("| aidlc-design | repository | done |", index)
            self.assertIn("| aidlc-plan | repository | to do |", index)
            self.assertIn("Tier: 1", (repo / "plans/SHIP-60/spec.md").read_text(encoding="utf-8"))
            self.assertIn("RECORDED BY  stated at Tier 1; the code owner sees it at Merge",
                          (repo / "plans/SHIP-60/design-note.md").read_text(encoding="utf-8"))
            self.assertFalse((repo / "plans/SHIP-60/plan.md").exists())

    def test_the_bump_case_lists_the_class_and_both_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("route-s-dependency-bump", repo)
            agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("## Standard changes", agents)
            self.assertIn("| Dependency bump |", agents)
            self.assertIn("No new dependency; never a major version", agents)
            manifest = (repo / "requirements-dev.txt").read_text(encoding="utf-8")
            self.assertIn("coverage==7.5.0", manifest)
            self.assertIn("mypy==1.11.2", manifest)
            self.assertFalse((repo / "plans").exists())
            self.assertIn("## Standard changes", git(repo, "show", "origin/main:AGENTS.md").stdout)

    def test_the_tier2_case_holds_the_design_unmerged_and_unapproved(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-tier2-design-plan-once", repo)
            self.assertEqual(git(repo, "branch", "--show-current").stdout.strip(), "docs/SHIP-80-design-plan")
            self.assertIn("Tier: 2", git(repo, "show", "origin/main:plans/SHIP-80/spec.md").stdout)
            self.assertNotEqual(git(repo, "show", "origin/main:plans/SHIP-80/design-note.md", check=False).returncode, 0)
            self.assertIn("| aidlc-plan | repository | to do |",
                          (repo / "plans/SHIP-80/README.md").read_text(encoding="utf-8"))
            for (case, name), rel in UNTOUCHED.items():
                self.assertTrue(regex_passes(grader(case, name), (repo / rel).read_text(encoding="utf-8")), name)

    def test_the_tier3_case_has_a_merged_hands_on_bundle_and_green_tests(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-restatement-tier3", repo)
            self.assertEqual(git(repo, "branch", "--show-current").stdout.strip(), "feat/SHIP-90-mask-phone")
            bundle = (repo / "plans/SHIP-90/bundle-1.md").read_text(encoding="utf-8")
            self.assertRegex(bundle, r"(?m)^TIER\s+3 ")
            self.assertRegex(bundle, r"(?m)^MODE\s+hands-on")
            self.assertEqual(git(repo, "show", "origin/main:plans/SHIP-90/bundle-1.md").stdout, bundle)
            self.assertFalse((repo / "tests/test_labels.py").exists())
            result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=repo,
                                    env=clean_env(), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


class RecordTest(unittest.TestCase):
    """Task 12: the plan is recorded."""

    RECORD = "docs/verification/2026-11-21-plan-24.md"

    def test_the_verification_record_exists(self):
        record = read(self.RECORD)
        for heading in ("## What changed", "## How it was checked", "## Evidence", "## Not verified here",
                        "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("ADR 0026", "python3 scripts/validate.py", "claude plugin validate .", *NEW_CASES):
            self.assertIn(phrase, record, phrase)

    def test_the_record_has_no_open_slot(self):
        self.assertNotIn("{{", read(self.RECORD))


class FinalReviewTest(unittest.TestCase):
    """The final review's findings: Tier 3 decides deploy and flag; the independent-slices exception is stated
    everywhere a Tier 1 plan is; build, specify, design, compliance and routes wording."""

    EXCEPTION_FILES = (
        "skills/aidlc-plan/assets/plan.md", "skills/aidlc-plan/assets/task-bundle.md", "skills/using-aidlc/SKILL.md",
        "docs/operating-model/routes.md", "docs/operating-model/tiers.md", "README.md", "starter/repo/AGENTS.md",
        "skills/aidlc-onboard/assets/agents-md.md", "skills/aidlc-plan/SKILL.md")

    def test_release_gate_flag_rule_is_tier_1_and_2(self):
        self.assertIn("turning a flag on is the release. The flag rule applies at Tier 1 and 2; at Tier 3 both the "
                      "deploy and turning the flag on are decided.", gate("aidlc-release"))

    def test_independent_slices_exception_is_everywhere(self):
        for rel in self.EXCEPTION_FILES:
            self.assertRegex(flat(rel), r"(?i)independent slices|slices are independent", rel)
        plan = skill("aidlc-plan")
        self.assertIn("A plan with independent slices is the exception: it waits for the tech lead at every tier "
                      "(ADR 0025).", plan)
        self.assertEqual(plan.count("A plan with independent slices is the exception"), 2)
        self.assertIn("unless the slices are independent: then the tech lead approves, as at Tier 2.",
                      flat("skills/aidlc-plan/assets/plan.md"))
        self.assertIn("none at Tier 1 unless slices are independent", flat("docs/operating-model/routes.md"))
        self.assertIn("ADR 0026); a plan with independent slices is still approved; people approve", flat("README.md"))
        for rel in ("docs/operating-model/tiers.md", "starter/repo/AGENTS.md",
                    "skills/aidlc-onboard/assets/agents-md.md"):
            self.assertIn("Release only when users see the change; a plan with independent slices is still approved",
                          flat(rel), rel)
        self.assertIn("A plan with independent slices is still approved by the tech lead at Tier 1",
                      flat("skills/using-aidlc/SKILL.md"))

    def test_build_wording(self):
        build = skill("aidlc-build")
        self.assertIn("Hands-on: wait for the person to confirm. (This wait is Tier 3's; at Tier 1 and 2 see below.)",
                      build)
        self.assertIn("not a separate stop before the push (ADR 0026). The engineer decides the findings on the pull "
                      "request, before the code owner's approval; high and medium findings block the merge.",
                      gate("aidlc-build"))

    def test_specify_gate_names_the_tiers(self):
        self.assertIn("At Tier 2 and 3 the spec also merges to the default branch first", gate("aidlc-specify"))

    def test_compliance_compares_the_standard_changes_section(self):
        text = flat("agents/reviewer-compliance.md")
        self.assertIn("compares the commit's `Recipe:` trailer with the evidence file's STANDARD line", text)
        self.assertIn("the Standard changes section of `AGENTS.md` as merged on the default branch", text)

    def test_progress_note_restatement_heading(self):
        text = read("skills/aidlc-build/assets/progress-note.md")
        self.assertIn("## Restatement (stated at Tier 1 and 2 in every mode; at Tier 3 confirmed under Pauses "
                      "confirmed)", text)

    def test_design_wireframe_approval_is_in_the_pull_request(self):
        self.assertIn("At Tier 2 and 3 you check that pull request's approval instead, and write it to the tracker as "
                      "ADR 0023 says.", flat("skills/aidlc-design/SKILL.md"))
        self.assertIn("the product owner approves it (at Tier 2 and 3, in the pull request that merges the design "
                      "and the plan)", skill("aidlc-design"))

    def test_routes_release_hexagon_and_s_row(self):
        routes = read("docs/operating-model/routes.md")
        self.assertIn('releaseok{{"Release approver, when users see the change (always at Tier 3)"}}', routes)
        s_row = [line for line in routes.splitlines() if line.startswith("| S · standard change")][0]
        self.assertIn("release when users see the change", s_row)


if __name__ == "__main__":
    unittest.main()
