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

File paths in the reports point at the reviewers' scratch copy of pstack; the same files are in the public repository.

## The owner's decisions (2026-11-22, in the session)
| Question | Decision |
|---|---|
| Which plan first | Connect the flow (Plan 27) |
| pstack text | Adapt its text where it helps, with pstack's MIT notice in `skills/NOTICE` |
| Existing tests and word caps | Each plan lists every existing test it must change and every word cap it must raise, for the owner's approval |
| These reports | Kept here, so the plans can cite them |

## The proposed order
| Plan | Theme | Content |
|---|---|---|
| 27 | Connect the flow | `story-run` (D1): one start after each decision; one route table; the story branch, the push of each document pull request, where an approval is recorded, the `merged` row, the way back to build after a red run or a finding, and a hand-off message at the end of every stage; the cuts that free the words (the placement paragraph, duplicate sentences, verify's PR description, the harness headers, the unused progress-note section) |
| 28 | Write plainly | `writing-plainly` (from `bro`, `technical-writing`, `unslop`, `ketchup`, `in-your-own-words`) at every moment a person reads or decides; `explaining-code` (from `how`, `why`, `teach`) |
| 29 | Diagnose and merge safely | The drift check before Merge; competing causes; back out a failed attempt; the shared premise after two failed fixes; block only for a problem you can show; fix every instance; dismissals cite their disproof; blast radius; review sends repeated findings to feedback |
| 30 | Decide by evidence | `driving-the-app` (item B3); spikes; DONE WHEN as commands with a live and a performance check; explain the number |
| 31 | The external flow and clean-up | `status.md`'s writer; "users see the change" recorded at Ready; release outputs reach operate; no extra Tier 1 approval for the readiness record; one "who decides" table; the remaining removals; the 12 principles; `worker.md` and a shorter `parallel-lanes` lane |

Every plan keeps aidlc's fixed decisions: people decide where the tiers file's decisions table says, the AI never
approves or merges, the product owner owns intent and Ready, aidlc ships instructions only and stays host-neutral.
