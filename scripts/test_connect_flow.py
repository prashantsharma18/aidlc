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


STAGE_WORD = re.compile(r"\b(?:aidlc-)?(intent|specify|discover|design|plan|build|verify|review|release|onboard|"
                        r"operate|feedback)\b")
ONE_SOURCE = "the one source of which stages each route runs"


def route_rows(text: str, heading: str) -> dict:
    """The route table after a heading: each route's code, and the stages its third cell (Stages) names."""
    rows = {}
    for line in text.split(heading, 1)[1].splitlines():
        found = re.match(r"\| ([A-Z]\d?) · [^|]+\|[^|]+\| ([^|]+) \|", line)
        if found:
            rows[found.group(1)] = set(STAGE_WORD.findall(found.group(2)))
        elif rows and not line.startswith("|"):
            break
    return rows


class RouteTableTest(unittest.TestCase):
    """Task 2: the map's route table is the one source; every listing agrees; the index names its branches and has a
    `merged` row on every route (G1, G4)."""

    def test_the_two_route_tables_agree_route_by_route(self):
        source = route_rows(skill_md("using-aidlc"), "## The routes")
        drawn = route_rows(read("docs/operating-model/routes.md"), "## The routes at a glance")
        self.assertEqual(sorted(source), ["C", "D1", "D2", "F0", "F1", "F2", "G", "I", "S"])
        self.assertEqual(sorted(drawn), sorted(source))
        for code, stages in source.items():
            self.assertEqual(drawn[code], stages, code)
        self.assertIn("release", source["S"])
        self.assertIn("release", source["D1"])
        self.assertNotIn("release", source["F0"])
        self.assertEqual(source["G"], {"intent", "specify", "design", "onboard", "plan", "build", "verify", "review",
                                       "release"})

    def test_every_listing_points_to_the_map(self):
        routes = flat(section(skill_md("using-aidlc"), "## The routes"))
        self.assertIn("This table is " + ONE_SOURCE + " (ADR 0028): `aidlc-start` writes a row for each stage it "
                      "lists, in this order, and a `merged` row after `aidlc-review` on every route.", routes)
        for rel in ("docs/operating-model/routes.md", "docs/operating-model/lifecycle.md", "README.md"):
            text = flat(read(rel))
            self.assertIn("the `using-aidlc` skill is " + ONE_SOURCE, text, rel)
        step7 = flat(section(skill_md("aidlc-start"), "## Steps")).split(" 7. ", 1)[1].split(" 8. ", 1)[0]
        self.assertIn("Fill SOURCE, KIND, ROUTE, LEVEL and the BRANCH lines, and one row per stage that the route "
                      "table in `using-aidlc` lists for the route (the one source, ADR 0028), in its order, with where it "
                      "runs and the status \"to do\"; where there is an `aidlc-review` row, a `merged` row follows it, on "
                      "every route.", step7)
        self.assertIn("**One repository:** every stage runs inside that repository; `aidlc-design` (always; at Tier 1 "
                      "usually a recorded \"none needed\") has a row on routes F1 and D2.", step7)
        self.assertNotIn("on events, `aidlc-operate`, `aidlc-feedback`", step7)

    def test_the_index_names_its_branches(self):
        template = read("skills/aidlc-start/assets/story-index.md")
        self.assertEqual(template, read("skills/aidlc-plan/assets/story-index.md"))
        block = template.split("```text\n", 1)[1].split("```", 1)[0]
        for line in ("BRANCH     code <type>/<KEY>-<slug>        (every row not named below runs on it; once a "
                     "document pull request merges, it starts from the default branch)",
                     "BRANCH     spec docs/<KEY>-spec        (Tier 2 and 3: the intent and specify rows; it merges "
                     "first, ADR 0020; delete the line at Tier 1)",
                     "BRANCH     plan docs/<KEY>-plan        (Tier 2 and 3: the discover, design and plan rows; it "
                     "starts from the default branch once the spec merges, and merges first; a Tier 1 plan with "
                     "independent slices adds it; delete the line otherwise)"):
            self.assertIn(line + "\n", block, line)
        self.assertLess(block.index("LEVEL"), block.index("BRANCH"))
        self.assertIn("Every route has a `merged` row after `aidlc-review`; a story index at a workspace root has none, "
                      "because each part's index holds it (ADR 0028).", flat(template))
        step7 = flat(section(skill_md("aidlc-start"), "## Steps")).split(" 7. ", 1)[1].split(" 8. ", 1)[0]
        self.assertIn("The BRANCH lines name the code branch always, and at Tier 2 and 3 the spec's and the plan's "
                      "branches, which merge first (ADR 0020). Commit the index on the first row's branch, made from the "
                      "default branch.", step7)

    def test_a_plan_adds_the_branch_lines_it_needs(self):
        slices = flat(read("skills/aidlc-plan/references/independent-slices.md"))
        self.assertIn("At Tier 1, where the index has no `plan` BRANCH line, add `BRANCH plan docs/<KEY>-plan` and "
                      "rename the branch you are on to it (`git branch -m docs/<KEY>-plan`): this plan merges first, "
                      "and every slice's branch starts from the default branch after it.", slices)
        parts = flat(read("skills/aidlc-plan/references/several-repositories.md"))
        self.assertIn("the BRANCH lines `code feat/<KEY>-<part>` and `plan docs/<KEY>-<part>-plan` (this plan's own "
                      "pull request, which merges first)", parts)
        self.assertIn("`aidlc-release` when users see the change, and `merged`", flat(read(
            "skills/aidlc-start/references/route-s.md")))


PLACEMENT = ("Run where the \"Runs in\" cell of this stage's row says, on the branch the index's BRANCH lines name for "
             "that row; started elsewhere, name the right folder, and stop.")
PART_PLACEMENT = "Where this runs: inside the repository, as the \"Runs in\" cell of this stage's row in its index"


class CutsTest(unittest.TestCase):
    """Task 3: R3 (one placement line that names the branch, G1), R5, R6, R9 and R10."""

    def test_every_story_level_stage_points_to_its_row_and_branch(self):
        for name in STORY_LEVEL:
            text = flat(skill_md(name))
            self.assertIn("No index: ask the person to run `aidlc-start` first, and stop.", text, name)
            self.assertEqual(text.count(PLACEMENT), 1, name)
            self.assertLess(text.index("No index: ask the person"), text.index(PLACEMENT), name)
            self.assertNotIn("When it routes the story to several repositories", text, name)
        self.assertIn("provisional key `NEW-<slug>`", flat(skill_md("aidlc-intent")))

    def test_every_part_level_stage_points_to_its_row_and_branch(self):
        for name in PART_LEVEL:
            inputs = flat(section(skill_md(name), "## Inputs"))
            self.assertTrue(inputs.startswith("## Inputs " + PART_PLACEMENT), name)
            for phrase in ("on the branch the index's BRANCH lines name for that row.",
                           "`../stories/<KEY>/coordination-plan.md`, from the repository's root (read-only;", "the workspace root is the folder that holds "
                           "`WORKSPACE.md`, as `parallel-lanes` says", "`[<KEY>] part <n> of <m>: <what>`",
                           "Started elsewhere: name the right folder, and stop."):
                self.assertIn(phrase, inputs, (name, phrase))
            self.assertNotIn("A one-repository story runs entirely in that repository.", inputs, name)

    def test_r5_the_repeated_lead_in_is_gone(self):
        design, plan = flat(section(skill_md("aidlc-design"), "## Gate")), flat(section(skill_md("aidlc-plan"), "## Gate"))
        self.assertEqual(design.count("For a story across several repositories, Decision 2"), 1)
        self.assertIn("never as a separate tracker approval. Its Decision 2 (design and plan) is this design's pull "
                      "request in the home repository", design)
        self.assertEqual(plan.count("For a story across several repositories, Decision 2"), 1)
        self.assertIn("For a part, Decision 2 is the home design pull request plus this plan's pull request", plan)

    def test_r6_review_owns_the_description(self):
        verify = flat(skill_md("aidlc-verify"))
        self.assertNotIn("Draft the pull request description", verify)
        self.assertIn("## Produces The evidence table; `aidlc-review` drafts the pull request description from it.",
                      verify)
        self.assertIn(" 6. Mark this stage's row in the index", verify)
        self.assertIn("2. Draft the pull request description from `assets/pr-description.md`, with the evidence table "
                      "first:", flat(skill_md("aidlc-review")))
        self.assertIn("(`aidlc-review` drafts it from the evidence table)", flat(skill_md("committing-changes")))
        readme = read("README.md")
        self.assertIn("| When the pull request's checks have run | The evidence table |", readme)
        self.assertIn("| Before the code owner reviews | The pull request description and the review record |", readme)

    def test_r9_r10_nothing_is_left_that_nothing_reads(self):
        for name, path in (("coordination-plan", "aidlc-design/assets/coordination-plan.md"),
                           ("workspace", "aidlc-onboard/assets/workspace.md"),
                           ("compat-matrix", "aidlc-release/assets/compat-matrix.md")):
            text = read(f"skills/{path}")
            self.assertTrue(text.startswith(f"<!-- aidlc template: {name} -->\n# "), path)
            self.assertNotIn("\nfields: [", text, path)
        self.assertNotIn("Context gaps noticed", read("skills/aidlc-build/assets/progress-note.md"))


PUSH_RULE = ("- The AI may push its own feature branch: no. Change it to yes only when the AI's credential can push "
             "feature branches and the code host stops it from pushing the default branch (ADR 0028). Never a force-push, "
             "a tag, a merge or an approval; a person opens every pull request.")
RECORD = "`done: approved in pull request <n> by <who>, <how it was confirmed>`"
PUSH = ("when the team's `AGENTS.md` lets you push your own feature branch (ADR 0028), or ask the person to")


class PushTest(unittest.TestCase):
    """Task 4: ADR 0028's push wherever "the person pushes" is stated; G2, the document pull requests' push and stop;
    G3, their record in the index."""

    def test_the_kept_rule_names_its_exception_in_every_copy(self):
        for rel in TIERS_COPIES + (TIERS_DOCS,):
            text = flat(read(rel))
            self.assertIn("- The person pushes: the AI holds no push credential. The exception is ADR 0028: when the "
                          "team's `AGENTS.md` says the AI may push its own feature branch, with a credential that cannot "
                          "push the default branch, the AI pushes the story's own branches; never a force-push or a tag, "
                          "and it never opens, approves or merges a pull request.", text, rel)
        self.assertEqual(read(TIERS_COPIES[0]), read(TIERS_DOCS).split("\n", 1)[1])

    def test_build_pushes_only_its_own_branch(self):
        build = skill_md("aidlc-build")
        step10 = flat(build).split(" 10. Report:", 1)[1].split(" ## Produces", 1)[0]
        self.assertIn("The person pushes and opens the pull request; you hold no push credential.", step10)
        self.assertIn("commit the note and the index together, as the session's last commit. Then, when the team's "
                      "`AGENTS.md` lets you push your own feature branch (ADR 0028) and this was the branch's last slice "
                      "(a slice on its own branch: once that slice is done), push it with a plain `git push`, never with "
                      "force and never the default branch; the person still opens the pull request.", step10)
        self.assertLess(step10.index("as the session's last commit"), step10.index("push it with a plain `git push`"))
        self.assertIn("and the person pushes: you hold no push credential. Where the team's `AGENTS.md` lets you push "
                      "your own feature branch (ADR 0028), you push it, never with force.", flat(section(build, "## Gate")))
        self.assertIn("- You are about to push without the team's leave in `AGENTS.md`, to force-push, or to push the "
                      "default branch or a tag; or to present local results as the verdict.",
                      flat(section(build, "## Red flags")))

    def test_the_other_statements_name_the_exception(self):
        commits = flat(skill_md("committing-changes"))
        self.assertIn("A push, force-push, history rewrite or release tag is needed: a person does it. A plain push of "
                      "your own feature branch, when the team's `AGENTS.md` allows it (ADR 0028), is the exception.",
                      commits)
        self.assertIn("You never push, force-push or tag; a person does. The one exception is a plain push of your own "
                      "feature branch, when the team's `AGENTS.md` allows it (ADR 0028).", commits)
        lanes = flat(skill_md("parallel-lanes"))
        self.assertIn("Ask the person first, unless the team's `AGENTS.md` lets a lane push its own branch. That leave "
                      "covers a plain push only: this lease push asks the person first, always (ADR 0028).", lanes)
        self.assertIn("- The team's `AGENTS.md`: whether a lane may push its own branch, and whether force-push is "
                      "forbidden. The leave is ADR 0028's: a plain push of the row's own feature branch, never the "
                      "default branch or a tag.", lanes)
        self.assertIn("Row 7's push: the AI pushes its own feature branch instead, when the team's `AGENTS.md` allows "
                      "it (ADR 0028).", flat(skill_md("using-aidlc")))
        self.assertIn("| The push | The person who ran the session; with ADR 0028's leave in the team's `AGENTS.md`, "
                      "also the session itself, on the story's own feature branch only, with a credential that cannot "
                      "push the default branch |", read("docs/operating-model/adoption.md"))
        for rel in RULES_FILES:
            self.assertIn(PUSH_RULE, flat(read(rel)), rel)

    def test_g2_a_document_pull_request_waits_commits_pushes_then_stops(self):
        specify = flat(section(skill_md("aidlc-specify"), "## Steps"))
        self.assertIn("as done, or as stopped with the reason. Until Ready is recorded, write `waiting: Ready by <spec "
                      "owner>` there in place of done, as the index's rule for a document's decision says. At Tier 2 and "
                      "3, write that wait first, then commit the spec and the index on the spec's branch (the index's "
                      "`spec` BRANCH line) and push it, " + PUSH + "; stop: a person opens the pull request "
                      "`[<KEY>] spec v<n>`, whose description is the spec's \"For the reviewer\" section.", specify)
        plan = flat(section(skill_md("aidlc-plan"), "## Steps"))
        self.assertIn("as done, or as stopped with the reason. When the plan merges first (at Tier 2 and 3, or with "
                      "independent slices), write `waiting: Design + plan by <tech lead>` there in place of done, as the "
                      "index's rule for a document's decision says; then commit the plan, its bundles and the index on "
                      "the plan's branch (the index's `plan` BRANCH line) and push it, " + PUSH + "; stop: a person "
                      "opens the pull request `[<KEY>] design + plan v<n>` (for a part, the title the Gate gives), whose "
                      "description is the plan's \"For the reviewer\" section.", plan)
        design = flat(section(skill_md("aidlc-design"), "## Steps"))
        self.assertIn("as done, or as stopped with the reason. For a story across several repositories, write "
                      "`waiting: Design + plan by <tech lead>` there in place of done, as the index's rule for a "
                      "document's decision says; then commit the design's documents and the index on the plan's branch "
                      "(the index's `plan` BRANCH line) and push it, " + PUSH + "; stop: a person opens the home design "
                      "pull request, whose description is the design note's \"For the reviewer\" section.", design)
        for steps in (specify, plan, design):
            self.assertLess(steps.index("waiting:"), steps.index("then commit"))
        review = flat(skill_md("aidlc-review"))
        self.assertIn("push that commit when the team's `AGENTS.md` lets you push your own feature branch (ADR 0028). "
                      "The session then tells the person the pull request is ready to merge; you never merge", review)

    def test_one_rule_says_which_row_holds_a_wait(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md"):
            self.assertIn("when the wait ends, that row reads `to do` again. That is every wait (a pause, a pull request "
                          "to open, CI, Merge in the `merged` row, Release) except one (ADR 0028): a document's decision "
                          "(Ready, Design + plan, a brief's confirmation) waits in that document's own row, in place of "
                          "done, and ends with its record, never with `to do`: for a pull request's approval, the record "
                          "below; for a brief's confirmation, `done: confirmed by <engineer>, <how it was confirmed>`.",
                          flat(read(rel)), rel)
        lanes = flat(skill_md("parallel-lanes"))
        for phrase in ("whichever row holds it (a plan's approval waits in the plan row, as the story index's rule for a "
                       "document's decision says, and is still the plan's);",
                       "So each cell has one writer at a time, and a stage's `done` is never overwritten. The exception is "
                       "a document's decision (Ready, Design + plan, a brief's confirmation): it waits in that document's "
                       "own row, which was never `done`, and ends with its record, never with `to do`, as the story "
                       "index's rule says (ADR 0028).",
                       "- A waiting row is in the row of the next unfinished stage (lane step 6), except a document's "
                       "decision (Ready, Design + plan, a brief's confirmation), which waits in its own row and ends with "
                       "its record, as the story index's rule says (ADR 0028)."):
            self.assertIn(phrase, lanes, phrase)

    def test_g3_a_merged_document_is_never_edited_for_its_record(self):
        specify = flat(section(skill_md("aidlc-specify"), "## Gate"))
        self.assertIn("then write the spec's Approval record and the work item's entry from it, with how it was "
                      "confirmed, and ask before posting (ADR 0026). At Tier 2 and 3, \"the spec's Approval record\" in "
                      "the sentence before means the specify row of the story's index, " + RECORD + ", which the next "
                      "start writes on the next row's branch; the spec's own slot names its pull request before the "
                      "push, so the merged spec is never edited (ADR 0028).", specify)
        plan = flat(section(skill_md("aidlc-plan"), "## Gate"))
        self.assertIn("That pull request approval is the record: the work item's entry is written from it (ADR 0026). "
                      "When the plan merges first, \"the plan's APPROVAL line\" above means the plan row of the story's "
                      "index, " + RECORD + ", which the next start writes on the next row's branch; the APPROVAL line "
                      "names its pull request before the push, so the merged plan is never edited (ADR 0028).", plan)
        design = flat(section(skill_md("aidlc-design"), "## Gate"))
        self.assertIn("When the design merges first, that APPROVED line and the ADR draft's Status are written before "
                      "the push instead, as `approved in its pull request` and `Accepted when its pull request merges`; "
                      "the merged files are never edited, and the record is a row of the story's index: in a single "
                      "repository, where the design merges with the plan at Tier 2 and 3, the plan row; for a story "
                      "across several repositories, where the home design pull request merges on its own, the design "
                      "row (ADR 0028).", design)
        for rel, slot in (("skills/aidlc-specify/assets/spec.md", "At Tier 2 and 3, where the spec merges first:"),
                          ("skills/aidlc-plan/assets/plan.md", "(When the plan merges first:"),
                          ("skills/aidlc-design/assets/design-note.md", "(When the design merges first:")):
            self.assertIn(slot, read(rel), rel)
            self.assertIn("in place of", read(rel), rel)
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md"):
            self.assertIn("A document that merges first (at Tier 2 and 3 the spec, and the design with the plan or, "
                          "across several repositories, on its own; a plan with independent slices) is never edited "
                          "after its approval: the next start that finds its pull request approved and merged first makes "
                          "the next row's branch, then writes the document's row there as " + RECORD + " (ADR 0028).",
                          flat(read(rel)), rel)


NO_TEST_ROW = ("`- <commit> · no test for <criterion> · <why a test is impractical> · <the other proof> · owner <the "
               "code owner>`")


class TestsFirstTest(unittest.TestCase):
    """Task 5: tests first when a test is practical; a criterion with no test is a decision-log row with why and the
    other proof (ADR 0029), and never a skipped test."""

    def test_build_keeps_the_gate_and_names_the_one_exception(self):
        build = skill_md("aidlc-build")
        step6 = flat(build).split(" 6. Write the tests first.", 1)[1].split(" 7. Implement", 1)[0]
        for phrase in ("The gate: one test per criterion or edge case, named with its ID, before any code.",
                       "For a defect, the first test reproduces the reported failure, and no fix is written until it "
                       "fails for that reason.",
                       "ADR 0029's one exception: a criterion whose test you judge impractical (its test path is unclear, "
                       "it is expensive to build, or there is nothing sensible to assert) gets no test; a cheap local test "
                       "is always written. Before the code, write its decision-log row (step 7), " + NO_TEST_ROW + ", and "
                       "show that proof (a command's output, a live check, a screenshot).",
                       "An unclear criterion is a stop (Stop if), never a criterion with no test, and a test marked skip "
                       "or disabled is still the Quality bar's stop.",
                       "A defect's reproduction still fails first: as a command or a live check, when a test is "
                       "impractical."):
            self.assertIn(phrase, step6, phrase)
        self.assertNotIn("skipped the test", flat(build))
        self.assertIn("| \"The fix is one line; the test can come after.\" | The test comes first.",
                      flat(section(build, "## Common excuses")))
        self.assertIn("| \"This test is impractical, so I will not write it.\" | Only when its path is unclear, it is "
                      "expensive to build, or there is nothing sensible to assert; a cheap local test is always written "
                      "first, and an unclear criterion is a stop. The criterion gets a decision-log row, `no test for "
                      "<criterion>`, with the other proof, and the tests reviewer lists it (ADR 0029). |",
                      flat(section(build, "## Common excuses")))
        self.assertIn("- A criterion has no test and no decision-log row, or a cheap local test is left unwritten (ADR "
                      "0029).", flat(section(build, "## Red flags")))
        self.assertIn("You are editing production code before a failing test exists.",
                      flat(section(build, "## Red flags")))

    def test_the_note_and_the_practice_say_how_the_row_reads(self):
        note = flat(read("skills/aidlc-build/assets/progress-note.md"))
        self.assertIn("A criterion with no test because one is impractical (ADR 0029) is a row too: `no test for "
                      "<criterion>`, why, and the other proof as its evidence; a test marked skip is never a row, but the "
                      "Quality bar's stop.", note)
        practice = flat(skill_md("writing-tests"))
        self.assertIn("- no new test, when none is practical (ADR 0029): its path is unclear, it is expensive to build, "
                      "or there is nothing sensible to assert. Prefer no new test over a bad one (one that tests mocks or "
                      "today's implementation): name the closest check that runs instead, a command, a live check or a "
                      "screenshot. A cheap local test is always written, and a test marked skip is never this case.",
                      practice)

    def test_the_reviewers_and_verify_show_every_criterion_with_no_test(self):
        tests = flat(read("agents/reviewer-tests.md"))
        self.assertIn("- List every criterion with no test (ADR 0029): each decision-log row `no test for <criterion>` in "
                      "the progress notes, with its reason and its other proof. A criterion with a cheap local test and no "
                      "test is a high finding; a row with no other proof is a medium one. A test marked skip is the "
                      "finding the `Nothing skipped` bullet names, never this case.", tests)
        self.assertIn("has a test named with its ID or a logged `no test` row (ADR 0029)",
                      flat(read("agents/reviewer-tests.md")))
        self.assertIn("or the reproduction (D1) has its test, or its `no test for <criterion>` row (ADR 0029)",
                      flat(read("agents/reviewer-compliance.md")))
        none_rule = "A criterion with no test always has its row: never `- none`."
        self.assertIn(none_rule, flat(read("skills/aidlc-build/assets/progress-note.md")))
        self.assertIn(none_rule, flat(skill_md("aidlc-build")))
        self.assertIn("On route D1 that reproduction is the criterion: a reproduction with no test gets its `no test for "
                      "<criterion>` row.", flat(skill_md("aidlc-build")))
        self.assertIn("Then a `Criteria with no test` list, one line per row (criterion, reason, other proof), or "
                      "`Criteria with no test: none`.", tests)
        compliance = flat(read("agents/reviewer-compliance.md"))
        self.assertIn("Every criterion and edge case the slice covers has a test named with its ID. A criterion with no "
                      "test needs a decision-log row, `no test for <criterion>`, with its other proof (ADR 0029); without "
                      "one, it is a high finding.", compliance)
        verify = flat(section(skill_md("aidlc-verify"), "## Steps"))
        self.assertIn("A criterion with no test because one is impractical (ADR 0029) is listed here, with its "
                      "decision-log row and its other proof; write `accepted at Merge by the code owner (ADR 0029)` in "
                      "its who-accepted cell.", verify)
        for text in (tests, compliance, verify, flat(read("skills/aidlc-build/assets/progress-note.md"))):
            self.assertNotIn("skipped as impractical", text)

    def test_the_rules_files_agents_md_and_the_readme_say_its_reach(self):
        for rel in RULES_FILES:
            self.assertIn("- Tests first: a failing test before any code; for a defect, a test that reproduces it. A "
                          "criterion whose test the AI judges impractical gets no test only with a decision-log row, `no "
                          "test for <criterion>`, that says why and what proved it instead (ADR 0029); a cheap local test "
                          "is always written, and a test marked skip is still the Quality bar's stop.",
                          flat(read(rel)), rel)
        self.assertIn("without a design change. Tests first is ADR 0029's rule: a criterion whose test is impractical "
                      "gets no test only with a decision-log row, `no test for <criterion>`, that says why and what proved "
                      "it instead; a test marked skip is still a stop.", flat(read("AGENTS.md")))
        self.assertIn("Tests come first (when a test is practical; a criterion with no test is a logged decision, ADR "
                      "0029); an existing test assertion is never changed to make a test pass.", flat(read("README.md")))


HANDOFF = ("Then give the hand-off: what you did, the index's next row and where it runs, who it waits on, and the "
           "tracker move to suggest now (posting asks first).")
FIX = "write `to do: fix <what>` in the build row and `to do` in the verify and review rows"


class HandoffTest(unittest.TestCase):
    """Task 6: a red run or an accepted finding returns to build in the same slice (G6); every stage that marks a row
    ends with the hand-off (G10, G11)."""

    def test_every_row_stage_ends_with_the_hand_off(self):
        for name in ROW_STAGES:
            steps = flat(section(skill_md(name), "## Steps"))
            self.assertEqual(steps.count(HANDOFF), 1, name)
            self.assertTrue(steps.endswith(HANDOFF), name)

    def test_a_red_run_or_an_accepted_finding_goes_back_to_build(self):
        verify = flat(section(skill_md("aidlc-verify"), "## Stop if"))
        self.assertIn("- A CI check is red, missing or skipped: report it, and never describe the change as passing. A "
                      "red check that passes on the base gets one fresh run, by the person or the team's CI; if it fails "
                      "again, the change caused it, and it returns the work to build in the same slice: " + FIX + ", in "
                      "place of marking this row stopped, and end this stage there (ADR 0028). A check that also fails on "
                      "the base is reported in one line, and the change still does not pass.", verify)
        review = flat(section(skill_md("aidlc-review"), "## Steps"))
        self.assertIn("a low finding may be dismissed with a reason. A high or medium finding the engineer accepts returns "
                      "the work to build in the same slice: " + FIX + "; the fix voids the reviewers' verdicts, so verify "
                      "and review run again (ADR 0028). End this stage there: skip steps 5 to 8, leave this row `to do`, "
                      "and give the hand-off.", review)
        build = flat(section(skill_md("aidlc-build"), "## When to use"))
        self.assertIn("**A fix.** When the build row reads `to do: fix <what>` (a red CI run the change caused, or a "
                      "review finding the engineer accepted), build the fix as new steps of the same slice, from the same "
                      "bundle and inside its MAY CHANGE, with step 8 for a failure; the reviewers' verdicts are void, so "
                      "verify and review run again.", build)
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md"):
            self.assertIn("A red CI run the change caused, or a review finding the engineer accepts, writes "
                          "`to do: fix <what>` in the build row and `to do` in the verify and review rows (ADR 0028).",
                          flat(read(rel)), rel)


RUN_LIMIT = 2150  # a new limit for a new skill: this task writes 2,048 words, and Plan 27b adds about 30
LOAD = re.compile(r"\b[Ll]oad the `([a-z0-9-]+)` skill")


class StoryRunTest(unittest.TestCase):
    """Task 7: `story-run` runs the stages from the index until the next person's decision (ADR 0028)."""

    def test_it_is_a_workflow_skill_only_a_person_starts(self):
        import validate
        text = skill_md("story-run")
        head = text.split("\n---", 1)[0]
        self.assertIn("name: story-run", head)
        self.assertIn("  kind: workflow", head)
        self.assertIn("disable-model-invocation: true", head)
        self.assertEqual(validate.check_skill(ROOT / "skills/story-run/SKILL.md", ROOT), [])
        self.assertLess(words("story-run"), RUN_LIMIT)
        self.assertEqual(LOAD.findall(text), [])
        self.assertTrue(flat(text).endswith(APPROVE))

    def test_its_steps_pick_run_and_go_on(self):
        steps = flat(section(skill_md("story-run"), "## Steps"))
        for phrase in ("1. **Find the story.** Read its index where this session runs. No index: the next stage is "
                       "`aidlc-start`, which writes it.",
                       "2. **Pick the next row.** Take the first row that is not done,",
                       "The `merged` row counts as done only once it reads done on the default branch",
                       "A row that reads `waiting: <decision> by <who>` resumes only when its decision can be had",
                       "or given by the decider in this session (ADR 0023)",
                       RECORD,
                       "3. **Get on the row's branch.** The index's BRANCH lines name it.",
                       "Never work on the default branch.",
                       "4. **Run the stage.** Read the row's stage `SKILL.md` by its path, and every reference whose "
                       "condition holds, and follow them in full",
                       "Its Inputs, its Gate, its Stop if and its Rules hold as written.",
                       "one slice at a time, in the plan's order.",
                       "5. **Go on, or stop.** Key on what the stage wrote in its row.",
                       "When it wrote `doing` (the build row, slices remain), go on with the next slice, or stop for a "
                       "fresh session as `aidlc-build`'s When to use says.",
                       "Push also a branch whose last slice is done but not yet pushed (no upstream, or ahead of it), when "
                       "opening its pull request is the next person's action.",
                       "6. **Before every stop.** First write the wait, `waiting: <decision> by <who>`, into the row the "
                       "index's rule names",
                       "Then commit it with what the stage wrote. Push only where a stage says to: build after a branch's "
                       "last slice, a document's pull request (specify, plan, the home design), and review's final commit;",
                       "Never push to pause: not at Ready, a checkpoint, a question, or a long session",
                       "Take the first row that is not done, even when a later row reads done",
                       "the wait ends only when its pull request is approved and merged: first make the next row's branch "
                       "(step 3), then write the document's row there",
                       "At a workspace root, once the design row is done, the next work is each part:",
                       "Check the tree is clean (`git status --porcelain` prints nothing)",
                       "7. **The hand-off.** Open with one sentence that names what waits, and on whom",
                       "the tracker move to suggest now", "the next start, `story-run <KEY>`",
                       "Posting to the tracker or a pull request asks first (ADR 0023)."):
            self.assertIn(phrase, steps, phrase)
        six = steps.split("6. **Before every stop.**", 1)[1]
        self.assertLess(six.index("First write the wait"), six.index("Then commit it"))
        self.assertLess(six.index("Then commit it"), six.index("Push only where"))
        inputs = flat(section(skill_md("story-run"), "## Inputs"))
        self.assertIn("The stage skills: the `aidlc-*` folders beside this skill's folder.", inputs)
        self.assertIn("read it from there, never from the repository.", inputs)

    def test_it_stops_where_the_stages_and_people_stop(self):
        stops = flat(section(skill_md("story-run"), "## Stop if"))
        for phrase in ("a question for the product owner or a criterion's owner, Ready, Design + plan at Tier 2 and 3 or "
                       "for a plan with independent slices, a MODE checkpoint, the Tier 3 restatement, the recipe review, "
                       "or any item of its own Stop if.",
                       "its pull request is not open yet: stop for the person to open it (\"open the pull request for "
                       "SHIP-12 slice 1\").",
                       "The team's CI has not run on the pull request yet, or is still running: stop;",
                       "Merge: the code owner's approval, and the merge after it, are a person's.",
                       "Release, when users see the change: the release approver decides.",
                       "route G's `aidlc-onboard (prepare)`, `slice 0` or `aidlc-onboard (confirm)`",
                       "A document's pull request is approved but not merged yet: stop for the person to merge it.",
                       "At a workspace root, the design row is done: the parts run in their repositories",
                       "The pull request has a merge conflict, or the default branch moved under it",
                       "The tree is not clean when the run starts",
                       "A step needs a force-push, a push to the default branch or of a tag, a merge, an approval, or "
                       "opening or closing a pull request: a person does it.",
                       "as `aidlc-build`'s When to use says"):
            self.assertIn(phrase, stops, phrase)
        when = flat(section(skill_md("story-run"), "## When to use"))
        self.assertIn("That start is the person's go-ahead for the stages up to that decision (ADR 0028), as a person's "
                      "start of a lane is (ADR 0025).", when)

    def test_it_never_pushes_past_its_own_branch(self):
        rules = flat(section(skill_md("story-run"), "## Rules"))
        self.assertIn("You never approve, merge, or open or close a pull request. You push only your own feature "
                      "branch, as the index's BRANCH lines name it, when the team's `AGENTS.md` allows it, and never "
                      "with force (ADR 0028).", rules)
        self.assertIn("This skill adds no step to a stage and lifts none of its gates.", rules)
        self.assertIn("\"where your AI tool has one\"", rules)
        flags = flat(section(skill_md("story-run"), "## Red flags"))
        self.assertIn("- You are about to force-push, push the default branch or a tag, merge, approve, or open or close "
                      "a pull request.", flags)

    def test_the_map_and_the_lanes_name_it(self):
        self.assertIn("`story-run` runs one story's stages in one session, one after another, until the next person's "
                      "decision (ADR 0028).", flat(skill_md("using-aidlc")))
        self.assertIn("no lane is needed. `story-run` runs such an item's stages one after another, in one session.",
                      flat(skill_md("parallel-lanes")))
        for rel in ("README.md", "AGENTS.md", "docs/codebase-map.md"):
            self.assertIn("story-run", read(rel), rel)
        self.assertIn("| `/aidlc:story-run SHIP-12` |", read("README.md"))


CASES = {"story-run-stops-at-ready": ("specify-waits.md", "no-design-note.md", "no-plan.md",
                                      "no-relayed-approval-write.md", "no-relayed-approval-edit.md", "reply.md"),
         "story-run-tier1-design-no-stop": ("design-stated.md", "design-row-done.md", "plan-written.md",
                                            "no-design-wait.md", "reply.md"),
         "story-run-pushes-own-branch": ("pushed.md", "never-main.md", "never-force.md", "never-merge.md", "reply.md"),
         "story-run-stops-at-merge": ("never-merge.md", "never-main.md", "merged-not-done.md",
                                      "no-relayed-approval-edit.md", "no-relayed-approval-write.md", "reply.md"),
         "gate-no-test-logged": ("note-written.md", "ac1-tested.md", "notes.md")}


class EvalCasesTest(unittest.TestCase):
    """Task 8: five behaviour cases for `story-run` and ADR 0029, written and not run."""

    def test_each_case_has_its_scaffold_prompt_and_graders(self):
        for name, graders in CASES.items():
            folder = ROOT / "evals" / name
            self.assertEqual(sorted(p.name for p in (folder / "graders").glob("*.md")), sorted(graders), name)
            self.assertIn(f"name: {name}", read(f"evals/{name}/case.yaml"), name)
            self.assertTrue((folder / "setup.sh").stat().st_mode & 0o111, name)
            prompt = read(f"evals/{name}/prompt.md")
            self.assertIn("tags: [gate]", prompt, name)
            start = "/aidlc:aidlc-build SHIP-74" if name.startswith("gate-") else "/aidlc:story-run SHIP-7"
            self.assertIn(start, prompt, name)

    def test_the_graders_push_on_the_rule(self):
        self.assertIn("waiting:", read("evals/story-run-stops-at-ready/graders/specify-waits.md"))
        self.assertIn("RECORDED BY", read("evals/story-run-tier1-design-no-stop/graders/design-stated.md"))
        self.assertIn("The AI may push its own feature branch: yes.", read("evals/story-run-pushes-own-branch/setup.sh"))
        self.assertIn("max: 0", read("evals/story-run-pushes-own-branch/graders/never-main.md"))
        for name in ("story-run-pushes-own-branch", "story-run-stops-at-merge"):
            self.assertIn("[^\"&;|]*", read(f"evals/{name}/graders/never-main.md"), name)
        self.assertIn("match: not_contains", read("evals/story-run-stops-at-merge/graders/merged-not-done.md"))
        self.assertIn("`no test for AC2`", read("evals/gate-no-test-logged/graders/notes.md"))

    def test_the_evals_readme_names_them(self):
        readme = flat(read("evals/README.md"))
        self.assertIn("there are 42 cases before Plan 27's five, 47 in all.", readme)
        self.assertIn("The five cases for `story-run` and tests first (ADR 0028, ADR 0029) are " +
                      ", ".join(f"`{n}`" for n in CASES) + "; all five need Bash.", readme)


CHANGES = "docs/design/2026-11-19-aidlc-6-change-list.md"


class DocsTest(unittest.TestCase):
    """Task 9: the docs name `story-run`; the change list after Plan 27; aidlc 8.0.0."""

    def test_the_docs_name_one_start_per_decision(self):
        for rel, phrase in (("docs/operating-model/routes.md", "A person can start each stage by name, or start "
                             "`story-run` once per decision: it runs the stages from one hexagon to the next, and stops "
                             "there (ADR 0028)."),
                            ("docs/operating-model/lifecycle.md", "- A person may start `story-run` once per decision: "
                             "it runs the stages between two decisions and stops at the next one (ADR 0028)."),
                            ("docs/quickstart/claude-code.md", "Or start `/aidlc:story-run <KEY>` once per decision: it "
                             "runs the stages until the next one a person takes (ADR 0028)."),
                            ("docs/operating-model/workspace-and-repositories.md", "its status (a person moves it, when "
                             "a stage's hand-off suggests the move, ADR 0028);")):
            self.assertIn(phrase, flat(read(rel)), rel)

    def test_the_change_list_and_the_version(self):
        changes = read(CHANGES)
        table = changes.split("## 11. After Plan 27 (2026-11-22)", 1)[1]
        self.assertRegex(table, r"(?m)^\| D1 \| Covered in part, as instructions \|")
        for item in ("G1", "G2", "G3", "G4", "G6", "G10, G11", "X3", "R3, R5, R6, R9, R10", "Tests first",
                     "Word limits"):
            self.assertRegex(table, rf"(?m)^\| {re.escape(item)} \|", item)
        for phrase in ("`docs/plans/2026-11-22-plan-27-connect-the-flow.md`", "aidlc 8.0.0", "ADR 0028", "ADR 0029"):
            self.assertIn(phrase, table, phrase)
        self.assertNotIn("Needs the owner's decision", changes)
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "8.0.0")


if __name__ == "__main__":
    unittest.main()
