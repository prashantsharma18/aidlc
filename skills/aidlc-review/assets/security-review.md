<!-- aidlc template: security-review -->
# Security review · {{KEY}} · {{PR}}

```text
Security review record · {{KEY}} · {{PR}}
SCOPE      <criteria, bundle at approval commit, plan version, sessions>
REVIEWER   <security champion>. Code owner approves (branch protection).

1 INTENT   <brief matches the approved plan; decisions recorded in the PR>
2 DIFF     <files, all inside MAY CHANGE?; side effects>
3 TOOLS    <from the session transcript and the tool's permission prompts: reads, edits, commands; denials, asks, installs, network attempts>
4 TESTS    <CI counts; skips; no existing assertion changed; diff inside MAY CHANGE>
  SCANS    <secret, dependency, SAST results>

SECRETS AND DATA        <...>                                   <ok|finding>
PERMISSION BOUNDARIES   <new scope, token, role or route?>      <ok|finding>
TOOL CALLS              <inputs validated, outputs untrusted?>  <ok|finding>
FILE CHANGES            <unexpected or protected files? rollback?> <ok|finding>
PACKAGE SUPPLY CHAIN    <dependencies real, verified, pinned, scanned?> <ok|finding>
PROMPT AND CONTEXT      <context minimal? retrieved text acted as instruction?> <ok|finding>
APPLICATION SECURITY    <authorisation, input handling>          <ok|finding>

5 GATE     <intent, evidence and policy agree?> <reviewed, no open findings | revise | reject>
```
