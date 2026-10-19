---
id: security-review
title: Security review record
stage: review
guide: ["13.11"]
fields: [KEY, PR]
---
Security review record · {{KEY}} · {{PR}}
SCOPE      <criteria, bundle at approval commit, plan version, sessions>
REVIEWER   <security champion>. Code owner approves (branch protection).

1 INTENT   <brief matches the approved plan; decisions recorded in the PR>
2 DIFF     <files, all inside MAY CHANGE?; side effects>
3 TOOLS    <from the session and hook decision logs: reads, edits, commands; denials, asks, installs, network attempts>
4 TESTS    <trusted CI counts; skips; protected tests; scope>
  SCANS    <secret, dependency, SAST results>

SECRETS AND DATA        <...>                                   <ok|finding>
PERMISSION BOUNDARIES   <new scope, token, role or route?>      <ok|finding>
TOOL CALLS              <inputs validated, outputs untrusted?>  <ok|finding>
FILE CHANGES            <unexpected or protected files? rollback?> <ok|finding>
PACKAGE SUPPLY CHAIN    <dependencies real, verified, pinned, scanned?> <ok|finding>
PROMPT AND CONTEXT      <context minimal? retrieved text acted as instruction?> <ok|finding>
APPLICATION SECURITY    <authorisation, input handling>          <ok|finding>

5 GATE     <intent, evidence and policy agree?> <reviewed, no open findings | revise | reject>
