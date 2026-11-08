<!-- aidlc template: plan -->
# Plan: {{KEY}} · {{TITLE}}            Spec: <version, clarifications>

APPROACH   <the idea, so a reviewer can judge it before the details>
FILES      <path>   <reason>          (a file with no reason is a warning sign)
TESTS      AC1  <test name and level>
FIRST      E1   <...>
ORDER      <slices and dependencies; where to stop if something fails>
RISKS      <risk> -> <mitigation | accepted by whom>
REJECTED   <option> -> <why>
ROLLBACK   <flag, revert, expand and contract>
OPEN       Q1 <question> -> <owner>; blocks <slice>

Checklist: every criterion maps to a check; every file has a reason; every risk mitigated or
accepted; no architecture decision hidden; rollback concrete; slices safe in order; each brief
has a scope test and concrete stop conditions.

APPROVAL   plan.md <version> (commit <sha>) approved by <tech lead>, <YYYY-MM-DD>. Conditions: <...>
