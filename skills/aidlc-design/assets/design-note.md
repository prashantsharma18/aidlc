<!-- aidlc template: design-note -->
# {{KEY}} · design note

1 Does it change the system's shape (new service, store, dependency, integration pattern)?  <yes|no — why>
2 Does it move a boundary (data ownership, security pattern, shared-module behaviour, new module dependency)?  <yes|no — why>
3 Does it change a contract someone outside the team relies on?  <yes|no — why>

Uncertain counts as yes.

OUTCOME  <"none needed" with reason | decisions, each with its owner -> decision frame>
RECORDED BY  <tech lead or architect>, <YYYY-MM-DD>
APPROVED  <ADR now Accepted · contract version and its tests · boundary rules · approvers (tech lead or architect; consumers for a contract), YYYY-MM-DD>
