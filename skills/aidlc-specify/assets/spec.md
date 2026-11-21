<!-- aidlc template: spec -->
# {{KEY}} · {{TITLE}} · specification

Spec owner: {{OWNER}} · Tier: {{TIER}} · Route: {{ROUTE, from the story index's ROUTE line; shown, the tech lead owns it}} · Version: v1

## For the reviewer
- **Asked of:** The spec owner, to approve the criteria and decide every edge case; a specialist reviews at Tier 3; the route is shown with the spec, and the tech lead owns it (ADR 0027)
- **Record it:** On the work item: "Spec vN approved by name · route F1 (shown; the tech lead owns it)" (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

## Outcome
{{what changes, for whom, and why}}

## Scope and non-goals
In: {{...}}
Non-goals: {{...}}

## Rules and constraints
- {{rule, judgeable true or false}} (set by {{who}})

## Context and contracts
{{interfaces and data touched, with their consumers; a contract change for someone else goes to design}}

## Acceptance criteria
AC1 {{one observable behaviour, with numbers, including the refusal}}
    Given {{precondition}}
    When  {{trigger}}
    Then  {{outcome}}

## Edge cases (each with a decided behaviour and its decider)
E1 {{condition}} -> {{decided behaviour}} (decided by {{who}}, {{how it was confirmed}})

## Verification
| Criterion | How it will be proved |
|---|---|
| AC1 | {{test level and name, named at planning}} |

## Open questions
| ID | Question | Owner | Blocks |
|---|---|---|---|

## Definition of Ready (Tier {{TIER}})
- [ ] Clear actor, observable behaviour, known constraints, examples, testable criteria
- [ ] Tier 2+: non-goals written; every edge case decided; contract changes agreed with consumers; questions owned
- [ ] Tier 3: specialist reviewed; every risk decision names its decider; data in the agent's context classified

## Approval record
Spec {{version}} approved by {{owner}} on {{YYYY-MM-DD}}, {{how it was confirmed: checked on the work item, or in the session}} · route {{ROUTE}} (shown; the tech lead owns it). Reviewed by {{specialist}}.
Amendments: {{date, criterion, reason, decider}}
