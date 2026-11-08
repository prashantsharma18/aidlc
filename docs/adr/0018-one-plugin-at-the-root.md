# 0018 · One plugin at the repository root

Status: Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-08-plan-17-one-plugin.md` · Supersedes: ADR 0011

## Context
The repository was a marketplace of two plugins: the core, `aidlc`, under `plugins/aidlc/`, and the modernise pack,
`aidlc-modernize`, with a pack contract (ADR 0011) that let a repository switch packs on and kept core from naming
them. That was more than teammates need. The goal is aidlc itself, installed as one plugin and understood quickly.

## Decision
- aidlc is one plugin, at the repository root: `skills/`, `agents/` and `evals/` at the root, and `.claude-plugin/`
  holding `plugin.json` and `marketplace.json`, whose one entry has the source `./`.
- The modernise pack is archived, not deleted: the tag `aidlc-modernize-archive` (commit f8e093c) holds it, and
  `docs/archive/aidlc-modernize.md` says what it held and how to restore it.
- The pack contract goes with it: the `Packs used here` section, `check_packs.py`, start's pack step, "pack skills"
  in USE SKILLS, and the validator's "core never names a pack" check.
- Install commands do not change: `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc`.
  The marketplace and the plugin keep the name `aidlc`.
- The recipe commit (ADR 0012) stays: it serves any deterministic tool.

## Consequences
- aidlc 5.0.0: the layout changes, and so does the skills' contract (no pack step, no pack skills in bundles).
- An install copies the whole repository into the plugin cache: `docs/`, `starter/` and `scripts/` as well as the
  skills.
- `claude plugin validate` warns that a `CLAUDE.md` at a plugin root is not loaded as project context. The root
  `CLAUDE.md` is for contributors, and stays.
- Bringing the pack back is a design change: as a second plugin with its own folder and marketplace entry, or as
  skills inside aidlc. Either needs a new ADR.

## Upgrading a repository onboarded with aidlc 4
- Remove `aidlc-modernize@aidlc` from `enabledPlugins` in `.claude/settings.json`: the marketplace no longer lists it.
- Optionally delete the `## Packs used here` section and the "Pack check" line from `AGENTS.md`, and
  `scripts/check_packs.py` with its CI step. Nothing in aidlc 5 reads them.
