# aidlc: codebase map
Owner: framework owners · Last verified: 2026-11-06

## What this repository is
One skills plugin, `aidlc`, at the repository root. Engineers install it in Claude Code, or copy its `skills/`
folders into Copilot, Codex or Cursor.

## Areas
`skills/aidlc-*/`   core stage skills; each `SKILL.md` names its templates in `assets/`
`skills/<practice>/`   engineering-practice skills (`skills/NOTICE` covers parts of the eight earlier ones)
`skills/using-aidlc/`   the map: stages in order and the practice for each kind of work
`agents/`   agent roles the core skills call (Claude Code subagent format)
`evals/`   behaviour eval cases, run with `claude plugin eval .`
`starter/repo/`, `starter/workspace/`   files a team copies once; `starter/repo/scripts/` holds `check_packs.py`,
`check_recipe_commit.py` and `run_slices.py`
`.claude-plugin/`   `plugin.json`, and `marketplace.json` whose one entry has the source `./`
`scripts/validate.py`   the marketplace check; `scripts/test_*.py` test it and every script above
`docs/`   quickstarts, operating model, ADRs, designs, plans, verification records

## Where common changes go
- A new core stage skill: `skills/aidlc-<name>/SKILL.md` with the house sections; templates in its `assets/`.
- A new practice skill: `skills/<gerund-name>/SKILL.md` with `metadata.kind: practice` and the practice
  sections (When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules); long checklists in its `references/`.
- A new pack: a folder under `plugins/` with `.claude-plugin/plugin.json` (a version, and `dependencies` on `aidlc` with a
  range), an entry in `.claude-plugin/marketplace.json`, skill names with the pack's own prefix, and a line in the README.
- A template change: the `assets/` file of every skill that uses it (search for its file name).

## Traps
- A skill names only "the repository's commands from AGENTS.md", never a tool-specific command.
- Core never names a pack; the validator fails if it does.
- In a `SKILL.md`, a backticked `assets/…`, `references/…` or `scripts/…` path must be a file inside that skill.
- Raise a plugin's version on every release: a pinned version that never changes stops installed copies from updating.
