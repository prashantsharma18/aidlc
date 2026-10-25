---
id: compat-matrix
title: Compatibility matrix
stage: discover
guide: ["14.8"]
fields: [KEY]
---
# {{KEY}} · compatibility matrix

Every combination of old and new must hold before the step that creates it ships.
Cell: ✓ proved (evidence) · ✗ broken · ? unknown (owner, date).

| Provider sends | <consumer A> current | <consumer A> updated | <consumer B> current | <consumer B> updated |
|---|---|---|---|---|
| Old version (and replayed old messages) | | | | |
| New, flag off (field absent) | | | | |
| New, no value (field absent) | | | | |
| New, with value | | | | |

Evidence per cell: <test file:line, expectations file, owner confirmation with date>
Rows "old" and "flag off" are also the rollback states: every consumer must keep handling them.
