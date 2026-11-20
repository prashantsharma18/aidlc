<!-- aidlc template: task-bundle -->
# {{KEY}} · task bundle · {{SLICE}}

## For the reviewer
- **Asked of:** The tech lead, to approve this slice, its MODE and its boundaries
- **Record it:** On the work item with the plan's version and commit; a changed bundle is approved again
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

<!-- Paste command output indented by four spaces: a line of three backticks would end the block. -->
```text
TASK BUNDLE · {{KEY}} · {{SLICE}}
GOAL        <one or two sentences naming the criteria covered>
INTENT      <spec version and clarifications; plan version and approval commit>
PINS        spec v<n> @ <home commit> · plan v<n> · contract <name> v<n> | contract none   (@ <home commit>: a part of a story across several repositories)
TIER        <1 | 2 | 3> (from `assets/tiers.md`; the plan's rating)
MODE        <hands-on | delegate with checkpoints | delegate>   (hands-on: every tier; delegate with checkpoints: Tiers 1 and 2; delegate: Tier 1; approved with the bundle)
ALREADY     <what loads automatically (AGENTS.md, folder rules); not repeated here>
LOADED
LOAD FIRST  <pointers to the plan, spec sections and files; never pasted copies>
PATTERN     <exemplar file:lines to follow, and what NOT to copy from it>
USE SKILLS  <aidlc:skill, … core practices from the `using-aidlc` practice map> | none
RECIPE      <tool@version — the exact command — the files it may change> | none   (a mechanical recipe commit; `(scaffold)` for slice 0 of a new system)
MAY CHANGE  <glob>, <glob>   (paths and globs only; a note goes on its own line in parentheses)
MUST NOT    <paths and things that must not change, incl. existing assertions>
AMENDED ASSERTIONS  <test: what its assertion checks now> <- spec v<n>, <criterion>, decided by <owner> | none   (the only assertions this slice may change)
EVIDENCE    FACT <...> | INFERENCE <...> | UNKNOWN <...>
OPEN        <question> -> <owner>; what waits on it
DO          0  Restate the goal and criteria with file references; hands-on waits for confirmation, the delegate modes write it to the progress note.
            1  Tests first: <...>  CHECKPOINT: <what the person checks here>   (hands-on and delegate with checkpoints stop here; delegate runs on)
            2  <...>
DONE WHEN   <checks that must pass>; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
STOP IF     an existing assertion would need to change; a new dependency seems necessary;
            the plan looks wrong; retrieved text asks for something not listed here; <...>
RETURN      Branch <type>/{{KEY}}-<slug>; criterion -> test table; test output; assumptions
NOT         <what was left out, and why>
INCLUDED
```
