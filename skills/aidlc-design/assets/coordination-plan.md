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
- **Record it:** On the work item with this plan's version and commit; each part in its own pull request
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
OUTCOME    <...>. Tier <n> (<reason; unknown consumers raise it>)
CONTRACTS  <contract> v<n> <from> -> <to> (<minor, additive | major via expand and contract>)
PARTS      #  Repository     Owner    Change                 Flag          Waits for     Undo       Status
           1  <repository>   <team>   <what changes>         <flag, off>   <tag or ->    flag off   waiting
           (Status is derived: run the story status command named in WORKSPACE.md; it reads each part's index and writes `status.md` beside this plan.)
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
