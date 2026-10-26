<!-- aidlc template: release-runbook -->
Release runbook · {{KEY}}
STEP  WHAT                              WHO (own process)      ROLLBACK, ALONE
1     <contract published>              <team>                 <none; fix forward>
2     <provider deployed, flags off>    <team>                 <redeploy previous>
3     <flag on: staging, then prod>     <team>                 <flag off>

INTEGRATION ENVIRONMENT (before the first behaviour change)
      <messages or requests to send; what every consumer must show>

STOP CRITERIA (written before the step; act at once, no further approval)
<step>  <signal, threshold, duration> -> <action>

WATCH  <window>; the agent posts read-only summaries; people decide.
