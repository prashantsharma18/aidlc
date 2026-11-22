# 0011 · One marketplace, a core plugin and packs that core never names

Status: Superseded by ADR 0018 (2026-11-08): one plugin at the repository root; no packs. (Was: Accepted (2026-10-26). · Decider: Prashant Sharma (framework owner))

## Context
aidlc will grow: modernisation factories for .NET and Java first, more later. With one plugin, every factory would be
in every repository. Claude Code, GitHub Copilot, Codex and Cursor now all distribute skills as plugins from a
marketplace and switch them on per repository.

A research run (Claude Code 2.1.296, two test plugins) showed how a core skill could reach a skill in another plugin,
and what happens when that plugin is off: a skill named in text gives "Unknown skill" and the model carries on; an
agent's preloaded skill is skipped with only a debug-log warning; there is no optional plugin dependency. A core that
depends on an optional pack therefore fails silently. A second, adversarial review checked the design against
Anthropic's plugin and skill documentation.

## Decision
- One marketplace (this repository) with plugins under `plugins/`: `aidlc` (core: the stage skills, the practice
  skills, the agents, the gates) and `aidlc-modernize` (the modernisation method and the .NET and Java factories).
- **Core never names a pack.** A repository declares its packs in AGENTS.md (`Packs used here`); a pack check script
  verifies the declaration against what is installed; `aidlc-start` runs it; the task bundle names pack skills in
  full (`<plugin>:<skill>`); `aidlc-build` loads them or stops; the compliance reviewer checks what was loaded.
- A pack requires core with a version range (`{"name": "aidlc", "version": "^2.0"}`); core requires nothing. Every
  release raises the version and is tagged `<plugin>--v<version>`.
- Skill names are unique across the marketplace. The practice skills stay in core.
- The factories live inside `aidlc-modernize` until a second owning team, a separate release cadence or the skill
  listing budget makes separate plugins worth their cost.

## Alternatives rejected
- One plugin for everything: every factory loads in every repository.
- Splitting the practice skills into packs: they refer to each other (code review to security and performance), so the
  links would break silently, for about 500 tokens of descriptions saved.
- A session-start router skill: hosts that route skills natively would run two routers (agent-skills makes the same
  choice for the same reason).

## Consequences
- The validator checks the marketplace: sources under `./plugins/`, semantic versions, dependencies that exist, core
  without dependencies, unique skill names, and no pack name in core's files.
- Copilot has no plugin dependencies and keeps the first skill of a given name: list every plugin a repository needs.
- Cloud sessions and headless (`-p`) runs do not add a repository's marketplaces (they need the folder-trust dialog):
  CI installs the plugins it needs explicitly.
