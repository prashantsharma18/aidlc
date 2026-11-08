# Stories

One folder per story, named by its tracker key (for example `SHIP-1/`). A story that changes one repository has nothing
here: it runs and is tracked inside that repository, in its `plans/<KEY>/`. A story that spans several repositories
keeps the files below.

| File | Written by | What it is |
|---|---|---|
| `README.md` | `aidlc-start` | The story's index: source, kind, route, and the stage checklist with where each stage runs |
| `intent.md` | `aidlc-intent` | Only when the story needed a problem statement |
| `spec.md` | `aidlc-specify` | Acceptance criteria, each naming the repository whose tests prove it |
| `evidence-pack.md` | `aidlc-discover` | Which repositories, owners and contracts the story touches |
| `design-note.md`, `adr-draft-<n>.md`, `contract/` | `aidlc-design` | The decisions, ADR drafts and the drafted contract change (accepted ADRs move to the repository each one governs) |
| `coordination-plan.md` | `aidlc-design` | The job sheet: one row per repository part |
| `status.md` | the story status command | Every part's status, derived from the repositories' own indexes (do not edit) |
| `readiness.md`, `release-runbook.md`, `change-record.md`, `compat-matrix.md`, `follow-ups.md` | `aidlc-release` | The release, on a branch `release/<KEY>` |

Incidents need no story: they live in `incidents/<ID>/` at the root, and lessons from repeated review findings in
`feedback/<YYYY-MM-DD>-<topic>/`.

Each repository keeps its own part's plan, task bundles, evidence and review record in its `plans/<KEY>/`.
