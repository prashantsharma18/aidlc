---
type: regex
target: {source: file, path: plans/SHIP-80/design-note.md}
pattern: '^(APPROVED|RECORDED BY)[ \t]+(?![ \t]|\(pending)'
flags: m
match: not_contains
---
