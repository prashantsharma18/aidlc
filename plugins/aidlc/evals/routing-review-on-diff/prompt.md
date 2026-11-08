---
tags: [routing]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```diff
--- a/app/permissions.py
+++ b/app/permissions.py
@@ -10,9 +10,9 @@ def can_delete(user, document):
     if document.locked:
         return False
-    if user.is_admin:
+    if user.is_admin or True:
         return True
     return document.owner_id == user.id
```

Review this before I merge it.
