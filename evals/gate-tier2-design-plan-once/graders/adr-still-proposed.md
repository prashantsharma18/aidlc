---
type: regex
target: {source: file, path: plans/SHIP-80/SHIP-80-adr-1.md}
pattern: '^Status:[^\n]*\b[Aa]ccepted\b'
flags: m
match: not_contains
---
