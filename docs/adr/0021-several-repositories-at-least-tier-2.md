# 0021 · A story across several repositories is at least Tier 2

Status: Accepted (2026-11-20; confirmed by the framework owner in the session). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-19-plan-20-gates-that-hold.md` · Change list: F12

Amended by ADR 0024 (2026-11-20): see the last section.

## Context
The tier table let a two-repository change with one owner and no contract change be Tier 1. Once Tier 1 can merge on
its own (change list C2), part 1 could ship while part 2 fails: half a story in production with no release decision.

## Decision
- A story that changes two or more repositories is at least Tier 2: its parts never merge on their own, and its
  release has a release approver.
- `check_plan.py` reports a part (its index's LEVEL reads "part n of m") whose bundle is Tier 1.

## Consequences
- Multi-repository parts use hands-on or delegate with checkpoints, never plain delegate.

## Amended by ADR 0024 (2026-11-20)
- `check_plan.py` is removed. The plan's checklist holds the rule (a part of a story across several repositories
  is at least Tier 2), and the tech lead checks it with the plan.
