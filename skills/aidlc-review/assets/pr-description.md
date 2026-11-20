<!-- aidlc template: pr-description -->
# [{{KEY}}] {{SLICE}}

## For the reviewer
- **Asked of:** A code owner who neither wrote nor pushed the change, to approve the merge; a required specialist can block
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
- {{decision}}: confirm with {{who}}

## Traceability
- **Work item:** {{key, title}} · Tier {{n}}
- **Spec:** {{version, clarifications}}
- **Plan:** plan.md {{version}} ({{commit}}), approved by {{who}} on {{YYYY-MM-DD}}, {{how it was confirmed}}
- **Bundle or brief:** {{path}} at its approval commit
- **Recipe:** {{sha, tool@version, and the recipe check's result from the evidence file}}, or none
- **Evidence:** {{link to the evidence table from the trusted run; what was proved only in CI}}
- **Assumptions:** {{assumption, or none}}

## Rollback
{{how; or "nothing at merge: the flag stays off"}}
