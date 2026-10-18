---
id: working-agreement
title: Team working agreement
stage: operate
guide: ["16.3", "16.2"]
fields: [TEAM]
---
TEAM WORKING AGREEMENT: AI-ASSISTED DELIVERY · {{TEAM}}     owner: <tech lead>   reviewed: <date>

1 SCOPE        Agents may: read, plan, write tests and code on feature branches, draft PR text.
               Agents may not: approve, merge, push (the harness pushes), hold production
               credentials, change harness or protected test files. Route: <approved route>.
2 TIERS/MODES  Tier 1 plan in PR; Tier 2 written spec and plan, delegated work pauses at
               contract decisions; Tier 3 specialist reviews spec, judgement slices hands-on.
3 READY/DONE   Ready: owner, testable criteria, tier; above Tier 1, approved plan and brief.
               Done: required checks green; evidence table complete; code owner approved;
               lessons routed; flags and follow-ups owned.
4 TASK SIZE    One slice per PR, reviewable in <30> minutes; PR carries key, evidence, assumptions.
5 CONTEXT      Rules file, codebase map, skills: <owner>, freshness <monthly>; harness: <owner>.
6 REVIEW       AI review first, findings are advice; the author never approves; first review
               within <1> working day; specialists by tier.
7 EVALS        Owner <name>; run on every change to rules, skills, hooks, permissions or model,
               and <weekly>; every escaped agent mistake adds a case.
8 RETRO        Cadence <fortnightly>; review findings per PR, reverts, escapes, eval pass rate,
               retries; route each lesson: rule | map | test | eval case | hook | CI check.
               Usage figures are context only, never targets.
9 STOP         At the retry limit, a scope or architecture question, any security finding, or
               an existing assertion needing change. Escalate to <tech lead>.
