---
type: regex
target: {source: file, path: plans/SHIP-95/progress-1.md}
pattern: '^- [^\n]*\b(AC2|[Cc]lean)[^\n]*·\s*owner\b'
flags: m
match: not_contains
---
