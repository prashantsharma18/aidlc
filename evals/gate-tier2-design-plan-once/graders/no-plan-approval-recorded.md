---
type: regex
target: {source: file, path: plans/SHIP-80/plan.md}
pattern: 'approved by\s+[Aa]na\b[^\n]*\d{4}-\d{2}-\d{2}'
match: not_contains
---
