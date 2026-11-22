# Several repositories

Sent here from `aidlc-start` step 5 or step 7, at a workspace root; this skill's Gate, Stop if and Rules still apply.

**Step 5.** **Which repositories change?** At a workspace root, send one `explorer` agent into each repository listed in
`WORKSPACE.md` with one question: "would this work change you, and how?" Spot-check two or three of each answer's
citations; a false one means that answer is discarded and asked again.

**Step 7.** **Several repositories:**
- story level, at the workspace root: `aidlc-intent` (only if the story needs it), `aidlc-specify`,
  `aidlc-discover`, `aidlc-design` (with the coordination plan, one row per repository part);
- part level, inside each repository: `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`. The root index
  has no rows for them, only the line "parts: see `status.md`";
- back at the root: `aidlc-release`; on events: `aidlc-operate`, `aidlc-feedback`.
