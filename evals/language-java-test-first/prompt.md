---
tags: [language]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```java
public final class Paging {
    static int pages(int total, int size) {
        return total / size;
    }
}
```

pages(21, 10) returns 2 but should be 3. Fix it.
