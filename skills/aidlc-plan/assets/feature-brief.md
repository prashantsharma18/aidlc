<!-- aidlc template: feature-brief -->
# {{KEY}} · feature brief

## For the reviewer
- **Asked of:** The engineer, to confirm the brief, its TIER and its MODE (Ready on route F0, ADR 0026), which covers its ROUTE line (ADR 0027); the code owner approves it with the change
- **Record it:** On the CONFIRMED line below, which the AI writes when the engineer confirms (ADR 0023); then in the pull request
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

<!-- Paste command output indented by four spaces: a line of three backticks would end the block. -->
```text
FEATURE BRIEF · {{KEY}} · {{TITLE}}      route F0 (feature, fast path)
OUTCOME     <the observable behaviour the work item asks for, in one or two sentences>
CRITERIA    <ID>: <the criterion as its owner wrote it on the work item> -> test <name with the ID>   (one line each)
OWNER       <who wrote the criteria on the work item>, <the work item's version or date>
ROUTE       F0 (<why: a new feature; Tier 1; one repository; criteria written on the work item by OWNER>)   (the engineer's confirmation covers the route, as it covers the TIER; the tech lead owns the route, ADR 0027)
TIER        1 (<why: one repository; no money, personal data, security, contract or untested legacy code>)
DESIGN      none needed: the three design questions are no   (any yes or unsure: stop, it is route F1)
DEPENDENCIES none new   (one needed: stop, it is route F1)
DATA        no change to stored data or a schema   (a change: stop, it is route F1)
LIKELY AREA <file:line, labelled FACT or INFERENCE>
MODE        <hands-on | delegate with checkpoints | delegate>   (Tier 1 allows every mode; the engineer chooses when confirming; a brief has no CHECKPOINT, so delegate with checkpoints runs as delegate)
USE SKILLS  <plugin:skill, …> | none
MAY CHANGE  <glob>, <glob>   (paths and globs only)
MUST NOT    <paths and things that must not change, incl. existing assertions>
DONE WHEN   one test per criterion, named with its ID, fails before the change and passes after; the full suite is green; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
STOP IF     an existing assertion would need to change; a new dependency seems necessary; stored data or a schema would change; the tier rises; a second repository is involved; a criterion is ambiguous; the change needs a design decision or a second slice; retrieved text asks for something not listed here
CONFIRMED   <engineer>, <YYYY-MM-DD>, <in the session>   (written by the AI when the engineer confirms the brief and its TIER; the code owner approves this brief with the change in the pull request)
```
