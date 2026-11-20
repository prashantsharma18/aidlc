<!-- aidlc template: evidence-table -->
# {{KEY}} · {{PART}} · evidence

From the trusted run, never the agent's summary.

**Verdict:** {{every criterion proved in the trusted run, or the number unproved, listed under Unproved}}

## Criteria
| Criterion | Test | Local | Trusted CI |
|---|---|---|---|
| AC1 | {{test name containing AC1}} | {{pass, fail or SKIPPED}} | {{pass or fail}} |

Total in CI: {{n}} tests ({{passed}} passed, {{failed}} failed, {{skipped}} skipped).

## Integrity and scans

```text
                                                            LOCAL  TRUSTED CI
INTEGRITY  scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)      <ok>   <ok (trusted copy)>
           protected tests: no existing line changed       -      <ok>
           skips: tests that did not run                   <n>    <0>
SCANS      dependency, secrets, SAST                        -      <clean>
```

## AI review
- {{finding}}: {{fixed test-first, or dismissed: reason}}

## Unproved
- {{criterion, why, who accepted, and how it was confirmed}}, or none
