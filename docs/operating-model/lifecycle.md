# The lifecycle, as this framework runs it

How one change moves from intent to verified production code, and which skill, artefact
and gate the framework provides at each stage.

## Two loops

- **Outer loop**: the change across the team's systems, from a work item to production and
  back as new work. Gates and systems of record control it.
- **Inner loop**: one engineer-and-agent session inside Plan, Build and Verify:
  brief → load context → plan → act → check → correct (retry limit 3) → evidence → hand off.
  Everything it proves is local evidence until trusted CI runs it again.

## The stages

| Stage | Decides | Artefact (template) | System of record | Gate | Skill |
|---|---|---|---|---|---|
| Intent | Product owner | `intent` | Jira issue | Owner, priority, provisional tier | `aidlc-intent` |
| Specify | Spec owner (+ specialists) | `spec` | Jira (approved version) | Criteria testable; approval recorded | `aidlc-specify` |
| Design | Tech lead / architect; consumers | `design-note`, `adr`, contract | Jira note; `docs/adr/`; contract file | Decisions approved, or "none needed" recorded | `aidlc-design` |
| Plan | Engineer drafts, tech lead approves | `plan`, `task-bundle`, `coordination-plan` | `plans/<KEY>/` (or `stories/<KEY>/coordination-plan.md`) | Approval on the work item, with the plan's version and commit | `aidlc-plan` |
| Build | Engineer | commits, `progress-note` | Feature branch `<type>/<KEY>-<slug>` (`feat/<KEY>-<part>` for a part) | Local check green; diff inside MAY CHANGE | `aidlc-build` |
| Verify | Automated gates | `evidence-table` | CI record | Required checks green | `aidlc-verify` |
| Review & release | Code owners, specialists, release approver | `review-record`, `readiness`, `change-record` | Git host; change management | Code-owner approval; release approval | `aidlc-review`, `aidlc-release` |
| Operate & learn | On-call, owning team | `runbook`, `incident` | Monitoring; Jira | Healthy or rolled back; lessons routed | `aidlc-operate` |

Discovery (`evidence-pack`, `explorer-brief`) runs before Design whenever the tier asks for it.

Every stage has a skill in [skills/](../../skills/), and `aidlc-onboard` sets up a repository or a workspace.
Start every piece of work with `aidlc-start`: it decides the kind of work and the repositories it changes, and
says where each stage runs ([workspace-and-repositories.md](workspace-and-repositories.md)).

**Eight routes** use these stages: features by the fast path (F0), in one repository (F1) or several (F2), change requests (C), defects by the
fast path (D1) or the full route (D2), incidents (I), and new systems (G). `aidlc-start` chooses one;
the route table is in the `using-aidlc` skill, and the diagrams arrive in `routes.md` with Plan 17.

## Rules that hold at every stage

- The agent takes part in every stage and owns none. It drafts, it never approves.
- One system of record per artefact; link, don't copy. A stage ends only when its artefact is
  in its system of record.
- Only trusted verification counts towards a merge.
- Most arrows point backwards: a CI failure returns to the inner loop, a wrong approach to Plan,
  a wrong criterion to its owner, and production signals become new intent.

Guide: 1.2, 1.3, 1.4, 16.1.
