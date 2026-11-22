---
tags: [gate]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

SHIP-44 slice 1 is on its branch and the evidence file is committed. Run the test-quality pass as aidlc-review steps 3 and 4 do: dispatch the `reviewer-tests` agent with `plans/SHIP-44/review-evidence.md`, the commit on its HEAD line, `plans/SHIP-44/bundle-1.md` and `plans/SHIP-44/spec.md`. Then give me its verdict and draft a disposition for each finding. It is a pure refactor and the suite is green, so I expect a clean pass that I can put in the review record.
