<!-- aidlc template: incident -->
# {{KEY}} · incident record

- **Title:** {{title}}
- **Severity:** {{severity}}
- **Impact:** {{who, what, from and to}}
- **Contained:** {{action}}. Undo: {{step and its trigger}}
- **Cause:** {{confirmed cause}} (confirmed by {{person}}, {{time}}, {{in the session, or how it was checked}})

## Timeline
- {{hh:mm}} {{event}}

## Actions
| ID | Action | Owner | Due |
|---|---|---|---|
| A1 | {{action}} | {{owner}} | {{YYYY-MM-DD}} |

## Prevention
- {{lesson}} -> {{test, eval case, context, guardrail, review checklist or measure}} -> {{where it went}}

## Measures
- {{counted as a failed change? rework?}}

The record closes only when every prevention change is merged or explicitly declined.
