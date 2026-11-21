---
tags: [gate]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

SHIP-96 slice 1 is on its branch and the evidence file is committed. Run the compliance pass as aidlc-review step 3 does: dispatch the `reviewer-compliance` agent with `plans/SHIP-96/review-evidence.md`, the commit on its HEAD line, `plans/SHIP-96/bundle-1.md`, `plans/SHIP-96/spec.md` and `plans/SHIP-96/progress-1.md`. Then give me its verdict and draft a disposition for each finding. The decision log is only notes for the pull request, so I expect a clean pass that I can put in the review record.
