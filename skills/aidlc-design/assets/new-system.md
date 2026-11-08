<!-- aidlc template: new-system -->
# {{KEY}} · {{TITLE}} · new system

## For the reviewer
- **Asked of:** The tech lead or architect, to approve the stack, every dependency and the scaffold commands
- **Record it:** On the APPROVED line below, and on the work item with this file's version and commit
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
NEW SYSTEM · {{KEY}} · {{TITLE}}          (one REPOSITORY block per repository the LAYOUT names)
LAYOUT       <one repository: name | several: name, name — the coordination plan holds one slice-0 part each>
CONTRACTS    <contract v1: provider -> consumers> | none
NFR CHECKS   <requirement: the test, check or monitor that shows it holds>
QUALITY BAR  <dimension: target, set by the team>          (no baseline exists yet)
UI           <the design note's UI REFERENCE line> | none

REPOSITORY   <name>
STACK        <language and runtime @version; framework @version>   ADR: <adr-draft-n.md>
DEPENDENCIES <name@version: why> | none          (approving this design is the approval to add them)
PATHS        <the folders the skeleton creates>
COMMANDS     tests: <command> · lint: <command> · build: <command> · run: <command>   (onboard writes them to AGENTS.md as "not yet run")
SCAFFOLD     <tool@version — the exact generator and install commands — the paths they create> | none: slice 0 writes the skeleton by hand, tests first
CI           <each required check, running one of the COMMANDS>

APPROVED     <tech lead or architect>, <YYYY-MM-DD>, recorded on the work item with this file's version and commit
```
