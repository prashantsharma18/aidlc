<!-- aidlc template: criteria -->
# {{KEY}} · part {{PART}} · acceptance criteria (read-only copy)

## For the reviewer
- **Asked of:** The tech lead, with the plan: that this copy holds the part's own criteria and non-goals, word for word
- **Record it:** With the plan's approval on the work item; the copy changes only when the plan does
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

This is a copy. The spec in the home repository is the original, and only its owner changes it. The part's CI, its
reviewers and its AI review read this copy, so they never need the home repository. The story status command reports
any line here that is not in the spec at the commit below.

```text
SOURCE     {{home repository}} stories/{{KEY}}/spec.md @ {{home commit}} (spec v{{n}})
```

## Acceptance criteria
{{each criterion this part's tests prove, copied word for word with its Given, When and Then lines}}

## Edge cases
{{each edge case this part handles, copied word for word with its decided behaviour and its decider}}

## Non-goals
{{the spec's Non-goals line, copied word for word}}
