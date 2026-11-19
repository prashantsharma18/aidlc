# aidlc: codebase map
Owner: framework owners · Last verified: 2026-11-08

## What this repository is
One skills plugin, `aidlc`, at the repository root. Engineers install it in Claude Code, or copy its `skills/`
folders into Copilot, Codex or Cursor.

## Areas
`skills/aidlc-*/`   core stage skills; each `SKILL.md` names its templates in `assets/`
`skills/<practice>/`   engineering-practice skills (`skills/NOTICE` covers parts of the eight earlier ones)
`skills/using-aidlc/`   the map: stages in order and the practice for each kind of work
`agents/`   agent roles the core skills call (Claude Code subagent format)
`evals/`   behaviour eval cases, run with `claude plugin eval .`, or on demand in CI by `.github/workflows/evals.yml`
`starter/repo/`, `starter/workspace/`   files a team copies once; `starter/repo/scripts/` holds `check_recipe_commit.py`, `check_slice.py` (the slice check, run in CI and as a Stop hook), `check_plan.py` (the plan check) and
`run_slices.py`
`.claude-plugin/`   `plugin.json`, and `marketplace.json` whose one entry has the source `./`
`scripts/validate.py`   the plugin check; `scripts/test_*.py` test it and every script above
`docs/`   quickstarts, operating model, ADRs, designs, plans, verification records

## Where common changes go
- A new core stage skill: `skills/aidlc-<name>/SKILL.md` with the house sections; templates in its `assets/`.
- A new practice skill: `skills/<gerund-name>/SKILL.md` with `metadata.kind: practice` and the practice
  sections (When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules); long checklists in its `references/`.
- A template change: the `assets/` file of every skill that uses it (search for its file name).

## Traps
- A skill names only "the repository's commands from AGENTS.md", never a tool-specific command.
- In a `SKILL.md`, a backticked `assets/…`, `references/…` or `scripts/…` path must be a file inside that skill.
- Raise the plugin's version on every release: a pinned version that never changes stops installed copies from updating.
