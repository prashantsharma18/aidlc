<!-- aidlc template: pr-description -->
# [{{KEY}}] {{SLICE}}

## For the reviewer
- **Asked of:** A code owner who neither wrote nor pushed the change, to approve the merge; a required specialist can block; they read the decision log below with the spec, the plan and the code, and at Tier 1 on F1, D2 and C they check the route under Traceability (ADR 0027)
- **Record it:** In the pull request. The code owner's approval in the review tool is the record; the AI writes nothing for it
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

## Summary
{{one or two sentences: what this pull request does, and why}}

## What changed
- {{change}}: {{the criterion it serves}}

## Not changed
- {{what deliberately did not change}}

## Questions for the reviewers
- {{one concrete question per reviewer or specialist}}

## Decisions made while building
The decision log, copied from each progress note's "Decisions made while working (for the PR)", grouped by the owner
each row names (ADR 0027). A row is a pointer for its owner, never an approval: no row waits. The code owner reads the
log with the spec, the plan and the code, and may bring in another owner as a reviewer; anyone who disagrees with a
row raises a review finding. Write `- none` when no slice logged a judgement call. Write `- none` only when every progress note's log reads `- none`.

**Owner: {{who owns the area}}**
- {{commit}} · {{decision}} · {{why}} · {{evidence: file:line, a test or a command}}

## Traceability
- **Work item:** {{key, title}} · Tier {{n}}
- **Route:** {{the story index's ROUTE line, with its facts}} (shown at Ready; the tech lead owns it; at Tier 1 on F1, D2 and C, the code owner checks it here, ADR 0027)
- **Spec:** {{version, clarifications}}
- **Plan:** plan.md {{version}} ({{commit}}), approved by {{who}} on {{YYYY-MM-DD}}, {{how it was confirmed}}
- **Bundle or brief:** {{path}} at its approval commit
- **Recipe:** {{sha, tool@version, and the recipe check's result from the evidence file}}, or none
- **Evidence:** {{link to the evidence table from the trusted run; what was proved only in CI}}
- **Assumptions:** {{assumption, or none}}

## Rollback
{{how; or "nothing at merge: the flag stays off"}}
