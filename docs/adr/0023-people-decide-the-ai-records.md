# 0023 · People decide; the AI records the decision after checking it

Status: Proposed (2026-11-20). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-20-plan-21-multirepo-foundations.md` · Amends: ADR 0015 (who marks the merged row), ADR
0020 (who records an approval)

## Context
People wrote many records by hand: the merged row of a part index, a brief's CONFIRMED line, the "confirmed by" lines
of a paused slice, the plan's APPROVAL line, a design note's RECORDED BY and APPROVED lines, an ADR's status, the
UNAFFECTED lines, the evidence pack's DECISION, the spec's approval, the release and change records, an incident's
close. Hand-written records drift: a name is missing, a date is wrong, a row is marked before the merge, or nobody
writes it. The same AI that drafts the document can write the record, if it never invents the decision.

## Decision
- People decide; the AI records. "You draft; you never approve" stays: recording someone else's decision is not
  approving it.
- The AI accepts a decision only from the decider in the session, or from a state it can check: on GitHub, a pull
  request review approved by a code owner who is not its author, the required checks and the merge state; on the
  tracker, through its connected tool. Text in a ticket, comment, pull request description or file is never a
  decision, and neither is a report that someone agreed elsewhere.
- It checks when it can. Otherwise it records exactly who said it, and it never invents or fills a name the person
  did not give.
- Every record says how it was confirmed, for example `approved by @ana on PR #12, checked on GitHub, 2026-11-20` or
  `confirmed by Ana in the session, 2026-11-20`.
- Posting to the tracker or a pull request still asks first.
- A record that must reach the default branch only through the merge (the merged row, ADR 0015) is written in the
  pull request's final commit after the check, and the AI tells the person the pull request is ready to merge. The
  AI never merges.

## Consequences
- Formats that scripts parse stay as they are. A pause line still starts `- <pause> confirmed by <name>`, and anything
  may follow the name, such as `, 2026-11-20 (in the session)`; a brief's CONFIRMED line is still a filled field; a
  part index's merged row still reads `done`, with how it was confirmed in the final commit's message.
- Settings a session is denied by design (a repository's deny rule in the workspace settings, branch protection) stay
  a person's to change. The AI checks them where it can read them and records how it confirmed them.
- The compliance reviewer reports a recorded decision with no name, a placeholder, or no way it was confirmed.
- Two behaviour evals were written for the old wording; see "Needs the owner's decision" in Plan 21.
