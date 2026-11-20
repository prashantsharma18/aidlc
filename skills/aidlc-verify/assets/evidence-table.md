<!-- aidlc template: evidence-table -->
# {{KEY}} · {{PART}} · evidence

From the trusted run, never the agent's summary.

**Summary of the trusted run at {{commit}}:** {{every criterion proved, or the number unproved, listed under
Unproved}}. This is evidence, not a verdict: the verdict comes from the reviewers who did not write the change,
in the review record.

## Criteria
| Criterion | Test | Local | Trusted CI |
|---|---|---|---|
| AC1 | {{test name containing AC1}} | {{pass, fail or SKIPPED}} | {{pass or fail}} |

Total in CI: {{n}} tests ({{passed}} passed, {{failed}} failed, {{skipped}} skipped).

## Integrity and scans

```text
                                                            FROM GIT       JUDGED BY
INTEGRITY  scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)      <ok or the paths>   <reviewer-compliance at commit>
           test files changed: <each path, or none>          <list>         <reviewer-tests at commit>
           test count: <n> at BASE, <n> at HEAD              <n -> n>       <reviewer-tests at commit>
           protected tests: no existing assertion changed    -              <reviewer-tests at commit>
           skips: tests that did not run                     <n>            <0 in CI>
SCANS      dependency, secrets, SAST                         -              <clean in CI>
```

## AI review
- {{finding}}: {{fixed test-first, or dismissed: reason}}

## Unproved
- {{criterion, why, who accepted, and how it was confirmed}}, or none
