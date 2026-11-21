<!-- aidlc template: design-note -->
# {{KEY}} · design note

## For the reviewer
- **Asked of:** The tech lead or architect, to approve the design or record "none needed"; consumers approve a contract change; Tier 3 adds the specialists. At Tier 1 nobody: the AI states "none needed" in the plan, and the code owner sees it at Merge (ADR 0026)
- **Record it:** On the APPROVED or RECORDED BY line below, and on the work item with this note's version and commit (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
1 Does it change the system's shape (new service, store, dependency, integration pattern)?  <yes|no — why>
2 Does it move a boundary (data ownership, security pattern, shared-module behaviour, new module dependency)?  <yes|no — why>
3 Does it change a contract someone outside the team relies on?  <yes|no — why>

Uncertain counts as yes.

OUTCOME  <"none needed" with reason | decisions, each with its owner -> decision frame>
UI REFERENCE  <Figma link and version | wireframes/<screen>.md vN, approved by <product owner>, <how it was confirmed> | none: no new screen or flow>
RECORDED BY  <tech lead or architect>, <YYYY-MM-DD>, <how it was confirmed> | stated at Tier 1; the code owner sees it at Merge
APPROVED  <ADR now Accepted · contract version and its tests · boundary rules · approvers (tech lead or architect; consumers for a contract), YYYY-MM-DD, how it was confirmed>
```
