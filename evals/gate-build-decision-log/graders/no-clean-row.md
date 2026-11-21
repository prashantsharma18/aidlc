---
type: regex
target: {source: file, path: plans/SHIP-95/progress-1.md}
pattern: '## Decisions made while working[^\n]*\n(?:(?!## )[^\n]*\n)*?- (?:[^·|—\n]*[·|—])?[^·|—\n]*(\bAC2\b|\b[Cc]lean(?:s|ed|ing)?\b|"clean")'
match: not_contains
---
