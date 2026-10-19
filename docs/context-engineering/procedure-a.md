# Procedure A: setting up context for a repository

Done once per repository, then maintained. Done when a fresh agent session finds what it needs
without being told, and a before/after comparison shows the context helps.

| Step | What you do | Framework support |
|---|---|---|
| A1 Inventory | Read-only survey: frameworks, commands, areas, documents and their age, shared modules; mine PR reviews for recurring corrections; ask reviewers what they would tell a new joiner | Explorer brief template (`aidlc new explorer-brief`); `aidlc-context-setup` skill (Plan 4) |
| A2 Placement | For each item, ask in order: sensitive? true only now? must hold every time? needed by almost every task? one area? a recipe? a pattern? reference? Stop at the first yes | Context classes policy; the standards |
| A3 Rules file | Write `AGENTS.md`: map, commands, standards with exemplars, boundaries, tools, where to look; apply the removal test | `aidlc init-repo` scaffolds it; budget enforced by the drift check |
| A4 Codebase map | Purpose, areas, key flows, where changes go, shared capabilities, traps, tests, plus owner and last-verified line | Template `codebase-map`; drift check |
| A5 Wire up | Folder rules in `.aidlc/rules/`; render tool files; enforce must-hold rules; make secrets unreachable | `aidlc render --tool claude-code`; permissions and sandbox (Plan 2) |
| A6 Validate | Fresh-session probe (`.aidlc/probe.yaml`) and a before/after comparison on 3 merged tasks | `aidlc eval --suite probe` (Plan 3) |
| A7 Maintain | Owners, last-verified dates, drift checks in CI, changes by reviewed PR, scheduled pruning | `aidlc check context-drift` in trusted CI (Plan 3) |

Quick start in a repository:

    aidlc init-repo . --name <name> --owner "<team>" --profile node|dotnet|generic --purpose "<one line>"
    # fill in AGENTS.md and docs/codebase-map.md (replace <sha> with the commit you verified against)
    aidlc render --tool claude-code
    aidlc check context-drift && aidlc check openwiki

`init-repo` never overwrites an existing file; it reports `skipped (exists)` instead.

Guide: 2.8.
