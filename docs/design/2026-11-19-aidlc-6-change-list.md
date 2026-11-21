# aidlc 6: the full change list

Status: draft for planning, 2026-11-19. Nothing here is built yet, except phases 0 and 1, built in Plan 20
(`docs/plans/2026-11-19-plan-20-gates-that-hold.md`); ADRs 0019–0021 proposed. Phase 2a is planned in Plan 21
(`docs/plans/2026-11-20-plan-21-multirepo-foundations.md`); ADRs 0022 and 0023 proposed. Gate changes (marked **ADR**) need a design
decision first, because AGENTS.md forbids weakening a gate without one.

**Superseded in part by ADR 0024 (2026-11-20, Plan 22):** aidlc ships no scripts and no CI workflows. Section 6
marks each item as built and then removed, kept as instructions, dropped, or still open.

This list gathers everything found and agreed in the review of 2026-11-17 to 2026-11-19:

- the review of aidlc 5.0.0's skills, agents, starter files, scripts and CI;
- the research on software factories, approval fatigue and enforcement (pstack, DORA, Anthropic);
- the independent multi-repo review against `~/work/shipment-tracking`;
- the research on where documents live (Home Repo, Spec Kit, AWS AI-DLC, BMAD, OpenSpec, HumanLayer, ADR practice).

The proposed flow is drawn at https://claude.ai/artifact/WMtSUvyfobDmr9iL18ZjCa (private to the owner).

## The target, in one paragraph

People make up to four decisions: **Ready**, **Design + plan** (Tier 2 and 3), **Merge** and **Release** (Tier 2 and
3). Each decision is a pull request approval, or a change-management record for release.

Between the decisions, agents work in parallel lanes. Each lane has its own worktree or CI runner. Lanes pull the
next ready item from the tracker. Each one is checked by an independent verifier and by mechanical CI checks.

Rules are enforced by code first and prose last. Code that ships together lives in one repository. When repositories
must stay separate, a home repo holds the shared facts and each repository holds its own part. The two stay in step
by version pins, generated status and an automatic change-request flow.

## 1. Problems found (why we change)

| ID | Problem | Evidence |
|---|---|---|
| P1 | The key rules hold only by instructions: MAY CHANGE, unchanged assertions, no new dependency, the Quality bar, MUST NOT paths. There are no hooks, no Edit denies in the repo starter, and no CI check. | `starter/repo/.claude/settings.json`; `aidlc-build` step 9 is a self-check |
| P2 | Gates before merge are self-attested text: `CONFIRMED`, `checkpoint … confirmed by`, `STATUS done`. Neither `aidlc-build` nor `run_slices.py` checks that a bundle was approved. | `run_slices.py` preflight; `aidlc-build` steps |
| P3 | Adopters get weaker CI than aidlc itself. `ai-review.yml` floats on `@v1`, uses a generic prompt, isn't required, and reads AGENTS.md from the PR branch. The reviewers' "rules from the protected branch" has no mechanism behind it. | `starter/repo/.github/workflows/ai-review.yml`; `aidlc-review` step 3 |
| P4 | There is little evidence the gates hold. The last eval run covered 20 of 28 cases, one run each with no baseline, and 5 failed. It predates 9 later skill commits. The 6 build-gate cases have never run here. | `evals/results/` |
| P5 | Approval fatigue. A Tier 2 story needs about 8 approvals and about 15 documents. | Stage skills; DORA on change approval |
| P6 | The guarantees work in Claude Code only. In Copilot, Codex and Cursor every rule is enforced only by the instructions. | Starter settings, agents, runner |
| P7 | Multi-repo status is hand-marked. `story_status.py --check-release` reads local clones, so it fails for released SHIP-1 while `customer-portal` sits on SHIP-2's branch. | Run against `~/work/shipment-tracking` |
| P8 | The contract is pinned by a code comment. Tag `api-v1.7.0` was cut before review and CI, and the portal built on it. | `customer-portal/src/api/shipments.ts:1`; SHIP-1 feedback L9 |
| P9 | Child documents point at paths that moved. The SHIP-1 bundles and PR descriptions cite `plans/SHIP-1/spec.md`, which no longer exists. | `shipments-api/plans/SHIP-1/*`, `customer-portal/plans/SHIP-1/*` |
| P10 | GitHub has no required check that spans repositories. A child's CI cannot read the home repo. Merge queue on private repos needs Enterprise Cloud. Rulesets on private repos need a paid plan. | GitHub docs (multi-repo review sources) |
| P11 | An F2 story can be rated Tier 1, so half a story could auto-merge and ship. | `tiers.md` Tier 1 column |
| P12 | A code repo's AI review can't see the spec, which lives in the home repo. | `ai-review.yml:19` |
| P13 | Demo hygiene: `carrier-rates/` isn't in the root `.gitignore`. SHIP-2, a one-repo story, has a root README. No repo has a remote or CI. | `~/work/shipment-tracking` |

## 2. Changes

Each change names what it fixes, where it lands in aidlc, and whether it needs an ADR.

### A. Make the gates real (enforce by code, not prose)

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| A1 | A required CI check, `check_slice.py` (stdlib), that fails a PR when: a changed path is outside MAY CHANGE or inside MUST NOT; an existing assertion changes outside AMENDED ASSERTIONS or a `Recipe:` commit; a manifest or lockfile changes; a suppression or skip marker appears without reason, owner and expiry; or the test count drops. CI runs the base branch's copy of the script. | P1 | `starter/repo/scripts/`, `starter/repo/.github/workflows/ci.yml`, `aidlc-build`, `reviewer-compliance` | no |
| A2 | Decisions are pull request approvals: Ready = the spec PR; Design + plan = the design/plan PR; Merge = the code PR. CI checks that the bundle a PR builds from is unchanged since the commit where it was merged. | P2 | `aidlc-specify`, `aidlc-design`, `aidlc-plan`, `aidlc-build`, templates | **ADR** |
| A3 | The hardened `ai-gates` workflow becomes the starter: pinned SHAs, key scrubbing, fail-closed, a required check, AGENTS.md read from the base branch. | P3 | `starter/repo/.github/workflows/` | no |
| A4 | Edit denies in the repo starter for `AGENTS.md`, `.claude/**`, `scripts/check_*`, `.github/workflows/**`. | P1 | `starter/repo/.claude/settings.json` | no |
| A5 | Optional: a thin Stop hook that runs `check_slice.py` locally for fast feedback. **Decision D3.** | P1 | plugin `hooks/hooks.json` | decision |
| A6 | `aidlc-feedback` works like `/correct`. Fix each repeated mistake at the highest level: architecture, then types, then a lint rule whose error names the fix, then a test, docs last. Prove each check fails on a real past mistake. Keep a rule-to-enforcer table in AGENTS.md. | P1 | `aidlc-feedback`, AGENTS.md template | no |
| A7 | Run all 28 evals, the 6 build-gate cases included, in a CI container on every release: 3 runs, with a baseline arm, pinned model. | P4 | `.github/workflows/`, `evals/README.md` | no |
| A8 | Note in the docs and in onboard that outside Claude Code only the CI checks (A1, A3) hold. | P6 | README, `aidlc-onboard` | no |

### B. Reviewers and verification

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| B1 | An independent verifier runs in its own session, on its own runner or worktree, at the PR head. It never sees the author's chat. Its token can read and comment, but not push. | P3 | new agent `verifier`, `aidlc-review` | no |
| B2 | The bug, security, tests and compliance reviewers move into the verifier's session. A finding counts only with a run that shows it. Compliance's mechanical rules move to A1. | P3, P5 | `agents/reviewer-*`, `aidlc-review` | no |
| B3 | `aidlc-onboard` generates a per-repo verification skill and feature map: launch, a doctor check, driving each feature, evidence, cleanup. The evidence table carries recordings and screenshots. | P5 | `aidlc-onboard`, `aidlc-verify`, `testing-in-browser` | no |
| B4 | A decision log: each judgement call in a lane becomes one row (time, decision, reason, evidence), audited with the PR. | P5 | `aidlc-build`, progress-note template | no |
| B5 | The spec and design PRs get a template check (criterion IDs, a named decider per edge case, the repo that proves each criterion) and an advisory AI pass for ambiguity. | P5 | `scripts/`, story repo workflow | no |

### C. Fewer approvals, by risk

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| C1 | Four decisions by tier. Tier 1: Ready, plus Merge after the verdict with sampled review. Tier 2: Ready, Design + plan, Merge, and Release when users see the change. Tier 3: as today. | P5 | `using-aidlc`, `tiers.md`, all stage skills | **ADR** |
| C2 | Tier 1 auto-merge after green checks and the verifier's verdict. A person reviews a sample, for example 1 in 5. **Decision D2.** | P5 | `aidlc-review`, branch protection guidance | **ADR** |
| C3 | Pre-approved classes of standard change: recipe commits, dependency bumps within policy, D1 fixes. | P5 | `tiers.md`, `aidlc-plan` | **ADR** |
| C4 | The mechanical parts of the plan checklist become a validator: every criterion maps to a test, every field is filled, MODE fits the TIER, PINS are current. People judge only approach and risk. | P5 | `scripts/`, `aidlc-plan` | no |
| C5 | Measure every gate: wait time, the "approved unchanged" rate, and DORA metrics. A gate that nearly always approves unchanged gets automated or sampled. | P5 | new `scripts/` report; OTel lab | no |
| C6 | Merge intent, route and Ready into the first approval. | P5 | `aidlc-start`, `aidlc-intent`, `aidlc-specify` | **ADR** |

### D. One autonomous lane

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| D1 | An entry skill, `aidlc-run KEY`, picks the route and runs plan, build, verify, review and CI fixes in one worktree, until the PR is ready or a STOP IF fires. | P5 | new skill; stage skills become its steps | no |
| D2 | The plan draws slices as a dependency graph. Independent slices run in parallel sub-sessions as sibling PRs. A PR stacks only on the PR it builds on. | speed | `aidlc-plan`, `aidlc-build`, `run_slices.py` | no |
| D3 | Shorter stage skills: route-specific branches (G, F0, D1, parts, revisions, amendments) move into playbooks under the entry skill. | P5 | skills restructure | no |

### E. The conveyor: parallel work and pulling the next item

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| E1 | The tracker is the queue. The `aidlc:ready` label is set automatically when the spec PR merges. | speed | `aidlc-start`, workflows | no |
| E2 | A dispatcher, built first as `run_queue.py` (decision D1). It runs N headless lanes, each in its own git worktree, and pulls the next ready item when a slot frees. A GitHub Actions version (claude-code-action, with a `concurrency` group) comes later. | speed | `starter/repo/scripts/`, `starter/workspace/scripts/` | no |
| E3 | Lock contracts, not files: one open change per contract. Take any file lock only after plan approval, never at queue time. | Flaw in the first proposal | dispatcher | no |
| E4 | A slot frees when the PR is ready for people. The lock frees at merge. | speed | dispatcher | no |
| E5 | A separate CI environment and spend cap for the dispatcher's key. Today `ai-gates` needs approval per run. | speed | repository settings, docs | no |

### F. Multi-repo: placement, sync and gating

| ID | Change | Fixes | Lands in | ADR |
|---|---|---|---|---|
| F1 | Guidance: code that ships together goes in **one repository** (Home Repo article, multi-repo review). `aidlc-onboard` and route G's design step recommend it. **Decision D4** for the demo. | P7–P10 | `aidlc-onboard`, `aidlc-design` (new system), docs | **ADR** |
| F2 | The placement rule: **each fact has one owner, and only the owner changes it.** The home repo holds the index, intent, spec, design note, ADR drafts, contract draft, coordination plan, status, release records and incidents. The child repo holds the plan, bundles, progress notes, evidence, PR description, review record, single-repo ADRs, the published contract and the code. | clarity | `starter/workspace/stories/README.md`, stage skills | no |
| F3 | ADRs by scope. A single-repo ADR moves to that repo's `docs/adr/`. A cross-repo ADR stays in the home repo's `docs/adr/`, with a one-line pointer in each affected repo. Draft names use the story key (`<KEY>-adr-<n>`). | P9 | `aidlc-design`, ADR template | no |
| F4 | Pin by version and commit, not by path. Each child records the spec version, the home commit SHA and the path. Paths under `stories/<KEY>/` are frozen once a child pins them. | P9 | `aidlc-plan`, bundle template, story index | no |
| F5 | Each child keeps a read-only copy of its own acceptance criteria and non-goals, with a SOURCE line naming the home commit. The child's CI and AI review then never need the home repo. | P10, P12 | `aidlc-plan`, templates | no |
| F6 | Status comes from GitHub: PR merge state and merge SHA, through the API. Remove the hand-marked "merged" rows. `--check-release` no longer reads local clones. | P7 | `story_status.py`, story index template | no |
| F7 | A drift and integration workflow in the home repo clones the children, compares pins with the current versions, and posts a required **story-gate** status on each child PR, through a GitHub App. | P10 | home repo workflow, App setup docs | no |
| F8 | The integration check runs **before the last part merges**, against per-PR container images (pinned digests in the home repo's compose). The verifier uses that environment. | P10 | `aidlc-release` (moves earlier), workflows | no |
| F9 | The contract becomes a versioned artifact (the Spec Kit rule, decision D5): the provider owns `openapi.yaml` and publishes each version only from protected `main` (tag `api-vX.Y.Z`); each consumer pins the exact version in a file CI reads; the consumer's CI checks its client and test fakes against that version; the provider's CI compares the new contract with the last published one and fails on a breaking change unless the major version rises with the consumers' agreement. Changes are proposed at the source. Pact stays a documented next step for teams with many services. | P8 | `designing-apis`, `aidlc-design`, `aidlc-release`, starter CI | diff tool: ask |
| F10 | Tokens by role: one GitHub App each for the writer, the reader and the gate. Mint every token with explicit `repositories` and permissions. Split the design lane so each PR comes from a lane scoped to its repo. | P10 | dispatcher, workflows, docs | no |
| F11 | Decision 2 for multi-repo work is the home design PR plus each part's plan PR. F7 enforces their order. | P2 | `aidlc-design`, `aidlc-plan` | **ADR** |
| F12 | F2 work is always at least Tier 2 for merge and release: no auto-merge, and Decision 4 always happens. | P11 | `tiers.md`, `aidlc-start` | **ADR** |
| F13 | Tracker links are GitHub permalinks at the pinned commit. | P9 | `aidlc-start`, templates | no |
| F14 | Story repo hygiene: CODEOWNERS for `stories/**`; `.gitignore` generated from `WORKSPACE.md`; a named owner for the runtime environment (compose, flags). | P13 | `aidlc-onboard`, workspace starter | no |
| F15 | One coordinator, many scoped lanes (decision D7). A coordinator session reads every repository and plans. It fans out one lane per repository in parallel, each with its own PR, owners and CI. The PRs are linked by story key and merged in dependency order. No session writes to two repositories. | speed, scale | `aidlc-run` coordinator mode, `run_queue.py`, workspace settings | **ADR** |

### G. Change requests from a child to the home repo (automatic except the decision)

| ID | Change | Lands in | ADR |
|---|---|---|---|
| G1 | When a lane hits a change to a shared fact, it stops and opens a change-request issue in the home repo. Its token may create issues there, but not edit files. | `aidlc-build` STOP IF, lane token | no |
| G2 | The stopped lane gives up its slot, and the dispatcher pulls other ready work. | dispatcher | no |
| G3 | The issue's label starts the story lane. It drafts the new spec or contract version, the impact on each part and the updated consumer tests, as one PR. | `aidlc-specify` / `aidlc-design` amendment mode | no |
| G4 | An additive contract change with every consumer test green is pre-approved and merges on its own. A breaking change or a criterion change goes to the owner with a one-page summary. **Decision D8.** | `aidlc-design` | **ADR** |
| G5 | The merge updates the home records (version, coordination plan, cross-repo ADR, status). The drift check re-queues the affected parts, with the stopped one first. | home workflow, dispatcher | no |
| G6 | Each affected part records "not affected" automatically when its tests pass on the new version. A person re-approves only when the part's criteria or allowed files change. | `aidlc-plan` | no |

### H. Release reflexes

| ID | Change | Lands in | ADR |
|---|---|---|---|
| H1 | The stop criteria (signal, threshold, duration) drive automatic rollback in the flag or canary tool. People approve the plan, and the machine rolls back. | `aidlc-release`, `adding-observability` | no |
| H2 | A post-release agent drives the new build with the verification skill and opens fix items through the normal lane. | new automation | no |
| H3 | An incident agent drafts the timeline, hypotheses and work item. On-call acts. | `aidlc-operate` | no |

### I. Demo fixes: parked (decision D4, no work on the shipment-tracking demo for now)

| ID | Change |
|---|---|
| I1 | Fix the stale `plans/SHIP-1/spec.md` links in both child repos (after F4, re-pin to the home commit). |
| I2 | Add `carrier-rates/` to the root `.gitignore`, or generate the file from `WORKSPACE.md` (F14). |
| I3 | Remove or justify the root README for one-repo story SHIP-2. |
| I4 | Give each repo a remote and CI before demonstrating A1, A3 or F7. |

## 3. Decisions (owner, 2026-11-19)

| ID | Decision | What it changes |
|---|---|---|
| D1 | **Local worktrees first.** | E2 is built as `run_queue.py`: N headless `claude -p` lanes, each in its own git worktree, using the owner's subscription, so lanes spend no API key. The GitHub Actions dispatcher comes later. The verifier (B1) runs as a separate local session in its own worktree. Locally, a lane's write scope (F10) comes from per-lane Claude Code settings: Edit allowed only in its worktree, which the sandbox also enforces. GitHub App tokens apply once lanes move to CI. |
| D2 | **Yes, pilot Tier 1 auto-merge with sampled review.** | C2 goes ahead after its ADR. It depends on required checks, so it is subject to the D6 limit below. |
| D3 | **Yes, a thin local Stop hook.** | A5 goes ahead. It runs the same `check_slice.py` as CI, for fast feedback only. CI stays the gate on record. |
| D4 | **No action on the shipment-tracking demo.** | I1–I4 are parked. F1 stays as framework guidance only. The demo's findings remain evidence for the problems. |
| D5 | **OpenAPI package, the Spec Kit rule** (changed 2026-11-20 from "Pact broker"). | F9 uses a versioned OpenAPI contract: one side owns it, consumers pin an exact version, changes are proposed at the source, readiness is checked against exact versions (GitHub Spec Kit, contract-driven development). No broker or account is needed. Why the change: Pact came from the multi-repo review's general research, not from any AI-delivery framework studied; Spec Kit, the one framework with contract guidance, uses pinned versions; the owner prefers standard, simple mechanisms. Pact (`can-i-deploy` across many services) stays a documented next step. |
| D6 | **GitHub Free.** | **Limit:** on Free, branch protection, rulesets and required status checks work only on **public** repositories. aidlc itself is public, so its own gates hold. For adopters' repositories, the docs must say plainly that A1, A3, F7 and C2 need either public repositories or a paid plan (Pro for a personal account, Team for an organisation). Without required checks, auto-merge (C2) must not be turned on. Merge queue is not used. |
| D7 | **One coordinator, many scoped lanes.** One session never writes to several repositories. A coordinator session may read every repository and plan the whole change. It then fans the work out to one lane per repository, in parallel. Each lane opens its own PR, reviewed by that repository's owners and checked by that repository's CI. The PRs are linked by the story key and merged in dependency order. | F15 is replaced by this rule. **Why:** advanced teams that work at scale do it this way. Google shards a large change "based upon project boundaries and ownership rules" and puts "each individually sharded change through an independent test-mail-submit pipeline" (Software Engineering at Google, ch. 22). Spotify's Honk runs many background agent sessions in parallel through Fleet Management, opening one verified PR per component. Sourcegraph Batch Changes and multi-gitter turn one change spec into one PR per repository. Tools that let one session write many repositories (Cursor or Copilot multi-repo sessions, the Home Repo pattern) suit one developer's speed, but they lose per-repo ownership, token scope and CI at scale. Fanning out in parallel loses no speed. |
| D8 | **Yes.** An additive contract change, where every consumer's check against the new version is green, is pre-approved and merges on its own. | G4 goes ahead after its ADR. With D5 (OpenAPI package), "additive and every consumer green" means: the provider's contract diff finds no breaking change, and each consumer's contract check passes against the new version. |
| D9 | **oasdiff for the provider's contract diff** (2026-11-20). | F9's "diff tool: ask" is answered. The provider's `contract-check` runs `oasdiff breaking --fail-on ERR --allow-external-refs=false` against the last published tag. It uses the release binary at a pinned version, checked against its published sha256: no action image built at run time, no account, and no upload of the contract. |

## 4. Suggested order

Each phase pays off on its own. A later phase depends on the one before it.

| Phase | Items | Why this order |
|---|---|---|
| 0 · Hygiene | A3, A4, A8, plus the D6 note on plans and visibility | Cheap, and removes known gaps (I1–I4 parked by D4) |
| 1 · Gates that hold | A1, A2, A6, A7, C4, F12 | Parallel agents on soft gates only make unchecked work faster |
| 2 · Multi-repo foundations | F1–F7, F9–F11, F13, F14 | Placement and sync must be right before lanes run in parallel |
| 3 · One lane | D1, D2, B1–B4, D3 | Prove one autonomous lane on SHIP stories |
| 4 · The conveyor | E1–E5, G1–G6, F8 | Parallel lanes and automatic change requests |
| 5 · Fewer approvals | C1–C3, C5, C6, B5, F15 | Needs the hard checks from phases 1–3 underneath it |
| 6 · Release reflexes | H1–H3 | Last, once releases come from the conveyor |

The plugin's major version is 6.0.0 (approved 2026-11-20), because routes, templates and gates change.

## 5. Sources

- pstack (Lauren Tan): https://github.com/cursor/plugins/tree/main/pstack; talk https://ai.engineer/talks/O_zcc6Xl12g-all-code-is-slop-except-mine
- DORA, streamlining change approval: https://dora.dev/capabilities/streamlining-change-approval/
- Home Repo pattern (Matt Pocock): https://www.aihero.dev/the-home-repo-pattern; video https://www.youtube.com/watch?v=hWe-j78vNpc
- Spec Kit contract-driven development: https://github.com/github/spec-kit/blob/main/docs/how-to/contract-driven-development.md
- AWS AI-DLC workflows: https://github.com/awslabs/aidlc-workflows
- OpenSpec stores: https://github.com/Fission-AI/OpenSpec
- HumanLayer thoughts: https://github.com/humanlayer/humanlayer
- Zuul gating: https://zuul-ci.org/docs/zuul/latest/gating.html
- Pact can-i-deploy: https://docs.pact.io/pact_broker/can_i_deploy
- GitHub App tokens: https://github.com/actions/create-github-app-token
- GITHUB_TOKEN scope: https://docs.github.com/en/actions/concepts/security/github_token
- Large-scale changes at Google (ch. 22): https://abseil.io/resources/swe-book/html/ch22.html
- Spotify Honk:
  - https://engineering.atspotify.com/2026/6/code-with-claude-coding-is-no-longer-the-constraint
  - https://engineering.atspotify.com/2026/4/background-coding-agents-dataset-migrations-honk-part-4
- Sourcegraph on large-scale changes: https://sourcegraph.com/blog/large-scale-code-changes
- GitHub protected branches (plan availability): https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- ADR practice:
  - Nygard: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
  - Azure: https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record
  - Google Cloud: https://docs.cloud.google.com/architecture/architecture-decision-records

## 6. After ADR 0024 (2026-11-20)

Plan 22 (`docs/plans/2026-11-20-plan-22-instructions-first.md`) removed the code that phases 0 to 2a shipped, and
dropped every item that adds shipped code or needs a code-host feature. The code is kept under the tag `checks-v1`
(`docs/archive/checks-v1.md`). Phases 2b to 6 of section 4 are replaced by this table.

| Item | State after Plan 22 | Why |
|---|---|---|
| A1, A3, A4 (the denies on the scripts and workflows), A5, decision D3 | Built in Plan 20, then removed | Shipped code; it blocked a merge only through GitHub's required checks |
| C4 | Built in Plan 20, then replaced by the plan's checklist | Shipped code |
| F6, and F14's `.gitignore` generator | Built in Plan 21, then replaced: status from git, one release row per repository, a `.gitignore` line a person adds | Shipped code |
| F9's scripts and workflows | Built in Plan 21, then replaced by the commands in `designing-apis` (oasdiff, `sha256sum -c`, `git ls-remote --tags`) | Shipped code; the contract rule (decisions D5 and D9) stays |
| A2, A6, A8, F1–F5, F11, F12, F13, F14's owners | Kept as instructions; A8 and F13 reworded host-neutral | Process rules |
| A7 | Kept | aidlc's own CI, not a team's |
| B1, B2 | Done in part: reviewer agents in a fresh context read the evidence file, and a verdict names its commit | A verifier with its own token needs a code-host feature |
| B3, B4, C1, C3, C6, items D1–D3, H1, H3 | Open, as instructions only (item D2 without `run_slices.py`) | No shipped code needed |
| B5, C5 | Dropped | Each adds a script |
| C2, decision D2, G4, decision D8 | Dropped | Auto-merge needs required checks, a code-host feature (decision D6) |
| E1–E5, decision D1, F15's `run_queue.py`, G1–G3, G5, G6, H2 | Dropped | A dispatcher, workflows, labels or tokens: shipped code or code-host features. Decision D7's rule (one session writes one repository) stays as guidance |
| F7, F8's workflows, F10 | Dropped (they were phase 2b) | A home workflow, a GitHub App and required statuses; `aidlc-release` keeps its integration check |

The plugin's major version: 6.0.0 (approved 2026-11-20).

## 7. After Plan 23 (2026-11-21)

Plan 23 (`docs/plans/2026-11-21-plan-23-parallel-lanes.md`, ADR 0025 proposed) builds parallel work as instructions:
the workflow skill `parallel-lanes`, a `QUEUE.md` a person keeps, and git worktrees as the lock. It updates these
items of section 6; the rest stand as section 6 says. The plugin's version for Plan 23 is aidlc 6.1.0, a minor release, because it adds a
skill and changes no route.

| Item | State after Plan 23 | How |
|---|---|---|
| D1 | Open | One autonomous lane: a later workflow skill |
| D2 | Covered, as instructions | A bundle's `DEPENDS ON` line; independent slices as sibling or stacked pull requests (`aidlc-plan`, `aidlc-build`, `aidlc-review`); a stacked slice moved with `git rebase --onto` after its parent merges (`parallel-lanes`) |
| E1 | Replaced | The queue is `QUEUE.md`, written by a person; the coordinator reads the tracker only to draft rows. No label |
| E2 | Covered, without `run_queue.py` | `parallel-lanes` coordinator mode: up to MAX LANES lanes, each in its own git worktree, started with the AI tool's own feature or by a person |
| E3 | Covered | The clash rules: one open change per contract; a shared MAY CHANGE path holds a row back only once building starts |
| E4 | Covered | A lane releases at every person's decision and before a push; its worktree goes, and its slot frees |
| E5 | Still dropped | No dispatcher ships, so there is no dispatcher key to fence |
| Decision D1 | Kept, without a script | Local git worktrees first; the lanes of one repository start from one clone |
| Decision D7 | Applied | A lane writes one repository; a story's parts are rows of the home repository's `QUEUE.md` |

## 8. After Plan 24 (2026-11-21)

Plan 24 (`docs/plans/2026-11-21-plan-24-fewer-approvals.md`, ADR 0026 accepted) builds fewer approvals as
instructions: one decisions-by-tier table in the tiers file every stage reads, one Gate line in each stage that holds
a decision, and route S for the standard changes a team lists in its `AGENTS.md`. It updates these items of section
6; the rest stand as sections 6 and 7 say.

| Item | State after Plan 24 | How |
|---|---|---|
| C1 | Covered, as instructions | The decisions-by-tier table: at Tier 1, Ready and Merge, and Release only when users see the change; Tier 2 adds Design + plan in one pull request and every affected area's code owner at Merge; Tier 3 adds the specialists, Release always and the hands-on restatement per slice. No decision is asked twice |
| C3 | Covered, as instructions | Route S: the Standard changes section of `AGENTS.md`, three suggested classes from `aidlc-onboard`, the standard brief from `aidlc-start`; the recipe-review pause lifted for a listed recipe class |
| C6 | Open | Intent, route and Ready as one first approval: a later plan |
```

## 9. After Plan 25 (2026-11-21)

Plan 25 (`docs/plans/2026-11-21-plan-25-route-in-ready-and-decision-log.md`, ADR 0027 accepted) builds the rest of
C6 and item B4 as instructions, in aidlc 7.1.0. It updates these items of sections 6 and 8; the rest stand as
sections 6 to 8 say.

| Item | State after Plan 25 | How |
|---|---|---|
| C6 | Covered, as instructions | Ready is the work, its acceptance criteria, its tier and its route. The ROUTE line carries its facts; the tech lead owns the route, and a technical person checks it at the first technical decision; a route change after Ready that touches the tier, the scope, the criteria or the controls is decided again |
| B4 | Covered, as instructions | The progress note's decision log: one row per judgement call, with its commit, evidence and owner, written when the call is made; `aidlc-review` copies the rows into the pull request description by owner; the compliance reviewer checks them; the code owner reads them at Merge |

## 10. After Plan 26 (2026-11-21)

Plan 26 (`docs/plans/2026-11-21-plan-26-shorter-stage-skills.md`, design
`docs/design/2026-11-21-shorter-stage-skills.md`) builds item D3 as instructions, in aidlc 7.2.0. It updates this item
of section 6; the rest stand as sections 6 to 9 say.

| Item | State after Plan 26 | How |
|---|---|---|
| D3 | Covered, as instructions | `aidlc-specify`, `aidlc-design`, `aidlc-start`, `aidlc-plan` and `aidlc-build` keep their main path and every gate in `SKILL.md`, and move the steps of one route or case into `references/<case>.md`, read on a named condition: amendments, route G, route S, several repositories, re-routing, the briefs, revisions, independent and stacked slices, and the recipe check. The text moved word for word; no decision and no stop changed. `scripts/validate.py` checks that a reference holds no gate section and that `SKILL.md` names it. `aidlc-specify` meets its word target (1,797 words). `aidlc-start` (2,675), `aidlc-design` (2,324), `aidlc-plan` (3,185) and `aidlc-build` (3,880) stay above theirs (Plan 26, item W1); the tests hold these counts as their limits. |
