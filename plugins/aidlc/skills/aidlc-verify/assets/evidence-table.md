<!-- aidlc template: evidence-table -->
{{KEY}} · {{SLICE}} · evidence (from the trusted run, never the agent's summary)

CRITERION  TEST                                   LOCAL       TRUSTED CI
AC1        <test name containing AC1>             <pass|fail|SKIPPED>   <pass|fail>
TOTAL      <n> tests (<passed> passed, <failed> failed, <skipped> skipped in CI)

INTEGRITY  scope: every changed path inside MAY CHANGE      <ok>   <ok (trusted copy)>
           protected tests: no existing line changed       -      <ok>
           skips: tests that did not run                   <n>    <0>
SCANS      dependency, secrets, SAST                        -      <clean>
AI REVIEW  <finding> -> <fixed test-first | dismissed: reason>
UNPROVED   <criterion, why, who accepted> | none
