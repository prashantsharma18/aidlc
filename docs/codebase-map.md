# aidlc: codebase map
Owner: framework owners · Last verified: 2026-11-06

## What this repository is
A marketplace of skills plugins. Engineers install `aidlc` (and, where needed, `aidlc-modernize`) in Claude Code, or
copy the plugins' `skills/` folders into Copilot, Codex or Cursor.

## Areas
`plugins/aidlc/skills/aidlc-*/`   core stage skills; each `SKILL.md` names its templates in `assets/`
`plugins/aidlc/skills/<practice>/`   engineering-practice skills (`skills/NOTICE` covers parts of the eight earlier ones)
`plugins/aidlc/skills/using-aidlc/`   the map: stages in order and the practice for each kind of work
`plugins/aidlc/agents/`   agent roles the core skills call (Claude Code subagent format)
`plugins/aidlc-modernize/`   the modernisation pack: method skills, factories (`dotnet-modernize` with `scripts/retarget.py`,
`java-modernize`), `modernize-parity/scripts/parity.py`, the `parity-checker` agent
`starter/repo/`, `starter/workspace/`   files a team copies once; `starter/repo/scripts/` holds `check_packs.py`,
`check_recipe_commit.py` and `run_slices.py`
`.claude-plugin/marketplace.json`   the marketplace listing both plugins
`scripts/validate.py`   the marketplace check; `scripts/test_*.py` test it and every script above
`docs/`   quickstarts, operating model, ADRs, designs, plans, verification records

## Where common changes go
- A new core stage skill: `plugins/aidlc/skills/aidlc-<name>/SKILL.md` with the house sections; templates in its `assets/`.
- A new practice skill: `plugins/aidlc/skills/<gerund-name>/SKILL.md` with `metadata.kind: practice` and the practice
  sections (When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules); long checklists in its `references/`.
- A new pack: a folder under `plugins/` with `.claude-plugin/plugin.json` (a version, and `dependencies` on `aidlc` with a
  range), an entry in `.claude-plugin/marketplace.json`, skill names with the pack's own prefix, and a line in the README.
- A new factory inside `aidlc-modernize`: `plugins/aidlc-modernize/skills/<tech>-modernize/` with `references/` and,
  when it has a deterministic recipe, `scripts/` plus its tests in `scripts/test_*.py`.
- A template change: the `assets/` file of every skill that uses it (search for its file name).

## Traps
- A skill names only "the repository's commands from AGENTS.md", never a tool-specific command.
- Core never names a pack; the validator fails if it does.
- In a `SKILL.md`, a backticked `assets/…`, `references/…` or `scripts/…` path must be a file inside that skill.
- Raise a plugin's version on every release: a pinned version that never changes stops installed copies from updating.
