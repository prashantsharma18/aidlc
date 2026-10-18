---
id: coordination-plan
title: Coordination plan (cross-repository)
stage: plan
guide: ["14.9", "7.14"]
fields: [KEY, TITLE]
---
Coordination plan · {{KEY}} · {{TITLE}} · v1
OUTCOME    <...>. Tier <n> (<reason; unknown consumers raise it>)
CONTRACTS  <contract> <from> -> <to> (<minor, additive | major via expand and contract>)
SLICES     S1 <repository>   <owner>   <what>; flags <names, created off>
READ-ONLY  <repositories read but not changed>
OUTSIDE    <work other teams must do outside this plan>
ORDER      Contract first; provider behind flags off; consumers in any order after the contract.
           Flags on: <order>
VERIFY     <compatibility check; provider contract tests and consumer verification; tolerant-reader tests; integration run>
UNKNOWNS   U1 <...>: owner <...>, answer by <date>, blocks <path only>
ROLLBACK   <per slice, each working alone (matrix rows)>
APPROVALS  Each slice by its own code owners. Plan: <approver>. Specialist: <role>.
           Nobody approves or merges in another team's repository on its behalf.
