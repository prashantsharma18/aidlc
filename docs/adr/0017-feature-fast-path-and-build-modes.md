# 0017 · Feature fast path and build modes

Status: Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (Plan 15) · Plan: `docs/plans/2026-11-08-plan-15-fast-path-delegate.md`

## Context
`aidlc-plan` offered three build modes, but nothing read them: every slice ran hands-on (the second half of W7). A
feature of a few lines took the whole F1 route: a spec, a design note, a plan and a bundle for one test and one change.
Defects already had a fast path (D1); features had none.

## Decision
- Route F0, the feature fast path. Its conditions, all of them: Tier 1; one repository; acceptance criteria written on
  the work item by its owner; the three design questions answer "no"; no new dependency; no change to stored data or
  a schema; one slice. `aidlc-start` checks what the work item shows; `aidlc-plan` (brief mode) checks what needs the
  code. Route: start, `brief.md`, the engineer confirms, build, verify, review, merge.
- A condition that fails late stops the stage. The person re-runs `aidlc-start`, which rewrites the ROUTE line and the
  rows still "to do", and keeps the rows already done. The same rule covers D1 to D2.
- Each bundle carries TIER and MODE, approved with it. Hands-on at every tier; delegate with checkpoints at Tiers 1
  and 2; delegate at Tier 1. Both briefs carry MODE; the engineer chooses it when confirming. A bundle without MODE
  runs hands-on.
- Every stop rule is unchanged. A mode changes only when the build waits for a person. The review of a recipe commit
  stops for the person in every mode.
- The progress note gains a STATUS line (`doing`, `paused: …`, `stopped: <reason>`, `done`) and is committed on its own
  before the slice's other commits, so a recipe commit starts on a clean tree.
- A starter script, `run_slices.py`, runs one fresh headless session per approved slice, in the order the person
  names. It refuses hands-on slices and modes above their tier before any session starts, stops at the first slice
  that does not end done, and never pushes. The person reviews the diffs at the end.

## Consequences
- aidlc 4.3.0.
- Bundles written before 4.3 keep today's behaviour.
- The runner's default command is Claude Code's headless mode with edits accepted. Other tools pass `--command` and
  `--prompt`. The starter settings keep `git push` on "ask", which a headless session cannot answer.
- The eval case for delegate at Tier 2 needs Bash, so it runs where the Bash sandbox runs.
