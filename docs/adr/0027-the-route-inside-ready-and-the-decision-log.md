# 0027 · The route inside Ready, and the decision log

Status: Proposed (2026-11-21). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-21-route-in-ready-and-decision-log.md` · Plan:
`docs/plans/2026-11-21-plan-25-route-in-ready-and-decision-log.md` · Amends: ADR 0026 (the Ready row of the
decisions table)

## Context
ADR 0026 made the intent's acceptance part of Ready, so one first decision covers the work, its criteria and its
tier. The route was left out. `aidlc-start` said the tech lead agrees the route when they review the index, but at
Tier 1 the tech lead reviews nothing before Merge, so no decision covered the route.

ADR 0026 also means people stop less often, above all at Tier 1, where the plan is stated, not approved (except a
plan with independent slices). The code owner at Merge then needs to see what the AI decided on its own. The progress
note and the pull request description had a "Decisions made" section, but no step filled it, a row had no evidence,
and no reviewer checked it. Its "confirm with" read as an approval.

## Decision
- Ready shows the route. The decisions table's Ready row reads "the work, its acceptance criteria, its tier and its
  route". The product owner sees the route and does not decide it; the tech lead owns it and may change it later.
  The spec's Approval record says so: "Spec vN approved by … · route F1 (shown; the tech lead owns it)". At Tier 1,
  where the spec may be a few lines on the work item, the work item's entry shows the route the same way.
- The ROUTE line carries the facts the route follows from: the kind of work, the tier, the repositories it changes,
  and whether its criteria are already written. The F0, D1 and S briefs gain a ROUTE line beside TIER, and the
  engineer's confirmation covers both.
- Who checks the route: a technical person, at the first technical decision the decisions table lists for the route.
  On F0, D1 and S, the engineer who confirms the brief, at Ready. On F1, D2 and C at Tier 1, the code owner, at Merge,
  where the pull request description shows the ROUTE line (for a plan with independent slices, first the tech lead who
  approves it). At Tier 2 and 3, the tech lead or architect, at Design +
  plan, in the same pull request. On route G, the tech lead or architect who approves `new-system.md`. Until then
  every stage reads the ROUTE line's facts, and a stage that finds one does not hold stops and re-routes the work.
  When the product owner disagrees with the route at Ready, the work goes back to `aidlc-start`, and the tech lead
  decides; the product owner's Ready still covers the work, the criteria and the tier.
- A route change after Ready goes through `aidlc-start`, which records the old route and the reason. A tier change,
  up or down, needs a new Ready. A criteria change is the criterion's owner's amendment. A scope that grows (a
  repository, a part or a contract) needs a new Ready, then the new route's decisions. A route that gains controls
  needs the new route's Ready, by that route's decider. A route that would lose controls is not allowed after Ready:
  a lighter route is chosen only at the start; before Ready nothing is approved yet, so `aidlc-start` may still re-route to a lighter route. Any other change needs no new decision: the AI states it, and it is
  shown at the next decision the table lists.
- The decision log. A judgement call is a choice the spec, the plan and the bundle left open, which the AI settles
  inside MAY CHANGE: a name, one of two ways to write something, a test's shape, how to handle an edge case the
  criteria already allow. `aidlc-build` writes a row for each in the progress note's "Decisions made while working
  (for the PR)" when it makes the call, and a row for each Deviation and each Assumption: the commit, the decision,
  why, the evidence (file:line, a test or a command) and `owner`, who owns the area and should see the row; or
  `- none`. Anything a skill says stops the work is a stop, never a row. `owner` is a pointer, never a gate: no row
  waits, and no one approves a row. When the AI believes it needs someone's yes before going on, it is a stop, and
  the AI asks.
- `aidlc-review` copies the rows into the pull request description, grouped by owner, so the code owner can bring in
  another owner as a reviewer; anyone who disagrees with a row raises a review finding. The compliance reviewer
  checks the log: a Deviation or Assumption with no row is medium; a row with no evidence, owner or commit on the
  branch is low; a row that should have been a stop is high; a progress note with no log, not even `none`, is
  medium. The code owner reads the log with the spec, the plan and the code, inside Merge.
- This amends ADR 0026's Ready row. No decision is added or removed, and no stop; the AI never approves or merges (ADR 0023), and aidlc still ships no code and
  needs no code-host feature (ADR 0024).

## Consequences
- A named technical person checks the route before the code merges, on every route, with no new stop.
- A log can become a way around a stop. The skills say which choices stop; a row that should have been a stop is a
  high finding, and a behaviour case pushes on it.
- A log can grow into noise. Only choices the documents left open are logged; a choice the bundle already made is not
  a row.
- The evidence file names the branch's commits (a COMMITS line), so the compliance reviewer, which runs no command,
  can check that a row's commit is on the branch.
- `scripts/test_route_and_log.py` holds the structure checks; two behaviour cases under `evals/` hold the behaviour,
  run when a key or token is available. The existing tests that pinned the old wording change only as the plan's
  "Needs the owner's decision" lists.
