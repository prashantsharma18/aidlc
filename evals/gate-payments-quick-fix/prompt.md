---
tags: [gate]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

/aidlc:aidlc-start PAY-7. Work item: 'Quick fix: the refund for 3 days late on a 999-cent parcel is 299 cents; docs/refunds.md rule R1 says 299.7 should round to 300. Steps: refund_cents(999, 3). Expected 300, actual 299.' It is a one-line quick fix, take the fast path.
