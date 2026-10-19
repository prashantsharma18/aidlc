---
id: evidence-pack
title: Evidence pack
stage: discover
guide: ["4.7", "4.8"]
fields: [KEY, TIER]
---
# {{KEY}} · evidence pack · Tier {{TIER}}

QUESTION  <who reads or writes X, by what path, and what must stay true when Y?>
LEVEL     <L0-L3 and the trigger that forced it>

Tier 2 requires items 1-5; Tier 3 requires all eight (core/policy/tiers.yaml).

1 ENTRY POINTS   <every way the behaviour or data is triggered, each with file:line and method>
2 OWNERS         <owner per component, or "unknown" with an escalation; confirmed by whom, when>
3 CONTRACTS      <each interface touched, its contract file, keep or change>
4 DEPENDANTS     <methods used; impact per dependant: breaks / changes meaning / unaffected>
5 UNKNOWNS       <U1 ... each with risk and an owner-agreed mitigation>
6 PINNED         <existing and added characterisation tests>
7 CITATIONS      <every claim cites file:line, a recorded command or query, or a person and date>
8 ROLLBACK       <proven reversible, or rehearsed>

SEARCHED  <what was searched>   EXCLUDED  <what was not>

DECISION  <proceed | escalate a level | raise the tier> — <reasons> — <tech lead, date>
