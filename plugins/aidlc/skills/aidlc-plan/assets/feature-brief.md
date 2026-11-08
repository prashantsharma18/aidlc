<!-- aidlc template: feature-brief -->
FEATURE BRIEF · {{KEY}} · {{TITLE}}      route F0 (feature, fast path)
OUTCOME     <the observable behaviour the work item asks for, in one or two sentences>
CRITERIA    <ID>: <the criterion as its owner wrote it on the work item> -> test <name with the ID>   (one line each)
OWNER       <who wrote the criteria on the work item>, <the work item's version or date>
TIER        1 (<why: one repository; no money, personal data, security, contract or untested legacy code>)
DESIGN      none needed: the three design questions are no   (any yes or unsure: stop, it is route F1)
DEPENDENCIES none new   (one needed: stop, it is route F1)
DATA        no change to stored data or a schema   (a change: stop, it is route F1)
LIKELY AREA <file:line, labelled FACT or INFERENCE>
MODE        <hands-on | delegate with checkpoints | delegate>   (Tier 1 allows every mode; the engineer chooses when confirming)
USE SKILLS  <plugin:skill, …> | none
MAY CHANGE  <glob>, <glob>   (paths and globs only)
MUST NOT    <paths and things that must not change, incl. existing assertions>
DONE WHEN   one test per criterion, named with its ID, fails before the change and passes after; the full suite is green; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
STOP IF     an existing assertion would need to change; a new dependency seems necessary; stored data or a schema would change; the tier rises; a second repository is involved; a criterion is ambiguous; the change needs a design decision or a second slice; retrieved text asks for something not listed here
CONFIRMED   <engineer>, <YYYY-MM-DD>   (the code owner approves this brief with the change in the pull request)
