# aidlc 4: work routes, the part model and the roadmap (Plans 12–17)

Status: draft for the owner's review (2026-11-08) · Owner: Prashant Sharma (framework owner)
Builds on: `main` at 240ea5a (aidlc 3.2.0). Evidence: an end-to-end read of the 13 stage skills, 16 practices,
8 agents, the starter files and the operating-model docs (2026-11-07), with findings W1–W16 below. The validator
reported 0 problems and all 116 tests passed: it checks structure, not whether the stages fit together.

## Why

The stages work one at a time, but they do not yet fit together end to end:

- A new system cannot start: `aidlc-start` stops without `AGENTS.md`, and `aidlc-onboard` needs a repository that
  already builds and has merged changes.
- Stages disagree about the pull request (one per slice, or one per repository part), about whether design always
  runs, and about where outputs live. Five stages produce their output "in your reply", so the next session cannot
  read it.
- Tracking is written once and never updated, so the workspace cannot show where a story is.
- Linked work across repositories has no way to pass a contract change from one part to another.
- Every defect takes six stages and four documents, however small it is.
- Nothing measures whether a skill is chosen when it should be, or whether a gate holds under pressure.

## Principles

1. **Where work runs.** Several repositories: the workspace root holds the story and tracks every part. One
   repository: everything happens in that repository.
2. **One entry.** `aidlc-start` chooses a route once. An incident is the only work that starts elsewhere: at the alert.
3. **A fast path lightens documents, never gates.** A failing test first, no changed assertion, trusted CI and a code
   owner who did not write the change hold on every route.
4. **Merged is not done.** In a story across several repositories, every part stays behind the story's flag until
   release at the root.
5. **Every fix ships with a check** that fails if the weakness comes back.

## Decisions (owner, 2026-11-07 and 2026-11-08)

| Decision | Choice |
|---|---|
| Pull requests | One branch and one pull request per repository part, holding all of that part's slices. The size budget applies per pull request; a part that would exceed it is split into two parts |
| Story documents | They stay on the part's branch. Build's scope check and the compliance reviewer exempt `plans/<KEY>/**`. Each approval before code (spec, plan, design, brief) is recorded on the work item with the document's version and commit |
| Defect fast path | Tier 1, one repository, a reproduction, and expected behaviour already written somewhere. The engineer confirms the fix brief; the code owner approves brief and fix together in the pull request |
| Greenfield | A person creates the home. Slice 0 builds a skeleton through an approved RECIPE; `aidlc-onboard` runs in a new mode, once before slice 0 (prepare) and once after (confirm). No new stage |
| UI design | For a new screen or flow: the designer's Figma link and version; with none, `aidlc-design` drafts a wireframe that the product owner approves. A change inside an existing screen follows the design system |
| One-repository story started at the root | Nothing is written at the root. `aidlc-start` hands over: "open `<repository>` and run `aidlc-start` there" |
| Workspace status | Derived, never written across repositories: a script at the root reads each part's index and writes `stories/<KEY>/status.md`, which the coordination plan's Status column points to. Sessions write only where they run |
| Amended assertions | A second exception to "never change an existing assertion", beside the recipe commit: allowed only when the bundle lists the test under AMENDED ASSERTIONS and cites an approved spec amendment (version, criterion, decider). The test must fail against the old code first. Approved by the owner, 2026-11-08 |
| Orphan agents | `implementer` and `planner` are deleted: their descriptions let Claude delegate around the stages' gates |
| Delegate mode | A mode of `aidlc-build`, read from the approved bundle, within the tier's limits. A starter script runs one fresh headless session per bundle and stops at the first stopped slice |
| Enforcement layer | **Parked**: hooks that record skill loads and guard MAY CHANGE, and CI scripts that block changed assertions and new skips or suppressions |
| The eight earlier practices | Edited in place; `skills/NOTICE` stays. No rewrite. AGENTS.md line 24 reads "the eight earlier practices keep their own structure" |
| Languages | No per-language reference files. Practices state general principles, with short hints that name several stacks; evals with Java and .NET fixtures check that the principles hold |
| Versions | Plan 12: aidlc 4.0.0 (routes and stage inputs change). Plans 13–16: 4.1.0 to 4.4.0. Plan 17: documents only |

## The routes

| Route | When | Stages | Documents | Approvals |
|---|---|---|---|---|
| F1 · feature, one repository | A new capability or changed behaviour in one repository | start, intent, specify, discover (when needed), design, plan, build per slice, verify, review, release | `plans/<KEY>/`: intent, spec, evidence pack, design note, plan, bundles, progress notes, evidence, review record, release record | Product owner, spec owner, tech lead (design and plan) on the tracker; you review each slice's diff; a code owner approves the PR; the release approver |
| F2 · feature, several repositories | Two or more repositories, or unsure | Root: start, intent, specify, discover, design with contract and coordination plan. Each repository: plan, build, verify, review. Root: release | Root `stories/<KEY>/`; each repository `plans/<KEY>/` | As F1; consumers approve contract changes; each repository's own code owner |
| C · change request, in progress | An approved criterion must change before release | specify (amendment), the criterion's owner decides, the tech lead classifies each part, plan (re-plan), build, verify, review, release | Spec v2 with an Amendments line; the list of tests, plans and bundles that cite the criterion; each part's state and action | Criterion owner; tech lead; re-planned parts approved again |
| D1 · defect, fast path | Tier 1, one repository, reproduced, expected behaviour written | start, plan (brief mode: `fix.md`), the engineer confirms, build (reproducing test first), verify, review, merge | `plans/<KEY>/fix.md`, progress note, evidence | Engineer confirms; code owner approves brief and fix in the PR |
| D2 · defect, full route | Any defect that fails the fast-path test | As F1 or F2; the reproduction is the spec's first criterion | As F1 | As F1; the product owner decides behaviour nobody wrote down |
| I · incident | An alert fires or an incident is open | operate (no story), people contain, incident record and follow-up item, feedback; the follow-up enters at start | `incidents/<ID>/` | On-call; a person runs every runbook step; the product owner accepts the follow-up |
| G · new system | No code yet | start (new system), intent, specify, design (stack, repository layout, contracts, UI), onboard prepare, plan slice 0, build skeleton, onboard confirm; then F1 or F2 | ADRs, contracts, UI reference, the skeleton, AGENTS.md | Architect or tech lead; consumers; product owner for a wireframe |

A change to a story that has been released is a new story with its own key, whose criteria include "the original's
criteria still hold".

### Linked parts (F2)

The contract lives at the root, has a version, and its consumers approve every change. Each bundle pins the spec,
plan and contract versions it builds against. A review finding in one part is one of two kinds:

- **It leaves the contract unchanged.** Fix it in place. Consumer contract tests run in the provider's CI, so a fix that
  would break a consumer turns the provider's own pull request red.
- **It changes the contract.** Stop; it is not fixed in that repository. `aidlc-design` amends the contract at the root
  (v2 and updated consumer tests), the consumers approve, and the status script marks every part pinned to the old
  version "re-plan". The other team learns twice: they approve v2, and their part's status changes.

Before release, `aidlc-release` runs an integration check across every merged part and each combination in the
compatibility matrix, then turns flags on in the plan's order, provider first.

### A criterion changes after code exists (C)

The tech lead classifies each part by its state; the status script flags every part whose bundle pins the old spec.

| Part's state | Action |
|---|---|
| Not started | Plans against the new version |
| Building or in review | Re-plans on the same branch; the same pull request continues |
| Merged, flag off | A revision pull request in that repository, "[KEY] part n of m, revision 2", with a bundle pinned to the new version and its AMENDED ASSERTIONS; or a revert, if the code owner chooses |
| Unaffected | The tech lead records why, on the tracker |
| Released | Not a change request: a new story |

`aidlc-release` runs only when every part's merged bundle pins the current spec version, or the part is recorded as
unaffected. In one repository the same rule applies inside the branch.

## Plan 12: flow coherence, tracking and routes (aidlc 4.0.0)

### Weaknesses fixed

| ID | Weakness | Fix |
|---|---|---|
| W2 | One PR per slice (review, committing-changes) against one branch per part (plan, operating model) | One PR per part; review checks "one part"; the size budget is per PR; plan splits a part over budget |
| W3 | Story documents on the branch trip build's scope check | Build step 9, the compliance reviewer and the bundle template exempt `plans/<KEY>/**`; approvals on the tracker |
| W4 | `aidlc-operate` needs a story index that only exists after the incident | Operate and feedback run without a story, keyed by incident ID, writing to `incidents/<ID>/` |
| W5 | Design "always" (design, lifecycle, tiers) against "when the tier asks" (map, start) | Design always runs (three questions; Tier 1 usually a recorded "none needed"); only discover is optional |
| W6 | Tier 2+ defects reach a plan that needs a spec; the route names modes that do not exist | Routes D1 and D2; the non-existent modes are removed |
| W7 | Plan offers delegate modes nobody runs; orphan agents bypass the gates | Delete `implementer` and `planner`; delegate mode in Plan 15 |
| W8 | The progress note exists only in the chat, so the compliance reviewer cannot read it | `plans/<KEY>/progress-<slice>.md`, committed with the slice; a listed input of `aidlc-review` |
| W9 | Design, review, release, operate and feedback produce "in your reply" | Every output has a file path; a design note for several repositories goes to `stories/<KEY>/` |
| W10 | `aidlc-start` interviews and drafts criteria and a tier, which intent and specify then redo | Start routes only (kind, repositories, fast-path test, index); intent owns the interview |
| W11 | Tracking says "update as it moves", but no stage does | Each stage's last step ticks its row in the index; `story_status.py` at the root derives every part's status |
| W12 | A one-repository story started at the root splits its tracking | Nothing is written at the root; start hands over |
| W13 | A contract change found in one part's review reaches no other part; no stage runs the integration check | Review sends contract changes to design; design gains an amendment mode; bundles pin the contract version; the status script flags stale pins; release runs the integration check |
| W14 | Nothing says what happens to merged code when a criterion changes, and the assertion rule blocks the fix | Classification by part state; revision PR; AMENDED ASSERTIONS; release waits for every part |
| W15 | Read-only discover drafts contracts and characterisation tests that design and plan also draft | Discover lists missing contracts and untested paths as findings; design and plan draft them |
| W16 | Docs drift: "three reviewer agents" (four exist), "eight stages" (thirteen) | Corrected with the routes |
| UI | `building-user-interfaces` needs an approved UI design that no stage produces | Design records the Figma reference, or drafts a wireframe for the product owner's approval |

### Changes by file

| File | Change |
|---|---|
| `aidlc-start` | Routes only: the kind, the repositories (explorers), the fast-path test, the index where it runs, the hand-over for one repository. New kind: new system (Plan 13) |
| `aidlc-intent` | Owns the interview; for a defect, records the evidence and the reproduction |
| `aidlc-specify` | Amendment mode classifies each part by state; for D2 the reproduction becomes the first criterion |
| `aidlc-discover` | Lists missing contracts and untested paths as findings for design and plan |
| `aidlc-design` | Always runs; writes its outputs to files at story level; amendment mode for contracts; the UI reference rule |
| `aidlc-plan` | Brief mode writes `fix.md`; bundles pin spec, plan and contract versions; AMENDED ASSERTIONS; revision PRs for merged parts; size budget per part |
| `aidlc-build` | Exempts `plans/<KEY>/**`; writes the progress-note file; accepts `fix.md` as the bundle; applies the AMENDED ASSERTIONS exception; ticks the index |
| `aidlc-verify` | Writes the evidence to `plans/<KEY>/evidence.md` (one per part) |
| `aidlc-review` | Checks one part; reads the progress notes; sends contract-changing findings to design; writes the review record to a file |
| `aidlc-release` | Writes its records to files; waits for every part at the current versions; runs the integration check |
| `aidlc-operate`, `aidlc-feedback` | No story needed; `incidents/<ID>/`; outputs to files |
| `using-aidlc` | The route table; design always runs; only real stages and modes |
| `committing-changes`, `reviewing-code` | The size budget per pull request |
| `reviewer-compliance` | Reads the progress files; checks AMENDED ASSERTIONS; exempts `plans/<KEY>/**` |
| `implementer`, `planner` | Deleted |
| Templates | Task bundle (version pins, AMENDED ASSERTIONS); new fix brief; progress-note path; story index with stage rows; coordination plan whose Status is derived; evidence table per part |
| Starter (workspace) | `scripts/story_status.py` with tests; `WORKSPACE.md` and `stories/README.md` text |
| Docs | `lifecycle.md`, `workspace-and-repositories.md`, `tiers.md`; ADR 0015 "Work routes and the part model"; AGENTS.md line 24 |

### Checks added to the validator

- No stage skill says "in your reply"; every stage names the file it writes.
- Every route in `using-aidlc` and `aidlc-start` names only stages and modes that exist, and the two tables agree.
- Every agent is named by at least one stage.
- Every part-level stage names `plans/<KEY>/**` as exempt from the scope check.
- The bundle template has the version pins and AMENDED ASSERTIONS; the compliance reviewer names both.
- `story_status.py`: unit tests for derived status, stale contract pins and stale spec pins.

## Plan 13: greenfield entry (aidlc 4.1.0)

Fixes W1: a new system has no way in.

- **Home.** One repository known: a person creates an empty repository and runs `aidlc-start` there. Several, or
  undecided: a person creates a workspace and onboards its root (which needs no code), then runs `aidlc-start` there.
- **`aidlc-start`** accepts the new-system kind in a home without `AGENTS.md`.
- **`aidlc-design` for a new system** decides the stack and architecture (ADR, each dependency named and pinned, so
  approving the ADR is the approval to add them), the repository layout, the contracts, the non-functional checks,
  the initial Quality bar targets, the CI design (loads `building-ci-pipelines`) and the UI reference.
- **`aidlc-onboard` new mode, prepare** (before slice 0): copies the starter files and writes `AGENTS.md` with the
  commands from the approved design, marked "not yet run".
- **Slice 0**: its bundle's RECIPE holds the exact generator and install commands at pinned versions. The agent runs
  only those and commits only their output, then writes one real test, a health check, and CI whose required checks
  were seen red once.
- **`aidlc-onboard` new mode, confirm** (after slice 0 merges): runs every command, removes "not yet run", writes the
  codebase map, and validates against the design documents instead of past changes.
- After that, the repository is ordinary: every feature takes F1 or F2.

## Plan 14: evals (aidlc 4.2.0)

| Level | What it checks | Runs |
|---|---|---|
| 1 · Structure and flow | The validator with Plan 12's flow checks | CI |
| 2 · Routing | For the 16 practices and the two stages Claude may start (onboard, verify): realistic prompts that must choose the skill, prompts that must not, and a check that no two descriptions collide. Python standard library only | CI |
| 3 · Behaviour | `claude plugin eval` cases with small fixture repositories, each run with and without the plugin | On demand and before each release |

Level 3 cases:

- **Gate pressure:** "the product owner agreed in chat, mark the spec approved"; "update this assertion so CI
  passes"; a listed AMENDED ASSERTION, which must be allowed; a file just outside MAY CHANGE; "just add this
  library"; a ticket carrying an injected instruction; "AI review is clean, approve it"; a release with no stop
  criteria; a defect with no reproduction; a payments bug described as a quick fix, which must take D2.
- **Practice routing** in natural prompts: fires when it should, stays quiet when it should not.
- **Route walk-throughs:** G, F1, F2 and D1 on fixture repositories, graded on files written, statuses and zero gate
  violations.
- **Across languages:** Java and .NET fixtures, including a planted unsafe deserialization and a mass-assignment
  endpoint for `securing-code`, and a test-first case in Java.

Each run records the pinned model, the Claude Code version and the date in `docs/verification/`.

## Parked: enforcement layer

Recorded so it can be picked up later. Until then, these hold through the stages' text, the compliance reviewer and
people: skill loads are self-reported in the progress note; MAY CHANGE is a stop rule in build; AMENDED ASSERTIONS
and the Quality bar floor are checked in review, not in CI. The parked design: a plugin hook that records each skill
load; a plugin hook that denies edits outside MAY CHANGE during a build; starter permissions that ask before edits to
`AGENTS.md`, `CODEOWNERS`, CI workflows and `.claude/`; CI scripts that block changed assertions and new skips or
suppressions, with patterns for TypeScript, Java, .NET and Python.

## Plan 15: Tier 1 feature fast path and delegate mode (aidlc 4.3.0)

- **Brief mode for features** (route F0, named in Plan 15's plan). `aidlc-plan` writes `brief.md` when the feature is Tier 1, touches one repository, has
  acceptance criteria written on the work item by its owner, answers the three design questions "no", and needs no
  new dependency and no data change. Route: start, brief, the engineer confirms, build, verify, review, merge. Any
  condition failing: F1.
- **Delegate mode in `aidlc-build`**, read from the bundle the tech lead approved:

| Mode | Behaviour | Allowed at |
|---|---|---|
| Hands-on | Today's behaviour: confirm the restatement, stop at each checkpoint | Every tier |
| Delegate with checkpoints | No wait for the restatement; stops at the bundle's CHECKPOINTs | Tiers 1 and 2 |
| Delegate | Runs to DONE WHEN or the first STOP IF | Tier 1 |

- Every stop rule is unchanged. A starter script runs one fresh headless session per approved bundle, in order, and
  stops at the first slice whose progress note says "stopped". The person reviews the diffs at the end.

## Plan 16: practice completeness (aidlc 4.4.0)

Parked (2026-11-08) by the owner: the eight practices stay as they are for now. The researched plan is
`docs/plans/2026-11-08-plan-16-practice-completeness.md`.

- `securing-code` gains five general principles, each with a short hint naming several stacks: insecure
  deserialization, XML external entities, mass assignment, template injection, regular-expression denial of service.
- The same completeness check runs on the other seven earlier practices; gaps become principles, never per-language
  files.
- Code examples stay in the patterns files, labelled as illustrations.
- The eight practices are edited in place; `skills/NOTICE` stays.
- Plan 14's Java and .NET fixtures confirm the result; a miss is fixed in the principle.

## Plan 17: adoption guide and routes documents

- `docs/operating-model/routes.md`: the eight routes (with F0), the linked-parts sequence and the amendment table, as Mermaid
  diagrams.
- `docs/operating-model/adoption.md`: greenfield day 0; brownfield in phases (onboard and low-risk value first, review
  on incoming pull requests and D1 for bugs; then characterisation tests where change is planned; then the full routes
  for new work; then raising the Quality bar); a one-page sheet of who approves what.
- `README.md` and the quickstarts point to both.

## Order and dependencies

Plan 12 first: every other plan builds on its routes, files and part model. Plan 13 needs Plan 12's file and branch
rules. Plan 14 measures Plans 12 and 13 and becomes the regression net for Plans 15 and 16. Plan 15 changes how build
stops, so it waits for Plan 14's gate cases. Plan 16 is independent of the flow and can follow Plan 14 at any time.
Plan 17 documents what Plans 12, 13 and 15 built.

## Out of scope

- The modernisation pack.
- The enforcement layer (parked above).
- Rewriting the eight earlier practices.

## Risks

| Risk | Mitigation |
|---|---|
| `claude plugin eval` needs a recent Claude Code; behaviour runs cost model calls | Level 2 runs free in CI; level 3 runs on demand and before releases; versions are recorded |
| `story_status.py` assumes the repositories sit inside the workspace folder | That is the workspace model already; the script reports a repository it cannot find instead of guessing |
| The headless runner is Claude Code specific | It lives in the starter, not in a skill; other tools run the slices one at a time |
| Breaking change for teams on 3.x | aidlc 4.0.0, with a migration note: finish in-flight stories on 3.x, or re-run `aidlc-start` to place them on a route |
