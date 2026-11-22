# Route G: a new system

Sent here from `aidlc-start` step 7, route G; this skill's Gate, Stop if and Rules still apply.

**New system (G):** each step's pull request merges before the next starts.
1. In the home (the repository, or the workspace root): `aidlc-intent` (when the story needs it), `aidlc-specify`
   (the system and its first criteria), `aidlc-design` (the new system's decisions and `new-system.md`). These
   documents merge in their own pull request: there is no code yet.
2. Several repositories, or undecided: the person creates each repository the design's LAYOUT names, then re-runs
   `aidlc-onboard` at the workspace root to add them to `WORKSPACE.md`; the person adds their deny rules to the
   root's `.claude/settings.json`, which a session cannot edit.
3. In each new repository: `aidlc-onboard` (new mode, prepare) on its own branch; then slice 0 (`aidlc-plan`,
   `aidlc-build`, `aidlc-verify`, `aidlc-review`) on `feat/<KEY>-slice-0`; then `aidlc-onboard` (new mode, confirm).
4. The story's criteria are then built as in F1 (one repository) or F2 (several), and the story ends with
   `aidlc-release`. Later features are new stories.

The index lists the rows `aidlc-onboard (prepare)`, `slice 0` and `aidlc-onboard (confirm)` before the build rows.
