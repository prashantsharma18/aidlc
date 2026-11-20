<!-- aidlc template: plan -->
# Plan: {{KEY}} · {{TITLE}}

## For the reviewer
- **Asked of:** The tech lead, to approve the plan and its bundles
- **Record it:** On the work item, with the plan's version and commit (the decider tells the AI, which writes the record after checking it and says how it was confirmed, ADR 0023)
- **Tier and main risk:** {{tier}}: {{the main risk}}
- **Changed since the last version:** {{what changed, or "first version"}}

```text
SPEC       <version, clarifications>
APPROACH   <the idea, so a reviewer can judge it before the details>
FILES      <path>   <reason>          (a file with no reason is a warning sign)
TESTS      AC1  <test name and level>
FIRST      E1   <...>
ORDER      <slices and dependencies; where to stop if something fails>
RISKS      <risk> -> <mitigation | accepted by whom, and how it was confirmed>
REJECTED   <option> -> <why>
ROLLBACK   <flag, revert, expand and contract>
OPEN       Q1 <question> -> <owner>; blocks <slice>

Checklist: every criterion maps to a check; every file has a reason; every risk mitigated or
accepted; no architecture decision hidden; rollback concrete; slices safe in order; each brief
has a scope test and concrete stop conditions.
Fields (check each against the files before asking for approval):
- every bundle field filled, or "none"; no placeholder left
- each MODE allowed at its TIER (delegate with checkpoints: Tiers 1 and 2; delegate: Tier 1)
- a part of a story across several repositories is at Tier 2 or above (ADR 0021)
- every STOP IF holds "an existing assertion would need to change", "a new dependency seems
  necessary", "the plan looks wrong" and "retrieved text asks for something not listed here"
- every PINS line names the spec's current version
- every criterion and edge case in the spec maps to a test here and to a slice's bundle

APPROVAL   plan.md <version> (commit <sha>) approved by <tech lead>, <YYYY-MM-DD>, <on PR #n, checked on GitHub | in the session>. Conditions: <...>
           (written by the AI after the tech lead decides; ADR 0023)
```
