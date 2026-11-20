# 0020 · At Tier 2 and 3, approved documents merge first

Status: Accepted (2026-11-20; confirmed by the framework owner in the session). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-19-plan-20-gates-that-hold.md` · Change list: A2 · Amends: ADR 0015 (where approvals live)

## Context
Approvals before code were text lines (`CONFIRMED`, "approved by") and records on the work item. Nothing a script could
check tied a build to an approved bundle; `run_slices.py` and `aidlc-build` never checked approval.

## Decision
- The approval is still recorded on the work item, with the document's version and commit.
- At Tier 2 and 3, the spec, the design, the plan and its bundles merge to the default branch first, in their own
  pull request, which the approver approves under CODEOWNERS. The commit on the work item is that merge.
- A build at Tier 2 and 3 starts only from a bundle identical to the copy on the default branch. `run_slices.py` and
  `check_slice.py` check it; a code pull request that adds or changes such a bundle fails the slice check.
- At Tier 1, the plan and bundle (or the brief) travel with the code, as before; the code owner approves them with it.

## Consequences
- Two pull requests per part at Tier 2 and 3: the documents, then the code. The documents pull request is small and
  fast to review.
- A re-plan is a new documents pull request, never an edit inside the code pull request.
