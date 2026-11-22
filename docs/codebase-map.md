# aidlc: codebase map
Owner: framework owners · Last verified: 2026-11-21

## What this repository is
One skills plugin, `aidlc`, at the repository root: instructions only (ADR 0024). Engineers install it in Claude
Code; its `skills/` folders also load in Copilot, Codex or Cursor, untested there.

## Areas
`skills/aidlc-*/`   core stage skills; each `SKILL.md` names its templates in `assets/`, and five of them keep the steps
of one route or case in `references/`, read on a named condition (Plan 26)
`skills/<practice>/`   engineering-practice skills (`skills/NOTICE` covers parts of the eight earlier ones)
`skills/using-aidlc/`   the map: stages in order and the practice for each kind of work
`skills/parallel-lanes/`   the workflow skill: lanes in git worktrees, from a `QUEUE.md` a person keeps (ADR 0025)
`skills/story-run/`   the workflow skill a person starts once per decision: one story's stages, one after another, in one session (ADR 0028)
`skills/story-run/references/`   eight playbooks, one per kind of work, which build and verify read from the bundle's PLAYBOOK line; a playbook holds no gate
`agents/`   agent roles the core skills call (Claude Code subagent format)
`evals/`   behaviour eval cases, run with `claude plugin eval .`, or on demand in CI by `.github/workflows/evals.yml`
`starter/repo/`, `starter/workspace/`   files a team copies once: a rules file, an ownership list and optional example
settings; no scripts and no workflows (ADR 0024). The scripts aidlc 5 shipped (`check_slice.py`, `check_plan.py`,
`check_recipe_commit.py`, `check_contract_version.py`, `check_contract_pin.py`, `run_slices.py`, `story_status.py`)
and the workflows (`ai-review.yml`, `ci.yml`, `contract-check.yml`, `contract-publish.yml`) are kept under the tag
`checks-v1` (`docs/archive/checks-v1.md`)
`.claude-plugin/`   `plugin.json`, and `marketplace.json` whose one entry has the source `./`
`scripts/validate.py`   the plugin check; `scripts/test_*.py` test it and the wording of the skills and documents
`docs/`   quickstarts, operating model, ADRs, designs, plans, verification records

## Where common changes go
- A new core stage skill: `skills/aidlc-<name>/SKILL.md` with the house sections; templates in its `assets/`.
- A route's or case's steps in a stage skill: its `references/<case>.md`, named in `SKILL.md` with the condition to read
  it; its stops and decisions stay in `SKILL.md`.
- A new practice skill: `skills/<gerund-name>/SKILL.md` with `metadata.kind: practice` and the practice
  sections (When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules); long checklists in its `references/`.
- A new workflow skill: `skills/<noun-phrase>/SKILL.md` with `metadata.kind: workflow` and the workflow sections
  (When to use, Inputs, Steps, Stop if, Common excuses, Red flags, Rules); its name never starts with `aidlc-` or with
  an "-ing" word.
- A template change: the `assets/` file of every skill that uses it (search for its file name).
- Who decides at a gate: the decisions table in the six identical `assets/tiers.md` copies and
  `docs/operating-model/tiers-table.md` (ADR 0026); each deciding stage's Gate keeps its one line that points there.

## Traps
- A skill names only "the repository's commands from AGENTS.md", never a tool-specific command.
- In a `SKILL.md`, a backticked `assets/…`, `references/…` or `scripts/…` path must be a file inside that skill.
- A stage skill's reference never holds a Gate, Stop if, Common excuses, Red flags or Rules section, and its `SKILL.md`
  names it; `scripts/validate.py` checks both.
- Raise the plugin's version on every release: a pinned version that never changes stops installed copies from updating.
