# Work routes, the part model and tracking Implementation Plan (Plan 12, aidlc 4.0.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the stages fit together end to end: seven routes chosen once by `aidlc-start`, one pull request per repository part, every stage output in a file, tracking that each stage updates and the workspace root derives, linked parts kept in step through a versioned contract, a defect fast path, and amended assertions as the second exception.

**Architecture:** Markdown skills under `plugins/aidlc/skills/`, agents under `plugins/aidlc/agents/`, starter files under `starter/`. A new repository-content test file, `scripts/test_routes.py`, pins each change; its tests are written first and seen failing. One new script, `starter/workspace/scripts/story_status.py`, with unit tests in `scripts/test_story_status.py`. Edits to existing text are given as "replace A with B" pairs; the file's line breaks may differ from the pair, so match the words and keep the file's wrapping (120 columns).

**Tech Stack:** Markdown, Python 3.12 standard library (`unittest`, `argparse`, `dataclasses`), Claude Code for `claude plugin validate .`.

**Spec:** `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md`

Branch: `docs/plan-12-aidlc-4-routes` (the design is commit b5da07f on it). `<scratch>` means the session's scratchpad directory; nothing written there enters the repository.

## Global Constraints

- Where work runs: several repositories, the workspace root holds the story and tracks every part; one repository, everything happens in that repository.
- A fast path lightens documents, never gates: a failing test first, no changed assertion outside the two exceptions, trusted CI, a code owner who did not write the change.
- Never change an existing test assertion. Every test in `scripts/test_validate.py`, `scripts/test_gates.py`, `scripts/test_loads.py` and the other `scripts/test_*.py` files keeps passing unchanged; every new check is a new test.
- `scripts/test_loads.py`'s `LOADS` table stays exactly as it is: no stage gains or loses a commanded load ("Load the `<name>` skill").
- Phrases the existing tests pin stay word for word, among them: "Always: `writing-tests`, `committing-changes`, `reviewing-code`"; "covers the bundle's USE SKILLS and every skill `aidlc-build` commands"; "the pull-request size `reviewing-code` gives"; "`aidlc-verify` drafts it and `aidlc-review` completes it"; "a test that passed before now fails" (twice in `aidlc-build`); "the approved UI design is the contract"; "High and medium findings block the merge"; "unless the change alters data or a schema"; "never change an existing assertion"; "load it and record it as a deviation"; "Every skill a step below tells you to load is loaded the same way"; "the core practices the slice needs"; "core practices from the `using-aidlc` practice map".
- Every stage skill keeps its house sections and ends its Gate with "You draft; you never approve."
- A skill names no tool-specific command; scripts are named as "the … named in AGENTS.md (or WORKSPACE.md)", with the script path in backticks, as `aidlc-build` does for the recipe check.
- New text uses British spelling and short sentences. The eight earlier practices change only by the targeted lines in Task 12 and Task 14, in each file's existing spelling; `plugins/aidlc/skills/NOTICE` is unchanged.
- No third-party project, author or URL is written into the repository.
- Standard library only; no new dependency. Core never names a pack. `aidlc-modernize` is unchanged.
- Version: aidlc 4.0.0 (Task 16).
- Commits use the noreply identity already set in this repository and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

- A story index or part index edited by hand: status words in another case ("Done"), Windows line endings, extra spaces. `story_status.py` should read them the same; Task 10 adds `test_case_and_crlf_are_tolerated`.
- A part that pins a contract the story no longer lists (the contract was removed in an amendment). A person expects a flag, not silence; Task 10 adds `test_a_pin_on_a_contract_the_story_dropped_is_reported`.
- A part index with no PINS line. A person expects "no PINS line", not a silent pass that would let release go ahead; Task 10 adds `test_a_part_without_pins_is_reported`.
- A story started on aidlc 3 that left a pointer index at the workspace root. `aidlc-start` must hand over to the repository, not write a second index; Task 4 adds `test_start_hands_over_an_old_pointer_index`.
- A fast-path brief whose SOURCE line is empty or says "none". Build must stop, because the expected behaviour has no owner; Task 13 adds `test_build_stops_on_a_brief_with_no_source`.

---

### Task 1: Remove the orphan agents (W7)

**Files:**
- Delete: `plugins/aidlc/agents/implementer.md`, `plugins/aidlc/agents/planner.md`
- Modify: `README.md:60`, `docs/quickstart/copilot.md:19`, `docs/codebase-map.md` (if it lists the agents)
- Create: `scripts/test_routes.py`

**Interfaces:**
- Produces: `scripts/test_routes.py` with `read(rel)`, `skill(name)`, `section(body, heading)` and `class RoutesTest`; every later task appends its tests inside `RoutesTest`.

- [ ] **Step 1: Write the failing tests.** Create `scripts/test_routes.py`:

```python
"""Plan 12: the routes, the part model and the tracking read the same in every file that states them."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "aidlc" / "skills"
AGENTS = ROOT / "plugins" / "aidlc" / "agents"
STAGES = sorted(p.name for p in SKILLS.iterdir() if p.name.startswith("aidlc-"))


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def skill(name: str) -> str:
    return read(f"plugins/aidlc/skills/{name}/SKILL.md")


def section(body: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed body."""
    start = body.index(heading)
    end = body.find(" ## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


class RoutesTest(unittest.TestCase):
    def test_the_orphan_agents_are_gone(self):
        for name in ("implementer", "planner"):
            self.assertFalse((AGENTS / f"{name}.md").exists(), name)

    def test_every_agent_is_named_by_a_core_skill(self):
        texts = [p.read_text(encoding="utf-8") for p in SKILLS.glob("*/SKILL.md")]
        for agent in sorted(p.stem for p in AGENTS.glob("*.md")):
            self.assertTrue(any(f"`{agent}`" in t for t in texts), agent)

    def test_no_document_lists_the_removed_agents(self):
        for rel in ("README.md", "docs/quickstart/copilot.md", "docs/codebase-map.md"):
            text = read(rel)
            self.assertNotIn("`implementer`", text, rel)
            self.assertNotIn("`planner`", text, rel)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 3 FAIL (`test_the_orphan_agents_are_gone`, `test_every_agent_is_named_by_a_core_skill` for `implementer` and `planner`, `test_no_document_lists_the_removed_agents` for `README.md`).

- [ ] **Step 3: Delete the agents and the mentions.**

```bash
git rm plugins/aidlc/agents/implementer.md plugins/aidlc/agents/planner.md
```

In `README.md:60` replace "`explorer`, `planner`, `implementer`, `reviewer-bug`" with "`explorer`, `reviewer-bug`". In `docs/quickstart/copilot.md:19` replace "explorer, planner and reviewers" with "explorer and reviewers". `docs/codebase-map.md` does not list the two agents today; the test keeps it that way.

- [ ] **Step 4: Run the tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; `validate: 2 plugin(s), 37 skill(s), 0 problem(s)`.

- [ ] **Step 5: Commit.**

```bash
git add -A scripts/test_routes.py plugins/aidlc/agents README.md docs/quickstart/copilot.md docs/codebase-map.md
git commit -m "fix(agents): remove the implementer and planner agents, which let Claude delegate around the stage gates (W7)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Incidents and repeated findings need no story (W4)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-operate/SKILL.md`, `plugins/aidlc/skills/aidlc-feedback/SKILL.md`
- Modify: `starter/workspace/.claude/settings.json`, `starter/workspace/WORKSPACE.md`, `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`, `starter/workspace/stories/README.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the folders `incidents/<ID>/` and `feedback/<YYYY-MM-DD>-<topic>/`, used again in Task 3 and Task 15.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_operate_and_feedback_need_no_story(self):
        for name in ("aidlc-operate", "aidlc-feedback"):
            text = skill(name)
            self.assertNotIn("No index: ask the person to run `aidlc-start` first", text, name)
            self.assertIn("No story is needed", text, name)
            self.assertIn("incidents/<ID>/", text, name)
        self.assertIn("feedback/<YYYY-MM-DD>-<topic>/", skill("aidlc-feedback"))

    def test_the_workspace_root_may_write_incidents_and_feedback(self):
        allow = json.loads((ROOT / "starter/workspace/.claude/settings.json").read_text(encoding="utf-8"))[
            "permissions"]["allow"]
        for rule in ("Edit(/stories/**)", "Edit(/incidents/**)", "Edit(/feedback/**)"):
            self.assertIn(rule, allow)
        for rel in ("starter/workspace/WORKSPACE.md", "plugins/aidlc/skills/aidlc-onboard/assets/workspace.md"):
            self.assertIn("write only under `stories/`, `incidents/` and `feedback/`", read(rel), rel)
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 2 FAIL.

- [ ] **Step 3: Edit `aidlc-operate`.**

Replace the whole first paragraph of `## Inputs` (it starts "Where this runs: read the story's index first:") with:

```markdown
Where this runs: wherever the person is, at the workspace root or inside a repository. No story is needed: during an
incident there is none yet. Use the incident's ID from the alert or the incident tool (for example `INC-231`) and write
to `incidents/<ID>/` where this session runs.
```

Replace step 5 with:

```markdown
5. Draft the incident record from `assets/incident.md` to `incidents/<ID>/incident.md`, filling Measures honestly (a
   change that caused the incident counts as failed), and, if the runbook lacked a step, a runbook change from
   `assets/runbook.md` to `incidents/<ID>/runbook-change.md` (load the `adding-observability` skill).
```

Replace step 6 with "6. Draft a new work item that states the problem, not a solution, to `incidents/<ID>/work-item.md`, for the person to raise. When it is raised, it enters at `aidlc-start`."

Replace `## Produces` body with:

```markdown
Files in `incidents/<ID>/`: `signal-log.md` (the signal, its context and the containment options), `diagnosis.md`
(the hypotheses and what tested them), `incident.md`, `runbook-change.md` when the runbook lacked a step, and
`work-item.md`. They go on a branch `incident/<ID>`; people review them in a pull request.
```

In `## Rules`, replace the line "Write your drafts to their files on the story branch (`plans/<KEY>/` in a repository, `stories/<KEY>/` at a workspace root); people review and approve them in the pull request. Never edit `AGENTS.md`, a published contract or another team's files: propose the change for its owner." with "Write your drafts to `incidents/<ID>/` on a branch `incident/<ID>`; people review them in a pull request. Never edit `AGENTS.md`, a published contract or another team's files: propose the change for its owner."

- [ ] **Step 4: Edit `aidlc-feedback`.**

Replace the whole first paragraph of `## Inputs` (it starts "Where this runs: read the story's index first:") with:

```markdown
Where this runs: where the lessons came from. No story is needed. After an incident, write to `incidents/<ID>/`; for
findings that repeat across reviews, write to `feedback/<YYYY-MM-DD>-<topic>/` where this session runs.
```

Replace step 4's sentence "Lessons from repeated review findings have no incident: list them in your reply instead." with "Lessons from repeated review findings have no incident: write them to `feedback/<YYYY-MM-DD>-<topic>/feedback.md`."

Replace `## Produces` body with:

```markdown
`feedback.md` in `incidents/<ID>/` or `feedback/<YYYY-MM-DD>-<topic>/`: the routing table, one drafted change per lesson,
and each change's state (merged, or declined with who and why); for an incident, the updated Prevention lines in
`incident.md`.
```

In `## Rules`, replace the same story-branch line as in Step 3 with "Write your drafts to `incidents/<ID>/` or `feedback/<YYYY-MM-DD>-<topic>/` on a branch; people review them in a pull request. Never edit `AGENTS.md`, a published contract or another team's files: propose the change for its owner."

- [ ] **Step 5: Let the workspace root write those folders.**

In `starter/workspace/.claude/settings.json`, replace `"Edit(/stories/**)",` with:

```json
      "Edit(/stories/**)",
      "Edit(/incidents/**)",
      "Edit(/feedback/**)",
```

In `starter/workspace/WORKSPACE.md` and `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`, replace "At this root, write only under `stories/`" with "At this root, write only under `stories/`, `incidents/` and `feedback/`". In `aidlc-onboard/SKILL.md` step 0, replace "so a session at the root can write only under `stories/`" with "so a session at the root can write only under `stories/`, `incidents/` and `feedback/`".

In `starter/workspace/stories/README.md`, delete the table row "| `incident-NN.md`, `feedback.md` | `aidlc-operate`, `aidlc-feedback` | Only when needed |" and add after the table: "Incidents need no story: they live in `incidents/<ID>/` at the root, and lessons from repeated review findings in `feedback/<YYYY-MM-DD>-<topic>/`."

- [ ] **Step 6: Run the tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; 0 problems.

- [ ] **Step 7: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-operate plugins/aidlc/skills/aidlc-feedback plugins/aidlc/skills/aidlc-onboard starter/workspace scripts/test_routes.py
git commit -m "fix(stages): operate and feedback run without a story, in incidents/<ID>/ and feedback/<date>-<topic>/ (W4)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Every stage writes its output to a file (W9)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-design/SKILL.md`, `plugins/aidlc/skills/aidlc-review/SKILL.md`, `plugins/aidlc/skills/aidlc-release/SKILL.md`, `starter/workspace/stories/README.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the phrase "the story's folder (`plans/<KEY>/` in a repository, `stories/<KEY>/` at a workspace root)"; the files `design-note.md`, `adr-draft-<n>.md`, `contract/`, `review-record.md`, `pr-description.md`, `security-review.md`, `readiness.md`, `change-record.md`, `release-runbook.md`, `compat-matrix.md`, `follow-ups.md`; the release branch `release/<KEY>`.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_no_stage_produces_only_in_the_reply(self):
        for stage in STAGES:
            self.assertNotIn("in your reply", skill(stage).lower(), stage)

    def test_design_review_and_release_name_their_files(self):
        self.assertIn("design-note.md", section(skill("aidlc-design"), "## Produces"))
        self.assertIn("review-record.md", section(skill("aidlc-review"), "## Produces"))
        for name in ("readiness.md", "change-record.md", "release-runbook.md", "follow-ups.md"):
            self.assertIn(name, section(skill("aidlc-release"), "## Produces"), name)
        self.assertIn("release/<KEY>", skill("aidlc-release"))
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 2 FAIL (`aidlc-design`, `aidlc-review` and `aidlc-release` still say "In your reply").

- [ ] **Step 3: Edit `aidlc-design`.** Replace the `## Produces` body with:

```markdown
In the story's folder (`plans/<KEY>/` in a repository, `stories/<KEY>/` at a workspace root): `design-note.md` with
its decision frames; one `adr-draft-<n>.md` per decision, which its owner moves into the governed repository's ADR
folder once it is accepted; `contract/` holding the drafted contract change and its failing provider and consumer
tests, which the contract's owner applies; and, for a story across several repositories, `coordination-plan.md`.
```

- [ ] **Step 4: Edit `aidlc-review`.** Replace the `## Produces` body with:

```markdown
In `plans/<KEY>/`, on the part's branch: `pr-description.md`, `review-record.md` (the dispositions and the reviewers'
questions) and, when required, `security-review.md`. Posting any of them to the pull request asks the person first.
```

- [ ] **Step 5: Edit `aidlc-release`.** Replace the `## Produces` body with:

```markdown
In the story's folder (`plans/<KEY>/` in a repository, `stories/<KEY>/` at a workspace root), on a branch
`release/<KEY>`: `readiness.md` with the stop criteria, `change-record.md`, `release-runbook.md`, `compat-matrix.md`
for a story across several repositories, and `follow-ups.md`. The release approver approves in change management; the
records merge in their own small pull request.
```

- [ ] **Step 6: Update the stories index.** In `starter/workspace/stories/README.md`, replace the row "| `readiness.md`, `release-runbook.md`, `change-record.md`, `compat-matrix.md` | `aidlc-release` | The release |" with "| `readiness.md`, `release-runbook.md`, `change-record.md`, `compat-matrix.md`, `follow-ups.md` | `aidlc-release` | The release, on a branch `release/<KEY>` |", and the row for `design-note.md` with "| `design-note.md`, `adr-draft-<n>.md`, `contract/` | `aidlc-design` | The decisions, ADR drafts and the drafted contract change (accepted ADRs move to the repository each one governs) |".

- [ ] **Step 7: Run the tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; 0 problems.

- [ ] **Step 8: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-design plugins/aidlc/skills/aidlc-review plugins/aidlc/skills/aidlc-release starter/workspace/stories/README.md scripts/test_routes.py
git commit -m "fix(stages): design, review and release write their outputs to files, never only to the reply (W9)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: `aidlc-start` only routes; a one-repository story is handed over (W10, W12)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-start/SKILL.md`
- Create: `plugins/aidlc/skills/aidlc-start/assets/story-index.md`
- Delete: `plugins/aidlc/skills/aidlc-start/assets/intent.md`
- Modify: `starter/workspace/stories/README.md`, `starter/workspace/WORKSPACE.md`, `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the index template `assets/story-index.md` with the lines `SOURCE`, `KIND`, `ROUTE`, `LEVEL`, `CURRENT`, `PINS`, `UNAFFECTED` and the table `| Stage | Runs in | Status |`; status words `to do`, `doing`, `done`, `merged`, `stopped: <reason>`. Task 9 copies the template into `aidlc-plan/assets/`; Task 10 parses `CURRENT`, `PINS`, `UNAFFECTED` and the table.
- Produces: the hand-over sentence "write nothing at the workspace root".

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_start_routes_and_never_drafts_the_story(self):
        text = skill("aidlc-start")
        self.assertNotIn("Draft the story from", text)
        self.assertNotIn("is only a pointer", text)
        self.assertIn("`aidlc-intent` interviews", text)
        self.assertIn("write nothing at the workspace root", text)
        self.assertFalse((SKILLS / "aidlc-start" / "assets" / "intent.md").exists())

    def test_start_hands_over_an_old_pointer_index(self):
        self.assertIn("an index left by aidlc 3 that only points to a repository", skill("aidlc-start"))

    def test_the_story_index_template_has_the_tracked_lines(self):
        template = read("plugins/aidlc/skills/aidlc-start/assets/story-index.md")
        for line in ("SOURCE", "KIND", "ROUTE", "LEVEL", "CURRENT", "PINS", "UNAFFECTED", "| Stage | Runs in | Status |"):
            self.assertIn(line, template, line)
        self.assertIn("`assets/story-index.md`", skill("aidlc-start"))

    def test_the_workspace_keeps_nothing_for_a_one_repository_story(self):
        for rel in ("starter/workspace/stories/README.md", "starter/workspace/WORKSPACE.md",
                    "plugins/aidlc/skills/aidlc-onboard/assets/workspace.md"):
            text = read(rel)
            self.assertNotIn("pointer", text, rel)
            self.assertIn("A story that changes one repository has nothing here", text, rel)
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 4 FAIL.

- [ ] **Step 3: Create the index template.** Write `plugins/aidlc/skills/aidlc-start/assets/story-index.md`:

```markdown
<!-- aidlc template: story-index -->
# {{KEY}} · {{TITLE}}

SOURCE     <work item link>
KIND       <new feature | change request | defect | incident follow-up>
ROUTE      <F1 | F2 | C | D1 | D2>
LEVEL      <repository | workspace root | part <n> of <m> in <repository>>
CURRENT    spec v<n> · contract <name> v<n>        (the story's approved versions; a part leaves this line out)
PINS       spec v<n> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on; a story leaves this line out)
UNAFFECTED <repository> spec v<n>: <why>, <tech lead>, <YYYY-MM-DD>        (one line per part recorded as unaffected; delete when none)

Each stage marks its own row when it ends: done, or stopped: <reason>. The build row reads doing while slices remain.
After the pull request merges, the person marks the merged row done.

| Stage | Runs in | Status |
|---|---|---|
| <stage> | <repository or workspace root> | to do |
```

- [ ] **Step 4: Rewrite `aidlc-start`.**

In the front matter, replace `templates: [intent]` with `templates: [story-index]`. Replace the description with: "Routes a piece of work to where it runs. It decides the kind of work (new feature, defect, change request, incident follow-up), finds which repositories the work changes, chooses the route, and writes the story's index where the work runs. Use when starting any work in a workspace or a repository, before intent, spec or code."

Replace step 4 and step 5 with:

```markdown
4. **No story yet:** do not draft one. Route to `aidlc-intent`: `aidlc-intent` interviews the person and drafts the story
   for the product owner, who creates it in the tracker.
5. **The story exists:** read it for its kind and its scope only. Judging whether it states a problem, an outcome and
   testable criteria is `aidlc-intent`'s job. Never redraft or split it: its parts are tracked in the coordination plan.
```

Replace step 7 with:

```markdown
7. **Route.** Load the `using-aidlc` skill for the routes.
   - One repository, started at a workspace root: write nothing at the workspace root. Tell the person to open
     `<repository>` and run `aidlc-start` there, and stop. An index left by aidlc 3 that only points to a repository
     is handled the same way: name that repository and stop.
   - One repository, started inside it: the story runs entirely here, with its documents in `plans/<KEY>/`.
   - Several repositories, or unsure (unsure counts as several): the story runs at the workspace root, with its
     documents in `stories/<KEY>/`; each repository's part runs inside that repository.
```

Replace step 8's first paragraph (from "**Write the story's index.**" up to and including "and its status (\"to do\").") with:

```markdown
8. **Write the story's index** where this session runs, from `assets/story-index.md`: `plans/<KEY>/README.md` inside a
   repository, `stories/<KEY>/README.md` at a workspace root. Fill SOURCE, KIND, ROUTE and LEVEL, and one row per stage
   of the route with where it runs and the status "to do".
```

Keep the route lists that follow in step 8 for now (Task 5 and Task 13 rewrite them). In `## Produces`, replace "The story's index, `stories/<KEY>/README.md` (started at a workspace root) or `plans/<KEY>/README.md` (started in a lone repository), plus" with "The story's index, `plans/<KEY>/README.md` in a repository or `stories/<KEY>/README.md` at a workspace root, plus". In `## Red flags`, add "- Writing anything at the workspace root for a one-repository story." In `## Common excuses`, replace the row whose excuse is "The story is vague, I will rewrite it properly." with "| \"The story is vague, I will rewrite it properly.\" | The story belongs to the product owner. Route to `aidlc-intent`, which asks the questions. |".

Delete the template that start no longer uses:

```bash
git rm plugins/aidlc/skills/aidlc-start/assets/intent.md
```

- [ ] **Step 5: Update the workspace texts.** In `starter/workspace/stories/README.md`, replace "A story that changes one repository has only `README.md` here, a pointer to that repository, where every stage runs." with "A story that changes one repository has nothing here: it runs and is tracked inside that repository, in its `plans/<KEY>/`." In `starter/workspace/WORKSPACE.md`, replace "a one-repository story has only its index there, a pointer, and runs every stage inside that repository." with "A story that changes one repository has nothing here: it runs and is tracked inside that repository." In `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`, after "A story that spans several repositories keeps its documents in `stories/<KEY>/`." add " A story that changes one repository has nothing here: it runs and is tracked inside that repository."

- [ ] **Step 6: Run the tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; 0 problems.

- [ ] **Step 7: Commit.**

```bash
git add -A plugins/aidlc/skills/aidlc-start plugins/aidlc/skills/aidlc-onboard starter/workspace scripts/test_routes.py
git commit -m "fix(start): start only routes; intent interviews; a one-repository story is handed over and tracked in its repository (W10, W12)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Design always runs; discover records findings (W5, W15)

**Files:**
- Modify: `plugins/aidlc/skills/using-aidlc/SKILL.md`, `plugins/aidlc/skills/aidlc-start/SKILL.md`, `plugins/aidlc/skills/aidlc-discover/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: Task 4's start step 8.
- Produces: the phrase "`aidlc-design` (always; at Tier 1 usually a recorded \"none needed\")".

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_design_always_runs_and_only_discover_is_optional(self):
        for name in ("aidlc-start", "using-aidlc"):
            text = skill(name)
            self.assertNotIn("`aidlc-discover` and `aidlc-design` (only when", text, name)
            self.assertNotIn("`aidlc-discover` or `aidlc-design` when the tier asks", text, name)
        self.assertIn('`aidlc-design` (always; at Tier 1 usually a recorded "none needed")', skill("aidlc-start"))
        self.assertIn("the approved design note (always)", skill("aidlc-plan"))

    def test_discover_records_findings_instead_of_drafting(self):
        text = skill("aidlc-discover")
        self.assertNotIn("draft one for its owner to review", text)
        self.assertNotIn("draft characterisation tests that record today's behaviour", text)
        self.assertIn("as a finding for `aidlc-design`", text)
        self.assertIn("as a finding for `aidlc-plan`", text)
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: 2 FAIL.

- [ ] **Step 3: Edit the map and start.** In `using-aidlc`'s lifecycle table, replace row 3's Next cell "`aidlc-discover` or `aidlc-design` when the tier asks, else `aidlc-plan`" with "`aidlc-discover` when the tier or an unknown asks, else `aidlc-design`", and row 4's Next cell "`aidlc-design` or `aidlc-plan`" with "`aidlc-design`". In `aidlc-start` step 8's route lists, replace each "`aidlc-discover` and `aidlc-design` (only when the tier or a contract asks)" with "`aidlc-discover` (only when the tier or an unknown asks), `aidlc-design` (always; at Tier 1 usually a recorded \"none needed\")".

- [ ] **Step 4: Edit discover and plan.** In `aidlc-discover` step 5, replace "Where a contract is missing, load the `designing-apis` skill and draft one for its owner to review." with "Where a contract is missing, load the `designing-apis` skill and record what the contract must cover as a finding for `aidlc-design`." In step 6, replace "Where none exist, load the `writing-tests` skill and draft characterisation tests that record today's behaviour." with "Where none exist, load the `writing-tests` skill and record which characterisation tests are needed, path by path, as a finding for `aidlc-plan`." In `aidlc-plan`'s Inputs, replace "The approved spec and its version, design decisions, discovery evidence, and the repository's rules and codebase map." with "The approved spec and its version, the approved design note (always), the evidence pack (when discover ran), and the repository's rules and codebase map."

- [ ] **Step 5: Run the tests (including `test_loads.py`, which must still pass unchanged) and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py | tail -1`
Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills/using-aidlc plugins/aidlc/skills/aidlc-start plugins/aidlc/skills/aidlc-discover plugins/aidlc/skills/aidlc-plan scripts/test_routes.py
git commit -m "fix(stages): design always runs, only discover is optional; discover records findings for design and plan (W5, W15)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: One pull request per part (W2)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-review/SKILL.md`, `plugins/aidlc/skills/committing-changes/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-verify/SKILL.md`, `plugins/aidlc/skills/aidlc-verify/assets/evidence-table.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the evidence file `plans/<KEY>/evidence.md` (one per part); the phrase "one part of the story".

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_a_pull_request_is_one_part(self):
        self.assertNotIn("Check that the pull request is one slice", skill("aidlc-review"))
        self.assertIn("Check that the pull request is one part", skill("aidlc-review"))
        commits = skill("committing-changes")
        self.assertNotIn("one slice, one reason", commits)
        self.assertIn("one part of the story", commits)
        self.assertIn("the pull-request size `reviewing-code` gives", commits)
        self.assertIn("split it into two parts", skill("aidlc-plan"))

    def test_verify_writes_one_evidence_file_per_part(self):
        self.assertNotIn("evidence-<slice>.md", skill("aidlc-verify"))
        self.assertIn("plans/<KEY>/evidence.md", skill("aidlc-verify"))
        self.assertIn("{{PART}}", read("plugins/aidlc/skills/aidlc-verify/assets/evidence-table.md"))
```

- [ ] **Step 2: Run them and watch them fail.** Run the `test_routes.py` command from Task 1 Step 2. Expected: 2 FAIL.

- [ ] **Step 3: Edit the texts.**
  - `aidlc-review` step 2: replace "Check that the pull request is one slice." with "Check that the pull request is one part: one repository's share of the story, within the pull-request size `reviewing-code` gives."
  - `committing-changes` step 5: replace "Size the pull request: one slice, one reason, within the pull-request size `reviewing-code` gives" with "Size the pull request: one part of the story (all of that part's slices), within the pull-request size `reviewing-code` gives". In its Checks, the line "In a slice, the pull request description maps each change to its criterion (`aidlc-verify` drafts it and `aidlc-review` completes it)." stays as it is.
  - `aidlc-plan` step 5: replace "Keep each slice within the pull-request size `reviewing-code` gives." with "The part's slices share one branch and one pull request, so keep the whole part within the pull-request size `reviewing-code` gives. When it would exceed it, split it into two parts, each with its own branch and pull request, the second waiting for the first; for a story across several repositories, add the row to the coordination plan."
  - `aidlc-verify` step 2: replace "written to `plans/<KEY>/evidence-<slice>.md` or the pull request description" with "written to `plans/<KEY>/evidence.md` (one per part), naming the commit the trusted run tested".
  - `aidlc-verify/assets/evidence-table.md` line 2: replace `{{KEY}} · {{SLICE}} · evidence` with `{{KEY}} · {{PART}} · evidence`.

- [ ] **Step 4: Run all tests and the validator** (command from Task 1 Step 4). Expected: `OK`; 0 problems.

- [ ] **Step 5: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-review plugins/aidlc/skills/committing-changes plugins/aidlc/skills/aidlc-plan plugins/aidlc/skills/aidlc-verify scripts/test_routes.py
git commit -m "fix(stages): one pull request per repository part; a part over the size budget is split; evidence per part (W2)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Story documents travel on the part's branch (W3)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/agents/reviewer-compliance.md`, `plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md`, `plugins/aidlc/skills/aidlc-verify/assets/evidence-table.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the exemption phrase "`plans/<KEY>/**` is exempt from this check", used again in Task 13's fix brief.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_story_documents_are_exempt_from_the_scope_check(self):
        phrase = "`plans/<KEY>/**` is exempt from this check"
        for rel in ("plugins/aidlc/skills/aidlc-build/SKILL.md", "plugins/aidlc/agents/reviewer-compliance.md",
                    "plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md"):
            self.assertIn(phrase, read(rel), rel)
        self.assertIn("plans/<KEY>/** exempt", read("plugins/aidlc/skills/aidlc-verify/assets/evidence-table.md"))

    def test_the_plan_approval_is_recorded_on_the_work_item(self):
        gate = section(skill("aidlc-plan"), "## Gate")
        self.assertIn("records the approval on the work item with the plan's version and commit", gate)
        self.assertNotIn("in the pull request that adds the plan", gate)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 FAIL.

- [ ] **Step 3: Edit the texts.**
  - `aidlc-build` step 9: replace "and compare them with MAY CHANGE; any file outside it is a stop." with "and compare them with MAY CHANGE. `plans/<KEY>/**` is exempt from this check, because the story's documents travel on the same branch; any other file outside MAY CHANGE is a stop."
  - `reviewer-compliance.md`: replace "- Every changed path is inside the bundle's MAY CHANGE, and nothing in MUST NOT changed." with "- Every changed path is inside the bundle's MAY CHANGE (`plans/<KEY>/**` is exempt from this check), and nothing in MUST NOT changed."
  - `task-bundle.md` DONE WHEN line: replace "the diff touches only MAY CHANGE paths" with "the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)".
  - `evidence-table.md` INTEGRITY line: replace "scope: every changed path inside MAY CHANGE" with "scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)".
  - `aidlc-plan` Gate: replace "The tech lead reviews the plan against its checklist and approves it in the pull request that adds the plan (or on the work item, for a plan kept in the same pull request as the code)." with "The tech lead reviews the plan against its checklist and records the approval on the work item with the plan's version and commit. The plan travels on the part's branch, in the same pull request as the code."

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 5: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-build plugins/aidlc/agents/reviewer-compliance.md plugins/aidlc/skills/aidlc-plan plugins/aidlc/skills/aidlc-verify scripts/test_routes.py
git commit -m "fix(build): story documents travel on the part's branch, exempt from the scope check; approvals on the tracker (W3)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The progress note is a committed file (W8)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/skills/aidlc-build/assets/progress-note.md`, `plugins/aidlc/skills/aidlc-review/SKILL.md`, `plugins/aidlc/agents/reviewer-compliance.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the path `plans/<KEY>/progress-<slice>.md`.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_the_progress_note_is_a_committed_file(self):
        build = skill("aidlc-build")
        self.assertNotIn("Keep the steps as a checklist in your reply", build)
        self.assertIn("plans/<KEY>/progress-<slice>.md", build)
        self.assertIn("plans/<KEY>/progress-{{SLICE}}.md", read("plugins/aidlc/skills/aidlc-build/assets/progress-note.md"))
        self.assertIn("plans/<KEY>/progress-<slice>.md", section(skill("aidlc-review"), "## Inputs"))
        compliance = read("plugins/aidlc/agents/reviewer-compliance.md")
        self.assertIn("plans/<KEY>/progress-<slice>.md", compliance)
        self.assertIn("covers the bundle's USE SKILLS and every skill `aidlc-build` commands", compliance)
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL.

- [ ] **Step 3: Edit the texts.**
  - `aidlc-build` step 4: replace "Keep the steps as a checklist in your reply, in the shape of `assets/progress-note.md`." with "Write the steps as a checklist to `plans/<KEY>/progress-<slice>.md`, from `assets/progress-note.md`, commit it with the slice's first commit, and keep it current as steps finish."
  - `aidlc-build` Produces: replace "and a hand-off in the shape of `assets/progress-note.md`." with "and the progress note `plans/<KEY>/progress-<slice>.md`, committed with the slice."
  - `aidlc-build` Rules: replace "`plans/` documents other than your progress" with "`plans/` documents other than your progress note".
  - `progress-note.md`: after the line "Session state, not memory: it lets a fresh session resume from the record." add a line "File: `plans/<KEY>/progress-{{SLICE}}.md`, committed with the slice; the compliance reviewer reads it."
  - `aidlc-review` Inputs: replace "The pull request, its evidence table, the spec, plan and task bundle it implements," with "The pull request, its evidence table, the spec, plan and task bundles it implements, the progress notes (`plans/<KEY>/progress-<slice>.md`, one per slice),".
  - `reviewer-compliance.md`: replace "- The progress note's `Skills loaded` covers the bundle's USE SKILLS and every skill `aidlc-build` commands" with "- Each progress note (`plans/<KEY>/progress-<slice>.md`) has a `Skills loaded` list that covers the bundle's USE SKILLS and every skill `aidlc-build` commands" (the rest of that bullet stays).

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 5: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-build plugins/aidlc/skills/aidlc-review plugins/aidlc/agents/reviewer-compliance.md scripts/test_routes.py
git commit -m "fix(build): the progress note is a committed file the compliance reviewer reads (W8)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Each stage marks its row in the index (W11, part 1)

**Files:**
- Modify: `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`, `aidlc-release` (each `SKILL.md` under `plugins/aidlc/skills/`)
- Create: `plugins/aidlc/skills/aidlc-plan/assets/story-index.md` (a copy of Task 4's template)
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: Task 4's `assets/story-index.md`.
- Produces: the sentence "Mark this stage's row in the index"; the part index `plans/<KEY>/README.md` with LEVEL `part <n> of <m> in <repository>`, PINS, and the rows `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`, `merged` (Task 10 reads these names).

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    TRACKED = ("aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan", "aidlc-build",
               "aidlc-verify", "aidlc-review", "aidlc-release")

    def test_each_tracked_stage_marks_its_row(self):
        for stage in self.TRACKED:
            self.assertIn("Mark this stage's row in the index", section(skill(stage), "## Steps"), stage)

    def test_plan_writes_the_part_index_with_the_rows_the_status_script_reads(self):
        text = skill("aidlc-plan")
        self.assertIn("`assets/story-index.md`", text)
        for row in ("`aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review` and `merged`", "part <n> of <m>"):
            self.assertIn(row, text, row)
        self.assertEqual((SKILLS / "aidlc-plan/assets/story-index.md").read_text(encoding="utf-8"),
                         (SKILLS / "aidlc-start/assets/story-index.md").read_text(encoding="utf-8"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 FAIL.

- [ ] **Step 3: Copy the template.**

```bash
cp plugins/aidlc/skills/aidlc-start/assets/story-index.md plugins/aidlc/skills/aidlc-plan/assets/story-index.md
```

- [ ] **Step 4: Add the closing step.** In each of `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-verify`, `aidlc-review` and `aidlc-release`, append one numbered step at the end of `## Steps` (use the next number; in `aidlc-specify` and `aidlc-design`, which have a mode list, append it after the last list as an unnumbered final paragraph starting "Last:"):

```markdown
N. Mark this stage's row in the index (`plans/<KEY>/README.md` in a repository, `stories/<KEY>/README.md` at a
   workspace root) as done, or as stopped with the reason.
```

In `aidlc-build`, append to step 10: "Mark this stage's row in the index (`plans/<KEY>/README.md`): doing while slices remain, done after the last slice, or stopped with the reason."

In `aidlc-plan`, replace step 8 with:

```markdown
8. Write the plan and every bundle to `plans/<KEY>/`, never over an existing file. For a re-plan, raise the version and
   say what changed. For a part of a story across several repositories, also write the part index
   `plans/<KEY>/README.md` from `assets/story-index.md`: LEVEL `part <n> of <m> in <repository>`, the PINS line of the
   latest bundle, and the rows `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review` and `merged`.
9. Mark this stage's row in the index (`plans/<KEY>/README.md`) as done, or as stopped with the reason.
```

In `aidlc-plan`'s front matter `templates:` list, add `- story-index`.

- [ ] **Step 5: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/skills scripts/test_routes.py
git commit -m "feat(stages): each stage marks its row in the index; plan writes the part index (W11)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: `story_status.py` derives every part's status at the root (W11, part 2)

**Files:**
- Create: `starter/workspace/scripts/story_status.py`
- Create: `scripts/test_story_status.py`
- Modify: `starter/workspace/WORKSPACE.md`, `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`, `plugins/aidlc/skills/aidlc-onboard/SKILL.md` (step 0), `plugins/aidlc/skills/aidlc-design/assets/coordination-plan.md`
- Test: `scripts/test_story_status.py`, `scripts/test_routes.py`

**Interfaces:**
- Consumes: the index format from Task 4 and Task 9.
- Produces: `story_status.STAGES: tuple[str, ...]`; `parse_versions(text: str) -> dict[str, int]`; `parts(plan: str) -> list[tuple[int, str]]`; `story_status(workspace: Path, key: str) -> list[PartStatus]`; `release_ready(rows: list[PartStatus]) -> bool`; `render(key: str, rows: list[PartStatus]) -> str`; `main(argv: list[str]) -> int`. CLI `python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release]`; `--write` saves `stories/<KEY>/status.md`; `--check-release` exits 1 unless release-ready; exit 2 when the story's index or coordination plan is missing. Need strings: `re-plan: <name> v<pinned> < v<current>`, `pins <name>, which the story no longer lists`, `no PINS line`, `<repository> is not in the workspace`, `<stage> stopped: <reason>`.

- [ ] **Step 1: Write the failing tests.** Create `scripts/test_story_status.py`:

```python
"""Tests for starter/workspace/scripts/story_status.py: each builds a small workspace in a temporary folder."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "workspace" / "scripts"))
import story_status  # noqa: E402

PLAN = """Coordination plan · SHIP-1 · Track shipments · v1
OUTCOME    Customers see where a shipment is. Tier 2
PARTS      #  Repository     Owner    Change                 Flag          Waits for     Undo       Status
           1  <repository>   <team>   <what changes>         <flag, off>   <tag or ->    flag off   waiting
           1  shipments-api  core     add tracking endpoint  track-v1      -             flag off   see status.md
           2  web-portal     web      show tracking          track-v1      part 1        flag off   see status.md
TRACKING   Branch feat/SHIP-1-<part> in each repository
"""
PINS = "spec v1 · plan v1 · contract tracking-api v1"


def story(root: Path, current: str = "spec v1 · contract tracking-api v1", extra: str = "") -> None:
    d = root / "stories" / "SHIP-1"
    d.mkdir(parents=True)
    (d / "README.md").write_text(f"# SHIP-1 · Track shipments\n\nCURRENT    {current}\n{extra}\n", encoding="utf-8")
    (d / "coordination-plan.md").write_text(PLAN, encoding="utf-8")


def part(root: Path, repo: str, pins: str | None = PINS, done=(), stopped=None, word: str = "done",
         newline: str = "\n") -> None:
    d = root / repo / "plans" / "SHIP-1"
    d.mkdir(parents=True)
    rows = []
    for stage in story_status.STAGES:
        status = word if stage in done else "to do"
        if stopped and stage == stopped[0]:
            status = f"stopped: {stopped[1]}"
        rows.append(f"| {stage} | {repo} | {status} |")
    lines = ["# SHIP-1 · part", ""] + ([f"PINS       {pins}"] if pins is not None else []) + [
        "", "| Stage | Runs in | Status |", "|---|---|---|", *rows, ""]
    (d / "README.md").write_bytes(newline.join(lines).encode("utf-8"))


ALL = story_status.STAGES


class StoryStatusTest(unittest.TestCase):
    def run_status(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            return {r.repository: r for r in story_status.story_status(root, "SHIP-1")}

    def test_template_rows_are_ignored(self):
        self.assertEqual(story_status.parts(PLAN), [(1, "shipments-api"), (2, "web-portal")])

    def test_versions_are_parsed(self):
        self.assertEqual(story_status.parse_versions(PINS), {"spec": 1, "plan": 1, "contract tracking-api": 1})
        self.assertEqual(story_status.parse_versions("none"), {})

    def test_a_part_with_no_index_is_waiting(self):
        rows = self.run_status(lambda r: (story(r), (r / "shipments-api").mkdir(), (r / "web-portal").mkdir()))
        self.assertEqual(rows["shipments-api"].reached, "waiting")

    def test_the_stage_reached_is_the_last_done_row(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL[:3]), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "aidlc-verify")
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_stale_spec_pin_needs_a_re_plan_even_when_merged(self):
        rows = self.run_status(lambda r: (story(r, current="spec v2 · contract tracking-api v1"),
                                          part(r, "shipments-api", done=ALL), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "merged")
        self.assertIn("re-plan: spec v1 < v2", rows["shipments-api"].needs)

    def test_an_unaffected_record_clears_the_spec_re_plan(self):
        extra = "UNAFFECTED shipments-api spec v2: only the portal shows the new label, Ana (tech lead), 2026-11-09"
        rows = self.run_status(lambda r: (story(r, current="spec v2 · contract tracking-api v1", extra=extra),
                                          part(r, "shipments-api", done=ALL), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_stale_contract_pin_needs_a_re_plan(self):
        rows = self.run_status(lambda r: (story(r, current="spec v1 · contract tracking-api v2"),
                                          part(r, "shipments-api"), part(r, "web-portal")))
        self.assertIn("re-plan: contract tracking-api v1 < v2", rows["web-portal"].needs)

    def test_a_missing_repository_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api")))
        self.assertEqual(rows["web-portal"].reached, "missing")
        self.assertIn("web-portal is not in the workspace", rows["web-portal"].needs)

    def test_a_stopped_stage_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL[:1],
                                                         stopped=("aidlc-build", "assertion would change")),
                                          part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "aidlc-plan")
        self.assertIn("aidlc-build stopped: assertion would change", rows["shipments-api"].needs)

    def test_release_is_ready_only_when_every_part_is_merged_at_current_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal", done=ALL[:4])
            self.assertFalse(story_status.release_ready(story_status.story_status(root, "SHIP-1")))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal", done=ALL)
            self.assertTrue(story_status.release_ready(story_status.story_status(root, "SHIP-1")))

    def test_write_saves_status_md_and_check_release_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal")
            with redirect_stdout(io.StringIO()):
                code = story_status.main(["SHIP-1", "--root", tmp, "--write", "--check-release"])
            self.assertEqual(code, 1)
            status = (root / "stories" / "SHIP-1" / "status.md").read_text(encoding="utf-8")
            self.assertIn("| 1 | shipments-api | merged |", status)
            self.assertIn("Release: not ready", status)

    def test_a_missing_story_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(story_status.main(["SHIP-9", "--root", tmp]), 2)

    def test_case_and_crlf_are_tolerated(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL, word="Done", newline="\r\n"),
                                          part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "merged")

    def test_a_pin_on_a_contract_the_story_dropped_is_reported(self):
        rows = self.run_status(lambda r: (story(r, current="spec v1"), part(r, "shipments-api"), part(r, "web-portal")))
        self.assertIn("pins contract tracking-api, which the story no longer lists", rows["shipments-api"].needs)

    def test_a_part_without_pins_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", pins=None, done=ALL[:2]),
                                          part(r, "web-portal")))
        self.assertIn("no PINS line", rows["shipments-api"].needs)


if __name__ == "__main__":
    unittest.main()
```

Append inside `class RoutesTest` in `scripts/test_routes.py`:

```python
    def test_the_workspace_names_the_status_command(self):
        for rel in ("starter/workspace/WORKSPACE.md", "plugins/aidlc/skills/aidlc-onboard/assets/workspace.md"):
            self.assertIn("`python3 scripts/story_status.py <KEY> --write`", read(rel), rel)
        self.assertIn("story_status.py", skill("aidlc-onboard"))
        self.assertIn("Status is derived", read("plugins/aidlc/skills/aidlc-design/assets/coordination-plan.md"))
```

- [ ] **Step 2: Run them and watch them fail.**

Run: `python3 -m unittest discover -s scripts -p 'test_story_status.py' 2>&1 | tail -3; python3 -m unittest discover -s scripts -p 'test_routes.py' 2>&1 | grep -E "^(FAIL|ERROR|Ran|OK|FAILED)"`
Expected: `ModuleNotFoundError: No module named 'story_status'`; 1 FAIL in `test_routes.py`.

- [ ] **Step 3: Write the script.** Create `starter/workspace/scripts/story_status.py`:

```python
#!/usr/bin/env python3
"""Shows where every part of a story stands, read from each repository's own index, so the workspace root tracks
the story without any session writing into another repository.

    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release]

Reads stories/<KEY>/README.md (the story index: its CURRENT versions and UNAFFECTED records) and
stories/<KEY>/coordination-plan.md (its PARTS rows), then <repository>/plans/<KEY>/README.md for each part (the part
index: its PINS line and its stage rows). Prints a table. --write also saves it to stories/<KEY>/status.md.
--check-release exits 1 unless every part is merged at the current versions. Exits 2 when the story's index or
coordination plan is missing. Standard library only."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

STAGES = ("aidlc-plan", "aidlc-build", "aidlc-verify", "aidlc-review", "merged")
HEADER = re.compile(r"^[A-Z][A-Z-]+\b")
PART_ROW = re.compile(r"^\s+(\d+)\s+([A-Za-z0-9._-]+)\s")
VERSION = re.compile(r"^(.*?)\s+v(\d+)$")
STAGE_ROW = re.compile(r"^\|\s*([a-z-]+)\s*\|[^|]*\|\s*([^|]+?)\s*\|$")
UNAFFECTED = re.compile(r"^UNAFFECTED\s+([A-Za-z0-9._-]+)\s+spec\s+v(\d+)\s*:", re.I)


@dataclass
class PartStatus:
    number: int
    repository: str
    reached: str
    pins: str
    needs: list[str] = field(default_factory=list)

    @property
    def merged(self) -> bool:
        return self.reached == "merged"


def parse_versions(text: str) -> dict[str, int]:
    """'spec v2 · contract orders-api v1' -> {'spec': 2, 'contract orders-api': 1}; 'none' or '' -> {}."""
    versions = {}
    for item in re.split(r"[·,]", text):
        m = VERSION.match(" ".join(item.split()).lower())
        if m:
            versions[m.group(1)] = int(m.group(2))
    return versions


def field_line(text: str, name: str) -> str:
    """The value of a 'NAME   value   (comment)' line, without the comment; '' when there is none."""
    for line in text.splitlines():
        if re.match(rf"^{name}\s", line, re.I):
            return line[len(name):].split("(")[0].strip()
    return ""


def stage_rows(text: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        m = STAGE_ROW.match(line.strip())
        if m and m.group(1) in STAGES:
            rows[m.group(1)] = " ".join(m.group(2).split()).lower()
    return rows


def parts(plan: str) -> list[tuple[int, str]]:
    """The (number, repository) of each real PARTS row; template rows with <placeholders> are skipped."""
    found, inside = [], False
    for line in plan.splitlines():
        if HEADER.match(line):
            inside = line.startswith("PARTS")
            continue
        m = PART_ROW.match(line) if inside else None
        if m:
            found.append((int(m.group(1)), m.group(2)))
    return found


def part_status(workspace: Path, key: str, number: int, repository: str, current: dict[str, int],
                unaffected: dict[str, int]) -> PartStatus:
    folder = workspace / repository
    if not folder.is_dir():
        return PartStatus(number, repository, "missing", "-", [f"{repository} is not in the workspace"])
    index = folder / "plans" / key / "README.md"
    if not index.is_file():
        return PartStatus(number, repository, "waiting", "-", [])
    text = index.read_text(encoding="utf-8")
    rows, reached, needs = stage_rows(text), "waiting", []
    for stage in STAGES:
        status = rows.get(stage, "to do")
        if status.startswith("stopped"):
            needs.append(f"{stage} {status}")
            break
        if status == "done":
            reached = stage
    pins_text = field_line(text, "PINS")
    pins = parse_versions(pins_text)
    if not pins:
        needs.append("no PINS line")
    for name, version in current.items():
        pinned = pins.get(name)
        if pinned is None or pinned >= version:
            continue
        if name == "spec" and unaffected.get(repository, 0) >= version:
            continue
        needs.append(f"re-plan: {name} v{pinned} < v{version}")
    for name in pins:
        if name not in ("spec", "plan") and name not in current:
            needs.append(f"pins {name}, which the story no longer lists")
    return PartStatus(number, repository, reached, pins_text or "-", needs)


def story_status(workspace: Path, key: str) -> list[PartStatus]:
    story = workspace / "stories" / key
    index = (story / "README.md").read_text(encoding="utf-8")
    current = parse_versions(field_line(index, "CURRENT"))
    unaffected: dict[str, int] = {}
    for line in index.splitlines():
        m = UNAFFECTED.match(line.strip())
        if m:
            unaffected[m.group(1)] = max(unaffected.get(m.group(1), 0), int(m.group(2)))
    plan = (story / "coordination-plan.md").read_text(encoding="utf-8")
    return [part_status(workspace, key, n, repo, current, unaffected) for n, repo in parts(plan)]


def release_ready(rows: list[PartStatus]) -> bool:
    return bool(rows) and all(r.merged and not r.needs for r in rows)


def render(key: str, rows: list[PartStatus]) -> str:
    lines = [f"# {key} · status (generated by scripts/story_status.py; do not edit)", "",
             "| Part | Repository | Reached | Pins | Needs |", "|---|---|---|---|---|"]
    lines += [f"| {r.number} | {r.repository} | {r.reached} | {r.pins} | {'; '.join(r.needs) or '-'} |" for r in rows]
    lines += ["", f"Release: {'ready' if release_ready(rows) else 'not ready'}", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Where every part of a story stands.")
    parser.add_argument("key")
    parser.add_argument("--root", default=".")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check-release", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.root)
    story = workspace / "stories" / args.key
    for name in ("README.md", "coordination-plan.md"):
        if not (story / name).is_file():
            print(f"story_status: {(story / name).as_posix()} not found", file=sys.stderr)
            return 2
    rows = story_status(workspace, args.key)
    text = render(args.key, rows)
    print(text)
    if args.write:
        (story / "status.md").write_text(text, encoding="utf-8")
    return 1 if args.check_release and not release_ready(rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the script's tests.**

Run: `python3 -m unittest discover -s scripts -p 'test_story_status.py' -v 2>&1 | tail -4`
Expected: `Ran 15 tests` … `OK`.

- [ ] **Step 5: Name the command where people and stages find it.**
  - `starter/workspace/WORKSPACE.md` and `plugins/aidlc/skills/aidlc-onboard/assets/workspace.md`: add after `## Tools` a section:

```markdown
## Commands
- Story status, after any part moves: `python3 scripts/story_status.py <KEY> --write` (writes `stories/<KEY>/status.md`).
- Before release: `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the
  current versions).
```

  - `aidlc-onboard` step 0: after "create `stories/README.md`," add "copy `story_status.py` from aidlc's `starter/workspace/scripts/` into the workspace's `scripts/` folder,".
  - `coordination-plan.md`: replace "(Status: waiting, planned, building, in review, merged, released, re-plan. Update it as each part moves.)" with "(Status is derived: run the story status command named in WORKSPACE.md; it reads each part's index and writes `status.md` beside this plan.)".

- [ ] **Step 6: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 7: Commit.**

```bash
git add starter/workspace scripts/test_story_status.py scripts/test_routes.py plugins/aidlc/skills/aidlc-onboard plugins/aidlc/skills/aidlc-design/assets/coordination-plan.md
git commit -m "feat(workspace): story_status.py derives every part's status at the root from each repository's index (W11)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Linked parts stay in step through a versioned contract (W13)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-design/SKILL.md`, `plugins/aidlc/skills/aidlc-review/SKILL.md`, `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/skills/aidlc-release/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md`, `plugins/aidlc/skills/aidlc-design/assets/coordination-plan.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: Task 10's command and the `CURRENT`/`PINS` lines.
- Produces: design's "**Amendment mode.**"; the bundle line `PINS`.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_design_amends_a_contract_at_the_story_level(self):
        text = skill("aidlc-design")
        self.assertIn("**Amendment mode.**", section(text, "## When to use"))
        self.assertIn("consumers approve the new version", text)
        self.assertIn("CURRENT line", text)
        self.assertIn("run in the provider's CI", text)

    def test_review_sends_a_contract_change_to_design(self):
        text = skill("aidlc-review")
        self.assertNotIn("the work returns to planning", text)
        self.assertIn("goes to `aidlc-design` in amendment mode", text)
        self.assertIn("needs a contract change", skill("aidlc-build"))

    def test_bundles_pin_their_versions(self):
        self.assertIn("PINS", read("plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md"))
        self.assertIn("pin the spec, plan and contract versions", skill("aidlc-plan"))
        self.assertIn("<contract> v<n>", read("plugins/aidlc/skills/aidlc-design/assets/coordination-plan.md"))

    def test_release_checks_every_part_and_runs_the_integration_check(self):
        text = skill("aidlc-release")
        self.assertIn("When the story spans several repositories", text)
        self.assertIn("--check-release", text)
        self.assertIn("integration check", text)
        self.assertIn("provider first", text)
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 4 FAIL.

- [ ] **Step 3: Edit `aidlc-design`.** In `## When to use`, append:

```markdown

**Amendment mode.** A review, a build or a consumer finds that an approved contract must change. Only this stage changes
a contract, and only with its consumers' approval.
```

Append to step 5: "The consumer tests run in the provider's CI, so a provider change that would break a consumer fails the provider's own pull request."

After the last draft-mode step (step 8) and before the "Last:" paragraph from Task 9, add:

```markdown
Amendment mode:
1. Quote the contract and the finding, and list the parts that consume it from the coordination plan.
2. Draft the contract's next version and the updated consumer tests. Say whether the change is additive (minor) or
   breaking (major, done by expand and contract).
3. The consumers approve the new version on the tracker. Record it in the ADR and in the story index's CURRENT line.
4. Run the story status command named in WORKSPACE.md: every part pinned to the old version shows "re-plan". Those
   parts return to `aidlc-plan`; their bundles are approved again.
```

- [ ] **Step 4: Edit review, build, plan and the templates.**
  - `aidlc-review` Stop if: replace "- A contract change or a new consumer appears: the tier rises and the work returns to planning." with "- A finding can only be fixed by changing a contract, or a new consumer appears: stop; it is not fixed in this repository. It goes to `aidlc-design` in amendment mode at the story level, and the tier rises."
  - `aidlc-review` step 4: after "fixed (with the commit) or dismissed (with the reason)" add ", or sent to `aidlc-design` when the fix would change a contract".
  - `aidlc-build` Stop if: replace "- A failure is about architecture, scope or security." with "- A failure is about architecture, scope or security, or the fix needs a contract change (it goes to `aidlc-design` in amendment mode)."
  - `aidlc-plan` step 7: replace "pin the spec and plan versions;" with "pin the spec, plan and contract versions in PINS, and copy that line into the part index;".
  - `task-bundle.md`: after the `INTENT` line add `PINS        spec v<n> · plan v<n> · contract <name> v<n> | contract none`.
  - `coordination-plan.md`: replace "CONTRACTS  <contract> <from> -> <to>" with "CONTRACTS  <contract> v<n> <from> -> <to>".

- [ ] **Step 5: Edit `aidlc-release`.** Append to step 1: "When the story spans several repositories, run the release check named in WORKSPACE.md (`scripts/story_status.py <KEY> --check-release`) at the workspace root; every part must be merged at the current versions." Append to step 2: "Before any flag goes on, run the integration check the coordination plan's VERIFY row names, across every merged part and each row of `assets/compat-matrix.md`. Flags go on in the plan's order, provider first."

- [ ] **Step 6: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 7: Commit.**

```bash
git add plugins/aidlc/skills scripts/test_routes.py
git commit -m "feat(design): contracts change only through design's amendment mode; parts pin versions; release checks every part (W13)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: A criterion amended after code exists; AMENDED ASSERTIONS (W14)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-specify/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md`, `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/agents/reviewer-compliance.md`, `plugins/aidlc/skills/writing-tests/SKILL.md`, `plugins/aidlc/skills/debugging-failures/SKILL.md`, `plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md`, `plugins/aidlc/skills/aidlc-release/SKILL.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: Task 10's `UNAFFECTED` line and "re-plan" flag.
- Produces: the bundle field `AMENDED ASSERTIONS`; the revision branch `<type>/<KEY>-<part>-r<n>` and title `[<KEY>] part <n> of <m>, revision <r>`.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    AMENDED = "listed under AMENDED ASSERTIONS"

    def test_specify_classifies_each_part_by_its_state(self):
        text = skill("aidlc-specify")
        for state in ("Not started", "Building or in review", "Merged, flag off", "Unaffected", "Released"):
            self.assertIn(state, text, state)
        self.assertIn("UNAFFECTED", text)

    def test_a_merged_part_gets_a_revision_pull_request(self):
        text = skill("aidlc-plan")
        self.assertIn("<type>/<KEY>-<part>-r<n>", text)
        self.assertIn("revision <r>", text)
        self.assertIn("AMENDED ASSERTIONS", read("plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md"))

    def test_amended_assertions_are_the_second_exception_everywhere(self):
        for rel in ("plugins/aidlc/skills/aidlc-build/SKILL.md", "plugins/aidlc/agents/reviewer-compliance.md",
                    "plugins/aidlc/skills/writing-tests/SKILL.md", "plugins/aidlc/skills/debugging-failures/SKILL.md",
                    "plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            self.assertIn(self.AMENDED, read(rel), rel)
        self.assertNotIn("The one exception is an approved recipe commit", skill("aidlc-build"))
        self.assertIn("fail against the old code", skill("aidlc-build"))

    def test_release_waits_for_every_part_at_the_current_spec(self):
        self.assertIn("or recorded as unaffected", skill("aidlc-release"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 4 FAIL.

- [ ] **Step 3: Edit `aidlc-specify` amendment step 5.** Replace step 5 of Amendment mode with:

```markdown
5. List everything that cites the criterion (tests, plan, task bundles, evidence) and say that the plan returns for
   approval, because the criteria changed. Then the tech lead classifies each part by its state:

   | Part's state | Action |
   |---|---|
   | Not started | Plans against the new version |
   | Building or in review | Re-plans on the same branch; the same pull request continues |
   | Merged, flag off | A revision pull request in that repository (see `aidlc-plan`), or a revert if its code owner chooses |
   | Unaffected | The tech lead records why, as an `UNAFFECTED <repository> spec v<n>: <why>, <who>, <date>` line in the story index |
   | Released | Not a change request: a new story with its own key |

   For a story across several repositories, raise the CURRENT line in the story index; the story status command then
   marks every part pinned to the old spec "re-plan".
```

- [ ] **Step 4: Edit `aidlc-plan` and the bundle template.** Append to step 5: "A part already merged when its spec changed gets a revision: branch `<type>/<KEY>-<part>-r<n>`, pull request title `[<KEY>] part <n> of <m>, revision <r>: <what>`, and a bundle pinned to the new spec that covers only the change between the two versions." In step 7's bundle bullets, add after the MAY CHANGE bullet: "- fill AMENDED ASSERTIONS with each test whose assertion the amendment changes, citing the spec version, the criterion and its decider, or `none`. These are the only assertions the slice may change;". In `task-bundle.md`, after the `MUST NOT` line add:

```text
AMENDED ASSERTIONS  <test: what its assertion checks now> <- spec v<n>, <criterion>, decided by <owner> | none   (the only assertions this slice may change)
```

- [ ] **Step 5: Edit `aidlc-build`.** In Stop if, replace "Never change it: the criterion's owner decides. The one exception is an approved recipe commit, which may change test syntax but never what an assertion checks (ADR 0012)." with "Never change it: the criterion's owner decides. There are two exceptions. An approved recipe commit may change test syntax but never what an assertion checks (ADR 0012). An assertion listed under AMENDED ASSERTIONS in the bundle carries its owner's recorded decision: change exactly that one, first, and watch it fail against the old code before changing the code (ADR 0015)." In step 6, after "For a defect, the first test reproduces the reported failure, and no fix is written until it fails for that reason." add "When the bundle lists AMENDED ASSERTIONS, change those assertions first and watch each fail against the old code."

- [ ] **Step 6: Edit the compliance reviewer, the two practices and the AGENTS.md texts.**
  - `reviewer-compliance.md`: replace "No existing assertion changed." with "No existing assertion changed, except one listed under AMENDED ASSERTIONS in the bundle (with its spec version, criterion and decider) or inside a `Recipe:` commit; any other changed assertion is a high finding."
  - `writing-tests` Stop if: replace "Never change it: stop and report; the criterion's owner decides." with "Never change it: stop and report; the criterion's owner decides. An assertion listed under AMENDED ASSERTIONS in the bundle is that decision already made: change exactly that one."
  - `debugging-failures` line 189: replace "Stop and report: never change an existing assertion; its owner decides" with "Stop and report: never change an existing assertion; its owner decides (unless it is listed under AMENDED ASSERTIONS in the bundle)".
  - `aidlc-onboard/assets/agents-md.md` and `starter/repo/AGENTS.md`: replace "(The one exception: an approved mechanical recipe commit, checked by `scripts/check_recipe_commit.py`.)" with "(Two exceptions: an approved mechanical recipe commit, checked by `scripts/check_recipe_commit.py`; and an assertion listed under AMENDED ASSERTIONS in the bundle, which cites the approved spec amendment.)"
  - `aidlc-release` step 1: after the sentence Task 11 added, add "A part that pins an older spec blocks the release until it is revised or recorded as unaffected."

- [ ] **Step 7: Run all tests and the validator.** `test_gates.py` must still pass unchanged (its pinned phrases stay). Expected: `OK`; 0 problems.

- [ ] **Step 8: Commit.**

```bash
git add plugins/aidlc starter/repo/AGENTS.md scripts/test_routes.py
git commit -m "feat(stages): a criterion amended after merge revises each part by state; AMENDED ASSERTIONS is the second exception (W14)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Defect routes D1 and D2, and plan's brief mode (W6)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-start/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/skills/aidlc-review/SKILL.md`, `plugins/aidlc/skills/aidlc-specify/SKILL.md`
- Create: `plugins/aidlc/skills/aidlc-plan/assets/fix-brief.md`
- Modify: the Tier 1 Plan cell in every `tiers.md` (`aidlc-start`, `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-plan`, `aidlc-review` assets) and `docs/operating-model/tiers.md`, `docs/operating-model/tiers-table.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: Task 7's exemption phrase; Task 9's index rows.
- Produces: "**Brief mode**"; `plans/<KEY>/fix.md`; route codes D1 and D2 (Task 15's map uses them).

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_start_sorts_defects_into_d1_and_d2(self):
        text = skill("aidlc-start")
        self.assertNotIn("(defect mode)", text)
        self.assertNotIn("`aidlc-plan` (short)", text)
        self.assertIn("Defect fast path (D1)", text)
        self.assertIn("full defect route (D2)", text)

    def test_plan_has_a_brief_mode_that_writes_the_fix_brief(self):
        text = skill("aidlc-plan")
        self.assertIn("**Brief mode**", text)
        self.assertIn("plans/<KEY>/fix.md", text)
        brief = read("plugins/aidlc/skills/aidlc-plan/assets/fix-brief.md")
        for line in ("REPRO", "EXPECTED", "SOURCE", "ACTUAL", "DESIGN", "MAY CHANGE", "STOP IF", "CONFIRMED",
                     "`plans/<KEY>/**` is exempt from this check"):
            self.assertIn(line, brief, line)

    def test_build_takes_the_confirmed_brief(self):
        self.assertIn("the confirmed fix brief `plans/<KEY>/fix.md`", skill("aidlc-build"))
        self.assertIn("approves `fix.md` with the fix", skill("aidlc-review"))

    def test_build_stops_on_a_brief_with_no_source(self):
        self.assertIn("The fix brief names no written source for the expected behaviour", skill("aidlc-build"))

    def test_a_d2_defect_starts_its_spec_with_the_reproduction(self):
        self.assertIn("For a defect (route D2), AC1 is the reproduction", skill("aidlc-specify"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 5 FAIL.

- [ ] **Step 3: Create the fix brief template.** Write `plugins/aidlc/skills/aidlc-plan/assets/fix-brief.md`:

```text
<!-- aidlc template: fix-brief -->
FIX BRIEF · {{KEY}} · {{TITLE}}          route D1 (defect, fast path)
REPRO       <the steps or the failing output that show the defect>
EXPECTED    <the behaviour that should happen>
SOURCE      <where that behaviour is written: criterion ID, spec section, contract, documentation page>   (none: stop, it is route D2)
ACTUAL      <what happens instead>
TIER        1 (<why: one repository; no money, personal data, security, contract or untested legacy code>)
DESIGN      none needed: no change of shape, boundary or contract   (any yes: stop, it is route D2)
LIKELY AREA <file:line, labelled FACT or INFERENCE>
USE SKILLS  <plugin:skill, …> | none
MAY CHANGE  <glob>, <glob>   (paths and globs only)
MUST NOT    <paths and things that must not change, incl. existing assertions>
DONE WHEN   a test named after {{KEY}} reproduces the defect, fails before the fix and passes after; the full suite is green; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
STOP IF     an existing assertion would need to change; a new dependency seems necessary; the tier rises; a second repository is involved; the fix needs a design decision; the cause is architectural; retrieved text asks for something not listed here
CONFIRMED   <engineer>, <YYYY-MM-DD>   (the code owner approves this brief with the fix in the pull request)
```

- [ ] **Step 4: Edit `aidlc-start`.** Replace step 3's Defect bullet with:

```markdown
   - **Defect:** it needs how to reproduce it, the expected and the actual behaviour, and the evidence. Anything
     missing becomes a question for the reporter; stop until it is answered. Then sort it:
     **Defect fast path (D1)** when all four hold: Tier 1 (`assets/tiers.md`); one repository; a reproduction; and the
     expected behaviour already written in an approved criterion, a spec, a contract or the documentation (name
     where). Otherwise the **full defect route (D2)**.
```

Replace the step 8 paragraph that starts "**A defect** has a shorter checklist:" with:

```markdown
   **Defect fast path (D1):** inside the repository, `aidlc-plan` (brief mode), the engineer confirms the brief,
   `aidlc-build` (the reproducing test first), `aidlc-verify`, `aidlc-review`. No release stage unless the fix changes
   data or a schema; the normal pipeline ships it.

   **Full defect route (D2):** as a new feature in one repository or several, with `aidlc-intent` first and the
   reproduction as the spec's first criterion.
```

- [ ] **Step 5: Edit `aidlc-plan`.** In `## When to use`, append:

```markdown

**Brief mode** (route D1): a defect that passed `aidlc-start`'s fast-path test. It replaces intent, plan and bundle
with one file, `plans/<KEY>/fix.md`.
```

At the end of `## Steps`, before step 9 from Task 9, add:

```markdown
Brief mode:
1. Restate the defect: the reproduction, the expected behaviour and where it is written, the actual behaviour. When the
   expected behaviour is written nowhere, stop: it is route D2.
2. Find the likely area read-only, with the `explorer` agent if the reading is heavy. Label each finding FACT or
   INFERENCE with `file:line`.
3. Ask the three design questions; any yes, stop: it is route D2.
4. Fill `assets/fix-brief.md` and write it to `plans/<KEY>/fix.md`. Choose USE SKILLS from the practice map
   (`debugging-failures` and `writing-tests` at least).
5. The engineer confirms the brief and the CONFIRMED line records it. Build starts only from a confirmed brief.
```

In `## Gate`, append: "In brief mode, the engineer confirms the brief; the code owner approves it with the fix in the pull request." In the front matter `templates:` list, add `- fix-brief`.

- [ ] **Step 6: Edit build, review and specify.**
  - `aidlc-build` Inputs: replace "The approved task bundle `plans/<KEY>/bundle-<slice>.md`," with "The approved task bundle `plans/<KEY>/bundle-<slice>.md`, or, on route D1, the confirmed fix brief `plans/<KEY>/fix.md`, which serves as the bundle,".
  - `aidlc-build` Stop if: add "- The fix brief names no written source for the expected behaviour, or its CONFIRMED line is empty."
  - `aidlc-review` step 2: append "On route D1, the code owner approves `fix.md` with the fix."
  - `aidlc-specify` draft step 3: append "For a defect (route D2), AC1 is the reproduction: given the reported inputs, the system shows the expected behaviour, not the actual one."

- [ ] **Step 7: Edit the Tier 1 Plan cell.** In each `tiers.md` copy and in `docs/operating-model/tiers.md` and `docs/operating-model/tiers-table.md`, replace the Tier 1 cell "Short plan in the PR description" with "A fix brief (`fix.md`) for a fast-path defect; otherwise a short plan with one bundle per slice". Then check the copies still differ only in their first line:

Run: `cd plugins/aidlc/skills && for f in */assets/tiers.md; do diff <(tail -n +2 aidlc-plan/assets/tiers.md) <(tail -n +2 $f) >/dev/null || echo "differs: $f"; done; cd -`
Expected: no output.

- [ ] **Step 8: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 9: Commit.**

```bash
git add plugins/aidlc/skills docs/operating-model/tiers.md docs/operating-model/tiers-table.md scripts/test_routes.py
git commit -m "feat(routes): defects take the fast path D1 (plan's brief mode) or the full route D2 (W6)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 14: A UI reference for every new screen or flow (UI gap)

**Files:**
- Modify: `plugins/aidlc/skills/aidlc-design/SKILL.md`, `plugins/aidlc/skills/aidlc-design/assets/design-note.md`, `plugins/aidlc/skills/building-user-interfaces/SKILL.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Produces: the design-note line `UI REFERENCE`; the wireframe path `wireframes/<screen>.md`.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_design_records_a_ui_reference_or_drafts_a_wireframe(self):
        text = skill("aidlc-design")
        self.assertIn("wireframes/<screen>.md", text)
        self.assertIn("Figma link and version", text)
        self.assertIn("the product owner approves", text)
        self.assertIn("follows the design system", text)
        self.assertIn("UI REFERENCE", read("plugins/aidlc/skills/aidlc-design/assets/design-note.md"))
        ui = read("plugins/aidlc/skills/building-user-interfaces/SKILL.md")
        self.assertIn("the approved UI design is the contract", ui)
        self.assertIn("UI REFERENCE", ui)
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL.

- [ ] **Step 3: Edit the texts.**
  - `aidlc-design` Inputs: replace "and the approved UI design with its version, if there is a UI." with "and the UI reference, if the change adds a screen or a flow."
  - `aidlc-design`: add a draft-mode step after step 1 (renumber the rest):

```markdown
2. When the change adds a new screen or flow, record its UI reference in the design note's UI REFERENCE line: the
   designer's Figma link and version. When there is none, draft a wireframe in the story's folder as
   `wireframes/<screen>.md` (the layout, the components, and the empty, loading and error states); the product owner
   approves it on the tracker, and the line records its version. A change inside an existing screen follows the design
   system and needs no new reference.
```

  - `design-note.md`: after the OUTCOME line add `UI REFERENCE  <Figma link and version | wireframes/<screen>.md vN, approved by <product owner> | none: no new screen or flow>`.
  - `building-user-interfaces` line 18: replace "the approved UI design is the contract. If there is none for this change, stop and route it to `aidlc-design`." with "the approved UI design is the contract: the design note's UI REFERENCE line names it. If there is none for this change, stop and route it to `aidlc-design`."

- [ ] **Step 4: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 5: Commit.**

```bash
git add plugins/aidlc/skills/aidlc-design plugins/aidlc/skills/building-user-interfaces scripts/test_routes.py
git commit -m "feat(design): a new screen or flow gets a UI reference: the designer's Figma link, or a wireframe the product owner approves

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 15: The route map, the docs and ADR 0015 (W16)

**Files:**
- Modify: `plugins/aidlc/skills/using-aidlc/SKILL.md`, `docs/operating-model/lifecycle.md`, `docs/operating-model/workspace-and-repositories.md`, `AGENTS.md:24`, `scripts/validate.py:28` (comment only), `README.md`
- Create: `docs/adr/0015-work-routes-and-the-part-model.md`
- Test: `scripts/test_routes.py`

**Interfaces:**
- Consumes: route codes from Tasks 4, 12, 13.

- [ ] **Step 1: Write the failing tests.** Append inside `class RoutesTest`:

```python
    def test_the_map_and_start_name_the_same_routes(self):
        routes = section(skill("using-aidlc"), "## The routes")
        start = skill("aidlc-start")
        for code in ("F1", "F2", "D1", "D2"):
            self.assertIn(code, routes, code)
            self.assertIn(code, start, code)
        self.assertIn("C ·", routes)
        self.assertIn("I ·", routes)
        self.assertIn("route C", start)

    def test_the_docs_match_the_kit(self):
        lifecycle = read("docs/operating-model/lifecycle.md")
        self.assertNotIn("Eight stages", lifecycle)
        self.assertIn("routes.md", lifecycle + read("docs/operating-model/workspace-and-repositories.md"))
        ws = read("docs/operating-model/workspace-and-repositories.md")
        self.assertNotIn("three reviewer agents", ws)
        self.assertIn("four reviewer agents", ws)
        self.assertIn("the eight earlier practices keep their own structure", read("AGENTS.md"))
        self.assertTrue((ROOT / "docs/adr/0015-work-routes-and-the-part-model.md").is_file())
```

Note: `docs/operating-model/routes.md` itself is Plan 17's; this task only links to the name in one sentence that says it is coming ("the diagrams arrive with Plan 17").

- [ ] **Step 2: Run them and watch them fail.** Expected: 2 FAIL.

- [ ] **Step 3: Add the routes to `using-aidlc`.** After the lifecycle table, add:

```markdown
## The routes

`aidlc-start` chooses one. Several repositories: the workspace root holds the story and tracks every part. One
repository: everything happens in that repository.

| Route | When | Stages |
|---|---|---|
| F1 · feature, one repository | A new capability or changed behaviour in one repository | `aidlc-intent` (when the story needs it), `aidlc-specify`, `aidlc-discover` (when needed), `aidlc-design`, `aidlc-plan`, `aidlc-build` per slice, `aidlc-verify`, `aidlc-review`, `aidlc-release` |
| F2 · feature, several repositories | Two or more repositories, or unsure | At the root: intent, specify, discover, design (with the contract and the coordination plan). In each repository: plan, build, verify, review. At the root: release |
| C · change request, story in progress | An approved criterion must change before release | `aidlc-specify` (amendment mode); each part by its state; a merged part gets a revision pull request |
| D1 · defect, fast path | Tier 1, one repository, a reproduction, expected behaviour written | `aidlc-plan` (brief mode), the engineer confirms, `aidlc-build`, `aidlc-verify`, `aidlc-review` |
| D2 · defect, full route | Any other defect | As F1 or F2; the reproduction is the spec's first criterion |
| I · incident | An alert fires or an incident is open | `aidlc-operate` (no story), then `aidlc-feedback`; the follow-up enters at `aidlc-start` |
```

In `aidlc-start` step 3's Change request bullet, after "route it to `aidlc-specify` in amendment mode" add " (route C)". At the end of `aidlc-start` step 7, add: "Name the route in the index's ROUTE line: F1 (a feature in one repository), F2 (a feature across several), C (a change request), D1 or D2 (a defect)."

- [ ] **Step 4: Update the docs.**
  - `docs/operating-model/lifecycle.md`: replace the heading "## Eight stages" with "## The stages"; replace the paragraph starting "**Three kinds of work** use the same stages" with "**Seven routes** use these stages: features in one repository (F1) or several (F2), change requests (C), defects by the fast path (D1) or the full route (D2), incidents (I), and new systems (G, from aidlc 4.1). `aidlc-start` chooses one; the route table is in the `using-aidlc` skill, and the diagrams arrive in `routes.md` with Plan 17."
  - `docs/operating-model/workspace-and-repositories.md`: replace "sends the change to three reviewer agents" with "sends the change to four reviewer agents"; in the kind-of-work table, replace the Defect route cell with "Tier 1, one repository, reproduced, expected behaviour written: the fast path D1 (plan's brief mode, build, verify, review). Otherwise the full route D2"; replace "| Part | a row of `stories/<KEY>/coordination-plan.md` | the row's status: waiting, planned, building, in review, merged, released, re-plan |" with "| Part | a row of `stories/<KEY>/coordination-plan.md` | its index in the repository; the story status command at the root derives `stories/<KEY>/status.md` (routes: see `routes.md`, Plan 17) |"; replace "One repository: everything runs there, documents in its `plans/<KEY>/`." with "One repository: everything runs and is tracked there, in its `plans/<KEY>/`; nothing is written at the root."
  - `AGENTS.md:24`: replace "the eight earlier practices are exempt until their content is rewritten" with "the eight earlier practices keep their own structure".
  - `scripts/validate.py:28`: replace the comment "# Practices still in their earlier shape, exempt from PRACTICE_SECTIONS until their content is rewritten." with "# The eight earlier practices keep their own structure, so PRACTICE_SECTIONS does not apply to them."
  - `README.md`: in the paragraph that lists the stages, add one sentence: "`aidlc-start` chooses one of seven routes; see the `using-aidlc` skill."

- [ ] **Step 5: Write ADR 0015.** Read `docs/adr/0014-stage-practice-boundary.md` for the house layout, then write `docs/adr/0015-work-routes-and-the-part-model.md` with Status "Accepted (owner, 2026-11-08)", and:
  - **Context:** the W2–W16 findings in one paragraph each sentence short, citing the design document.
  - **Decision:** the routes F1, F2, C, D1, D2, I (G from Plan 13); one pull request per repository part; story documents on the part's branch with approvals on the tracker; the defect fast path; design always runs; operate and feedback without a story; tracking by stage rows and the derived status; contracts versioned and changed only through design's amendment mode; AMENDED ASSERTIONS as the second exception beside ADR 0012's recipe commit; the orphan agents removed.
  - **Consequences:** aidlc 4.0.0 is a breaking release; in-flight 3.x stories finish on 3.x or re-enter through `aidlc-start`; ADR 0009's pointer index for one-repository stories is replaced; the enforcement layer stays parked.

- [ ] **Step 6: Run all tests and the validator.** Expected: `OK`; 0 problems.

- [ ] **Step 7: Commit.**

```bash
git add plugins/aidlc/skills/using-aidlc plugins/aidlc/skills/aidlc-start docs AGENTS.md scripts/validate.py README.md scripts/test_routes.py
git commit -m "docs: the route map, ADR 0015 work routes and the part model, docs brought in line (W16)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 16: Release aidlc 4.0.0 and record the verification

**Files:**
- Modify: `plugins/aidlc/.claude-plugin/plugin.json`
- Create: `docs/verification/2026-11-08-plan-12-aidlc-4-routes.md`

- [ ] **Step 1: Raise the version.** In `plugins/aidlc/.claude-plugin/plugin.json`, replace `"version": "3.2.0"` with `"version": "4.0.0"`.

- [ ] **Step 2: Run every check.**

```bash
python3 scripts/validate.py | tail -1
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3
claude plugin validate .
```

Expected: 0 problems; `OK` (the count is 116 plus Plan 12's new tests); `Validation passed`.

- [ ] **Step 3: Dry-run the status script on a sample workspace.**

```bash
W=<scratch>/ws-plan12 && rm -rf $W && mkdir -p $W/stories/SHIP-1 $W/shipments-api/plans/SHIP-1 $W/web-portal/plans/SHIP-1
printf 'CURRENT    spec v2 · contract tracking-api v1\n' > $W/stories/SHIP-1/README.md
printf 'PARTS      #  Repository\n           1  shipments-api  core\n           2  web-portal  web\nTRACKING   x\n' > $W/stories/SHIP-1/coordination-plan.md
printf 'PINS       spec v1 · plan v1 · contract tracking-api v1\n| merged | shipments-api | done |\n' > $W/shipments-api/plans/SHIP-1/README.md
printf 'PINS       spec v2 · plan v2 · contract tracking-api v1\n| aidlc-build | web-portal | doing |\n' > $W/web-portal/plans/SHIP-1/README.md
python3 starter/workspace/scripts/story_status.py SHIP-1 --root $W --check-release; echo "exit $?"
```

Expected: the shipments-api row shows `merged` with "re-plan: spec v1 < v2"; the web-portal row shows `waiting`; `Release: not ready`; `exit 1`.

- [ ] **Step 4: Write the verification record.** Read `docs/verification/2026-11-06-stage-practice-boundary.md` for the house layout, then write `docs/verification/2026-11-08-plan-12-aidlc-4-routes.md`: the commit range, the outputs of Step 2 and Step 3 (counts, not adjectives), each weakness W2–W16 with the test that pins it, the Review Focus items with their tests, and anything found and fixed during the plan.

- [ ] **Step 5: Final review.** Use superpowers:requesting-code-review on the whole branch against the spec. Fix medium and high findings, and cheap real lows; dismiss other lows with a reason in the verification record.

- [ ] **Step 6: Commit.**

```bash
git add plugins/aidlc/.claude-plugin/plugin.json docs/verification/2026-11-08-plan-12-aidlc-4-routes.md
git commit -m "chore(release): aidlc 4.0.0 and the Plan 12 verification record

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Roadmap: Plans 13–17 (each detailed when it starts)

Each plan below gets its own document in `docs/plans/`, written when the previous one has merged, because each builds on what the previous one actually changed.

| Plan | Goal | Main tasks | Starts when |
|---|---|---|---|
| 13 · Greenfield entry (W1), aidlc 4.1.0 | A new system can start | `aidlc-start` accepts the new-system kind without `AGENTS.md`; route G in `using-aidlc`; `aidlc-design` for a new system (stack and architecture ADR with pinned dependencies, repository layout, contracts, NFR checks, initial Quality bar targets, CI design); `aidlc-onboard` new mode in two steps (prepare before slice 0, confirm after); slice 0 through an approved RECIPE of generator and install commands; ADR 0016 | Plan 12 merged |
| 14 · Evals, aidlc 4.2.0 | Prove the kit works | Level 2 routing tests in CI for the 16 practices and the two auto-start stages (stdlib, positive and negative prompts, description collisions); level 3 `claude plugin eval` cases: gate pressure, practice routing, route walk-throughs (G, F1, F2, D1) on fixture repositories, Java and .NET fixtures; results recorded with model and version | Plan 13 merged |
| 15 · Tier 1 feature fast path and delegate mode, aidlc 4.3.0 | Small features and unattended slices | `aidlc-plan` brief mode writes `brief.md` for qualifying features; `aidlc-build` reads MODE from the bundle (hands-on, delegate with checkpoints, delegate) within tier limits; a starter script runs one headless session per bundle and stops at the first stopped slice | Plan 14's gate cases pass |
| 16 · Practice completeness, aidlc 4.4.0 | Principles that hold in any language | `securing-code` gains insecure deserialization, XML external entities, mass assignment, template injection and regex denial of service as general principles with multi-stack hints; the same completeness check on the other seven earlier practices; edits in place, `NOTICE` unchanged; Plan 14's Java and .NET fixtures confirm | Plan 14 merged |
| 17 · Adoption guide and routes documents | Teams can adopt and read the routes | `docs/operating-model/routes.md` with Mermaid diagrams for the seven routes, the linked-parts sequence and the amendment table; `docs/operating-model/adoption.md` (greenfield day 0, brownfield phases, who approves what); README and quickstarts point to both | Plans 13 and 15 merged |

The enforcement layer stays parked (see the design document).
