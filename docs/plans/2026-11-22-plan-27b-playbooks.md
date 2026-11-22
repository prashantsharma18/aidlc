# The Playbooks: Implementation Plan (Plan 27b)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eight playbooks, adapted from pstack, say for one kind of work what to do, in what order, which practices the
bundle names and what proof that kind needs: `feature`, `bug-fix`, `performance`, `refactoring`, `visual-change`,
`dependency-bump`, `investigation` and `spike`, in `skills/story-run/references/`. `aidlc-plan` writes a PLAYBOOK line
in each bundle; build and verify read the playbook it names, whoever runs them. A playbook never holds or lifts a gate:
the validator checks it holds no gate section, and a test checks that every stop it points to is in that stage's Stop
if. People's decisions and every stage's gates are unchanged.

**Architecture:** A playbook is a stage reference that lives in `story-run`'s folder, so build, verify, discover and
design reach it by the same path, `../story-run/references/playbook-<kind>.md` from their own folder, whether `story-run`
runs the stage or a person does. It holds steps and proof only. Each limit a playbook names is a stop in the stage's own
`SKILL.md` (Plan 26's rule 1); four lines are added to the stages' Stop if for the limits no stage stated yet.

**Tech Stack:** Markdown, Python 3.12 standard library `unittest` and `scripts/validate.py`, git. No new dependency.

**Spec:** `docs/design/2026-11-22-connect-the-flow.md`, Part 3 (approved by the framework owner in the session,
2026-11-22), and ADR 0028's playbook decision. The split from Plan 27 follows the design ("the playbooks become their
own plan") and the independent review of Plan 27's first draft, which judged it sound and set its conditions: the
change list's "Playbooks" row and the record's playbook sentence move here (done); the notice is widened in Plan 27
(done); ADR 0028 keeps the decision (done); the word limits are checked for the words this plan adds (items W1 and W2
below); this plan carries the fix for the review's finding M8 (Task 1).

Branch: `docs/connect-the-flow`. Base: Plan 27 executed in full on this branch, its record committed. aidlc 8.0.0 (this
plan ships in the same release, so it raises no version). The suite is then 698 tests, OK; the validator reports
`validate: 1 plugin, 32 skill(s), 0 problem(s)`.

## Decisions this plan makes

| Question | Ruling | Why |
|---|---|---|
| How a stage names a playbook | As `../story-run/references/playbook-<kind>.md` "from this skill's folder", never as `references/…` | The validator checks that a `references/<file>` a skill names is in its own folder; the `../` form is not checked, and `aidlc-build`'s `stacked-slices.md` already reads `parallel-lanes` "in the folder beside this skill's" the same way |
| Which playbooks a bundle names | Six: `feature`, `bug-fix`, `performance`, `refactoring`, `visual-change`, `dependency-bump`, or `none` on slice 0 of route G (review L7). `investigation` and `spike` have no bundle: `aidlc-discover` step 3 reads both, and `aidlc-design` step 4 reads `spike` | The design's table gives them no route; slice 0 builds a skeleton no playbook fits |
| What a playbook says about practices | A **USE SKILLS** line that `aidlc-plan` copies into the bundle; never a "Load the `<name>` skill" phrase | `scripts/test_loads.py` pins each stage's loads |
| The briefs' PLAYBOOK line | `fix.md`: `bug-fix`; `brief.md`: `feature` or `visual-change`; `standard.md`: `dependency-bump` or `refactoring` (a recipe class), or the class's own | A brief serves as the bundle on routes D1, F0 and S |
| Where a playbook's stop points (review M8) | Each sentence that points to a Stop if names the stage: `aidlc-build`'s for the bundle playbooks (verify only reads their proof), and "the stage's" for the spike, which design and discover both read. A test maps every such sentence to the stop it names and checks that stop is in that stage's Stop if; a new pointer must be added to the test's table | A sentence that only contains the words "Stop if" passed the first draft's test with the stop missing from `SKILL.md` |
| The limits a playbook names that no stage stated | Four Stop if lines: in `aidlc-build`, a baseline a test compares against, and the harness that compares or measures it, are an assertion (the existing assertion line, widened), and a change that needs a file outside MAY CHANGE stops (so far only in steps 4 and 9); in `aidlc-design` and `aidlc-discover`, a spike's code is never committed or moved into the build, and a package a spike or a check needs is a new dependency. The dependency-bump playbook's "never edit the lock file by hand" becomes a step (the package manager writes it) | Plan 26's rule 1: every limit stays in `SKILL.md` |
| Production in the bug-fix playbook (review L7) | "locally or in a test environment: a person acts on production (`aidlc-operate`)" | The conflicts list, item 14; `aidlc-operate` already says the AI has no production access |
| The record | Its own file, `docs/verification/2026-11-22-plan-27b.md` (Task 2) | Each plan's evidence reads alone, and Plan 27's record is already committed when this plan runs |
| The word limits | Raised again only where this plan passes Plan 27's: `aidlc-design` and `aidlc-build` (items W1 and W2). `aidlc-plan` reaches 3,417, under Plan 27's 3450, so it stays | The review asked that each plan's limits fit its own words |

## Global Constraints

Plan 27's Global Constraints hold, with these for this plan: new tests go in `scripts/test_connect_flow.py` (one class
per task, above its `if __name__ == "__main__":` line) and the validator's in `scripts/test_validate.py` (one class,
Task 1); a playbook holds steps and proof only, opens with the line that says which stage reads it, names no decision,
and has no `## ` heading; no "Load the `<name>` skill" phrase is added anywhere; the `../story-run/references/` path is
the only way a stage names a playbook; never run the suite with `GIT_DIR` or `GIT_WORK_TREE` set, and never run
`claude plugin eval`.

## Review Focus

1. **A stop or a decision in a playbook.** Task 1's `test_every_stop_a_playbook_points_to_is_in_that_stages_stop_if`
   checks every pointer; a reviewer reads each playbook for a limit with no pointer ("never", "only after", "wait").
2. **A playbook the AI does not read.** The pointers in build step 4, verify step 2, discover step 3 and design step 4
   come before the steps or rows they shape.
3. **Fidelity to pstack.** Each playbook against its source (below): what was taken, and that nothing on report 2's
   conflicts list came in.
4. **The word limits** (items W1 and W2).

## pstack sources consulted

pstack (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan), read again for this plan; `PB/` is
`skills/poteto-mode/playbooks/`. pstack's notice is in `skills/NOTICE` since Plan 27.

| Concept | pstack file | Taken, adapted or rejected |
|---|---|---|
| Playbook: feature | `PB/feature.md` (trace the subsystem; name the data shape first; port a shared-primitive fix to every consumer; verify on the matching surface; small ordered commits) | Adapted: steps 1 to 6 and its proof. Rejected: mandatory delegation (item 15); porting to consumers outside MAY CHANGE (item 16: a stop, `aidlc-build`'s Stop if) |
| Playbook: bug fix | `PB/bug-fix.md` ("Every shipped line traces to runtime evidence"; binary-search the cause through hypotheses; confirm the mechanism; revert what a refuted hypothesis motivated; the failing repro lands before the fix) | Adapted: steps 1 to 6 and its proof; the three-attempt limit stays `aidlc-build`'s. Rejected: `/loop` and sub-agent delegation (item 21); any production action (item 14) |
| Playbook: performance | `PB/perf-issue.md` (the mantras, in order), `PB/hillclimb.md` (one change, one measurement; freeze the harness), `principle-explain-the-number` (via report 2) | Adapted: steps 1 to 6 and its proof; a change to the measurement is a change to the assertion, as `aidlc-build`'s Stop if says. Rejected: parsing traces into sqlite (tool-specific); "push past the plateau" (item 17) |
| Playbook: refactoring | `PB/refactoring.md` (pin the contract first, "Type check and lint are not a pin"; subtract before you add; migrate every caller and delete in one wave; equivalence check; reader load) | Adapted: steps 1 to 7 and its proof. Rejected: deleting tests that pin old internals (item 8) |
| Playbook: visual change | `PB/visual-parity.md` ("no harness modifications, no baseline tampering, no component restructuring to make a diff pass"; image diff, not the eye; shared primitives first) | Adapted: steps 1 to 5; the baseline and its harness are an assertion. Rejected: `/loop` per component until the diff is zero (item 17) |
| Playbook: dependency bump | none in pstack; `PB/babysit.md`'s drift sweep and report 2's route S rows | aidlc's own, in pstack's shape |
| Playbook: investigation | `PB/investigation.md` (read-only; the output shape; push back on a wrong premise; hand back to re-route) | Adapted: steps 1 to 5 |
| Playbook: spike | `PB/prototype.md` ("No decision means no prototype"; throwaway, isolated; variants behind one switch; "The observation is the test"; the output is the decision, not shippable code) | Adapted: steps 1 to 7. Rejected: fetching CDN packages (item 18: a new dependency asks first, now in design's and discover's Stop if) |
| A multi-PR plan's evidence boxes | `PB/multi-phase-plan.md` (unit, live and perf boxes; trunk baseline first) | Adapted into the feature and performance playbooks' proof |

## Needs the owner's decision

**Approving this plan approves exactly the items below, and no other change to an existing test.** The list was built
by applying Plan 27 and then this plan, task by task, to a fresh clone of the branch (see "Self-review notes").

**Totals:** 0 test files deleted; 0 test methods deleted; 2 assertions with a changed expected value (W1, W2). The
suite goes from 698 tests to 711 (698 kept, 13 new: 10 in `scripts/test_connect_flow.py`, 3 in
`scripts/test_validate.py`).

| Item | Skill | Words after Plan 27 | After this plan | Limit after Plan 27 | New limit |
|---|---|---|---|---|---|
| W1 | `aidlc-design` | 2,480 | 2,541 | 2550 | 2600 |
| W2 | `aidlc-build` | 4,271 | 4,346 | 4350 | 4400 |

What the words buy: `aidlc-design` the spike pointer and two Stop if lines; `aidlc-build` the playbook pointer and its
two Stop if changes. `aidlc-plan` (the PLAYBOOK bullet) reaches 3,417, under its 3450; `story-run`
reaches 2,078, under its 2,150. Options: (a) accept; (b) leave the four Stop if lines out, which keeps the limits
and leaves the limits only in the playbooks, against rule 1. Recommended: (a).

**O1. The rulings above.** Approving the plan approves them. 0 test changes.

---
### Task 1: The eight playbooks, the PLAYBOOK line and the validator's check

Eight playbooks, adapted from pstack's (with its notice in `skills/NOTICE`, Plan 27 Task 1), say for one kind of work
what to do, in what order, which practices the bundle names, and what proof that kind needs:
`skills/story-run/references/playbook-<kind>.md` for `feature`, `bug-fix`, `performance`, `refactoring`,
`visual-change`, `dependency-bump`, `investigation` and `spike`. Each opens with the line that says which stage reads
it and that the stage's Gate, Stop if and Rules still apply; each holds steps only (no `## ` heading at all, so no gate
section) and names no decision of its own. Every sentence of a playbook that points to a Stop if names the stage
(`aidlc-build`'s, or for the spike, the stage that reads it), and the test checks that the stop it points to is really
in that stage's Stop if. The limits a playbook names that no stage stated yet go into the stages' Stop if: a baseline
a test compares against, and the harness that compares or measures it, are an assertion; a change that needs a file
outside MAY CHANGE stops (`aidlc-build`, which so far said it only in steps 4 and 9); a spike is thrown away, and a
package it would fetch is a new dependency (`aidlc-design`, `aidlc-discover`). `aidlc-plan` writes a `PLAYBOOK` line in
each bundle (`none` on slice 0 of route G; the task bundle template and the three brief templates gain it);
`aidlc-build` step 4 and `aidlc-verify` step 2 read the playbook it names, from `story-run`'s folder, whoever runs
them; `aidlc-discover` step 3 reads the investigation and spike playbooks, and `aidlc-design` step 4 the spike
playbook. The validator checks that a playbook holds no gate section, with tests. The change list gains its
"Playbooks" row, and two word limits rise again (items W1 and W2 of this plan).

The pstack file each playbook adapts, and what it rejects, is in "pstack sources consulted" above.

**Files:**
- Create: the eight `skills/story-run/references/playbook-<kind>.md`
- Modify: `scripts/validate.py` (`PLAYBOOK_FILES`, `check_playbooks`, one call in `check_skill`),
  `scripts/test_validate.py` (one class); `skills/aidlc-plan/assets/task-bundle.md`,
  `skills/aidlc-plan/assets/fix-brief.md`, `skills/aidlc-plan/assets/feature-brief.md`,
  `skills/aidlc-start/assets/standard-brief.md` (one line each); `skills/aidlc-plan/SKILL.md` (step 7),
  `skills/aidlc-start/references/route-s.md`, `skills/aidlc-build/SKILL.md` (step 4), `skills/aidlc-verify/SKILL.md`
  (step 2), `skills/aidlc-discover/SKILL.md` (step 3), `skills/aidlc-design/SKILL.md` (step 4),
  the Stop if of `aidlc-build`, `aidlc-design` and `aidlc-discover` (four lines for the limits a playbook names), `skills/story-run/SKILL.md` (Inputs), `skills/using-aidlc/SKILL.md` (How a slice
  gets its practices), `AGENTS.md`
  (Map and Standards), `docs/codebase-map.md` (one line), `docs/design/2026-11-19-aidlc-6-change-list.md` (one row),
  `scripts/test_references.py` (items W1 and W2)
- Add to git: `docs/plans/2026-11-22-plan-27b-playbooks.md` (this plan, untracked until now; not edited)
- Test: `scripts/test_connect_flow.py` (`PlaybookTest`), `scripts/test_validate.py` (`PlaybooksTest`)

**Interfaces:**
- Produces: `KINDS`, `BUNDLE_KINDS`, `playbook(kind)`, `outside_code(text)` and `stop_sentences(text)` in
  `scripts/test_connect_flow.py`; `validate.check_playbooks(folder, folder_rel)` and `validate.PLAYBOOK_FILES`.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_connect_flow.py`, above its `if __name__ == "__main__":` line:

````python
KINDS = ("feature", "bug-fix", "performance", "refactoring", "visual-change", "dependency-bump", "investigation",
         "spike")
BUNDLE_KINDS = KINDS[:6]
PLAYBOOK_OPENING = re.compile(r"Read from `aidlc-[a-z]+`[^\n;]* when [^\n;]+; the stage's Gate, Stop if and Rules still "
                              r"apply, and this playbook lifts none of them\.")
STOP_WORD = re.compile(r"\b[Ss]tops?\b")


def playbook(kind: str) -> str:
    return read(f"skills/story-run/references/playbook-{kind}.md")


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def stop_sentences(text: str) -> list:
    """The sentences outside code that tell the AI to stop (as `scripts/test_references.py` finds them)."""
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*]|\d+\.|\|)\s)", outside_code(text))
    return [re.sub(r"^(?:[-*]|\d+\.|\|)\s+", "", flat(p)) for p in parts if STOP_WORD.search(p)]


def sentences(text: str) -> list:
    """Every sentence of a text outside code, whitespace-collapsed."""
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*]|\d+\.|\|)\s)", outside_code(text))
    return [re.sub(r"^(?:[-*]|\d+\.|\|)\s+", "", flat(p)) for p in parts if p.strip()]


BUILD = ("aidlc-build",)
SPIKE_READERS = ("aidlc-design", "aidlc-discover")
MAY_CHANGE = "- A change needs a file outside MAY CHANGE (a caller of a shared helper, a use of a renamed name): stop and report."
# Each sentence of a playbook that points to a Stop if: (a phrase of the sentence, the stages it names, the stop that
# must be in each of those stages' Stop if).
POINTERS = {
    "feature": (("A caller outside MAY CHANGE is a stop", BUILD, MAY_CHANGE),),
    "bug-fix": (("The limit on attempts", BUILD, "The same failure has had three attempts"),),
    "performance": (("a change to the measurement during the work", BUILD,
                     "and the harness that compares or measures it, is an assertion too"),),
    "refactoring": (("A caller outside MAY CHANGE is a stop", BUILD, MAY_CHANGE),
                    ("Stop if says for a contract change", BUILD, "the fix needs a contract change"),
                    ("no assertion changed", BUILD, "A test can only pass by changing an existing assertion")),
    "visual-change": (("the harness that compares it, are an assertion", BUILD,
                       "and the harness that compares or measures it, is an assertion too"),
                      ("that passes a check by lowering the bar", BUILD,
                       "A check can pass only by lowering the Quality bar"),
                      ("proposing one is a new dependency", BUILD, "A new dependency seems necessary.")),
    "dependency-bump": (("A package it adds is a new dependency", BUILD,
                         "a package added to any lock file counts as a new dependency"),
                        ("A major version passes the class's limits", BUILD, "pass one of its LIMITS (a major version"),
                        ("A major version passes the class's limits", BUILD, MAY_CHANGE)),
    "spike": (("never commit it to the story's branch", SPIKE_READERS,
               "- A spike's code would be committed to the story's branch or moved into the build: a spike is thrown "
               "away."),
              ("A package you would have to fetch", SPIKE_READERS,
               "- A spike or a check needs a package that is not installed: that is a new dependency; ask first."),
              ("A spike's code never moves into the build", SPIKE_READERS,
               "- A spike's code would be committed to the story's branch or moved into the build: a spike is thrown "
               "away.")),
}


class PlaybookTest(unittest.TestCase):
    """Task 8: eight playbooks hold steps and proof only; the bundle names one; build and verify read it."""

    def test_the_eight_playbooks_exist_and_open_with_who_reads_them(self):
        names = sorted(p.name for p in (ROOT / "skills/story-run/references").glob("*.md"))
        self.assertEqual(names, sorted(f"playbook-{kind}.md" for kind in KINDS))
        for kind in KINDS:
            lines = playbook(kind).split("\n")
            self.assertEqual(lines[0], "# Playbook: " + kind.replace("-", " "), kind)
            self.assertEqual(lines[1], "", kind)
            self.assertIsNotNone(PLAYBOOK_OPENING.fullmatch(lines[2]), (kind, lines[2]))
            for label in ("**What you own.**", "**Typical route.**", "**Steps.**", "**Its proof.**", "**Hand back.**"):
                self.assertIn(label, playbook(kind), (kind, label))

    def test_a_playbook_holds_no_gate_and_points_every_stop_to_stop_if(self):
        for kind in KINDS:
            text = playbook(kind)
            self.assertNotRegex(text, r"(?m)^## ", kind)
            for line in (DECIDE, APPROVE, "In a lane, release at your gate"):
                self.assertNotIn(line, flat(text), (kind, line))
            self.assertEqual(LOAD.findall(flat(text)), [], kind)
            for sentence in stop_sentences(text):
                self.assertIn("Stop if", sentence, (kind, sentence))

    def test_every_stop_a_playbook_points_to_is_in_that_stages_stop_if(self):
        for kind in KINDS:
            pointers = [s for s in sentences(playbook(kind)) if "Stop if" in s and not s.startswith("Read from")]
            for sentence in pointers:
                found = [entry for entry in POINTERS.get(kind, ()) if entry[0] in sentence]
                self.assertTrue(found, (kind, "a pointer POINTERS does not list", sentence))
                for _, stages, stop in found:
                    for name in stages:
                        self.assertIn(stop, flat(section(skill_md(name), "## Stop if")), (kind, name, stop))
            self.assertEqual(len(pointers), len({entry[0] for entry in POINTERS.get(kind, ())}), kind)

    def test_the_bundle_and_the_briefs_name_a_playbook(self):
        bundle = read("skills/aidlc-plan/assets/task-bundle.md").split("```text\n", 1)[1].split("```", 1)[0]
        self.assertIn("PLAYBOOK    <" + " | ".join(BUNDLE_KINDS) + "> | none   (the kind of work; its steps and its proof "
                      "are in story-run's references/playbook-<kind>.md; none on slice 0 of route G)\n", bundle)
        self.assertLess(bundle.index("USE SKILLS"), bundle.index("PLAYBOOK"))
        for rel, line in (("skills/aidlc-plan/assets/fix-brief.md", "PLAYBOOK    bug-fix   "),
                          ("skills/aidlc-plan/assets/feature-brief.md", "PLAYBOOK    <feature | visual-change>   "),
                          ("skills/aidlc-start/assets/standard-brief.md", "PLAYBOOK    <dependency-bump | refactoring>   ")):
            self.assertIn("\n" + line, read(rel).split("```text\n", 1)[1].split("```", 1)[0], rel)
        steps = flat(section(skill_md("aidlc-plan"), "## Steps"))
        self.assertIn("- fill PLAYBOOK with the slice's kind of work, chosen from the route and the work item: `feature`, "
                      "`bug-fix`, `performance`, `refactoring`, `visual-change` or `dependency-bump` (`none` on slice 0 "
                      "of route G). Its playbook, "
                      "`../story-run/references/playbook-<kind>.md` from this skill's folder, names the practices USE "
                      "SKILLS takes;", steps)
        self.assertIn("and its PLAYBOOK, from the class", flat(read("skills/aidlc-start/references/route-s.md")))

    def test_build_verify_discover_and_design_read_it(self):
        build = flat(section(skill_md("aidlc-build"), "## Steps"))
        self.assertIn("4. Read the playbook the bundle's PLAYBOOK line names, `../story-run/references/playbook-<kind>.md` "
                      "from this skill's folder, and follow its steps inside this skill's; a bundle with no PLAYBOOK line "
                      "has none. Propose numbered steps, tests first,", build)
        verify = flat(section(skill_md("aidlc-verify"), "## Steps"))
        self.assertIn("Add a row for each item of the proof the bundle's playbook names "
                      "(`../story-run/references/playbook-<kind>.md` from this skill's folder).", verify)
        discover = flat(section(skill_md("aidlc-discover"), "## Steps"))
        self.assertIn("3. Trace as `../story-run/references/playbook-investigation.md` (from this skill's folder) says; "
                      "an UNKNOWN that a short run can settle follows `../story-run/references/playbook-spike.md` "
                      "there. Trace outward in five directions", discover)
        design = flat(section(skill_md("aidlc-design"), "## Steps"))
        self.assertIn("An UNKNOWN that a short run can settle follows `../story-run/references/playbook-spike.md` from "
                      "this skill's folder; cite what it showed as FACT.", design)
        self.assertIn("- The playbooks, in this skill's `references/` folder, one per kind of work", flat(section(
            skill_md("story-run"), "## Inputs")))
        self.assertIn("The bundle's PLAYBOOK line names the kind of work: its playbook, in `story-run`'s `references/`, "
                      "says the steps and the proof that kind needs, and which practices USE SKILLS takes (ADR 0028).",
                      flat(skill_md("using-aidlc")))

    def test_the_limits_a_playbook_names_are_in_the_stages_stop_if(self):
        build = flat(section(skill_md("aidlc-build"), "## Stop if"))
        self.assertIn("Never change it: the criterion's owner decides. A baseline a test compares against (a screenshot, "
                      "a recorded output), and the harness that compares or measures it, is an assertion too.", build)
        self.assertIn(MAY_CHANGE, build)
        for name in SPIKE_READERS:
            stops = flat(section(skill_md(name), "## Stop if"))
            self.assertIn("- A spike's code would be committed to the story's branch or moved into the build: a spike is "
                          "thrown away.", stops, name)
            self.assertIn("- A spike or a check needs a package that is not installed: that is a new dependency; ask "
                          "first.", stops, name)

    def test_the_change_list_names_the_playbooks(self):
        table = read("docs/design/2026-11-19-aidlc-6-change-list.md").split("## 11. After Plan 27 (2026-11-22)", 1)[1]
        self.assertRegex(table, r"(?m)^\| Playbooks \| Covered, as instructions \(Plan 27b\) \|")
        self.assertIn("raised again by Plan 27b's W1 and W2: `aidlc-design` 2600, `aidlc-build` 4400 |", table)

    def test_agents_md_states_the_playbook_rule(self):
        agents = flat(read("AGENTS.md"))
        self.assertIn("- A playbook (`skills/story-run/references/playbook-<kind>.md`, ADR 0028) says how one kind of "
                      "work is done and proved. It holds steps only, as a stage's reference does: no Gate, Stop if, "
                      "Common excuses, Red flags or Rules section, no decision, and no \"Load the `<name>` skill\" "
                      "phrase; a stop it names points to the stage's Stop if. `scripts/validate.py` checks that it holds "
                      "no gate section.", agents)
        self.assertIn("licences for parts of the eight earlier practices and for the playbooks `story-run` adapts from "
                      "pstack", agents)
        self.assertIn("`skills/story-run/references/`   eight playbooks, one per kind of work", read("docs/codebase-map.md"))
````

Append to `scripts/test_validate.py`, above its `if __name__ == "__main__":` line:

````python
class PlaybooksTest(unittest.TestCase):
    """Plan 27: a playbook in a skill's references/ holds steps only; like a stage's reference, never a gate."""

    WORKFLOW = PRACTICE_BODY.replace("## Checks\nx\n", "").replace("## Steps", "## Inputs\nx\n## Steps")
    PLAY = ("# Playbook: feature\n\nRead from `aidlc-build` when the bundle names `feature`; the stage's Gate, Stop if "
            "and Rules still apply, and this playbook lifts none of them.\n\n**Steps.**\n1. x\n")

    def check(self, refs):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"story-run": practice("story-run", body=self.WORKFLOW, kind="workflow")})
            folder = root / "skills" / "story-run" / "references"
            folder.mkdir()
            for file_name, text in refs.items():
                (folder / file_name).write_text(text, encoding="utf-8")
            return validate.validate(root)

    def test_a_playbook_with_steps_only_has_no_problems(self):
        self.assertEqual(self.check({"playbook-feature.md": self.PLAY}), [])

    def test_a_playbook_never_holds_a_gate_section(self):
        for heading in ("## Gate", "## Stop if", "## Common excuses", "## Red flags", "## Rules"):
            problems = self.check({"playbook-feature.md": self.PLAY + f"\n{heading}\nx\n"})
            self.assertTrue(any("playbook-feature.md" in p and heading in p for p in problems), (heading, problems))

    def test_a_file_that_is_not_a_playbook_is_not_checked_as_one(self):
        self.assertEqual(self.check({"notes.md": self.PLAY + "\n## Rules\nx\n"}), [])
````

- [ ] **Step 2: Run them to see them fail**

Run: `env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest scripts.test_connect_flow.PlaybookTest scripts.test_validate.PlaybooksTest -v`

Expected: the eight `PlaybookTest` tests FAIL or ERROR (no playbook exists), and
`test_a_playbook_never_holds_a_gate_section` FAILS (the validator has no such check); the other two `PlaybooksTest`
tests pass already, because they pin what must stay true.

- [ ] **Step 3: The validator's check**

In `scripts/validate.py` find:

````text
GATE_SECTIONS = ("## Gate", "## Stop if", "## Common excuses", "## Red flags", "## Rules")
````

Replace with:

````text
GATE_SECTIONS = ("## Gate", "## Stop if", "## Common excuses", "## Red flags", "## Rules")
# A playbook says how one kind of work is done and proved (ADR 0028). Like a stage's reference, it never holds a gate.
PLAYBOOK_FILES = "playbook-*.md"
````

In `scripts/validate.py` find:

````text
def check_skill(path: Path, root: Path) -> list[str]:
````

Replace with:

````text
def check_playbooks(folder: Path, folder_rel: str) -> list[str]:
    """A skill's playbooks (`references/playbook-*.md`) hold no gate section."""
    problems = []
    for ref in sorted((folder / "references").glob(PLAYBOOK_FILES)):
        body = ref.read_text(encoding="utf-8")
        problems += [f"{folder_rel}/references/{ref.name}: holds '{h}'; a playbook never holds a gate, which stays in "
                     f"the stage's SKILL.md" for h in GATE_SECTIONS if re.search(rf"(?m)^{re.escape(h)}[ \t]*$", body)]
    return problems


def check_skill(path: Path, root: Path) -> list[str]:
````

In `scripts/validate.py` find:

````text
    problems += portability(rel, text)
    for sub in SKILL_DIRS:
````

Replace with:

````text
    problems += portability(rel, text)
    problems += check_playbooks(path.parent, folder_rel)
    for sub in SKILL_DIRS:
````

- [ ] **Step 4: The eight playbooks**

Create `skills/story-run/references/playbook-feature.md`:

````markdown
# Playbook: feature

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `feature`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The behaviour the criteria name, proved on the surface users reach. The design and the plan are
decided already; you build what they say.

**Typical route.** F0, F1, F2, C, and route G's criteria after slice 0.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `building-user-interfaces` and `testing-in-browser` for a
screen; `designing-apis` for an API or a module boundary; `migrating-safely` for a data change.

**Steps.**
1. Trace the code the slice changes before you write any: its callers, its data, and the tests that cover it (the
   bundle's LOAD FIRST and PATTERN).
2. Name the data shape first: the structure the slice adds, chosen before the logic. A state machine, not scattered
   booleans; a table, not a chain of branches; a typed model, not the same assumption about a shape in many files.
3. One criterion at a time: its failing test, the least code that turns it green, then the whole suite. A criterion
   whose test is impractical follows ADR 0029, as `aidlc-build` step 6 says.
4. A change to a shared helper reaches every caller: find each one, and check it. A caller outside MAY CHANGE is a
   stop, as `aidlc-build`'s Stop if says.
5. Prove it on the surface users reach: a page in a browser, a request to the endpoint, a command in a terminal. A
   result from another surface, or an inconclusive one, is not a pass: say so.
6. Commit small ordered steps, each green.

**Its proof.** Each criterion's test, named with its ID, failing first, then passing; the bundle's DONE WHEN checks,
each a command and what it showed; for a criterion users see, the check on that surface and what passed.

**Hand back.** What you built, each choice you made and why (the decision log), and what stays unproven.
````

Create `skills/story-run/references/playbook-bug-fix.md`:

````markdown
# Playbook: bug fix

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `bug-fix`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The evidence that the bug is gone. Every line you ship traces to evidence. A change that "might
help" is a guess, and it does not ship: the smallest change the evidence supports ships, nothing more.

**Typical route.** D1, D2, and an incident's follow-up (it enters at `aidlc-start`).

**USE SKILLS** (`aidlc-plan` names them in the bundle): none beyond what `aidlc-build` loads; its step 8 loads
`debugging-failures` for a failing check.

**Steps.**
1. Reproduce it yourself, on the surface where it fails, locally or in a test environment: a person acts on
   production (`aidlc-operate`). Ask a person only with a stated reason that surface cannot be reached from here. When it will not fire, build the trigger: narrow the conditions, or add logging, until it
   does.
2. Write the competing causes down, each with the observation that would rule it out. Seed them from the code and
   from the area's history (`git log -L`, and the pull requests that changed it). Each pass, run the check that rules
   out the most causes, write what it showed, and cross out the causes it ruled out. Never guess.
3. Confirm the mechanism with a run before you write the fix, and name that run.
4. The reproduction comes first: the failing test, or, when a test is impractical, the command or live check that
   shows the failure (ADR 0029). Its commit comes before the fix's in git history.
5. Make the smallest fix the evidence supports. Before another attempt, back the last one out in full, so the diff
   holds only what the evidence supports. The limit on attempts is `aidlc-build`'s, as its Stop if says.
6. Run the reproduction again, on the same surface: it passes now. A unit test shows how a branch behaves, not that
   the bug is gone; an inconclusive result is not a pass.

**Its proof.** The reproduction, failing before the fix and passing after, with both outputs; the competing causes,
each with the run that ruled it in or out; nothing in the diff that the evidence did not call for.

**Hand back.** What was broken, its cause and the run that proved it, the fix, and the failing-then-passing output,
word for word.
````

Create `skills/story-run/references/playbook-performance.md`:

````markdown
# Playbook: performance

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `performance`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** A number, measured and explained. Every change is tied to a measurement; reading the code is never a
measurement.

**Typical route.** F1 or C for a performance criterion; D2 for a regression.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `tuning-performance`.

**Steps.**
1. Measure a baseline on the default branch, before the slice changes anything, on a case that shows the reported
   slowness. When no case shows it, that case is the first thing to build.
2. Show that the measurement tells a slow case from a fast one. Then keep it as it is for the whole slice: a change to
   the measurement during the work is a change to the assertion, as `aidlc-build`'s Stop if says.
3. Explain the number before you trust it: what limits it (the CPU, the network, a lock, the database), how much it
   moves over repeated runs, and that it measured the work you think it did.
4. Try the remedies in this order, cheapest first, and end with the first one that meets the target: remove the work;
   avoid doing it again; do less of it; do it later; do it off the user's path; do it in parallel; make it cheaper.
5. One change, one measurement. Keep a change that moved the number past the run-to-run noise; back out the rest. A
   neutral change is backed out.
6. Correctness first: the suite stays green, and a simpler change that holds the number is the one you keep.

**Its proof.** The baseline on the default branch and the number after, each with how it was measured, its repeated
runs and what limits it; the criterion's threshold, and whether it holds; each change, kept or backed out, with its
number.

**Hand back.** The baseline, the result, the difference, and where the measurements are kept.
````

Create `skills/story-run/references/playbook-refactoring.md`:

````markdown
# Playbook: refactoring

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `refactoring`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The contract. The structure changes; the behaviour does not.

**Typical route.** F1 (a refactoring slice), S (a recipe class), or the last slice of a feature.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `simplifying-code`.

**Steps.**
1. Pin today's behaviour before any structure moves: a characterisation test, a snapshot, or a script that runs the
   old and the new code on the same inputs and compares the outputs. A type check or a lint run is not a pin.
2. Name the structure the code is missing (a state machine, a table, a typed model). The new shape removes branches
   or invalid states; it does not add a layer.
3. Subtract before you add: delete dead code, fold wrappers that have one caller and remove orphan references, in a
   commit of their own, before the reshape.
4. Move in small steps, each keeping the pin green. For an internal API with no users outside the repository, move
   every caller and delete the old one in the same slice; then search for the old name in strings, docs,
   configuration and tests. A caller outside MAY CHANGE is a stop, as `aidlc-build`'s Stop if says. A published API
   is a contract: changing it is a stop too, as `aidlc-build`'s Stop if says for a contract change, and it follows
   `migrating-safely`'s steps in its own plan.
5. Show that the new code is equivalent: the pin green, and, for a large reshape, the comparison script's output.
6. Name what got simpler: fewer layers to trace, or less state to hold. When nothing did, back the change out.
7. A bug found on the way is its own work item, which the person raises at `aidlc-start`; the structural change ships
   first, against the pin.

**Its proof.** The pin, green before and after; the equivalence check's output; what got simpler; no test deleted and
no assertion changed, which `aidlc-build`'s Stop if holds.

**Hand back.** The structure that changed, the pin it held against, the equivalence proof, and what got simpler.
````

Create `skills/story-run/references/playbook-visual-change.md`:

````markdown
# Playbook: visual change

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `visual-change`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** How a screen looks. The baseline is the check, and you never touch it.

**Typical route.** F0 or F1 for a change to how a page looks; S for an upgrade (a framework or a design system) that
must not change it.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `building-user-interfaces`, `testing-in-browser`.

**Steps.**
1. Record the baseline first, before any change: a screenshot of each screen the slice touches, in each of its states
   (empty, loading, error, full), with the repository's visual comparison tool. Without a baseline, there is no claim
   that a page looks the same.
2. A baseline image, and the harness that compares it, are an assertion, as `aidlc-build`'s Stop if says: never
   update one to make a difference pass, and never change the harness. Never restructure a component to hide a
   difference either: that passes a check by lowering the bar, as `aidlc-build`'s Stop if says. A baseline that looks
   wrong is its owner's to decide.
3. Change one component at a time; shared parts first.
4. Compare by image difference, not by eye. A difference fails until someone explains it. For a change meant to show,
   the new screenshot is reviewed with the change, against the design note's UI REFERENCE.
5. With no comparison tool in the repository, proposing one is a new dependency, which a person approves, as
   `aidlc-build`'s Stop if says.

**Its proof.** The baseline screenshots, the screenshots after, and the image difference for each, zero or explained;
for a change meant to show, the reference it matches.

**Hand back.** The screens changed, the difference for each, and where the baseline is kept.
````

Create `skills/story-run/references/playbook-dependency-bump.md`:

````markdown
# Playbook: dependency bump

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `dependency-bump`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** One dependency moved to a new version, within the limits its class or its plan names, and nothing
else changed.

**Typical route.** S (a dependency-bump class in `AGENTS.md`), or F1.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `securing-code` when the bump answers a security advisory.

**Steps.**
1. Read the changelog or the release notes between the two versions, from the project's own source, and list each
   change that can reach this code: a removed or renamed API, a changed default, a new minimum runtime.
2. Change only the manifest and the lock file, with the package manager's own command, which writes the lock file.
3. Read the lock file's diff: every package it adds or moves. A package it adds is a new dependency, unless the class
   allows it, as `aidlc-build`'s Stop if says.
4. Run the full suite and the build, not only the tests near the change, and check each listed change of step 1.
5. A major version passes the class's limits, and a change the notes say needs code outside MAY CHANGE is a file
   outside it: both are a stop, as `aidlc-build`'s Stop if says, and the work takes its normal route.

**Its proof.** The manifest and lock-file diff (the evidence file's Dependency manifests section); the changelog read,
with each change that can reach this code and how it was checked; the full suite green.

**Hand back.** The versions before and after, the changes that can reach this code, and how each was checked.
````

Create `skills/story-run/references/playbook-investigation.md`:

````markdown
# Playbook: investigation

Read from `aidlc-discover` when its question is answered by reading, with no code change; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The answer, with its evidence. An investigation is read-only: it changes no code and merges
nothing.

**Typical route.** None: there is no code. Inside a story, `aidlc-discover`.

**Steps.**
1. Trace the code the question is about: its entry points, callers, callees, data, events and configuration. For
   "why is it like this", read the history too: the commits, pull requests and ADRs that shaped it.
2. Label every finding FACT, INFERENCE or UNKNOWN, with its file and line, or the commit or record it comes from.
3. Write the finding: what it is, how it works, where things live, and the gotchas; for a choice between options, a
   recommendation with a table of what each option gets and costs.
4. When the question's premise is wrong, say so, with the evidence.
5. When the answer turns into a code change, hand it back: that is a new work item, which the person raises at
   `aidlc-start`.

**Its proof.** The written finding, each claim with its evidence; nothing merged.

**Hand back.** The finding, your own judgement with its reasons, and what stays unknown.
````

Create `skills/story-run/references/playbook-spike.md`:

````markdown
# Playbook: spike

Read from `aidlc-design` or `aidlc-discover` when an UNKNOWN is a fact a short run can settle (how a library behaves, a query plan, a timing, how a layout feels); the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** A decision's evidence, not code. A spike is a throwaway instrument; the real build follows the plan,
tests first.

**Typical route.** From `aidlc-discover` or `aidlc-design`, before the decision it informs.

**Steps.**
1. Write the question, and the result that would change the choice. When you cannot, there is nothing to spike.
2. Work outside the repository's source, in a scratch folder, and never commit it to the story's branch, as the
   stage's Stop if says.
3. Use only tools already installed. A package you would have to fetch is a new dependency, which a person approves,
   as the stage's Stop if says.
4. Keep to a time-box, as discovery does (`aidlc-discover` step 1); when it runs out, report what is known.
5. Build the smallest thing that answers the question: a script for a behaviour or a timing; for a new screen with no
   example in the product, two or three variants behind one switch, each with a screenshot.
6. Observe the thing you are deciding: print the output, log the timing, take the screenshot. The observation is the
   evidence, never an opinion.
7. Write the result in the design note or the evidence pack as a FACT, with the observation and the scratch folder's
   path. A spike's code never moves into the build, as the stage's Stop if says. A choice between screen variants is the product owner's, as the
   stage's Gate says for a wireframe.

**Its proof.** The question, the observation, and the UNKNOWN it turned into a FACT; nothing merged.

**Hand back.** The variants or runs, what each showed, your recommendation, and the scratch folder's path; say
plainly that the spike is thrown away.
````

- [ ] **Step 5: The PLAYBOOK line, and the stages that write and read it**

In `skills/aidlc-plan/assets/task-bundle.md` find:

````text
USE SKILLS  <aidlc:skill, … core practices from the `using-aidlc` practice map> | none
````

Replace with:

````text
USE SKILLS  <aidlc:skill, … core practices from the `using-aidlc` practice map> | none
PLAYBOOK    <feature | bug-fix | performance | refactoring | visual-change | dependency-bump> | none   (the kind of work; its steps and its proof are in story-run's references/playbook-<kind>.md; none on slice 0 of route G)
````

In `skills/aidlc-plan/assets/fix-brief.md` find:

````text
USE SKILLS  <plugin:skill, …> | none
````

Replace with:

````text
USE SKILLS  <plugin:skill, …> | none
PLAYBOOK    bug-fix   (its steps and its proof are in story-run's references/playbook-bug-fix.md)
````

In `skills/aidlc-plan/assets/feature-brief.md` find:

````text
USE SKILLS  <plugin:skill, …> | none
````

Replace with:

````text
USE SKILLS  <plugin:skill, …> | none
PLAYBOOK    <feature | visual-change>   (its steps and its proof are in story-run's references/playbook-<kind>.md)
````

In `skills/aidlc-start/assets/standard-brief.md` find:

````text
USE SKILLS  <plugin:skill, …> | none
````

Replace with:

````text
USE SKILLS  <plugin:skill, …> | none
PLAYBOOK    <dependency-bump | refactoring>   (from the class: a dependency bump, or a recipe commit; another class names its own; its steps and its proof are in story-run's references/playbook-<kind>.md)
````

In `skills/aidlc-plan/SKILL.md` find:

````text
   - fill RECIPE only for a deterministic tool
````

Replace with:

````text
   - fill PLAYBOOK with the slice's kind of work, chosen from the route and the work item: `feature`, `bug-fix`,
     `performance`, `refactoring`, `visual-change` or `dependency-bump` (`none` on slice 0 of route G). Its playbook,
     `../story-run/references/playbook-<kind>.md` from this skill's folder, names the practices USE SKILLS takes;
   - fill RECIPE only for a deterministic tool
````

In `skills/aidlc-start/references/route-s.md` find:

````text
for a recipe class, its RECIPE (the approved tool, version and command).
````

Replace with:

````text
for a recipe class, its RECIPE (the approved tool, version and command); and its PLAYBOOK, from the class.
````

In `skills/aidlc-build/SKILL.md` find:

````text
4. Propose numbered steps, tests first,
````

Replace with:

````text
4. Read the playbook the bundle's PLAYBOOK line names, `../story-run/references/playbook-<kind>.md` from this skill's folder, and follow its steps inside this skill's; a bundle with no PLAYBOOK line has none. Propose numbered steps, tests first,
````

In `skills/aidlc-verify/SKILL.md` find:

````text
with the test whose name carries its ID, the local result and the CI result.
````

Replace with:

````text
with the test whose name carries its ID, the local result and the CI result. Add a row for each item of the proof the bundle's playbook names (`../story-run/references/playbook-<kind>.md` from this skill's folder).
````

In `skills/aidlc-discover/SKILL.md` find:

````text
3. Trace outward in five directions
````

Replace with:

````text
3. Trace as `../story-run/references/playbook-investigation.md` (from this skill's folder) says; an UNKNOWN that a short run can settle follows `../story-run/references/playbook-spike.md` there. Trace outward in five directions
````

In `skills/aidlc-design/SKILL.md` find:

````text
and add the strongest argument against your recommendation.
````

Replace with:

````text
and add the strongest argument against your recommendation. An UNKNOWN that a short run can settle follows `../story-run/references/playbook-spike.md` from this skill's folder; cite what it showed as FACT.
````

In `skills/aidlc-build/SKILL.md` find:

````text
- A test can only pass by changing an existing assertion. Never change it: the criterion's owner decides.
````

Replace with:

````text
- A test can only pass by changing an existing assertion. Never change it: the criterion's owner decides. A baseline a test compares against (a screenshot, a recorded output), and the harness that compares or measures it, is an assertion too.
````

In `skills/aidlc-build/SKILL.md` find:

````text
- The plan looks wrong, or the code differs from what the plan assumed.
````

Replace with:

````text
- A change needs a file outside MAY CHANGE (a caller of a shared helper, a use of a renamed name): stop and report.
- The plan looks wrong, or the code differs from what the plan assumed.
````

In `skills/aidlc-design/SKILL.md` find:

````text
- The evidence cannot support a choice: return to discovery, or to the spec owner.
````

Replace with:

````text
- The evidence cannot support a choice: return to discovery, or to the spec owner.
- A spike's code would be committed to the story's branch or moved into the build: a spike is thrown away.
- A spike or a check needs a package that is not installed: that is a new dependency; ask first.
````

In `skills/aidlc-discover/SKILL.md` find:

````text
- Discovery outlasts its time-box: report what is known and what is not.
````

Replace with:

````text
- Discovery outlasts its time-box: report what is known and what is not.
- A spike's code would be committed to the story's branch or moved into the build: a spike is thrown away.
- A spike or a check needs a package that is not installed: that is a new dependency; ask first.
````

In `skills/story-run/SKILL.md` find:

````text
- The team's `AGENTS.md`: whether the AI may push its own feature branch (ADR 0028).
````

Replace with:

````text
- The team's `AGENTS.md`: whether the AI may push its own feature branch (ADR 0028).
- The playbooks, in this skill's `references/` folder, one per kind of work (`playbook-<kind>.md`): the stages you run
  read the one the bundle's PLAYBOOK line names, as their steps say.
````

In `skills/using-aidlc/SKILL.md` find:

````text
writes them into the bundle's USE SKILLS. The tech lead approves them with the plan.
````

Replace with:

````text
writes them into the bundle's USE SKILLS. The tech lead approves them with the plan. The bundle's PLAYBOOK line names the kind of work: its playbook, in `story-run`'s `references/`, says the steps and the proof that kind needs, and which practices USE SKILLS takes (ADR 0028).
````

In `AGENTS.md` find:

````text
  licence for parts of the eight earlier practices);
````

Replace with:

````text
  licences for parts of the eight earlier practices and for the playbooks `story-run` adapts from pstack);
````

In `AGENTS.md` find:

````text
  phrase stays in `SKILL.md`. `scripts/validate.py` checks that a reference holds no gate section and that `SKILL.md`
  names it.
````

Replace with:

````text
  phrase stays in `SKILL.md`. `scripts/validate.py` checks that a reference holds no gate section and that `SKILL.md`
  names it.
- A playbook (`skills/story-run/references/playbook-<kind>.md`, ADR 0028) says how one kind of work is done and
  proved. It holds steps only, as a stage's reference does: no Gate, Stop if, Common excuses, Red flags or Rules
  section, no decision, and no "Load the `<name>` skill" phrase; a stop it names points to the stage's Stop if.
  `scripts/validate.py` checks that it holds no gate section.
````

In `docs/codebase-map.md` find:

````text
`skills/story-run/`   the workflow skill a person starts once per decision: one story's stages, one after another, in one session (ADR 0028)
````

Replace with:

````text
`skills/story-run/`   the workflow skill a person starts once per decision: one story's stages, one after another, in one session (ADR 0028)
`skills/story-run/references/`   eight playbooks, one per kind of work, which build and verify read from the bundle's PLAYBOOK line; a playbook holds no gate
````

In `docs/design/2026-11-19-aidlc-6-change-list.md` find:

````text
`aidlc-plan` 3450, `aidlc-build` 4350; the tests hold these as their limits now |
````

Replace with:

````text
`aidlc-plan` 3450, `aidlc-build` 4350; the tests hold these as their limits now; raised again by Plan 27b's W1 and W2: `aidlc-design` 2600, `aidlc-build` 4400 |
````

Append to `docs/design/2026-11-19-aidlc-6-change-list.md`:

````text
| Playbooks | Covered, as instructions (Plan 27b) | Eight playbooks adapted from pstack (with its notice in `skills/NOTICE`) in `skills/story-run/references/`, from `docs/plans/2026-11-22-plan-27b-playbooks.md`; the bundle's PLAYBOOK line names one; a playbook holds no gate, and every stop it points to is in that stage's Stop if; `aidlc-design` 2600 and `aidlc-build` 4400 words now |
````

- [ ] **Step 6: Raise two word limits again (items W1 and W2 of this plan, the owner's decision)**

In `scripts/test_references.py` find:

````text
    LIMIT = 2550  # the design's target is 2,000; Plan 26 reached 2,324 (item W1); Plan 27 reaches 2,480 (item W5)
````

Replace with:

````text
    LIMIT = 2600  # the design's target is 2,000; Plan 26 reached 2,324; Plan 27 2,480; Plan 27b reaches 2,541 (27b item W1)
````

In `scripts/test_references.py` find:

````text
    LIMIT = 4350  # the design's target is 2,500; Plan 26 reached 3,880 (item W1); Plan 27 reaches 4,271 (item W4)
````

Replace with:

````text
    LIMIT = 4400  # the design's target is 2,500; Plan 26 reached 3,880; Plan 27 4,271; Plan 27b reaches 4,346 (27b item W2)
````

- [ ] **Step 7: Run the tests, the validator and the suite**

Run: `env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest scripts.test_connect_flow.PlaybookTest scripts.test_validate.PlaybooksTest -v && python3 scripts/validate.py && env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest discover -s scripts -p 'test_*.py' && wc -w skills/aidlc-*/SKILL.md skills/story-run/SKILL.md`

Expected: PASS. The validator prints `validate: 1 plugin, 32 skill(s), 0 problem(s)`; the suite runs 709 tests, OK.

- [ ] **Step 8: Commit**

```bash
git add skills/story-run/references/playbook-feature.md skills/story-run/references/playbook-bug-fix.md skills/story-run/references/playbook-performance.md skills/story-run/references/playbook-refactoring.md skills/story-run/references/playbook-visual-change.md skills/story-run/references/playbook-dependency-bump.md skills/story-run/references/playbook-investigation.md skills/story-run/references/playbook-spike.md scripts/validate.py scripts/test_validate.py skills/aidlc-plan/assets/task-bundle.md skills/aidlc-plan/assets/fix-brief.md skills/aidlc-plan/assets/feature-brief.md skills/aidlc-start/assets/standard-brief.md skills/aidlc-plan/SKILL.md skills/aidlc-start/references/route-s.md skills/aidlc-build/SKILL.md skills/aidlc-verify/SKILL.md skills/aidlc-discover/SKILL.md skills/aidlc-design/SKILL.md skills/story-run/SKILL.md skills/using-aidlc/SKILL.md AGENTS.md docs/codebase-map.md docs/design/2026-11-19-aidlc-6-change-list.md scripts/test_references.py scripts/test_connect_flow.py docs/plans/2026-11-22-plan-27b-playbooks.md
git commit -m "feat(story-run): eight playbooks adapted from pstack; the bundle's PLAYBOOK line; a playbook holds no gate (ADR 0028)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --porcelain   # prints nothing
```

### Task 2: The verification record of Plan 27b

Plan 27b keeps its own record, beside Plan 27's (`docs/verification/2026-11-22-plan-27.md`), so each plan's evidence
reads alone.

**Files:**
- Create: `docs/verification/2026-11-22-plan-27b.md`
- Test: `scripts/test_connect_flow.py` (`PlaybooksRecordTest`)

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_connect_flow.py`, above its `if __name__ == "__main__":` line:

````python
class PlaybooksRecordTest(unittest.TestCase):
    """Plan 27b, Task 2: the plan is recorded."""

    RECORD = "docs/verification/2026-11-22-plan-27b.md"

    def test_the_verification_record_exists(self):
        record = read(self.RECORD)
        for heading in ("## What changed", "## How it was checked", "## Evidence", "## Not verified here",
                        "## Rulings", "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("Plan 27b", "playbook", "ADR 0028", "python3 scripts/validate.py", "claude plugin validate .",
                       "aidlc-design", "aidlc-plan", "aidlc-build"):
            self.assertIn(phrase, record, phrase)

    def test_the_record_has_no_open_slot(self):
        self.assertNotIn("{{", read(self.RECORD))
````

- [ ] **Step 2: Run them to see them fail**

Run: `env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest scripts.test_connect_flow.PlaybooksRecordTest -v`

Expected: ERROR in both (no such file).

- [ ] **Step 3: Run everything, then write the record**

Create `docs/verification/2026-11-22-plan-27b.md`:

````markdown
# Verification: the playbooks (Plan 27b)

Date: {{YYYY-MM-DD}} · Claude Code: {{the output of `claude --version`}}
Plan: `docs/plans/2026-11-22-plan-27b-playbooks.md`, executed after Plan 27
(`docs/plans/2026-11-22-plan-27-connect-the-flow.md`) on the same branch · Design:
`docs/design/2026-11-22-connect-the-flow.md`, Part 3 · ADR 0028 (its playbook decision). aidlc 8.0.0, the same release.

## What changed
Commits of this plan on `docs/connect-the-flow`, after Plan 27's record, as `git log --reverse --oneline` prints them:

    {{one line per commit: `sha` subject}}

Eight playbooks, adapted from pstack, say how each kind of work is done and proved, in `skills/story-run/references/`.
The bundle's PLAYBOOK line names one; build and verify read it, discover and design read the investigation and spike
playbooks. A playbook holds no gate section, which the validator checks, and every stop it points to is in that
stage's Stop if, which a test checks. Test changes: exactly the items the owner approved under "Needs the owner's
decision" in the plan, and no other existing assertion.

## How it was checked
- {{per task: what the review found and how it was fixed, or "approved", and by whom}}

## Evidence
The words in `aidlc-design`, `aidlc-plan`, `aidlc-build` and `story-run` (`wc -w`), after Plan 27 and after this plan,
with each limit:

    {{one line per skill}}

`python3 scripts/validate.py`:

    {{output}}

`env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest discover -s scripts -p 'test_*.py'`:

    {{the last three lines of the output}}

`claude plugin validate .`:

    {{output; the known warning about the root CLAUDE.md is expected}}

## Not verified here
- That the AI reads the playbook the bundle names, and follows it: the route cases and Plan 27's five new cases show
  it when they run; none has run here (they cost money).

## Rulings
- {{each ruling made while executing, with what changes if it is wrong}}

## For the owner
{{what the owner still decides}}
````

Fill every `{{…}}` above with the real value before you commit, as Plan 27's Task 10 says; nothing in braces is left:
`grep -c '{{' docs/verification/2026-11-22-plan-27b.md` prints 0.

- [ ] **Step 4: Run the tests, the validator and the suite**

Run: `env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest scripts.test_connect_flow.PlaybooksRecordTest -v && python3 scripts/validate.py && env -u GIT_DIR -u GIT_WORK_TREE python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 32 skill(s), 0 problem(s)`; the suite runs 711 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add docs/verification/2026-11-22-plan-27b.md scripts/test_connect_flow.py
git commit -m "docs(verification): Plan 27b record: the playbooks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git status --porcelain   # prints nothing
```

## Out of scope

- Everything Plan 27 lists as out of scope; the playbooks' wording past what pstack's sources give (Plan 29's
  `writing-plainly`); a playbook for route G's slice 0.

## Self-review notes

- Coverage of the design's Part 3: the eight playbooks, the PLAYBOOK line chosen by `aidlc-plan` and read by build and
  verify, and "a playbook never holds or lifts a gate", checked by the validator: Task 1. The review's M8: Task 1
  (the pointer test and the four Stop if lines). The review's L7 points for playbooks (slice 0, production): Task 1.
- Dry run: Plan 27, then this plan, applied in order to a fresh clone by the same script as Plan 27's, every find
  matched exactly once, the new tests failed first, the validator and the suite ran after each task, and each commit
  step left a clean tree:

  | Task | New tests that failed first | Suite after the task | Validator |
  |---|---|---|---|
  | 1 | 9 of 11 (two `PlaybooksTest` tests pin what must stay true, and pass before) | 709 tests, OK | 32 skill(s), 0 problem(s) |
  | 2 | 2 of 2 | 711 tests, OK | 32 skill(s), 0 problem(s) |

  The words after this plan: `aidlc-design` 2,541; `aidlc-discover` 1,347; `aidlc-plan` 3,417; `aidlc-build` 4,346; `aidlc-verify` 1,554; `story-run` 2,078.
- The re-review's N5: Task 1 appends 27b's raised limits to the change list's "Word limits" row, with a test.
- A mutation check: with design's or discover's new "package that is not installed" line removed, the pointer test
  and the limits test fail.
- No placeholder is left, except the record's `{{…}}` slots, which Task 2 fills from real output.
