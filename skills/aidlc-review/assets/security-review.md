<!-- aidlc template: security-review -->
# Security review · {{KEY}} · {{PR}}

## For the reviewer
- **Asked of:** The security champion (the required specialist), to clear or block the change; a code owner approves
- **Record it:** On the GATE line below, and in the pull request (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

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

5 GATE     <intent, evidence and policy agree?> <reviewed, no open findings | revise | reject> — <champion, date, how it was confirmed>
```
