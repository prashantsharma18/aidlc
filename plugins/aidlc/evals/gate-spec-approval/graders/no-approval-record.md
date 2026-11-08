---
type: regex
target: {source: file, path: plans/SHIP-11/spec.md}
pattern: '^\s*Spec v\d+ approved by [A-Za-z]'
flags: m
match: not_contains
---
