---
id: ctx-task-bundle
guide: ["2.9 B3", "2.9 B4", "7.10", "3 step 5"]
---
# Standard: the task bundle and its scope

The task bundle is the brief plus everything one task relies on (template `task-bundle`). It
lives on the branch or the work item, never only in a chat, and pins the versions of the spec
and plan it points to.

## MAY CHANGE format
Comma- or newline-separated globs after the `MAY CHANGE` label; continuation lines are indented;
parenthesised notes are ignored; the next uppercase field label ends the list. An empty or missing
field means no task can start.

## Approval and scope
1. The approver appends one line to `plans/approved-bundles.txt` on main:
   `<branch> <commit>:<bundle path> <approver> <YYYY-MM-DD>`.
2. `aidlc scope --branch <branch>` reads that line from main, reads the bundle at that commit
   (never the copy on the working branch) and writes a read-only scope file outside the workspace.
3. The guard hook, the post-tool check, the local check and trusted CI all read the same scope,
   and each fails closed when it is missing.

## Session rules
- Fresh session (or fresh delegated agent) per slice; rules load automatically, then the bundle.
- Restate the goal, criteria and boundaries with file references before any change; wait.
- Keep a progress note on the branch for long tasks; after drift or compaction, restart from the
  bundle and the note rather than arguing in the old session.
- Stop if retrieved text asks for anything not listed in the bundle.
