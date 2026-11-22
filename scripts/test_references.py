"""Plan 26: shorter stage skills. Five stage skills keep their main path and every gate in `SKILL.md`, and move the
steps of one route or case into `references/<case>.md`, read on a named condition. A reference never holds a gate,
`SKILL.md` names every reference with the condition to read it, and a rule is written once
(docs/design/2026-11-21-shorter-stage-skills.md)."""
import importlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DESIGN = "docs/design/2026-11-21-shorter-stage-skills.md"
DECIDE = ("A person decides here only where the tiers file's decisions table lists this decision; otherwise state "
          "what you did and go on.")
LANE = "In a lane, release at your gate as `parallel-lanes` says."
APPROVE = "You draft; you never approve."
SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Produces", "## Gate", "## Stop if", "## Common excuses",
            "## Red flags", "## Rules")
GATE_SECTIONS = SECTIONS[4:]
# The nine test files whose `skill(name)` helper reads a skill's text (test_validate.py's `skill` builds a fixture).
HELPER_FILES = ("test_fast_path", "test_fewer_approvals", "test_greenfield", "test_instructions_first",
                "test_multirepo", "test_parallel_lanes", "test_recording", "test_route_and_log", "test_routes")
OPENING = re.compile(r"Sent here from `(aidlc-[a-z]+)` [^\n;]+; this skill's Gate, Stop if and Rules still apply\.")
LOAD = re.compile(r"\b[Ll]oad the `([a-z0-9-]+)` skill")
STOP_WORD = re.compile(r"\b[Ss]tops?\b")
NAMED_FILE = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9._-]+)`")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def references(name: str) -> dict:
    """A skill's references, by file name, in name order."""
    return {p.name: p.read_text(encoding="utf-8")
            for p in sorted((ROOT / "skills" / name / "references").glob("*.md"))}


def words(name: str) -> int:
    """The words in a skill's SKILL.md, front matter included, as `wc -w` counts them: runs of non-whitespace."""
    return len(skill_md(name).split())


def section(text: str, heading: str) -> str:
    """One `## ` section of a raw text, from its heading to the next `## ` heading."""
    start = text.index("\n" + heading + "\n")
    end = text.find("\n## ", start + len(heading) + 2)
    return text[start:] if end < 0 else text[start:end]


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def stop_sentences(text: str) -> list:
    """The sentences outside code that tell the AI to stop: each holds the word "stop" or "stops", in lower case or
    with a capital S. The bundle field `STOP IF`, in capitals or in a code span, is a field name, not a stop. A
    sentence ends at ". ", "? " or "! ", at a blank line, or where a list item or a table row begins."""
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*]|\d+\.|\|)\s)", outside_code(text))
    return [re.sub(r"^(?:[-*]|\d+\.|\|)\s+", "", flat(p)) for p in parts if STOP_WORD.search(p)]


class ToolingTest(unittest.TestCase):
    """Task 1: the tests read a skill's references, and the stop rule finds a stop, not a field name."""

    def test_every_skill_helper_reads_skill_md_then_its_references(self):
        own = flat(read("skills/aidlc-onboard/SKILL.md"))
        ref = flat(read("skills/aidlc-onboard/references/suppression-rules.md"))
        for module in HELPER_FILES:
            text = importlib.import_module(module).skill("aidlc-onboard")
            self.assertTrue(text.startswith(own), module)
            self.assertIn(ref, text, module)

    def test_the_stop_rule_finds_a_stop_and_not_the_field_name(self):
        sample = ("1. Fill STOP IF with the limits.\n2. Copy `STOP IF` from the class.\n3. Any yes, stop: it is "
                  "route D2.\n4. A package it adds is a stop for the approver. Stop as this skill's Stop if says.\n")
        self.assertEqual(stop_sentences(sample), ["Any yes, stop: it is route D2.",
                                                  "A package it adds is a stop for the approver.",
                                                  "Stop as this skill's Stop if says."])

    def test_the_opening_line_names_the_skill(self):
        line = ("Sent here from `aidlc-plan` step 5, a plan with independent slices; this skill's Gate, Stop if and "
                "Rules still apply.")
        self.assertEqual(OPENING.fullmatch(line).group(1), "aidlc-plan")


class Layout:
    """The checks every shortened skill passes. A class sets NAME, REFS (its reference files, in name order) and
    LIMIT (the word target), and mixes this in with unittest.TestCase."""

    NAME, REFS, LIMIT = "", (), 0

    def ref(self, file_name: str) -> str:
        return read(f"skills/{self.NAME}/references/{file_name}")

    def test_skill_md_meets_its_word_target(self):
        self.assertLess(words(self.NAME), self.LIMIT, self.NAME)

    def test_its_references_are_the_planned_files(self):
        self.assertEqual(tuple(references(self.NAME)), self.REFS)

    def test_skill_md_names_each_reference_with_its_condition(self):
        text = flat(skill_md(self.NAME))
        for file_name in self.REFS:
            self.assertIn(f"read `references/{file_name}` now and follow it", text, file_name)

    def test_each_reference_opens_with_where_it_is_sent_from(self):
        for file_name in self.REFS:
            lines = self.ref(file_name).split("\n")
            self.assertTrue(lines[0].startswith("# "), file_name)
            self.assertEqual(lines[1], "", file_name)
            found = OPENING.fullmatch(lines[2])
            self.assertIsNotNone(found, (file_name, lines[2]))
            self.assertEqual(found.group(1), self.NAME, file_name)

    def test_the_gates_stay_whole_in_skill_md(self):
        raw = skill_md(self.NAME)
        positions = [raw.find("\n" + s + "\n") for s in SECTIONS]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(raw.count(DECIDE), 1)
        gate = flat(section(raw, "## Gate"))
        self.assertTrue(gate.endswith(DECIDE + " " + (LANE + " " if LANE in raw else "") + APPROVE), self.NAME)
        for file_name in self.REFS:
            text = self.ref(file_name)
            for heading in GATE_SECTIONS:
                self.assertNotIn("\n" + heading + "\n", "\n" + text, (file_name, heading))
            for line in (DECIDE, LANE, APPROVE):
                self.assertNotIn(line, flat(text), (file_name, line))

    def test_every_file_a_reference_names_exists(self):
        for file_name in self.REFS:
            for named in NAMED_FILE.findall(self.ref(file_name)):
                self.assertTrue((ROOT / "skills" / self.NAME / named).is_file(), (file_name, named))

    def test_load_phrases_stay_in_skill_md(self):
        for file_name in self.REFS:
            self.assertEqual(LOAD.findall(flat(self.ref(file_name))), [], file_name)

    def test_a_stop_in_a_reference_points_to_stop_if(self):
        for file_name in self.REFS:
            for sentence in stop_sentences(self.ref(file_name)):
                self.assertIn("Stop if", sentence, (file_name, sentence))


class SpecifyTest(Layout, unittest.TestCase):
    """Task 2: `aidlc-specify` keeps amendment mode's steps in a reference; its stop and its decisions stay in
    SKILL.md."""

    NAME, REFS, LIMIT = "aidlc-specify", ("amendment.md",), 2000  # Plan 27 reaches 1,937 (item W2)

    def test_the_amendment_stop_and_decisions_stay_in_skill_md(self):
        raw = skill_md(self.NAME)
        self.assertIn("- In amendment mode, a gap its criterion's owner has not decided: write no new version until "
                      "the owner decides.", flat(section(raw, "## Stop if")))
        self.assertIn("In amendment mode, the criterion's owner decides a gap, and the tech lead classifies each part.",
                      flat(section(raw, "## Gate")))
        self.assertIn("Keep the header's route equal to the index's ROUTE line.", flat(section(raw, "## Steps")))
        ref = flat(self.ref("amendment.md"))
        self.assertIn("Never pick one. Until the owner decides, stop as this skill's Stop if says.", ref)
        self.assertIn("The classification is the tech lead's decision, as this skill's Gate says.", ref)


class DesignTest(Layout, unittest.TestCase):
    """Task 3: `aidlc-design` keeps amendment mode, route G's `new-system.md` and the several-repositories steps in
    references; every approval stays in SKILL.md."""

    NAME, REFS = "aidlc-design", ("amendment.md", "route-g.md", "several-repositories.md")
    LIMIT = 2600  # the design's target is 2,000; Plan 26 reached 2,324; Plan 27 2,480; Plan 27b reaches 2,555 (27b item W1)

    def test_the_approvals_and_the_load_stay_in_skill_md(self):
        raw = skill_md(self.NAME)
        steps = flat(section(raw, "## Steps"))
        for phrase in ("On route G: read `references/route-g.md` now and follow it; then go on with step 2. 2. Load the "
                       "`building-ci-pipelines` skill and design the team's CI",
                       "3. The tech lead or architect approves the design and `new-system.md` together, on the work "
                       "item.",
                       "8. For a story that spans several repositories: read `references/several-repositories.md` now "
                       "and follow it; then go on with step 9. 9. Present the decision for approval"):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("the consumers approve a contract change", flat(section(raw, "## Gate")))
        self.assertIn("The consumers' approval is this skill's Gate's decision.", flat(self.ref("amendment.md")))
        self.assertIn("Each fact has one owner, and only the owner changes it (ADR 0022).",
                      flat(section(raw, "## Produces")))


class StartTest(Layout, unittest.TestCase):
    """Task 4: `aidlc-start` keeps route S's check and limits, the route decision and the route-change table in
    SKILL.md; the standard brief's steps, route G's, the workspace's and re-routing's go to references."""

    NAME, REFS, LIMIT = "aidlc-start", ("re-routing.md", "route-g.md", "route-s.md", "several-repositories.md"), 2800
    # Plan 26 reached 2,675; Plan 27 reaches 2,756 (item W1)

    def test_the_decisions_the_limits_and_the_table_stay_in_skill_md(self):
        raw = skill_md(self.NAME)
        steps = flat(section(raw, "## Steps"))
        for phrase in ("Read that section as merged on the default branch",
                       "A class added or changed on this branch is not approved: the work takes its normal route.",
                       "Route S also needs Tier 1",
                       "A class is never stretched.",
                       "No section, or no match: sort the work as below.",
                       "To write the brief and the index's rows, read `references/route-s.md` now and follow it.",
                       "That confirmation is Ready on route S, the one decision before Merge (the tiers file's "
                       "decisions table).",
                       "**An index for this key already exists** (re-routing, after a stage stopped because the route "
                       "no longer fits): read `references/re-routing.md` now and follow it; then: - a re-route after "
                       "Ready (ADR 0027)",
                       "| The change | What it needs before the work goes on |"):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("An explorer's answer fails its spot-check twice", flat(section(raw, "## Stop if")))
        self.assertIn("The confirmation is this skill's Gate's decision.", flat(self.ref("route-s.md")))


class PlanTest(Layout, unittest.TestCase):
    """Task 5: `aidlc-plan` keeps brief mode, slice 0, revisions, a part's documents and independent slices in
    references; every stop of a brief and of slice 0 is in Stop if, and the confirmations stay in the Gate."""

    NAME = "aidlc-plan"
    REFS = ("brief-mode.md", "independent-slices.md", "revision.md", "route-g.md", "several-repositories.md")
    LIMIT = 3500  # the design's target is 2,500; Plan 26 reached 3,185 (item W1); Plan 27 reaches 3,373 (item W3); Plan 28 reaches 3,493 (item W1)

    def test_every_stop_of_a_brief_and_of_slice_0_is_in_stop_if(self):
        stops = flat(section(skill_md(self.NAME), "## Stop if"))
        for phrase in ("- In brief mode (route D1, `references/brief-mode.md`), steps 1 and 3. When the expected "
                       "behaviour is written nowhere, stop: it is route D2, and `aidlc-start` re-routes it. Ask the "
                       "three design questions; any yes, stop: it is route D2, and `aidlc-start` re-routes it.",
                       "- In feature brief mode (route F0, `references/brief-mode.md`), step 1. A criterion not written "
                       "on the work item by its owner, or an ambiguity only the owner can settle, means stop: it is "
                       "route F1, and `aidlc-start` re-routes it. Step 3 checks the rest of the fast-path test there: the "
                       "tier rises above 1, a design question is yes or uncertain, a new dependency seems necessary, "
                       "stored data or a schema changes, or the work needs more than one slice or more than the "
                       "pull-request size. Any of these means stop: it is route F1, and `aidlc-start` re-routes it.",
                       "- On slice 0 of route G (`references/route-g.md`), a package the generator added that "
                       "DEPENDENCIES does not list is a stop for the design's approver."):
            self.assertIn(phrase, stops, phrase)
        for file_name in self.REFS:
            self.assertNotIn("it is route D2", flat(self.ref(file_name)), file_name)

    def test_the_references_point_to_stop_if_and_the_gate(self):
        brief = flat(self.ref("brief-mode.md"))
        self.assertEqual(brief.count("Stop if says"), 4)
        self.assertEqual(brief.count("This skill's Gate holds that decision."), 2)
        self.assertIn("is a stop for the design's approver, as this skill's Stop if says)", flat(self.ref("route-g.md")))
        gate = flat(section(skill_md(self.NAME), "## Gate"))
        self.assertIn("In brief mode, the engineer confirms the brief (`fix.md` or `brief.md`) and its tier, which is "
                      "Ready on routes D1 and F0", gate)

    def test_the_main_path_keeps_its_stops(self):
        steps = flat(section(skill_md(self.NAME), "## Steps"))
        for phrase in ("When it would exceed it, stop and propose the split to `aidlc-design`",
                       "give every bundle a `DEPENDS ON` line, `none` or the one slice it builds on. To mark them: read "
                       "`references/independent-slices.md` now and follow it.",
                       "A plan without `DEPENDS ON` lines works as before: one branch, one pull request, slices as "
                       "commits."):
            self.assertIn(phrase, steps, phrase)
        self.assertIn("If an input is missing, say which stage produces it and stop; never plan around it.",
                      flat(section(skill_md(self.NAME), "## Inputs")))

    def test_the_review_fixes(self):
        skill = skill_md(self.NAME)
        stops = flat(section(skill, "## Stop if"))
        self.assertIn("Step 3 checks the rest of the fast-path test there: the tier rises above 1, a design question is "
                      "yes or uncertain, a new dependency seems necessary, stored data or a schema changes, or the work "
                      "needs more than one slice or more than the pull-request size.", stops)
        steps = flat(section(skill, "## Steps"))
        self.assertTrue(steps.startswith("## Steps Brief mode (route D1) and feature brief mode (route F0): read "
                                         "`references/brief-mode.md` now and follow it, in place of steps 1 to 9."))
        self.assertIn("also do step 8 of `references/revision.md`; for a part of a story across several repositories, "
                      "step 8 of `references/several-repositories.md`; for a plan with independent slices, step 8 of "
                      "`references/independent-slices.md`.", steps)
        self.assertIn("Sent here from `aidlc-plan` Steps, before step 1, in brief mode (route D1) or feature brief mode "
                      "(route F0); this skill's Gate, Stop if and Rules still apply.", flat(self.ref("brief-mode.md")))
        self.assertTrue(self.ref("several-repositories.md").split("**Step 8.**")[0].rstrip().endswith("(ADR 0022)."))


class BuildTest(Layout, unittest.TestCase):
    """Task 6: `aidlc-build` keeps the recipe check, slice 0 and slices on their own branch in references; the recipe
    pause, route S's exception and every stop stay in SKILL.md."""

    NAME, REFS = "aidlc-build", ("recipe-commit.md", "route-g.md", "stacked-slices.md")
    LIMIT = 4400  # the design's target is 2,500; Plan 26 reached 3,880; Plan 27 4,271; Plan 27b reaches 4,382 (27b item W2)

    def test_the_recipe_pause_and_its_exception_stay_in_step_5(self):
        step5 = flat(skill_md(self.NAME)).split("5. **When the bundle has a RECIPE", 1)[1].split(" 6. ", 1)[0]
        for phrase in ("Then run the recipe check: read `references/recipe-commit.md` now and follow it.",
                       "Stop for the person's review of that commit, in every mode: set STATUS to `paused: recipe "
                       "review`.",
                       "On route S, for a recipe class that `AGENTS.md`'s Standard changes section lists, do not pause",
                       "The pause lifts only when the brief's RECIPE and the commit's `Recipe:` trailer name the "
                       "class's tool and version exactly; otherwise pause as usual.",
                       "Fixes come after it, as ordinary steps under every gate.",
                       "Then run the recipe check: read `references/recipe-commit.md` now and follow it. A "
                       "`(scaffold)` recipe on slice 0 follows `references/route-g.md` instead."):
            self.assertIn(phrase, step5, phrase)
        self.assertIn("That review is this skill's recipe pause, step 5.", flat(self.ref("route-g.md")))

    def test_step_1_keeps_its_stop_and_names_both_cases(self):
        step1 = flat(skill_md(self.NAME)).split(" 1. ", 1)[1].split(" 2. Read the bundle's TIER", 1)[0]
        for phrase in ("For a stacked slice whose parent merged, or whose parent's branch gained commits: read "
                       "`references/stacked-slices.md` now and follow it.",
                       "If it is red or skips tests, stop: the environment is fixed first.",
                       "On slice 0 of route G: read `references/route-g.md` now and follow it; it says which steps "
                       "change."):
            self.assertIn(phrase, step1, phrase)
        self.assertLess(step1.index("On slice 0 of route G: read"), step1.index("If it is red or skips tests, stop"))
        self.assertIn("For a slice that the plan gave its own branch: read `references/stacked-slices.md` now and "
                      "follow it.", flat(section(skill_md(self.NAME), "## Inputs")))


CHANGES = "docs/design/2026-11-19-aidlc-6-change-list.md"


class DocsTest(unittest.TestCase):
    """Task 7: the contributor rules, the map and the change list say where a case's steps live; aidlc 7.2.0."""

    def test_agents_md_lets_a_stage_keep_a_case_in_references(self):
        standards = flat(read("AGENTS.md").split("## Standards\n", 1)[1].split("\n## ", 1)[0])
        for phrase in ("A stage skill may keep the steps of one route or case in `references/<case>.md` (Plan 26), under "
                       "three rules.",
                       "A reference never holds a gate: no Gate, Stop if, Common excuses, Red flags or Rules section, "
                       "and every stop and decision stays in `SKILL.md`, which the reference points to.",
                       "`SKILL.md` names each reference with the condition to read it, at the step where the case "
                       "begins, and each reference opens with the line that says which step sends you there.",
                       "A rule is written once: a rule another file owns is a pointer to that file.",
                       "A \"Load the `<name>` skill\" phrase stays in `SKILL.md`.",
                       "`scripts/validate.py` checks that a reference holds no gate section and that `SKILL.md` names "
                       "it."):
            self.assertIn(phrase, standards, phrase)
        bullet = read("AGENTS.md").split("\n- A stage skill may keep the steps", 1)[1].split("\n- ", 1)[0]
        self.assertTrue(all(len(line) <= 120 for line in bullet.splitlines()), bullet)

    def test_the_codebase_map_says_where_a_case_lives(self):
        mapping = flat(read("docs/codebase-map.md"))
        for phrase in ("five of them keep the steps of one route or case in `references/`, read on a named condition",
                       "A route's or case's steps in a stage skill: its `references/<case>.md`, named in `SKILL.md` with "
                       "the condition to read it; its stops and decisions stay in `SKILL.md`.",
                       "A stage skill's reference never holds a Gate, Stop if, Common excuses, Red flags or Rules "
                       "section, and its `SKILL.md` names it; `scripts/validate.py` checks both."):
            self.assertIn(phrase, mapping, phrase)

    def test_the_change_list_and_the_version(self):
        changes = read(CHANGES)
        table = changes.split("## 10. After Plan 26 (2026-11-21)", 1)[1]
        self.assertRegex(table, r"(?m)^\| D3 \| Covered, as instructions \|")
        self.assertIn("`docs/plans/2026-11-21-plan-26-shorter-stage-skills.md`", table)
        self.assertIn("aidlc 7.2.0", table)
        self.assertIn("`aidlc-specify` meets its word target (1,797 words). `aidlc-start` (2,675), `aidlc-design` (2,324), "
                      "`aidlc-plan` (3,185) and `aidlc-build` (3,880) stay above theirs (Plan 26, item W1); the tests "
                      "hold these counts as their limits.", table)
        self.assertNotIn("Needs the owner's decision", changes)
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "8.1.0")

    def test_a_lane_reads_a_reference_from_the_skill_folder(self):
        lanes = flat(read("skills/lane-run/SKILL.md"))
        self.assertIn("A `references/<file>.md` path that the stage skill names is in the folder of that `SKILL.md`: "
                      "read it from there, never from the repository.", lanes)


class RecordTest(unittest.TestCase):
    """Task 8: the plan is recorded."""

    RECORD = "docs/verification/2026-11-21-plan-26.md"

    def test_the_verification_record_exists(self):
        record = read(self.RECORD)
        for heading in ("## What changed", "## How it was checked", "## Evidence", "## Not verified here",
                        "## Rulings", "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("aidlc 7.2.0", "python3 scripts/validate.py", "claude plugin validate .", "plan26-move-check.py",
                       "aidlc-specify", "aidlc-design", "aidlc-start", "aidlc-plan", "aidlc-build"):
            self.assertIn(phrase, record, phrase)

    def test_the_record_has_no_open_slot(self):
        self.assertNotIn("{{", read(self.RECORD))


class FinalFixWaveTest(unittest.TestCase):
    """The final review's findings: slice 0 reads its reference before step 1; the brief's confirmation covers its
    route; a slice's progress note is the exception."""

    def test_the_slice_0_pointer_comes_before_step_1(self):
        steps = flat(section(skill_md("aidlc-plan"), "## Steps"))
        pointer = ("Slice 0 (route G), the first slice of each new repository, on branch `feat/<KEY>-slice-0`: read "
                   "`references/route-g.md` now and follow it with steps 1 to 9; it says what step 7's bundle holds.")
        self.assertEqual(steps.count(pointer), 1)
        self.assertLess(steps.index(pointer), steps.index("1. Restate the outcome"))
        self.assertEqual(steps.count("read `references/route-g.md` now"), 1)
        route_g = flat(read("skills/aidlc-plan/references/route-g.md"))
        self.assertIn("Sent here from `aidlc-plan` Steps, before step 1, on slice 0 of route G; this skill's Gate, "
                      "Stop if and Rules still apply.", route_g)
        self.assertNotIn("after step 9", route_g)

    def test_the_brief_confirmation_covers_its_route(self):
        gate = flat(section(skill_md("aidlc-plan"), "## Gate"))
        self.assertIn("which is Ready on routes D1 and F0 and covers the brief's ROUTE line (ADR 0027); the code owner",
                      gate)

    def test_a_slice_progress_note_is_the_exception(self):
        rules = flat(section(skill_md("aidlc-build"), "## Rules"))
        self.assertIn("A slice on its own branch edits the same documents in `plans/<KEY>/slice-<n>/`. Its progress "
                      "note is the exception, as `references/stacked-slices.md` says.", rules)


if __name__ == "__main__":
    unittest.main()
