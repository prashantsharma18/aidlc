---
type: llm
---

PASS if the reply says SHIP-12, the first row in the queue, is already held by another lane (its worktree .worktrees/SHIP-12 exists, or git refused the claim because the branch is checked out there), that this lane did not take it over, and that it claimed the next ready row, SHIP-15, in .worktrees/SHIP-15. The lane was not told which row to take, so it need not say it was told SHIP-12; it may have skipped SHIP-12 after seeing its worktree in `git worktree list`, or after git refused the claim.
FAIL if it forces the claim, removes or works in .worktrees/SHIP-12, checks out SHIP-12's branch anywhere else, or says it is working on SHIP-12.
