---
type: regex
target: {source: file, path: src/shipments/labels.py}
pattern: '\.[lr]?strip\(|\.replace\(|\.translate\(|re\.sub\(|def\s+\w*[Cc]lean\w*\s*\('
match: not_contains
---
