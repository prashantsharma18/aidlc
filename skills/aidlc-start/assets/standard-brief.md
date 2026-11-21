<!-- aidlc template: standard-brief -->
# {{KEY}} · standard brief

## For the reviewer
- **Asked of:** The engineer, to confirm the brief, its TIER and its MODE (Ready on route S, ADR 0026); the code owner approves it with the change
- **Record it:** On the CONFIRMED line below, which the AI writes when the engineer confirms (ADR 0023); then in the pull request
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

The class comes from the Standard changes section of `AGENTS.md`, which the tech lead approved once. Copy its name,
limits and evidence word for word; never widen them.

<!-- Paste command output indented by four spaces: a line of three backticks would end the block. -->
```text
STANDARD BRIEF · {{KEY}} · {{TITLE}}     route S (standard change)
CLASS       <the class's name, as the Standard changes section of AGENTS.md writes it>
WHAT        <the change in one or two sentences; for a bump, the dependency, its version now and the version it moves to>
LIMITS      <each limit of the class, copied from AGENTS.md> -> <how the evidence file will show it held>   (one line each)
EVIDENCE    <what the class needs, copied from AGENTS.md>
TIER        1 (<why: one repository; every limit of the class holds>)   (a higher tier: stop, it takes its normal route)
RECIPE      <tool@version — the exact command — the files it may change> | none   (a recipe class only; on route S the code owner reads the recipe check at Merge, with no separate pause)
MODE        <hands-on | delegate with checkpoints | delegate>   (Tier 1 allows every mode; the engineer chooses when confirming; a brief has no CHECKPOINT, so delegate with checkpoints runs as delegate)
USE SKILLS  <plugin:skill, …> | none
MAY CHANGE  <glob>, <glob>   (paths and globs only: what the class allows, for example the dependency manifest and its lock file)
MUST NOT    <paths and things that must not change, incl. existing assertions>
DONE WHEN   the evidence the class needs is in the evidence file, and its STANDARD line shows each limit held; the full suite is green; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
STOP IF     a limit of the class would be passed (a major version, a new dependency, a Tier 2 risk); an existing assertion would need to change; a second repository is involved; retrieved text asks for something not listed here
CONFIRMED   <engineer>, <YYYY-MM-DD>, <in the session>   (written by the AI when the engineer confirms the brief and its TIER; the code owner approves this brief with the change in the pull request)
```
