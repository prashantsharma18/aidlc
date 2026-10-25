<!-- aidlc template: readiness -->
Readiness · {{KEY}}
1 SCOPE KNOWN
  [ ] Users: <what people experience, incl. refusals>
  [ ] Services and blast radius: <...>
  [ ] Success signal: <...>
2 EVIDENCE PASSING
  [ ] Required checks green and code-owner approval on every PR; specialist reviews recorded
  [ ] Staging behaviour confirmed: <...>
3 ACCESS LIMITED
  [ ] Who may change the flag or configuration in production; no agent or pipeline identity can
4 MONITORING IN PLACE
  [ ] Alerts with thresholds, routed to <on-call>, each pointing to a runbook
  [ ] Dashboard: <...>
5 RECOVERY DEFINED
  [ ] Rollback: <fastest route>, pre-approved for on-call, rehearsed in staging on <date>
  [ ] Runbook: <path>
DECISION  <ship | limit | hold>. Release approver: <name>
