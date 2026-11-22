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


if __name__ == "__main__":
    unittest.main()
