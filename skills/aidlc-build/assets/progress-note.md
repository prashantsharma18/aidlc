<!-- aidlc template: progress-note -->
# Progress · {{KEY}} · {{SLICE}}

Session state, not memory: it lets a fresh session resume from the record.
File: `plans/<KEY>/progress-{{SLICE}}.md`, committed on its own as the slice's first commit, then with the slice; the
compliance reviewer and the next session read it.

```text
STATUS      doing   (doing | paused: {{checkpoint n | recipe review}} | stopped: {{reason}} | done)
MODE        {{the bundle's MODE; hands-on when the bundle has none}}
TESTS BEFORE {{passed}} passed, {{failed}} failed, {{skipped}} skipped at {{commit}}, before any change
```

## Restatement (delegate modes)
- {{goal, criteria covered, MAY CHANGE and STOP IF, with file references}}

## Pauses confirmed (by the person)
The person confirms each pause by telling the AI, which writes the line with the name given (ADR 0023).
- {{restatement | checkpoint n | recipe review}} confirmed by {{name}}, {{YYYY-MM-DD}} ({{in the session}})

## Session plan
- [ ] 1 {{step}} — files: {{...}} — check: {{...}}

## Skills loaded
- {{plugin:skill}} — plugin version {{x.y.z}}

## Deviations
- {{a practice loaded that the bundle does not name, or another departure from the bundle}} — {{why}}

## Amended assertions seen red
- {{test}} — failed against the old code: {{the failing line of the output}} | none

## Decisions made while working (for the PR)
- {{decision}} — {{why}} — confirm with {{who}}

## Assumptions
- {{assumption}} — {{confirmed in code at file:line | flagged for reviewer}}

## Context gaps noticed (B5)
- {{gap | wrong | ignored | not context}}: {{what the agent did not know}}
