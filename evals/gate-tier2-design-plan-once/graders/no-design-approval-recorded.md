---
type: regex
target: {source: file, path: plans/SHIP-80/design-note.md}
pattern: '^APPROVED\s+[^\n]*\b[Aa]na\b'
flags: m
match: not_contains
---
