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
| `design-note.md`, `<KEY>-adr-<n>.md`, `contract/` | `aidlc-design` | The decisions, ADR drafts and the drafted contract change (an accepted ADR that governs one repository moves there; one across repositories stays in the home repository's `docs/adr/`) |
| `coordination-plan.md` | `aidlc-design` | The job sheet: one row per repository part |
| `status.md` | the story status command | Every part's status, derived from the repositories' own indexes (do not edit) |
| `readiness.md`, `release-runbook.md`, `change-record.md`, `compat-matrix.md`, `follow-ups.md` | `aidlc-release` | The release, on a branch `release/<KEY>` |

Incidents need no story: they live in `incidents/<ID>/` at the root, and lessons from repeated review findings in
`feedback/<YYYY-MM-DD>-<topic>/`.

Each repository keeps its own part's plan, task bundles, evidence and review record in its `plans/<KEY>/`.

## Who owns each fact (ADR 0022)

Each fact has one owner, and only the owner changes it. The others read it at a version and a commit.

| Here, in the home repository (`stories/<KEY>/`, `docs/adr/`, `incidents/`) | In each part's repository |
|---|---|
| The index, intent, spec, evidence pack, design note, ADR drafts and the contract draft | The plan, the task bundles and the progress notes |
| The coordination plan and `status.md` | `plans/<KEY>/criteria.md`: a read-only copy of the part's criteria, with the home commit it came from |
| The release records and incidents | The evidence, the pull request description and the review record |
| ADRs across repositories | ADRs that govern only that repository, and the code |
| | The published contract, in the provider (tag `api-v<version>`); each consumer's read-only copy in `contracts/<provider>/` |

A part pins the spec as `spec v<n> @ <commit>`. Once a part pins it, nothing under `stories/<KEY>/` is moved or
renamed: a change is a new version.
