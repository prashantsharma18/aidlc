# 0016 · Greenfield entry

Status: Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (Plan 13)

Amended by ADR 0024 (2026-11-20): see the last section.

## Context
A new system had no way in (W1). `aidlc-start` stopped without `AGENTS.md`, and `aidlc-onboard` needed a repository
that already builds, with merged changes to validate against. No stage chose a stack or built a skeleton, and the
build's first step runs commands that do not exist yet.

## Decision
- Route G. A person creates the home: an empty repository when the team knows the system is one repository, or a
  workspace, onboarded at its root, when it is several or undecided. The agent never creates a repository. A folder
  with code or with `AGENTS.md` is never route G.
- `aidlc-design` fills `new-system.md`: the stack and architecture, every dependency pinned, the repository layout, the
  contracts, the non-functional checks, the initial Quality bar targets, the commands and the scaffold commands.
  Approving it is the approval to add those dependencies and run those commands.
- `aidlc-onboard` gains a new mode in two steps. Prepare, before slice 0: the starter files and `AGENTS.md`, each
  command marked `(not yet run)`. Confirm, after slice 0 merges: every command run, the marks removed, the map written.
- Slice 0 builds the skeleton under the usual gates: tests first, MAY CHANGE, trusted CI, a code owner who did not
  write it. Its scaffold recipe, marked `(scaffold)`, is reviewed as generated code instead of by the recipe check,
  because generators are not reproducible.
- No new stage.

## Consequences
- aidlc 4.1.0.
- After confirm, the repository is ordinary: every feature takes F1 or F2.
- The recipe check is unchanged for every other recipe.

## Amended by ADR 0024 (2026-11-20)
- The recipe check is now a git procedure in `aidlc-build`, not a script. A `(scaffold)` recipe is still reviewed
  as generated code and is not re-run.
