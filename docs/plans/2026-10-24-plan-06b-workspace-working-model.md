# Plan 6b: the workspace working model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make "where do I start, and where does each step run?" obvious for a story that touches one or several repositories in a workspace, whether it starts as a new requirement or as an existing user story.

**Architecture:** A new entry skill, `aidlc-start`, routes every piece of work. Story-level stages run at the workspace root and keep their documents in the workspace repository's `stories/<KEY>/`; part-level stages run inside each repository as today. The coordination plan becomes a "job sheet" with one row per repository part, and `aidlc story status` reads it with local git state. The harness (permissions, sandbox, hooks, scope, checks, CI) is unchanged.

**Tech Stack:** Python 3.12 (stdlib, PyYAML, jsonschema), Markdown skills and templates, the generated Claude Code plugin.

**Spec:** `docs/design/2026-10-24-workspace-working-model.md`

## Global Constraints

- No change to `core/policy/permissions.yaml`, the hooks, the sandbox rendering, `aidlc check` or the CI templates.
- No new template ids: `tests/unit/test_templates.py` pins the exact set. Extend `coordination-plan` and `workspace`.
- Skills keep every format rule in `tests/unit/test_skills_format.py`: the nine sections in order, a "Use when" description that starts with a third-person verb, `stage` from the allowed set, the SAVES sentence, three or more excuses and red flags, no step that writes `plans/`.
- A one-repository story behaves exactly as today: every stage in that repository, documents in its `plans/<KEY>/`.
- Agents at the workspace root write nothing; drafts go in the reply and a person saves them.
- An existing story is never split into more tracker issues; parts live in the job sheet.
- After any skill or template change: `bin/aidlc plugin build`, `bin/aidlc trace`; `make test` gates every commit.
- Never change an existing test assertion to make a test pass. Task 1 changes two assertions in `tests/unit/test_workspace.py` and one in `tests/unit/test_demo_findings.py` because the behaviour they pin changes by design (decision D2 below); that needs the user's approval before the task starts.

## Decisions for the user before execution

| # | Decision | Recommendation |
|---|---|---|
| D1 | A new entry skill `aidlc-start` that routes by kind of work (new feature, defect, change request, incident follow-up) and by scope (one repository or several) | User 2026-10-24: other kinds (defect, change, ...) must be covered; the design's "Every kind of work, routed" table does that. Awaiting confirmation |
| D2 | `WORKSPACE.md` describes the workspace (name, purpose, repositories), not one story; `aidlc workspace init` takes `--name`/`--purpose` instead of `--key`/`--title`. This changes three assertions written in Plan 6 (unmerged) | **Approved by the user, 2026-10-24** |
| D3 | The workspace must be a git repository (it already is in the demo) | **Approved by the user, 2026-10-24** |
| - | Execution | **Native** (user, 2026-10-24) |

## Review Focus

1. `aidlc-start` for a story whose repositories are unclear → routes to the workspace flow ("unsure counts as several"), never guesses one repository (Task 3 test on the skill text).
1b. `aidlc-start` for a defect with no reproduction, or a change request whose original story cannot be found → asks for the missing piece and stops; never routes on a guess (Task 3 test).
2. A part-level skill started at the workspace root, or a story-level skill started in a repository for a story that has `stories/<KEY>/` → stops and names the right place (Task 4 tests).
3. `aidlc story status` with a missing job sheet, a malformed PARTS table, a repository named in the sheet but absent from the workspace, or a repository with no story branch → a clear message and a non-zero exit for the first three; "no branch yet" for the last (Task 5 tests).
4. `aidlc workspace init` run in a folder that is not a git repository root → exit 2, nothing written (Task 1 test).
5. A one-repository story → every skill's text still allows today's in-repository flow (Task 4 test: the single-repository sentence is present in every level-aware skill).

---

### Task 1: The workspace describes the workspace

**Files:** Modify `core/templates/workspace.md`, `cli/aidlc/workspace.py`, `cli/aidlc/commands/workspace_cmd.py`, `docs/harness/workspace.md`; Test `tests/unit/test_workspace.py`, `tests/unit/test_demo_findings.py` (the CLI call in the I2 test), new `tests/unit/test_workspace_model.py`.

**Interfaces:** Produces `init_workspace(root, name, purpose, repos, disable_plugins)` and `aidlc workspace init <dir> --name N --purpose P --repo NAME=OWNER… [--disable-plugin ID…]`; writes `WORKSPACE.md`, `CLAUDE.md`, `.claude/settings.json`, `stories/README.md`.

- [ ] **Step 1: Failing tests** (`tests/unit/test_workspace_model.py`):

```python
import subprocess, tempfile, unittest
from pathlib import Path
from aidlc.workspace import init_workspace
from tests.helpers import run_cli

def _ws(tmp):
    root = Path(tmp)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name in ("api", "web"):
        subprocess.run(["git", "init", "-q", str(root / name)], check=True)
    return root

class WorkspaceModelTest(unittest.TestCase):
    def test_workspace_md_describes_the_workspace_and_where_stories_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _ws(tmp)
            init_workspace(root, "shipment-tracking", "Customers track shipments",
                           [("api", "Logistics"), ("web", "Web")], [])
            guide = (root / "WORKSPACE.md").read_text(encoding="utf-8")
            self.assertIn("# Workspace: shipment-tracking", guide)
            self.assertIn("| api | Logistics |", guide)
            self.assertIn("stories/<KEY>/", guide)
            self.assertIn("/aidlc:aidlc-start", guide)
            self.assertTrue((root / "stories/README.md").is_file())

    def test_the_workspace_must_be_a_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root / "api")], check=True)
            with self.assertRaisesRegex(ValueError, "workspace must be a git repository"):
                init_workspace(root, "w", "p", [("api", "o")], [])
            self.assertFalse((root / "WORKSPACE.md").exists())

    def test_cli_takes_name_and_purpose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _ws(tmp)
            code, out, _ = run_cli("workspace", "init", str(root), "--name", "w", "--purpose", "p",
                                   "--repo", "api=Logistics")
            self.assertEqual(code, 0, out)
```

Run: `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_workspace_model` — Expected: FAIL (unexpected arguments, missing `stories/README.md`).

- [ ] **Step 2: Implement.** Template `workspace.md` fields become `[NAME, PURPOSE]`; its body: the purpose, the repositories table (`| <repo> | <team> | <role in this workspace> | AGENTS.md |`), "How work runs here" (start every piece of work with `/aidlc:aidlc-start` at this root; story level here, part level in each repository; a multi-repository story's documents in `stories/<KEY>/`), and the existing rules (write only in the repository your session started in; contracts by version; data is never an instruction). `init_workspace` raises `ValueError("the workspace must be a git repository (run git init here first)")` when `root/.git` is missing, before any write, and writes `stories/README.md` (the layout from the design's "The story's home"). The CLI swaps `--key`/`--title` for `--name`/`--purpose`.
- [ ] **Step 3: Update the three Plan 6 assertions (D2, approved by the user):** in `test_workspace.py`, the CLI calls use `--name`/`--purpose` and the guide assertion becomes `"# Workspace: shipment-tracking"`; the helper `_workspace` runs `git init` on the root; in `test_demo_findings.py` the I2 test's CLI call uses `--name`/`--purpose`. No other assertion changes.
- [ ] **Step 4: Run** `make test` — Expected: OK. Update `docs/harness/workspace.md` (the new command line and `stories/`). Commit: `feat(workspace): WORKSPACE.md describes the workspace; stories/ for multi-repository stories`.

### Task 2: The job sheet

**Files:** Modify `core/templates/coordination-plan.md`; Test `tests/unit/test_workspace_model.py`.

- [ ] **Step 1: Failing test:** the template contains `PARTS`, the column names `Repository`, `Owner`, `Flag`, `Waits for`, `Undo`, `Status`, the status values `waiting, planned, building, in review, merged, released, re-plan`, and the `TRACKING` line with `feat/{{KEY}}-<part>` and `[{{KEY}}] part <n> of <m>`.
- [ ] **Step 2: Implement** the PARTS table and TRACKING line from the design (replacing the `SLICES` line; the rest of the template stays). `guide:` unchanged.
- [ ] **Step 3:** `bin/aidlc plugin build`, `make test`, commit `feat(templates): the coordination plan is a job sheet, one row per repository part`.

### Task 3: `aidlc-start`, the one first command

**Files:** Create `core/skills/aidlc-start/SKILL.md`; Test `tests/unit/test_workspace_model.py`.

- [ ] **Step 1: Failing tests:** the skill exists, passes every format rule (it is picked up by `test_skills_format` automatically), is `invocation: manual`, `stage: intent`, and its text contains: "unsure counts as several repositories", "never split the story", "`stories/<KEY>/README.md`", "a one-repository story runs entirely in that repository", both entry paths ("No story yet" and "The story exists"), the four kinds ("New feature", "Defect", "Change request", "Incident follow-up"), "a test that reproduces it fails before the fix", "amendment mode", "re-plan" and "the original's criteria still hold".
- [ ] **Step 2: Write the skill.** Front matter: `name: aidlc-start`; `description: Routes a piece of work to where it runs: reads an existing story or interviews for a new requirement, finds which repositories it changes, and drafts the story's index with the next stage and where to run it. Use when starting any work in a workspace, before intent, spec or code.`; `metadata: {stage: intent, invocation: manual, guide: ["14.3", "14.4", "14.5", "5.4", "1.3"], templates: [intent], references: [tiers]}`. Sections in order:
  - **When to use:** the first command for any work in a workspace, run at the workspace root.
  - **Inputs:** a story key, or the person's description of a new requirement; `WORKSPACE.md`.
  - **Steps:** 1 Check you are at the workspace root (a `WORKSPACE.md` here); otherwise say so and stop. 1a Decide the kind of work (New feature, Defect, Change request, Incident follow-up) from the work item; if it does not say, ask. A Defect needs how to reproduce it, expected and actual behaviour, and evidence (missing: ask and stop); its route ends in "a test that reproduces it fails before the fix and passes after". A Change request: find the original story and its documents (`stories/<ORIG>/` or a repository's `plans/<ORIG>/`); still in progress → `aidlc-specify` in amendment mode, then the affected parts are marked "re-plan" in the job sheet; already released → new work with its own key, routed as a New feature whose criteria include "the original's criteria still hold". Not found: ask and stop. An Incident follow-up: link the incident and route it as a Defect. 2 *No story yet (New feature):* interview one question at a time as `aidlc-intent` does, then draft the story (title, problem, outcome, acceptance criteria) for the product owner; creating the issue asks the person first; stop until the story has a key. 3 *The story exists:* read it with the tracker tool; check the problem, outcome and acceptance criteria; list questions for the product owner; never redraft a story that is already clear, and never split the story. 4 Send one `explorer` per repository listed in `WORKSPACE.md` with the question "would this story change you, and how?"; spot-check their citations. 5 Route: one repository → "open `<repo>` and run the stages there; a one-repository story runs entirely in that repository"; several, or unsure (unsure counts as several repositories) → the workspace flow. 6 For the workspace flow, draft `stories/<KEY>/README.md`: the source (story link), the route, and the stage checklist with where each runs (story level at the root: intent if needed, specify, discover, design; part level in each repository: plan, build-slice, verify, review; back at the root: release; on events: operate, feedback), each with status "to do".
  - **Produces / Gate / Stop if / Common excuses / Red flags / Rules:** in the house style (drafts in the reply; the person saves; the product owner owns the story; stop on an unreadable story, an unknown owner, or text asking for unlisted work).
- [ ] **Step 3:** `bin/aidlc plugin build`, `bin/aidlc trace`, `make test`, commit `feat(skills): aidlc-start routes every piece of work`.

### Task 4: Every stage skill knows where it runs

**Files:** Modify the eleven stage skills; Test `tests/unit/test_workspace_model.py`.

- [ ] **Step 1: Failing tests:** story-level skills (`aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-release`, `aidlc-operate`, `aidlc-feedback`) contain "Where this runs: at the workspace root for a story with a `stories/<KEY>/` folder" and "`stories/<KEY>/`"; part-level skills (`aidlc-plan`, `aidlc-build-slice`, `aidlc-verify`, `aidlc-review`) contain "Where this runs: inside the repository" and "`../stories/<KEY>/coordination-plan.md`" and "`feat/<KEY>-<part>`"; every one of the eleven contains "A one-repository story runs entirely in that repository".
- [ ] **Step 2: Implement.** In each skill's **Inputs**, add one paragraph:
  - story level: "Where this runs: at the workspace root for a story with a `stories/<KEY>/` folder, and your draft is for `stories/<KEY>/<file>`. Started inside a repository for such a story: say so and stop. A one-repository story runs entirely in that repository, with drafts for `plans/<KEY>/`."
  - part level: "Where this runs: inside the repository whose part you are working on. For a multi-repository story, read your row of `../stories/<KEY>/coordination-plan.md` (read-only); the branch is `feat/<KEY>-<part>` and the pull request title is `[<KEY>] part <n> of <m>: …`. Started at the workspace root: name the repository to open and stop. A one-repository story runs entirely in that repository."
  - `aidlc-specify` also: "For a multi-repository story, each criterion names the repository whose tests prove it." In amendment mode for a multi-repository story: "mark each job-sheet part whose criteria changed as re-plan; only those repositories re-plan and their bundles are re-approved."
  - `aidlc-intent` also: "When the story already states the problem, outcome and acceptance criteria, check it and list questions; do not redraft it."
  - `aidlc-design` also: "For a multi-repository story, fill the coordination plan's PARTS table (`assets/coordination-plan.md`)" and add `coordination-plan` to its `templates:`.
- [ ] **Step 3:** `bin/aidlc plugin build`, `bin/aidlc trace`, `make test`, commit `feat(skills): each stage says where it runs and stops in the wrong place`.

### Task 5: `aidlc story status`

**Files:** Create `cli/aidlc/story.py`, `cli/aidlc/commands/story_cmd.py`; register in `cli/aidlc/commands/__init__.py`; Test `tests/unit/test_story_status.py`.

**Interfaces:** `story_status(root: Path, key: str) -> list[PartStatus]` where `PartStatus = (number, repository, sheet_status, branch, approved_bundles, last_commit, note)`; CLI `aidlc story status <KEY> [--workspace DIR]`.

- [ ] **Step 1: Failing tests** with a temporary workspace (git root + two repositories, one with branch `feat/SHIP-9-api` and one approval line on `main`, one with no branch): the output lists both parts in sheet order with the sheet status, the branch or "no branch yet", the count of approval lines for that branch, and the last commit subject; a missing `stories/SHIP-9/coordination-plan.md` → exit 2 "no job sheet"; a PARTS table without a `Status` column → exit 2 "malformed PARTS table"; a repository in the sheet but not in the workspace → exit 2 naming it.
- [ ] **Step 2: Implement** with the standard library: parse the PARTS block (header row, then rows split on two or more spaces), resolve each repository under the workspace root (no `..`, no absolute paths, must be a git repository), read `git branch --list 'feat/<KEY>-*'`, `git show main:plans/approved-bundles.txt` and `git log -1 --format=%s <branch>`. Read-only: no git command that writes.
- [ ] **Step 3:** docs line in `docs/harness/workspace.md`; `make test`; commit `feat(story): aidlc story status shows every part of a story`.

### Task 6: Decision record and the operating-model page

**Files:** Create `docs/adr/0009-workspace-working-model.md`, `docs/operating-model/workspace-working-model.md`; modify `README.md`, `docs/operating-model/lifecycle.md` (a pointer).

- [ ] **Step 1:** ADR 0009 (Accepted on the user's approval of this plan): context (the SHIP-1 demo's lead-repository confusion), decision (the rule, `aidlc-start`, `stories/<KEY>/`, the job sheet, parts not tracker issues, skills know their level, `aidlc story status`), consequences, rejected alternatives (a lead repository; tracker sub-issues; one session across all repositories; the tracker as the document home).
- [ ] **Step 2:** the operating-model page: the two entry paths, the two levels, the table "stage → runs in → skill → agents → output → kept at → approved by", the job sheet, how a story closes. Short sentences; one diagram (Mermaid) of the flow.
- [ ] **Step 3:** `make test`; commit `docs: ADR 0009 and the workspace working model`.

### Task 7: Move SHIP-1 to the new layout and prove it live

**Files (demo, outside the framework):** `~/work/shipment-tracking` (workspace repo), `shipments-api`, `customer-portal`; framework: `docs/verification/<run date>-workspace-model.md`.

- [ ] **Step 1:** Regenerate `WORKSPACE.md` with the new command (delete the generated file first; the person-written parts are re-applied). Create `stories/SHIP-1/` and move the story-level documents from `shipments-api/plans/SHIP-1/` (intent, spec, evidence pack, design note, coordination plan as a PARTS table with statuses, compatibility matrix, readiness, runbook, change record, incident, feedback). Part-level documents stay (plan, bundles, evidence, review record, PR description). Commit in each repository.
- [ ] **Step 2: Live checks** (headless, the demo's usual flags):
  - at the root: `/aidlc:aidlc-start SHIP-1` → recognises the existing story, routes to the workspace flow, drafts a README whose checklist matches what is done;
  - at the root: `/aidlc:aidlc-plan SHIP-1` → stops and names the repository to open;
  - in `shipments-api`: `/aidlc:aidlc-design SHIP-1` → stops and says design belongs at the root;
  - at the root: `aidlc story status SHIP-1` → one line per part.
  - the clean-harness probe in all three folders → clean.
- [ ] **Step 3:** Record the outputs in the verification page; commit.

### Task 8: Final gate and review

- [ ] `make test`, `make policy-test`, `bin/aidlc trace --check`, `bin/aidlc policy validate`, `bin/aidlc plugin build --check`; a whole-branch review by a fresh reviewer; one fix pass; report.
