# aidlc: codebase map
Owner: framework owners · Last verified: 2026-10-25

## What this repository is
A skills package. Engineers install it in Claude Code (the repository root is the plugin), or copy `skills/` into
Copilot, Codex or Cursor.

## Areas
`skills/aidlc-*/`   stage skills; each `SKILL.md` names its templates in `assets/`
`skills/<practice>/`   engineering-practice skills adapted from addyosmani/agent-skills (MIT, `skills/NOTICE`)
`agents/`   agent roles the skills call (Claude Code subagent format)
`starter/repo/`, `starter/workspace/`   files a team copies once
`.claude-plugin/`   marketplace and plugin manifest
`scripts/validate.py`   the package check, with `scripts/test_validate.py`
`docs/`   quickstarts, operating model, ADRs, designs, plans, verification records

## Where common changes go
- A new stage skill: `skills/aidlc-<name>/SKILL.md` with the house sections; its templates in its `assets/`.
- A template change: the `assets/` file of every skill that uses it (search for its file name).

## Traps
- A skill names only "the repository's commands from AGENTS.md", never a tool-specific command.
- `CLAUDE.md` at the root is for contributors; `claude plugin validate` warns that a plugin does not ship it, which is expected.
