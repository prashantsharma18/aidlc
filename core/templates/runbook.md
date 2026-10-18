---
id: runbook
title: Operational runbook
stage: operate
guide: ["12.2", "12.4"]
fields: [SERVICE, ALERT]
---
# Runbook · {{SERVICE}} · {{ALERT}}

ALERT     <signal> fires above <threshold> over <window>. Owner: <team>. Routed to: <on-call, operations agent>.

Each step is marked: agent may execute (read-only or draft) | human only.

R1  <triage query>                                   agent may execute
R2  <second query>                                   agent may execute
C1  <containment: most rehearsed, reversible action> human only
C2  <containment needing a change> -> reviewed PR, change record, production gate
                                                      agent may draft the PR; <who> approves
When no step fits, people decide; the agent never improvises one.
