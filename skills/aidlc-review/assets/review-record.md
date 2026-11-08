<!-- aidlc template: review-record -->
# Review · {{KEY}} · {{PR}}

## For the reviewer
- **Asked of:** The engineer, to decide each finding (high and medium block the merge); the reviewer named below, to give the DECISION; then a code owner, to approve
- **Record it:** Each finding's disposition under Findings; the reviewer's DECISION line below; the approval in the pull request
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
DECISION  {{approve | revise (back to build) | reject (back to plan or spec owner)}}  {{date}}
```
