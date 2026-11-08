---
tags: [routing]
max_turns: 12
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Skill]
---

```diff
--- a/app/users.py
+++ b/app/users.py
@@ -1,4 +1,4 @@
-def getUser(user_id):
+def fetchUser(user_id):
     return db.users.find(user_id)
--- a/app/views.py
+++ b/app/views.py
@@ -3,7 +3,7 @@
-    user = getUser(request.user_id)
+    user = fetchUser(request.user_id)
--- a/app/admin.py
+++ b/app/admin.py
@@ -8,3 +8,3 @@
-    owner = getUser(doc.owner_id)
+    owner = fetchUser(doc.owner_id)
```

Write me a commit message for this.
