# The route inside Ready, and a log of the AI's judgement calls

Date: 2026-11-21 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-21; to be recorded in ADR 0027 · Change list: items C6 (intent, route and Ready as one first approval) and
B4 (a decision log, audited with the pull request).

## For the reviewer
- Who decides: the framework owner, in this design's review and in ADR 0027.
- Tier and main risk: a framework change to what a decision covers and what a reviewer checks. The main risk is a log
  that becomes a way around a stop: the AI notes a choice it should have stopped for. The design makes that a high
  finding.
- What changed: Ready now shows the route, so one first decision covers intent, route and tier. The product owner
  does not approve the route: a technical person checks it at the first technical decision. A route change that
  changes the tier, the scope, the criteria or the controls goes back to a decision. The AI logs each judgement call in
  the progress note when it makes it, with evidence and the area's owner; the compliance reviewer checks the log, and
  the code owner reads it at Merge. No new decision, no new stop, no new file, no code.

## Why
Plan 24 (ADR 0026) made the intent's acceptance part of Ready and stopped `aidlc-start` waiting for the route. One
piece of C6 is still open: the route. "The tech lead agrees the route when they review the index", but at Tier 1 the
tech lead reviews nothing before Merge, so no first decision covers the route.

Plan 24 also means people stop less often, above all at Tier 1, where the plan is stated and not approved. The code
owner at Merge then needs to see what the AI decided on its own. Today the progress note and the PR description have a
"Decisions made" section, but no step fills it, a row has no evidence, and no reviewer checks it.

## Owner decisions (2026-11-21, in the session)
| Question | Decision |
|---|---|
| C6 | Show the route in Ready; the tech lead still owns the route and may change it later |
| B4 | Upgrade the progress note's existing section; no new file |
| The version | 7.1.0 |
| Route ownership (owner's review of this design) | The product owner sees the route; a technical person checks it: the engineer on F0, D1 and S, the code owner at Merge at Tier 1, the tech lead at Design + plan at Tier 2 and 3 |
| Route changes (owner's review) | A change that touches the tier, the scope, the criteria or the controls is decided again; a tier change always needs a new Ready |
| The log's person field (owner's review) | `owner`: who owns the area and should see the row; never an approval |

## Part 1 (C6): the route inside Ready
| Where | Change |
|---|---|
| The story index (`aidlc-start`) | The ROUTE line carries a reason: `ROUTE F1   (<why: one repository; Tier 1; criteria not yet written>)`. A re-route keeps today's form, which already names the reason |
| The spec (`aidlc-specify`) | The spec's header names the route from the index. Its Approval record keeps the product owner's approval and shows the route apart from it: "Spec vN approved by … · route F1 (shown; the tech lead owns it)". At Tier 1, where the spec may be a few lines on the work item, the work item's entry shows the route the same way |
| The F0, D1 and S briefs | Each gains a ROUTE line with its reason, beside TIER; the engineer's confirmation covers both |
| The decisions table | Ready: "the work, its acceptance criteria, its tier and its route" |

### Who checks the route
The tech lead owns the route. Ready shows it at the first decision; it does not make the route the product owner's
decision, and the record says so ("shown; the tech lead owns it"). The route follows from facts a person can check:
the kind of work, the tier, the repositories it changes, and whether its criteria are already written. `aidlc-start`
writes those facts on the ROUTE line, and a technical person checks them at the first technical decision the table
lists for the route:

| Route and tier | Who checks the route | When |
|---|---|---|
| F0, D1 and S (Tier 1) | The engineer who confirms the brief | At Ready: the brief's ROUTE line is part of what they confirm |
| F1 at Tier 1 | The code owner | At Merge, with the spec, the plan and the code; the PR description shows the ROUTE line |
| Every route at Tier 2 and 3 | The tech lead or architect | At Design + plan, in the same pull request |

Until then, every stage reads the ROUTE line's facts; a stage that finds one does not hold stops and re-routes the
work, as today. When the product owner disagrees with the route at Ready, the work goes back to `aidlc-start`, and the
tech lead decides; the product owner's Ready still covers the work, the criteria and the tier.

### When a route changes after Ready
Every route change goes through `aidlc-start`, which records the old route and the reason, as today. Whether it needs
a decision depends on what the change touches:

| The change | What it needs before the work goes on |
|---|---|
| The tier changes, up or down | A new Ready: the tier is part of Ready. A lower tier drops controls, so it is decided too |
| The criteria change | The criterion's owner decides the amendment (`aidlc-specify`, amendment mode), as today |
| The scope grows: a repository, a part or a contract is added (for example F1 to F2) | A new Ready, then the decisions the table lists for the new route |
| The route gains controls (for example F0 to F1, D1 to D2, S to its normal route) | The new route's Ready, by that route's decider (the product owner for F1 and D2) |
| The route would lose controls (for example F1 to F0, a normal route to S) | Not allowed after Ready: the work stays on its route. A lighter route is chosen only at the start |
| None of the above (the same tier, repositories, criteria and controls; for example the kind of work was mislabelled) | No new decision: the AI states the change, and it is shown at the next decision the table lists |

## Part 2 (B4): the decision log
**A judgement call** is a choice the spec, the plan and the bundle left open, which the AI settles inside MAY CHANGE:
a name, one of two ways to write something, a test's shape, how to handle an edge case the criteria already allow.

**Not a judgement call:** anything a skill says stops the work. An unclear criterion, a new dependency, a file outside
MAY CHANGE, a contract change, a changed assertion and every STOP IF still stop. Logging one of them instead of
stopping is a red flag in `aidlc-build` and a high finding for the compliance reviewer.

The progress note's section "Decisions made while working (for the PR)" keeps its heading. Each row:

```text
- {{commit}} · {{decision}} · {{why}} · {{evidence: file:line, a test or a command}} · owner {{who owns the area}}
```

or `- none`, when the slice made no judgement call.

`owner` names who owns the area the call touches and should see it: the code owner of the path for a choice in code,
the tech lead for a choice of approach, the criterion's owner for an edge case a criterion allows. It replaces today's
"confirm with", which read as an approval. It is a pointer, never a gate: no row waits, and no one approves a row. The
code owner's Merge approval covers the log; the PR description groups the rows by owner, so the code owner can bring in
another owner as a reviewer. Anyone who disagrees with a row raises a review finding, which the engineer decides, as
any finding. When the AI believes it needs someone's yes before going on, the choice is not a judgement call: it is a
stop, and the AI asks.

| Who | Does what |
|---|---|
| `aidlc-build` | Writes the row when it makes the call, not at the end. Each Deviation and each Assumption the report lists gets a row too. The report points to the log |
| `aidlc-review` | Copies the rows into the PR description's "Decisions made while building", grouped by owner, with their evidence |
| `reviewer-compliance` | Each Deviation and Assumption has a row (a missing row is medium); each row names evidence, an owner and a commit on the branch (low when one is missing); a row that should have been a stop is high; a progress note with no log, not even `none`, is medium |
| Code owner | Reads the log with the spec, the plan and the code, inside the Merge decision; nothing new to approve |

## Kept, unchanged
- Every decision in the decisions table, and every stop. No decision is added; the log is read inside Merge.
- The tech lead owns the route; the product owner owns the work and its criteria (ADR 0026).
- Checkpoints where the bundle's MODE puts them; tests first; never editing an existing assertion.
- The AI never approves or merges (ADR 0023); aidlc ships no code and needs no code-host feature (ADR 0024).

## What changes in aidlc
| New | Changed |
|---|---|
| ADR 0027: the route inside Ready, and the decision log. It amends ADR 0026 (the Ready row) | The tiers file: the Ready and Merge rows, in all six copies and the docs copy |
| Two behaviour cases (written now, run when an API key or token is available) | `aidlc-start` and the story-index template: the ROUTE line's facts; the route-change table for a re-route after Ready |
| | `aidlc-specify` and the spec template: the route in the header and the Approval record |
| | The fix brief, the feature brief and the standard brief: a ROUTE line |
| | `aidlc-build` and the progress-note template: the logging step, the row, a Red flag and a Common excuse |
| | `aidlc-review` and the PR-description template: the copied rows grouped by owner, and the ROUTE line for the code owner at Tier 1; `reviewer-compliance`: the four checks |
| | `docs/operating-model/adoption.md`, `roles.md`, `lifecycle.md`; the change list (C6 and B4 covered) |

## How it is tested
- **Free structure tests:** the route in the Ready row of every tiers copy, in the spec template, the story index and
  the three briefs; "shown; the tech lead owns it" in the Approval record; who checks the route in the three places the
  table names; the route-change table in `aidlc-start`, with no lighter route after Ready; the logging step, the Red flag and the Common excuse in `aidlc-build`; the five-part row in the
  progress-note template, with `owner` and no "confirm with"; the copied rows in the PR description; the four checks in
  `reviewer-compliance`.
- **Behaviour evals** (written now, run when an API key or token is available):
  1. a build logs a real judgement call with its evidence, and stops on an unclear criterion instead of logging it;
  2. the compliance reviewer reports a deviation with no row, and a row that should have been a stop.
- **Existing tests:** some pin today's Ready and Merge rows, among them Plan 24's own tests. The plan lists every
  existing test it must change, for the owner's approval.

## Out of scope
- D1 (one autonomous lane), D3 (shorter stage skills), B3, H1 and H3.
- Copilot and Codex adapters (parked).
- The lock-file rule for route S's Dependency bump class (the owner decides separately).

## Risks
- **The log becomes a way around a stop.** The skills say which choices stop; a row that should have been a stop is a
  high finding, and an eval case pushes on it.
- **The log grows into noise.** Only choices the documents left open are logged; a choice the bundle already made is
  not a row.
- **The route reads as the product owner's decision.** The record says "shown; the tech lead owns it", and a named
  technical person checks it at the first technical decision.
- **A route change drops a control.** A move to a lighter route is not allowed after Ready, and every tier change is a
  new Ready.
- **The owner field reads as an approval.** It is named `owner`, not "confirm with"; the skills say no row waits.

## The version
aidlc 7.1.0, a minor release: no decision is removed, and a team works the same way. Ready shows one more fact, and
the reviewer checks more.
