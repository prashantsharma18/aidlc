<!-- aidlc template: new-system -->
NEW SYSTEM · {{KEY}} · {{TITLE}}
STACK        <language and runtime @version; framework @version>   ADR: <adr-draft-n.md>
DEPENDENCIES <name@version: why> | none          (approving this design is the approval to add them)
LAYOUT       <one repository: name | several: name, name — the coordination plan holds one slice-0 part each>
CONTRACTS    <contract v1: provider -> consumers> | none
NFR CHECKS   <requirement: the test, check or monitor that shows it holds>
QUALITY BAR  <dimension: target, set by the team>          (no baseline exists yet)
COMMANDS     tests: <command> · lint: <command> · build: <command> · run: <command>   (onboard writes them to AGENTS.md as "not yet run")
SCAFFOLD     <tool@version — the exact command — the paths it creates> | none: slice 0 writes the skeleton by hand, tests first
CI           <each required check, running one of the COMMANDS>
UI           <the design note's UI REFERENCE line> | none
APPROVED     <tech lead or architect>, <YYYY-MM-DD>, recorded on the work item with this file's version and commit
