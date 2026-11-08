# Greenfield entry Implementation Plan (Plan 13, aidlc 4.1.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A new system can start: route G takes it from an empty home through intent, specify and design, a prepared rules file, a slice-0 skeleton and a confirmed rules file, after which every feature takes route F1 or F2 (fixes W1).

**Architecture:** Markdown skills under `plugins/aidlc/skills/`, one agent under `plugins/aidlc/agents/`, docs. A new repository-content test file, `scripts/test_greenfield.py`, pins each change; its tests are written first and seen failing. One new template, `aidlc-design/assets/new-system.md`. Edits are "replace A with B" pairs; the file's line breaks may differ, so match the words and keep the file's wrapping (120 columns).

**Tech Stack:** Markdown, Python 3.12 standard library (`unittest`), Claude Code for `claude plugin validate .`.

**Spec:** `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (section "Plan 13: greenfield entry"; route G in "The routes"). Builds on Plan 12 (aidlc 4.0.0, `main` at e1a5096).

Branch: `docs/plan-13-greenfield`.

## Global Constraints

- A person creates the home; the agent never creates a repository. One repository known: an empty repository. Several, or undecided: a workspace, onboarded at its root first.
- No new stage: route G uses `aidlc-start`, `aidlc-intent`, `aidlc-specify`, `aidlc-design`, `aidlc-onboard` (new mode, in two steps: prepare before slice 0, confirm after), `aidlc-plan` (slice 0), `aidlc-build`, `aidlc-verify`, `aidlc-review`.
- Slice 0 gets the same gates as any slice: tests first, MAY CHANGE, no assertion change, trusted CI, a code owner who did not write it.
- Approving the design's `new-system.md` is the approval to add the dependencies and run the scaffold commands it pins.
- Never change an existing test assertion: every `scripts/test_*.py` test keeps passing unchanged; new checks are new tests. `scripts/test_loads.py`'s `LOADS` table stays exactly as it is.
- Phrases existing tests pin stay word for word (see Plan 12's list, and `scripts/test_routes.py`, for example "`aidlc-intent` interviews", "write nothing at the workspace root", "provisional key `NEW-<slug>`").
- Every stage skill keeps its house sections and ends its Gate with "You draft; you never approve." Skills name no tool-specific command.
- New text uses British spelling and short sentences. No third-party project, author or URL is written into the repository. Standard library only. Core never names a pack.
- Version: aidlc 4.1.0 (Task 6). Commits use the noreply identity and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A home that holds only a README, a licence, a `.gitignore`, `.github/`, `docs/` or `plans/`. A person expects it to count as empty; Task 1 adds `test_start_counts_config_only_folders_as_empty`.
- A folder that already has `AGENTS.md`, where someone says "new system". A person expects it is never route G; Task 1 adds `test_a_folder_with_agents_md_is_never_route_g`.
- A stack with no generator (a hand-written skeleton). A person expects slice 0 to work without a recipe; Task 2 adds `test_a_stack_without_a_generator_has_no_scaffold`, Task 4 adds `test_slice_0_without_a_scaffold_is_written_by_hand`.
- A new system across several repositories. A person expects one slice-0 part per repository in the coordination plan; Task 2 adds `test_several_repositories_get_one_slice_0_part_each`.
- A command in the prepared `AGENTS.md` that fails at confirm. A person expects onboard to stop, not to drop the mark silently; Task 3 adds `test_confirm_stops_on_a_command_that_fails`.

---

### Task 1: `aidlc-start` accepts a new system (route G)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-start/SKILL.md`, `plugins/aidlc/skills/aidlc-start/assets/story-index.md`, `plugins/aidlc/skills/aidlc-plan/assets/story-index.md`, `plugins/aidlc/skills/using-aidlc/SKILL.md`
- Create: `scripts/test_greenfield.py`

**Interfaces:**
- Produces: `scripts/test_greenfield.py` with `read(rel)`, `skill(name)`, `section(body, heading)` and `class GreenfieldTest`; later tasks append inside it. The route code G and the phrase "New system (route G)".

- [ ] **Step 1: Write the failing tests.** Create `scripts/test_greenfield.py`:

```python
"""Plan 13: a new system enters through route G and reaches an ordinary repository."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "aidlc" / "skills"


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def skill(name: str) -> str:
    return read(f"plugins/aidlc/skills/{name}/SKILL.md")


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    end = body.find(" ## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


class GreenfieldTest(unittest.TestCase):
    def test_start_accepts_a_new_system(self):
        start = skill("aidlc-start")
        self.assertIn("the kind is New system (route G)", start)
        self.assertIn("the agent never creates a repository", start)
        self.assertIn("On route G there is no `AGENTS.md` yet: skip this step.", start)
        self.assertIn("G (a new system)", start)
        self.assertIn("**New system (G):**", start)

    def test_start_counts_config_only_folders_as_empty(self):
        self.assertIn("only a README, a licence, a `.gitignore`, `.github/`, `docs/` or `plans/`", skill("aidlc-start"))

    def test_a_folder_with_agents_md_is_never_route_g(self):
        start = skill("aidlc-start")
        self.assertIn("A folder with `AGENTS.md` is never route G", start)
        self.assertIn("name `aidlc-onboard`, and stop", start)

    def test_the_index_and_the_map_know_route_g(self):
        for rel in ("plugins/aidlc/skills/aidlc-start/assets/story-index.md",
                    "plugins/aidlc/skills/aidlc-plan/assets/story-index.md"):
            text = read(rel)
            self.assertIn("| G>", text, rel)
            self.assertIn("| new system>", text, rel)
        self.assertIn("G · new system", section(skill("using-aidlc"), "## The routes"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_greenfield.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 4 FAIL.

- [ ] **Step 3: Edit `aidlc-start`.**
  - Step 1: replace "Neither: ask the person where the work belongs, and stop." with:

```markdown
   Neither: if the folder holds no code yet (only a README, a licence, a `.gitignore`, `.github/`, `docs/` or `plans/`),
   ask whether the work is a new system; if it is, the kind is New system (route G). If it holds code, it is an
   existing repository that aidlc has not onboarded: name `aidlc-onboard`, and stop. Otherwise ask the person where the
   work belongs, and stop. A folder with `AGENTS.md` is never route G: its system already exists.
```

  - Step 2: replace "2. **Packs.** Read AGENTS.md's `Packs used here`." with "2. **Packs.** On route G there is no `AGENTS.md` yet: skip this step. Otherwise read AGENTS.md's `Packs used here`."
  - Step 3: replace "New feature, Defect, Change request or Incident follow-up" with "New feature, Defect, Change request, Incident follow-up or New system". After the Incident follow-up bullet, add:

```markdown
   - **New system:** there is no code yet. A person creates the home first; the agent never creates a repository. One
     repository known: an empty repository, where the story runs. Several, or undecided: a workspace whose root
     `aidlc-onboard` has set up (that needs no code); the story runs at the root, and `aidlc-design` decides the
     repositories.
```

  - Step 7: replace "D1 or D2 (a defect)." with "D1 or D2 (a defect), G (a new system)."
  - Step 8: after the paragraph that starts "**Full defect route (D2):**", add:

```markdown

   **New system (G):** `aidlc-intent` (when the story needs it), `aidlc-specify`, `aidlc-design` (the new system's
   decisions); then in each new repository `aidlc-onboard` (new mode, prepare), `aidlc-plan` (slice 0), `aidlc-build`,
   `aidlc-verify`, `aidlc-review`, `aidlc-onboard` (new mode, confirm). After that, every feature takes F1 or F2.
```

- [ ] **Step 4: Edit both index templates and the map.** In `aidlc-start/assets/story-index.md` and `aidlc-plan/assets/story-index.md` (they stay identical), replace `<new feature | change request | defect | incident follow-up>` with `<new feature | change request | defect | incident follow-up | new system>`, and `<F1 | F2 | C | D1 | D2>` with `<F1 | F2 | C | D1 | D2 | G>`. In `using-aidlc`'s routes table, after the I row, add:

```markdown
| G · new system | No code yet: a new product, service or application | `aidlc-intent` (when needed), `aidlc-specify`, `aidlc-design` (the new system's decisions); in each new repository `aidlc-onboard` (new mode, prepare), `aidlc-plan` (slice 0), `aidlc-build`, `aidlc-verify`, `aidlc-review`, `aidlc-onboard` (new mode, confirm); then F1 or F2 |
```

- [ ] **Step 5: Run all tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; `validate: 2 plugin(s), 37 skill(s), 0 problem(s)`.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-start plugins/aidlc/skills/aidlc-plan/assets/story-index.md plugins/aidlc/skills/using-aidlc scripts/test_greenfield.py
git commit -m "feat(start): a new system enters through route G; a folder with code or AGENTS.md never does (W1)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `aidlc-design` decides a new system

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-design/SKILL.md`
- Create: `plugins/aidlc/skills/aidlc-design/assets/new-system.md`
- Test: `scripts/test_greenfield.py`

**Interfaces:**
- Produces: the template fields `STACK`, `DEPENDENCIES`, `LAYOUT`, `CONTRACTS`, `NFR CHECKS`, `QUALITY BAR`, `COMMANDS`, `SCAFFOLD`, `CI`, `UI`, `APPROVED`; the file `new-system.md` in the story's folder. Task 3 reads COMMANDS and QUALITY BAR; Task 4 reads SCAFFOLD.

- [ ] **Step 1: Write the failing tests.** Append inside `class GreenfieldTest`:

```python
    def test_design_decides_a_new_system(self):
        design = skill("aidlc-design")
        self.assertIn("**New system** (route G)", section(design, "## When to use"))
        self.assertIn("`assets/new-system.md`", design)
        self.assertIn("approving this design is the approval to add them", design)
        self.assertIn("On route G there is no codebase map, rules file or ADR yet", section(design, "## Inputs"))
        template = read("plugins/aidlc/skills/aidlc-design/assets/new-system.md")
        for field in ("STACK", "DEPENDENCIES", "LAYOUT", "CONTRACTS", "NFR CHECKS", "QUALITY BAR", "COMMANDS",
                      "SCAFFOLD", "CI", "UI", "APPROVED"):
            self.assertIn(field, template, field)

    def test_a_stack_without_a_generator_has_no_scaffold(self):
        self.assertIn("| none: slice 0 writes the skeleton by hand", read("plugins/aidlc/skills/aidlc-design/assets/new-system.md"))

    def test_several_repositories_get_one_slice_0_part_each(self):
        self.assertIn("one slice-0 part each", skill("aidlc-design"))
```

- [ ] **Step 2: Run them and watch them fail.** Run the Task 1 Step 2 command. Expected: 3 FAIL.

- [ ] **Step 3: Create the template.** Write `plugins/aidlc/skills/aidlc-design/assets/new-system.md`:

```text
<!-- aidlc template: new-system -->
NEW SYSTEM · {{KEY}} · {{TITLE}}
STACK        <language and runtime @version; framework @version>   ADR: <adr-draft-n.md>
DEPENDENCIES <name@version: why> | none          (approving this design is the approval to add them)
LAYOUT       <one repository: name | several: name, name — the coordination plan holds one slice-0 part each>
CONTRACTS    <contract v1: provider -> consumers> | none
NFR CHECKS   <requirement: the test, check or monitor that shows it holds>
QUALITY BAR  <dimension: target, set by the team>          (no baseline exists yet)
COMMANDS     tests: <command> · lint: <command> · build: <command> · run: <command>   (onboard writes them to AGENTS.md as "not yet run")
SCAFFOLD     <tool@version — the exact command — the paths it creates> | none: slice 0 writes the skeleton by hand, tests first
CI           <each required check, running one of the COMMANDS>
UI           <the design note's UI REFERENCE line> | none
APPROVED     <tech lead or architect>, <YYYY-MM-DD>, recorded on the work item with this file's version and commit
```

- [ ] **Step 4: Edit `aidlc-design`.**
  - In `## When to use`, append:

```markdown

**New system** (route G): the first design of a system with no code. It also fills `assets/new-system.md`.
```

  - In `## Inputs`, append to the paragraph that starts "The approved spec, the evidence pack": " On route G there is no codebase map, rules file or ADR yet: this design creates the architecture contract."
  - Before the line "Amendment mode:", add:

```markdown
New system (route G), after the draft steps:
1. Fill `assets/new-system.md` and write it to the story's folder as `new-system.md`: the stack and the architecture,
   with an ADR draft for each choice; every dependency named and pinned to a version, because approving this design is
   the approval to add them; the repository layout (one repository, or several, where the coordination plan holds one
   slice-0 part each); the contracts; a check for each non-functional requirement; the initial Quality bar targets,
   which the team sets; the commands for tests, lint, build and run; and the scaffold commands, at pinned versions,
   that slice 0 runs.
2. Load the `building-ci-pipelines` skill and design the CI: the required checks, each running one of the commands.
3. The tech lead or architect approves the design and `new-system.md` together, on the work item.

```

  - In the front matter `templates:` list, add `- new-system`.

- [ ] **Step 5: Run all tests and the validator** (Task 1 Step 5 command). Expected: `OK`; 0 problems. `test_loads.py` passes unchanged (the design already loads `building-ci-pipelines`).

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-design scripts/test_greenfield.py
git commit -m "feat(design): a new system's design pins the stack, dependencies, layout, commands and scaffold in new-system.md

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `aidlc-onboard` new mode, prepare and confirm

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-onboard/SKILL.md`, `plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md`
- Test: `scripts/test_greenfield.py`

**Interfaces:**
- Consumes: Task 2's COMMANDS and QUALITY BAR.
- Produces: the mark `(not yet run)` on a command in `AGENTS.md`, removed at confirm; Task 4's build step 1 reads it.

- [ ] **Step 1: Write the failing tests.** Append inside `class GreenfieldTest`:

```python
    def test_onboard_has_a_new_mode_in_two_steps(self):
        onboard = skill("aidlc-onboard")
        self.assertIn("**New mode** (route G)", section(onboard, "## When to use"))
        self.assertIn("Prepare, before slice 0", onboard)
        self.assertIn("Confirm, after slice 0 merges", onboard)
        self.assertIn("each marked `(not yet run)`", onboard)
        self.assertIn("it is not a new system", section(onboard, "## Stop if"))
        self.assertIn("never run and is not marked `(not yet run)`", section(onboard, "## Red flags"))
        self.assertIn("(not yet run)", read("plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md"))

    def test_confirm_stops_on_a_command_that_fails(self):
        self.assertIn("stop on any that does not", skill("aidlc-onboard"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 FAIL.

- [ ] **Step 3: Edit `aidlc-onboard`.**
  - `## When to use`: append "**New mode** (route G), in two steps: prepare, before slice 0 builds the skeleton; and confirm, after slice 0 merges."
  - `## Inputs`: append "In new mode: the approved design's `new-system.md`, instead of code that builds and merged changes."
  - After step 7 (before "Never overwrite an existing `AGENTS.md` or map"), add:

```markdown
New mode (route G), instead of steps 1 to 6:
- Prepare, before slice 0: copy the starter files that fit (`.claude/settings.json`, `CODEOWNERS`, the CI workflow,
  `scripts/check_packs.py`, `scripts/check_recipe_commit.py`). Write `AGENTS.md` from `assets/agents-md.md` with the
  COMMANDS of the approved `new-system.md`, each marked `(not yet run)`; the Quality bar's Enforced lines from its
  targets; `Packs used here` as `- none`; and Legacy as `- none: a new system`. No map yet: there is no code to map.
- Confirm, after slice 0 merges: run every command; remove `(not yet run)` from each that works, and stop on any that
  does not. Write `docs/codebase-map.md` from the skeleton and the design. Validate with the five probe questions,
  judged against the design documents instead of past changes. Record today's measured values under the Quality bar's
  Measured lines.
```

  - `## Produces`: append "In new mode, prepare produces `AGENTS.md` and the starter files; confirm produces `docs/codebase-map.md`, the probe results and the confirmed commands."
  - `## Stop if`: add "- In new mode, the folder already holds code: it is not a new system. Use the steps for an existing repository."
  - `## Red flags`: replace "- A command in the draft was never run." with "- A command in the draft was never run and is not marked `(not yet run)`."

- [ ] **Step 4: Edit the AGENTS.md template.** In `aidlc-onboard/assets/agents-md.md`, after the `## Commands` heading line, add the line "(On route G, a command written before slice 0 reads `(not yet run)` until `aidlc-onboard` confirms it.)"

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-onboard scripts/test_greenfield.py
git commit -m "feat(onboard): new mode for route G: prepare AGENTS.md and the starter before slice 0, confirm every command after

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Slice 0 in plan and build

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md`, `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/agents/reviewer-compliance.md`
- Test: `scripts/test_greenfield.py`

**Interfaces:**
- Consumes: Task 2's SCAFFOLD and COMMANDS; Task 3's `(not yet run)`.
- Produces: the recipe mark `(scaffold)` and the trailer `Recipe: <tool>@<version> (scaffold)`.

- [ ] **Step 1: Write the failing tests.** Append inside `class GreenfieldTest`:

```python
    def test_plan_writes_slice_0(self):
        plan = skill("aidlc-plan")
        self.assertIn("**Slice 0** (route G)", section(plan, "## When to use"))
        self.assertIn("marked `(scaffold)`", plan)
        self.assertIn("seen red once", plan)
        self.assertIn("(scaffold)", read("plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md"))

    def test_slice_0_without_a_scaffold_is_written_by_hand(self):
        self.assertIn("When SCAFFOLD is none, there is no RECIPE", skill("aidlc-plan"))

    def test_build_runs_slice_0_under_the_usual_gates(self):
        build = skill("aidlc-build")
        self.assertIn("skip this step; the scaffold recipe commit comes first", build)
        self.assertIn("`Recipe: <tool>@<version> (scaffold)`", build)
        self.assertIn("is not checked by the recipe check", build)
        self.assertIn("(scaffold)", read("plugins/aidlc/agents/reviewer-compliance.md"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 3 FAIL.

- [ ] **Step 3: Edit `aidlc-plan` and the bundle template.**
  - `## When to use`: append "**Slice 0** (route G): the first slice of each new repository, the skeleton."
  - Before the line "Brief mode:", add:

```markdown
Slice 0 (route G), the first slice of each new repository:
1. RECIPE holds the SCAFFOLD commands from the approved `new-system.md`, marked `(scaffold)`. When SCAFFOLD is none,
   there is no RECIPE: the DO steps write the skeleton by hand, tests first.
2. DO adds, tests first: one real test of behaviour, a health check that answers (an endpoint or a page), and the CI
   workflow that runs the COMMANDS, each required check seen red once in a draft pull request.
3. MAY CHANGE covers the paths the scaffold creates and `.github/workflows/**`. DONE WHEN: every command in `AGENTS.md`
   runs green locally, and CI runs them on the pull request.

```

  - `task-bundle.md` RECIPE line: replace "| none   (a mechanical recipe commit)" with "| none   (a mechanical recipe commit; `(scaffold)` for slice 0 of a new system)".

- [ ] **Step 4: Edit `aidlc-build` and the compliance reviewer.**
  - Step 1: append "On slice 0 of route G there is no code yet and the commands in `AGENTS.md` read `(not yet run)`: skip this step; the scaffold recipe commit comes first, and step 8 is the first full run."
  - Step 5: append "A `(scaffold)` recipe in slice 0 is not checked by the recipe check, because generators are not reproducible (fresh identifiers, current package versions). Its commit holds only the generators' output, its trailer reads `Recipe: <tool>@<version> (scaffold)`, and the person reviews it as generated code."
  - `reviewer-compliance.md`: after the bullet that starts "- A commit with a `Recipe:` trailer", add "- A commit whose trailer ends `(scaffold)` belongs to slice 0 of route G: it touches only paths the bundle's MAY CHANGE lists, and the recipe check does not apply to it."

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-plan plugins/aidlc/skills/aidlc-build plugins/aidlc/agents/reviewer-compliance.md scripts/test_greenfield.py
git commit -m "feat(plan): slice 0 builds a new system's skeleton under the usual gates; a scaffold recipe is reviewed as generated code

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Docs and ADR 0016

**Files:**
- Modify: `docs/operating-model/lifecycle.md`, `docs/operating-model/workspace-and-repositories.md`, `README.md`
- Create: `docs/adr/0016-greenfield-entry.md`
- Test: `scripts/test_greenfield.py`

- [ ] **Step 1: Write the failing test.** Append inside `class GreenfieldTest`:

```python
    def test_the_docs_describe_route_g(self):
        self.assertNotIn("G, from aidlc 4.1", read("docs/operating-model/lifecycle.md"))
        self.assertIn("| New system |", read("docs/operating-model/workspace-and-repositories.md"))
        self.assertIn("route G", read("README.md"))
        self.assertTrue((ROOT / "docs/adr/0016-greenfield-entry.md").is_file())
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL.

- [ ] **Step 3: Edit the docs.**
  - `lifecycle.md`: replace "and new systems (G, from aidlc 4.1)" with "and new systems (G)".
  - `workspace-and-repositories.md`: in the kind-of-work table, after the Incident follow-up row, add "| New system | No code yet; a person creates the home (one repository, or a workspace onboarded at its root) | intent, specify, design (stack, layout, contracts, UI); then in each new repository onboard (new mode, prepare), slice 0, onboard (new mode, confirm); then F1 or F2 |".
  - `README.md`: after the sentence ending "and says where the next stage runs.", add "A new system starts the same way, in an empty repository or a new workspace (route G)."

- [ ] **Step 4: Write ADR 0016.** Write `docs/adr/0016-greenfield-entry.md` in ADR 0015's layout: Status "Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)"; Design: the spec path. Context: W1 (start stopped without `AGENTS.md`; onboard needed a building repository with merged changes; nothing chose a stack or built a skeleton). Decision: route G; a person creates the home; design fills `new-system.md` and its approval covers the pinned dependencies and scaffold commands; onboard new mode in two steps; slice 0 under the usual gates, its scaffold recipe reviewed as generated code instead of by the recipe check; no new stage. Consequences: aidlc 4.1.0; after confirm the repository is ordinary; the recipe check stays unchanged for every other recipe.

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.**

```bash
git add docs README.md scripts/test_greenfield.py
git commit -m "docs: route G in the operating model and README; ADR 0016 greenfield entry

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Release aidlc 4.1.0 and record the verification

**Files:**
- Modify: `plugins/aidlc/.claude-plugin/plugin.json`
- Create: `docs/verification/2026-11-08-plan-13-greenfield.md`

- [ ] **Step 1:** In `plugin.json`, replace `"version": "4.0.0"` with `"version": "4.1.0"`.
- [ ] **Step 2: Run every check.**

```bash
python3 scripts/validate.py | tail -1
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3
claude plugin validate .
```

Expected: 0 problems; `OK` (192 plus Plan 13's tests); `Validation passed`.

- [ ] **Step 3: Final review.** Use superpowers:requesting-code-review on the branch against the spec's Plan 13 section and the Review Focus above. Fix critical, important and cheap real low findings test-first; dismiss other lows with a reason.
- [ ] **Step 4: Write the verification record** in Plan 12's record layout: the checks, each Review Focus case with its test, the review's findings and their fixes, and any decisions made during the plan.
- [ ] **Step 5: Commit.**

```bash
git add plugins/aidlc/.claude-plugin/plugin.json docs/verification/2026-11-08-plan-13-greenfield.md
git commit -m "chore(release): aidlc 4.1.0 and the Plan 13 verification record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
