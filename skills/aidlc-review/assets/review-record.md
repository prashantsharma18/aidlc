<!-- aidlc template: review-record -->
# Review · {{KEY}} · {{PR}}

## For the reviewer
- **Asked of:** The engineer, to decide each finding (high and medium block the merge); the reviewer named below, to give the DECISION; then a code owner, to approve
- **Record it:** Each finding's disposition under Findings, and the reviewer's DECISION line below (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023). The approval itself is the code owner's, in the review tool; the AI writes only the DECISION line and the dispositions, never the approval
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

Reviewer: {{name, role}} — not the author, not the engineer who directed the agent, not the pushing identity.
Order followed: context -> evidence -> tests (against criteria) -> diff (before the summary) -> risk

| Dimension | Notes |
|---|---|
| Correctness and completeness | |
| Safety and security | |
| Architecture fit and maintainability | |
| Test meaning and evidence | |
| Operational fit | |

Findings (high and medium block the merge until fixed or dismissed with a reason; low may be dismissed with a reason):
[high]     {{...}}
[medium]   {{...}}
[low]      {{...}}
[question] {{...}}

Specialist reviews required by the tier: {{role}} — reviewed {{what}} — {{outcome}}
```text
DECISION  {{approve | revise (back to build) | reject (back to plan or spec owner)}} at {{commit}}  {{date}}  {{reviewer, and how it was confirmed}}
```

## Reviewer verdicts
Each verdict counts only from someone who did not write the change: one of the `reviewer-*` agents, dispatched with
the evidence file and the story documents it names, never the author's conversation; or a person other than the
engineer who ran the session. It names the commit it judged. A later commit that changes a path outside `plans/<KEY>/` voids it.
- {{reviewer-bug | reviewer-security | reviewer-compliance | reviewer-tests | person}}: {{no findings | the number of findings}} at {{commit}}
