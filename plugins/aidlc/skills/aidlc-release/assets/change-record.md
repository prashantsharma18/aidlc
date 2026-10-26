<!-- aidlc template: change-record -->
Change record · {{KEY}}
CHANGE      <what is switched or deployed>
ARTEFACT    <build of commit <sha>; digest recorded by the release pipeline>
LINKS       <work item; spec version; plan; PRs with evidence and reviews; readiness>
TIER        <n>
PLAN        1 <staging step>   2 <rehearse rollback>   3 <production step>   4 <watch window>
STOP        <signal, threshold, duration> -> <action at once, by whom, no further approval>
CAUTION     <signal> -> <hold the next stage; follow the runbook>
AGENT ROLE  <read-only: summaries and proposals; no flags, configuration or credentials>
FOLLOW-UPS  <flag removal: owner, date, work item>
SUBMITTED   <engineer (drafted with the agent)>
APPROVED    <release approver, in change management>
