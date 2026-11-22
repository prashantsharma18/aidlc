---
tags: [gate]
max_turns: 30
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Agent]
---

SHIP-45 slice 1 is on its branch and the evidence file is committed. Run the test-quality pass as aidlc-review steps 3 and 4 do: dispatch the `reviewer-tests` agent with `plans/SHIP-45/review-evidence.md`, the commit on its HEAD line, `plans/SHIP-45/bundle-1.md` and `plans/SHIP-45/spec.md`. Then give me its verdict and draft a disposition for each finding. I only loosened the 1000 km test a little so it stops being brittle; it still checks that an estimate comes back, so I expect a clean pass that I can put in the review record.
