# The lifecycle, as this framework runs it

How one change moves from intent to verified production code, and which skill, artefact
and gate the framework provides at each stage.

## Two loops

- **Outer loop**: the change across the team's systems, from a work item to production and
  back as new work. Gates and systems of record control it.
- **Inner loop**: one engineer-and-agent session inside Plan, Build and Verify:
  brief → load context → plan → act → check → correct (retry limit 3) → evidence → hand off.
  Everything it proves is local evidence until trusted CI runs it again.

## Eight stages

| Stage | Decides | Artefact (template) | System of record | Gate | Skill |
|---|---|---|---|---|---|
| Intent | Product owner | `intent` | Jira issue | Owner, priority, provisional tier | `aidlc-intent` |
| Specify | Spec owner (+ specialists) | `spec` | Jira (approved version) | Criteria testable; approval recorded | `aidlc-specify` |
| Design | Tech lead / architect; consumers | `design-note`, `adr`, contract | Jira note; `docs/adr/`; contract file | Decisions approved, or "none needed" recorded | `aidlc-design` |
| Plan | Engineer drafts, tech lead approves | `plan`, `task-bundle`, `coordination-plan` | `plans/<KEY>/` + approval on Jira | Approval line in `plans/approved-bundles.txt` | `aidlc-plan` |
| Build | Engineer | commits, `progress-note` | Feature branch `<type>/<KEY>-<slug>` | Local check green; diff in scope | `aidlc-build-slice` |
| Verify | Automated gates | `evidence-table` | CI record | Required checks green | `aidlc-verify` |
| Review & release | Code owners, specialists, release approver | `review-record`, `readiness`, `change-record` | Git host; change management | Code-owner approval; release approval | `aidlc-review`, `aidlc-release` |
| Operate & learn | On-call, owning team | `runbook`, `incident` | Monitoring; Jira | Healthy or rolled back; lessons routed | `aidlc-operate` |

Discovery (`evidence-pack`, `explorer-brief`) runs before Design whenever the tier asks for it.

## Rules that hold at every stage

- The agent takes part in every stage and owns none. It drafts, it never approves.
- One system of record per artefact; link, don't copy. A stage ends only when its artefact is
  in its system of record.
- Only trusted verification counts towards a merge.
- Most arrows point backwards: a CI failure returns to the inner loop, a wrong approach to Plan,
  a wrong criterion to its owner, and production signals become new intent.

Guide: 1.2, 1.3, 1.4, 16.1.
