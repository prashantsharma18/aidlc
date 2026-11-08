---
tags: [routing]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

Fix this bug:

```python
def last_page(total, size):
    return total // size
```

last_page(21, 10) returns 2, but there are 3 pages.
