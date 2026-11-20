---
id: coordination-plan
title: Coordination plan (cross-repository)
stage: plan
guide: ["14.9", "7.14"]
fields: [KEY, TITLE]
---
# Coordination plan · {{KEY}} · {{TITLE}} · v1

## For the reviewer
- **Asked of:** The tech lead or architect, to approve the parts, their order and the contract versions with the design; each part's own code owners approve its pull request
- **Record it:** On the work item with this plan's version and commit; each part in its own pull request (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
OUTCOME    <...>. Tier <n> (<reason; unknown consumers raise it>)
CONTRACTS  <contract> v<n> <from> -> <to> (<minor, additive | major via expand and contract>; each version written
           as its published tag's, v<MAJOR.MINOR.PATCH>)
PINS       Each part pins spec v<n> @ <home commit>; each consumer pins the provider's published tag
           api-v<version> in contracts/<provider>/SOURCE (ADR 0022)
PARTS      #  Repository     Owner    Change                 Flag          Waits for     Undo       Status
           1  <repository>   <team>   <what changes>         <flag, off>   <tag or ->    flag off   waiting
           (Status is derived: the AI at the workspace root reads each part's index on its repository's default branch with git and writes `status.md` beside this plan; nobody edits it by hand.)
TRACKING   Branch feat/{{KEY}}-<part> in each repository; pull request title "[{{KEY}}] part <n> of <m>: <what>".
           The story stays one tracker item: parts are tracked here, never as more issues.
READ-ONLY  <repositories read but not changed>
OUTSIDE    <work other teams must do outside this plan>
ORDER      Contract first; provider behind flags off; consumers in any order after the contract.
           Flags on: <order>
VERIFY     <compatibility check; provider contract tests and consumer verification; tolerant-reader tests; integration run>
UNKNOWNS   U1 <...>: owner <...>, answer by <date>, blocks <path only>
ROLLBACK   <per slice, each working alone (matrix rows)>
APPROVALS  Each slice by its own code owners. Plan: <approver>. Specialist: <role>.
           Nobody approves or merges in another team's repository on its behalf.
```
