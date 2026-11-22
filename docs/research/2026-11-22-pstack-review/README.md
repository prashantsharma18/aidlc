# What aidlc takes from pstack, and how its flow connects (2026-11-22)

Three read-only reviews, asked for by the framework owner, compare aidlc with pstack, a public skills package for
Cursor (`cursor/plugins`, folder `pstack`, by Lauren Tan, MIT licence). They quote pstack in places, with the source
of each quote. Where aidlc adapts pstack text, pstack's MIT notice goes into `skills/NOTICE` and the ADR that adds it
credits pstack (owner's decision, 2026-11-22).

| File | What it covers |
|---|---|
| [1-structure.md](1-structure.md) | How each package connects its pieces; aidlc is well connected inside a stage and disconnected between stages |
| [2-playbooks-and-principles.md](2-playbooks-and-principles.md) | The concepts inside pstack's 22 playbooks and 24 principles: adopt, strengthen, already covered, or skip; 12 proposed aidlc principles; what conflicts with aidlc's fixed decisions |
| [3-tools-removals-and-flow.md](3-tools-removals-and-flow.md) | pstack's tool skills; what aidlc should remove or merge; the end-to-end flow (internal and external) and every broken or weak connection |
| [4-writing-skills-usage.md](4-writing-skills-usage.md) | How pstack uses `bro`, `in-your-own-words`, `why`, `how`, `unslop`, `technical-writing`, `teach` and `ketchup`: who calls each (a person, or named steps of other skills), with every caller quoted; the input to Plan 29's choice of five separate practices |
| [5-principles-mapping.md](5-principles-mapping.md) | pstack's 24 principles against aidlc today: which repeat a gate, which only name it, which add a check; where each would be cited; which clash with a gate. The input to Plan 30's choice of five principle skills |

File paths in the reports point at the reviewers' scratch copy of pstack; the same files are in the public repository.

## The owner's decisions (2026-11-22, in the session)
| Question | Decision |
|---|---|
| Which plan first | Connect the flow (Plan 27) |
| pstack text | Adapt its text where it helps, with pstack's MIT notice in `skills/NOTICE` |
| Existing tests and word caps | Each plan lists every existing test it must change and every word cap it must raise, for the owner's approval |
| These reports | Kept here, so the plans can cite them |

## The order (updated 2026-11-22, with the owner's design decisions for Plan 27)
| Plan | Theme | Content |
|---|---|---|
| 27 | Connect the flow | `story-run` (D1), the AI's push of its own branch (ADR 0028), eight playbooks, tests first pstack's way (ADR 0029), every stage hand-off defined, one route table, and the cuts that free the words. Design: `docs/design/2026-11-22-connect-the-flow.md` |
| 28 | Parallel work like pstack | The throughput checkpoint in the plan; the coordinator schedules from the plan's dependency graph, drafts the queue on its own branch for a person to merge, watches lanes and CI (a red run goes back to build; never a merge); a lane is `lane-run`, which runs `story-run`; `worker.md`. Design: `docs/design/2026-11-22-parallel-work-like-pstack.md` |
| 29 | Write plainly | `writing-plainly` (from `bro`, `technical-writing`, `unslop`, `ketchup`, `in-your-own-words`); `explaining-code` (from `how`, `why`, `teach`) |
| 30 | Principles | Five of pstack's principle skills, cited where they apply (option B). Design: `docs/design/2026-11-22-principles.md` |
| 31 | Diagnose and merge safely | The drift check before Merge; block only for a problem you can show; dismissals cite their disproof; blast radius; review sends repeated findings to feedback |
| 32 | Decide by evidence | `driving-the-app` (item B3); DONE WHEN as commands with a live and a performance check |
| 33 | The external flow and clean-up | `status.md`'s writer; "users see the change" recorded at Ready; release outputs reach operate; no extra Tier 1 approval for the readiness record; one "who decides" table; the remaining removals |

Every plan keeps aidlc's fixed decisions: people decide where the tiers file's decisions table says, the AI never
approves or merges, the product owner owns intent and Ready, aidlc ships instructions only and stays host-neutral.
