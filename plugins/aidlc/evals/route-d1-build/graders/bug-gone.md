---
type: regex
target: {source: file, path: src/shipments/eta.py}
pattern: 'floor\(distance_km / 500\) \+ 1'
match: not_contains
---
