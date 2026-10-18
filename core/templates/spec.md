---
id: spec
title: Specification
stage: specify
guide: ["5.2", "5.7", "5.8", "5.9"]
fields: [KEY, TITLE, OWNER, TIER]
---
# {{KEY}} · {{TITLE}} · specification

Spec owner: {{OWNER}} · Tier: {{TIER}} · Version: v1

## Outcome
<what changes, for whom, and why>

## Scope and non-goals
In: <...>
Non-goals: <...>

## Rules and constraints
- <rule, judgeable true or false> (set by <who>)

## Context and contracts
<interfaces and data touched, with their consumers; a contract change for someone else goes to design>

## Acceptance criteria
AC1 <one observable behaviour, with numbers, including the refusal>
    Given <precondition>
    When  <trigger>
    Then  <outcome>

## Edge cases (each with a decided behaviour and its decider)
E1 <condition> -> <decided behaviour> (decided by <who>)

## Verification
| Criterion | How it will be proved |
|---|---|
| AC1 | <test level and name, named at planning> |

## Open questions
| ID | Question | Owner | Blocks |
|---|---|---|---|

## Definition of Ready (Tier {{TIER}})
- [ ] Clear actor, observable behaviour, known constraints, examples, testable criteria
- [ ] Tier 2+: non-goals written; every edge case decided; contract changes agreed with consumers; questions owned
- [ ] Tier 3: specialist reviewed; every risk decision names its decider; data in the agent's context classified

## Approval record
Spec <version> approved by <owner> on <YYYY-MM-DD>. Reviewed by <specialist>.
Amendments: <date, criterion, reason, decider>
