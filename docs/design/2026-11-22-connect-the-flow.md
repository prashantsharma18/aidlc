# Connect the flow: one start per decision, playbooks, and every hand-off defined

Date: 2026-11-22 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-22; to be recorded in ADR 0028 (story-run and the AI's push) and ADR 0029 (tests first, pstack's way) ·
Change list: item D1 (one autonomous lane), and the gaps G1–G4, G6, G10, G11 and the cuts R3, R5, R6, R9, R10 from
`docs/research/2026-11-22-pstack-review/3-tools-removals-and-flow.md`. Research: `docs/research/2026-11-22-pstack-review/`.

## For the reviewer
- Who decides: the framework owner, in this design's review and in ADRs 0028 and 0029.
- Tier and main risk: a framework change to how work moves from stage to stage, to who pushes, and to the tests-first
  gate. The main risks are an untested change that the AI judged "impractical to test", and an AI push credential
  used beyond its own branch.
- What changed: a person starts `story-run` once per decision, and it runs the stages until the next person's
  decision. The AI may push its own feature branch. Eight playbooks, adapted from pstack, say how each kind of work is
  done and proved. The AI may skip a failing test first when it judges it impractical, and logs why and what proof it
  used instead. Every stage hand-off is defined. People still decide where the tiers file's decisions table says, open
  each pull request, and merge.

## Why
aidlc is well connected inside a stage and disconnected between stages (research, report 1). A Tier 1 story has two
decisions, Ready and Merge, but a person types about ten commands, and six stages end without saying what runs next.
Several hand-offs are undefined: no stage names the story's branch, document pull requests have no push step, an
approval has no writer, most routes have no `merged` row, and a red CI run or a review finding has no way back to build
(report 3, G1–G4, G6, G10, G11). The routes pick which stages run, but nothing says how each kind of work is done
inside them; pstack's playbooks do (report 2).

## Owner decisions (2026-11-22, in the session)
| Question | Decision |
|---|---|
| Where `story-run` begins | From the start, stopping for people, as today's stages stop |
| How it runs a stage | In the same session, reading the stage's `SKILL.md` by path |
| Who pushes | The AI may push its own feature branch: never force, never the default branch, never tags, never merge or approve |
| How far the push goes | Every push to its own branch; the person opens the pull request |
| Playbooks | pstack-style playbooks, inside this plan |
| Tests first | pstack's way: the AI decides when a failing test first is impractical, skips it, and says why |
| pstack text | Adapt it where it helps, with pstack's MIT notice in `skills/NOTICE` |
| Parallel work | A separate plan (Plan 28): the agent schedules from the plan's dependency graph, the throughput checkpoint, one owner for coupled slices, a watch pass, CI watching; the agent drafts the queue and a person confirms it |
| Merge | Always a person |
| The version | 8.0.0 |

## Part 1: `story-run`
A new workflow skill (`metadata.kind: workflow`, ADR 0025), `skills/story-run/`, with the workflow sections (When to
use, Inputs, Steps, Stop if, Common excuses, Red flags, Rules) and `disable-model-invocation: true`: only a person starts
it (`story-run SHIP-12`).

| Step | What it does |
|---|---|
| Find the story | Read the story's index (`plans/<KEY>/README.md` in a repository, `stories/<KEY>/README.md` at a workspace root). No index: run `aidlc-start` first |
| Pick the next stage | The first row that is not `done`. A `waiting:` row resumes only when its decision can be had, as `parallel-lanes` already says (checked where its stage says, or the decider's word in this session) |
| Run it | Read that stage's `SKILL.md` by path (the stage skills are the folders beside this one) and every reference whose condition holds, and follow them in full. Every gate of the stage stays as it is |
| Go on, or stop | When the stage marks its row done and the tiers file's decisions table lists no decision for it, go on to the next row. Otherwise stop (below) |
| Before a stop | Write the wait into the row (`waiting: <decision> by <who>`) and give the stage's hand-off (Part 4). The next start, in this session or a new one, reads the index and goes on |

**It stops** wherever today's stages stop: a question to the product owner, Ready, Design + plan at Tier 2 and 3, a
Stop if, a MODE checkpoint, the Tier 3 restatement, the recipe pause; and after it pushes a branch whose pull request
is not open yet ("open the pull request for SHIP-12 slice 1"), and at Merge. It runs one slice at a time, in order;
running slices at the same time is Plan 28.

**The start is the go-ahead.** Every stage keeps `disable-model-invocation: true`. ADR 0028 records that a person's
start of `story-run` is the go-ahead for the stages up to the next person's decision, the rule ADR 0025 already uses for
lanes (a lane reads a stage's file by path once a person started it).

## Part 2: The AI's push (ADR 0028)
ADR 0026 keeps "the person pushes; the AI holds no push credential". ADR 0028 changes it:

| | Rule |
|---|---|
| Allowed | Pushing to its own feature branch: the story's code branch, a slice's branch, or a document pull request's branch, as the index's BRANCH lines name them |
| Never | A force-push, a push to the default branch, a tag, a merge, an approval, opening or closing a pull request |
| Needs | The team gives the AI a credential that can push feature branches and cannot push the default branch (the team's code host rules). Without one, the person pushes, as today, and `story-run` stops at the push |
| Stacked slices | Moving a slice with `git rebase --onto` needs a force-push, so it still asks the person (ADR 0025) |
| The verdict rule | Unchanged: a non-author verdict names its commit, and any later change outside `plans/<KEY>/` voids it |

## Part 3: Playbooks
A playbook says, for one kind of work, what to do, in what order, which practice to load and what proof that kind needs.
They are adapted from pstack's playbooks, with pstack's MIT notice in `skills/NOTICE`, and live in
`skills/story-run/references/playbook-<kind>.md`.

| Playbook | Typical route | Its own proof |
|---|---|---|
| feature | F0, F1, F2, C, G | the criteria's tests, and the bundle's DONE WHEN |
| bug fix | D1, D2, I | a reproduction first; the competing causes listed and the one that rules out the most tested; a failed attempt backed out before the next |
| performance | F1, C | a baseline measured on the default branch first; the number explained (what limits it, repeat runs) |
| refactoring | F1, C | today's behaviour pinned; the new code shown equivalent |
| visual change | F0, F1 | a baseline screenshot as the check |
| dependency bump | S, F1 | the manifest and lock-file diff; the changelog read; the full suite green |
| investigation | none (no code) | a written finding with its evidence; nothing merged |
| spike | from design or discover | outside the repository's source, time-boxed, never merged; its result written in the design note |

**How one is chosen.** `aidlc-plan` writes a `PLAYBOOK <kind>` line in each task bundle, chosen from the route and the
work item. Build and verify read the playbook the bundle names, from `story-run`'s folder, so a playbook works whether
`story-run` runs the stage or a person does.

**The limit.** A playbook, like a reference, never holds or lifts a gate: it has no Gate, Stop if, Common excuses,
Red flags or Rules section, and every stop stays in the stage skills. The validator checks it.

## Part 4: Every hand-off defined
| Gap | Fix |
|---|---|
| G1 No branch is named | `aidlc-start` writes BRANCH lines in the index: at Tier 1 the code branch (`<type>/<KEY>-<slug>`); at Tier 2 and 3 also the spec's pull request branch and the design-and-plan pull request branch. Every stage reads its branch there |
| G2 Document pull requests have no push | `aidlc-specify` and `aidlc-plan` end by pushing their branch (Part 2), then stop: "open the pull request" |
| G3 An approval has no writer | A document merges first, so its own file is not edited after the approval. The story index carries the record: when the next start finds the pull request approved (checked in the review tool, or the decider says so in the session), it marks the row `done: approved in pull request <n> by <who>, <how it was confirmed>` on its own branch (ADR 0023). The document's approval slot points to its pull request |
| G4 The `merged` row is missing | `aidlc-start` writes a `merged` row on every route |
| G6 No way back from a red run or a finding | A red CI run, or a high or medium review finding the engineer accepts, returns the work to build in the same slice: the build row reads `to do: fix <what>`, and `story-run` runs build, then verify and review again |
| G10, G11 Silent hand-offs | Every stage ends with a short hand-off: what it did, the next row, who it waits on, and the tracker move to suggest (the AI asks before posting, ADR 0023). Plan 29's `writing-plainly` refines the wording |
| One route table (report 1, X3) | The table in `using-aidlc` is the one source of which stages each route runs; `docs/operating-model/routes.md`, `lifecycle.md`, `aidlc-start` and the README point to it; a test checks every listing agrees |

## Part 5: Tests first, pstack's way (ADR 0029)
| | Rule |
|---|---|
| Default | Write the failing test first when the change has a cheap local test |
| May write no test | When the AI judges the test impractical: the test path is unclear, the test is expensive to build, or there is nothing sensible to assert |
| When it writes none | A decision-log row, `no test for <criterion>`, says why and what proof it used instead (a command's output, a live check, a screenshot) |
| Who sees it | The tests reviewer lists every criterion with no test, with its reason; the code owner reads them at Merge |
| Unchanged | Never editing an existing assertion; a test marked skip is still the Quality bar's stop; no new dependency without asking; every Stop if |

## Part 6: The cuts that free the words
Four stage skills are near their word limits (Plan 26, item W1). These cuts come first:

| Cut | What |
|---|---|
| R3 | The placement paragraph copied into nine stages becomes one line that points to the index's "Runs in" column |
| R5 | The duplicate Decision 2 sentence in the `aidlc-design` and `aidlc-plan` Gates |
| R6 | `aidlc-verify` stops drafting the pull request description; `aidlc-review` owns it |
| R9 | The old harness's YAML header in three templates (nothing reads it) |
| R10 | The progress note's unused "Context gaps noticed" section |

## Kept, unchanged
- Every decision in the tiers file's decisions table (ADR 0026, ADR 0027); the product owner owns intent and Ready.
- A person opens every pull request and merges; the AI never approves or merges (ADR 0023).
- Never editing an existing assertion; the gates stay in each stage's `SKILL.md` (Plan 26).
- aidlc ships instructions only and needs no code-host feature (ADR 0024); `story-run` names the tool's own features only
  as "where your AI tool has one".

## How it is tested
- **Structure tests:** `story-run`'s sections, its stops and its "go on" rule; the route table has one source and every
  listing agrees; the BRANCH lines and the `merged` row on every route; every stage ends with a hand-off; the eight
  playbooks exist, are named from the bundle template's PLAYBOOK line, and hold no gate; ADR 0028's push rule in build,
  specify, plan and `story-run`; ADR 0029's rule in build and the tests reviewer.
- **The validator:** a playbook holds no gate heading (as a stage skill's reference).
- **Behaviour evals** (written, run when an API key or token is available): `story-run` stops at Ready; it runs a Tier 1
  design without stopping; it pushes its own branch and never the default branch; it stops at Merge; a criterion with no
  test has its decision-log row.
- **Existing tests:** several pin "the person pushes", "tests first" wording, the placement paragraph and the loads
  table; some eval cases expect tests first strictly. The plan lists every one for the owner's approval, with any word
  limit it must raise.

## Out of scope
- Plan 28, parallel work like pstack: the agent schedules from the plan's DEPENDS ON graph and the throughput
  checkpoint; coupled slices go to one lane; a watch pass finds stuck lanes; lanes watch CI and fix a red run; lanes run
  `story-run`; the agent drafts `QUEUE.md` and a person confirms it.
- Plan 29 `writing-plainly` and `explaining-code`; Plan 30 diagnose and merge safely; Plan 31 decide by evidence
  (`driving-the-app`, item B3); Plan 32 the external flow, the remaining removals, the principles and `worker.md`.
- The AI opening pull requests, force-pushing, merging or approving.

## Risks
- **Untested changes.** The AI may call a test impractical to save effort. Every skip is a decision-log row with its
  reason and its other proof, the tests reviewer lists them, and the code owner reads them at Merge.
- **The push credential.** Scoped to feature branches by the team's code host rules; without it, the person pushes.
- **A long session.** Every stop writes the index, so the next start can be a fresh session.
- **The plan's size.** Two ADRs, `story-run`, eight playbooks, the hand-offs and the cuts. If the plan is too large, the
  playbooks become their own plan before the owner approves it.

## The version
aidlc 8.0.0, a major release: two kept rules change (who pushes, and tests first).
