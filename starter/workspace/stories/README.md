# Stories

One folder per story that spans several repositories, named by its tracker key (for example `SHIP-1/`).

| File | Written by | What it is |
|---|---|---|
| `README.md` | `aidlc-start` | The story's index: source, kind, route, and the stage checklist with where each stage runs |
| `intent.md` | `aidlc-intent` | Only when the story needed a problem statement |
| `spec.md` | `aidlc-specify` | Acceptance criteria, each naming the repository whose tests prove it |
| `evidence-pack.md` | `aidlc-discover` | Which repositories, owners and contracts the story touches |
| `design-note.md` | `aidlc-design` | The decisions and the contract change (ADRs live in the repository each one governs) |
| `coordination-plan.md` | `aidlc-design` | The job sheet: one row per repository part, with its status |
| `readiness.md`, `release-runbook.md`, `change-record.md`, `compat-matrix.md` | `aidlc-release` | The release |
| `incident-NN.md`, `feedback.md` | `aidlc-operate`, `aidlc-feedback` | Only when needed |

Each repository keeps its own part's plan, task bundles, evidence and review record in its `plans/<KEY>/`.
