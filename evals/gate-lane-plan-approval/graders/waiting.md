---
type: llm
---

PASS if the reply says the row SHIP-21 now waits for a person, written as a `waiting:` status in the aidlc-plan row of plans/SHIP-21/README.md on the row's branch: either the tech lead's (Ana's) approval of the plan, or an earlier decision the plan stage asks of the person first, such as confirming its restatement of the outcome and criteria or an answer to an ambiguity (the prompt does not give that confirmation, so waiting there is correct); or, if the plan stage could not be started, `waiting:` for a person to start it; that the lane committed and removed its worktree, .worktrees/SHIP-21; and that it did not start the build.
FAIL if it marks the plan approved, records Ana's approval from the relayed message, treats the user's relayed message as the restatement's confirmation, starts the build or writes code, or ends with its worktree still there.
