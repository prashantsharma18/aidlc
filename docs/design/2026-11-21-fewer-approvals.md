# Fewer approvals: one decision once, and fewer at low risk

Date: 2026-11-21 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-21; to be recorded in ADR 0026 · Change list: items C1 (decisions by tier) and C3 (pre-approved standard changes). Item C6
(intent, route and Ready as one approval) is out of scope.

## For the reviewer
- Who decides: the framework owner, in this design's review and in ADR 0026.
- Tier and main risk: a framework change to gates. The main risk is that a decision a person used to make at low risk
  is no longer made, and a misunderstanding is caught only at the merge. The four decisions below are where a person
  still decides; everything else the AI states and a person may correct.
- What changed: one decisions-by-tier table in the tiers file decides where a person stops. A decision is asked once.
  At Tier 1 a person decides only Ready and Merge, and Release only when users see the change. Teams list their own standard changes in `AGENTS.md`; aidlc-start
  routes them as route S.

## Why
The owner raised "approval fatigue" at the start of the aidlc 6 work. With parallel lanes (ADR 0025), people's
decisions are the bottleneck: more lanes make more waits on people. An inventory of every person stop (2026-11-21)
counted, from start to release:

| Story | Person stops today |
|---|---|
| F0, Tier 1 | 7 |
| D1, Tier 1 | 8 |
| F1, Tier 1 | 13 (11 when intent is skipped) |
| F1, Tier 2 | about 17–19 |
| F1, Tier 3 | about 21, plus one per slice |
| F2, two repositories | about 25 |

Several stops are the same decision taken twice:
- at Tier 2 and 3, the spec, design and plan are each approved on the tracker and again as the pull request that
  merges them first (ADR 0020): the same person, the same file, the same version;
- the code owner's approval appears in both the verify and the review gates;
- the plan's restatement, then the hands-on build's restatement of the same approved bundle;
- the engineer reviews the diff before pushing, then decides each review finding on the same diff;
- the release approval is written in the readiness record and again in the change record;
- the intent's acceptance and the spec's approval, often by the same product owner.

And one gap: on F0 and D1, no person agrees the Tier 1 rating; only the AI rates it.

## Owner decisions (2026-11-21, in the session)
| Question | Decision |
|---|---|
| The aim | No decision asked twice, and fewer decisions at low risk (C1 and C3); not C6 |
| Tier 1 | Two blocking decisions: Ready and Merge, and Release only when users see the change |
| Standard changes | Each team lists them in its `AGENTS.md`, approved once by the tech lead |
| Tier 2 and 3 | Tier 2: Ready, Design + plan, Merge, and Release only when users see the change. Tier 3: the same four plus the specialists and the hands-on restatement per slice. Each pull request approval is the record |
| How it is built | Approach A: one decisions-by-tier table in the tiers file every stage reads |

## The decisions-by-tier table
This table goes into the tiers file. A person stops only where it says so.

| Decision | Who | Tier 1 | Tier 2 | Tier 3 | Recorded |
|---|---|---|---|---|---|
| **Ready**: the work, its acceptance criteria and its tier | product owner; the tier with whoever owns the risk (on F0, D1 and route S, the engineer who confirms the brief) | yes | yes | yes, with a specialist's spec review | Tier 1: the decider's word in the session or their own tracker entry, checked (ADR 0023). Tier 2 and 3: the approval of the spec's pull request, which merges first (ADR 0020) |
| **Design + plan** | tech lead or architect | no | yes: one pull request approval that merges design and plan first | yes, with the specialists | the pull request approval |
| **Merge** | a code owner who did not write the change, after a non-author PASS | yes; the code owner sees spec, plan and code together | yes; every affected area | yes; the security specialist when the change touches secrets, permissions, tool calls, dependencies or prompts | the pull request |
| **Release** | release approver | only when users see the change | only when users see the change | always; a named approver and a rehearsed rollback | change management, cited in the readiness record |

"When users see the change": a change behind a flag that is still off needs no release decision until the flag goes on;
turning a flag on is the release.

Where a pull request approval is the record, the AI writes the tracker entry from it, with how it was confirmed, and
asks before posting (ADR 0023). When the AI cannot read the review tool, the decider confirms in the session.

## What stops being a separate stop
| Today | After |
|---|---|
| Spec, design and plan approved on the tracker and again as a pull request | The pull request approval is the record |
| The code owner's approval in the verify gate and the review gate | Once: Merge |
| The intent's acceptance and the spec's approval | Both inside Ready |
| The plan's restatement, then the hands-on build's restatement of the same bundle | The AI states its restatement; the person may correct it. It waits only at Tier 3 (hands-on, per slice) or where the bundle's MODE says |
| The engineer reviews the diff before pushing, then decides each finding | Once: deciding the findings is the diff review |
| The release approval in two records | The readiness record's decision cites the change-management record |
| At Tier 1, design "none needed" as a stop | The AI states it in the plan; the code owner sees it at Merge |

A stage that is not a decision for its tier still runs and still writes its document. It states what it did, in the
document and in the session, and goes on. A person who disagrees says so, and the stage revises.

## Kept at every tier, unchanged
- A new dependency, a quality-bar exception, and an assertion change (the criterion's owner decides).
- Checkpoints where the bundle's MODE puts them.
- The person pushes: the AI holds no push credential.
- Every decision in operate, feedback and onboard, and every `parallel-lanes` person action.
- The AI never approves or merges (ADR 0023).

## Standard changes (C3)
- **Where.** A "Standard changes" section in the team's `AGENTS.md`. Each class names what qualifies, its limits, and
  the evidence it needs. The tech lead approves the list once, in a pull request, as any rule.
- **Suggested classes** (onboard proposes them; the team edits them):
  - a recipe commit with an approved tool and version;
  - a dependency patch or minor bump within the team's policy: no new dependency, never a major version;
  - a D1 defect fix that stays Tier 1.
- **Route S (standard).** `aidlc-start` checks the work against the list and its limits. A match takes route S: a
  brief that names the class, which the engineer confirms (with the tier, closing the F0/D1 gap), then build, verify
  and review. It skips intent, spec, design and plan approval.
- **What still holds.** The code owner reviews and merges the pull request after a non-author PASS. The evidence file
  names the class and shows its limits held. For a listed recipe class, the build's separate recipe-review pause is
  lifted: the evidence file's Recipe commits section shows the re-run, and the code owner reads it at Merge.
- **When the work grows.** If it goes past a limit (a major version, a new dependency, a Tier 2 risk), the AI stops
  and the work takes its normal route. It never stretches a class.

## What changes in aidlc
| New | Changed |
|---|---|
| ADR 0026: decisions by tier and standard changes. It amends ADR 0020 (the pull request approval is the record), ADR 0015 (route S) and ADR 0012 (the recipe pause for a listed recipe) | The tiers file: the decisions-by-tier table, and all six copies (`aidlc-start`, `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-plan`, `aidlc-review`) made identical (today three carry "(generated)" in the title) |
| A "Standard changes" section in the `AGENTS.md` template and the starter copy | Each stage's Gate: one identical line, "A person decides here only where the tiers file's decisions table lists this decision; otherwise state what you did and go on." |
| Route S in `aidlc-start`, `using-aidlc` and `docs/operating-model/routes.md` | Intent, specify, design, plan, build, verify, review and release: the duplicates removed; restatements stated, not waited on, outside Tier 3 hands-on and MODE checkpoints |
| | `aidlc-onboard` proposes the three standard classes; the decisions sheet in `docs/operating-model/adoption.md` is redrawn from the table; `docs/operating-model/tiers.md` matches the skill copy |

aidlc still ships no code and needs no code-host feature (ADR 0024).

## How it is tested
- **Free structure tests:** the table is identical in all six copies; every stage Gate carries its one line; route S
  appears wherever routes are listed; the `AGENTS.md` template has the Standard changes section; no stage asks for a
  decision the table does not list for that tier.
- **Behaviour evals** (written now, run when an API key or token is available):
  1. a Tier 1 story does not stop for plan approval, and does stop at Merge;
  2. a listed minor dependency bump goes straight to build; a major bump is refused as standard and takes its normal
     route;
  3. at Tier 2, design and plan are approved once, by the pull request;
  4. a restatement is stated at Tier 1 and waited on at Tier 3 hands-on.
- **Existing tests:** many check today's gate wording. The plan lists every existing test it must change, for the
  owner's approval.

## Out of scope
- C6: intent, route and Ready as one first approval.
- Copilot and Codex adapters (parked).
- Automatic merges: a person always merges.

## Risks
- **A misunderstanding is caught later.** At Tier 1 no one approves the plan before building, so a wrong plan shows at
  Merge. The stated restatement and plan, which the person may correct at any time, limit it; Tier 1 is small and
  reversible by definition.
- **A standard class is stretched.** The limits are written in `AGENTS.md`, the evidence file shows them, and the code
  owner checks them at Merge; the AI stops when a limit is passed.
- **The pull request as the record needs the review tool.** When the AI cannot read it, the decider confirms in the
  session (ADR 0023), as today.

## Open for the plan
- The version: 7.0.0 (teams see fewer decisions, a behaviour change) or 6.2.0. Recommended: 7.0.0.
