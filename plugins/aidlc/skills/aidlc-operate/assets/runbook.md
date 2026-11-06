<!-- aidlc template: runbook -->
# Runbook · {{SERVICE}} · {{ALERT}}

ALERT     <signal> fires above <threshold> over <window>. Owner: <team>. Routed to: <on-call>.

A person runs every step. Each step is marked: read-only | changes state.

R1  <triage query>                                   read-only
R2  <second query>                                   read-only
C1  <containment: most rehearsed, reversible action> changes state
C2  <containment needing a change> -> reviewed PR, change record, production gate
                                                      an agent may draft the PR; <who> approves
When no step fits, people decide; the agent never improvises one.
