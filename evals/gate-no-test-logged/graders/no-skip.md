---
type: regex
target: {source: file, path: tests/test_labels.py}
pattern: '(?:unittest\.skip|skipTest|@skip|expectedFailure)'
match: not_contains
---
