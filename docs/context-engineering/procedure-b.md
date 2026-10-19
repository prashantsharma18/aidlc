# Procedure B: assembling context for a task

Repository context says how the project works, not what you want today.

| Step | What happens | Framework support |
|---|---|---|
| B1 Gather | Start from the work item, spec, criteria and plan; find entry points, reusable capabilities, the closest example, related decisions, covering tests; list unknowns and who answers | Explorer brief; evidence pack |
| B2 Select | Keep only what a decision needs; pointers for what the agent can reach, short dated excerpts otherwise; pin versions; never secrets, personal or production data | Bundle "NOT INCLUDED" field |
| B3 Structure | Write the bundle: the brief's fields plus intent, already loaded, pattern, evidence, open questions, not included | `aidlc new task-bundle --out plans/<KEY>/<slice>.md --set KEY=<KEY> --set SLICE=<slice>` |
| B4 Inject | Approver appends the approval line on main; `aidlc scope --branch <branch> --out <file outside the workspace>`; fresh session; restate and wait | `plans/approved-bundles.txt`; `aidlc scope` (fails closed) |
| B5 Validate | Classify each miss: gap, wrong, ignored (context rot, compaction), not context | Progress note "Context gaps noticed" |
| B6 Update | Route each lasting lesson to its layer (rule, map, example, procedure, decision record, enforcement, eval case) by PR | `aidlc-feedback` skill (Plan 4) |

The scope is read by the guard hook, the post-tool check, the local check and trusted CI; a
missing or empty scope stops the task.

Guide: 2.9, 7.10, 3 step 5.
