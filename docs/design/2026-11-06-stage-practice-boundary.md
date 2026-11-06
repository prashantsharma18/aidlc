# The stage and practice boundary: stages load practices, one map (Plan 11)

Status: draft for review (2026-11-06) · Owner: Prashant Sharma (framework owner)
Builds on: branch `docs/plan-10-practice-reword` (01eff4c). Evidence: a read-only audit of all 13 stage skills, their
templates and the 8 agents against the 15 practices (2026-11-06; findings C1–C17, D1–D7, M1–M14, S1–S4, G1–G19 below).

## Why

A person starts each stage; Claude picks practices by their descriptions. That pick varies from run to run, so inside a
stage a practice may or may not load. Stage skills mention practices in passing ("the `writing-tests` skill says how")
instead of commanding the load. Some stages also re-explain a technique a practice owns, and some practices contradict
the gates: `debugging-failures` says to update an outdated test and to fix before writing the reproducing test.
Nobody has one page that shows which stage comes next and which practice applies.

## Principle

**A stage says when, what must hold and who approves. A practice says how.**

- A stage step that needs a technique says "Load the `<practice>` skill" and keeps its gate in one sentence.
- A practice never contradicts a gate. Where the two touch, the practice defers to the stage.
- A stage's template wins over a practice's format for the same record.
- One number per measure, stated in one place and cited elsewhere.

## Decisions (owner, 2026-11-06)

| Decision | Choice |
|---|---|
| Pattern | Each stage step commands the load by name: "Load the `<practice>` skill" (the pattern of a manually started phase command whose first line invokes its skill) |
| `reviewing-code` | Becomes loadable by the model (drop `disable-model-invocation`); `aidlc-build` step 9 and `aidlc-review` load it |
| Severity | One scheme everywhere: high, medium, low, plus `question`. High and medium block the merge until fixed or dismissed with a reason; low may be dismissed with a reason; a question asks the author and is not a defect |
| A commanded load fails | Stop and report. The progress note lists every skill loaded with its plugin version; the compliance reviewer checks it covers what the stage and the bundle required |
| Slice-specific practices | `aidlc-plan` chooses them per slice from the practice map and writes them into the bundle's USE SKILLS (full name, for example `aidlc:securing-code`); the tech lead approves them with the plan; `aidlc-build` loads them or stops. A practice the build finds it also needs is loaded and recorded as a deviation |
| Single stop | A new skill, `using-aidlc`: the lifecycle map and the practice map, loaded by description and by `aidlc-start` and `aidlc-plan`. No session hook |
| Documentation | A new practice, `writing-documentation`, in our own words and format (originality check 0): README, API reference, inline comments, docs for agents. ADRs stay with `aidlc-design` |
| Version | aidlc 3.2.0 |

## Part 1: make the practices safe to load (conflicts and blockers)

| ID | Where | Change |
|---|---|---|
| C1 | `debugging-failures` triage tree and Common rationalizations | "Test is outdated → update the test" and "if the test is wrong, fix the test" become "the test may be wrong → stop and report; never change an existing assertion; the criterion's owner decides" |
| C2 | `debugging-failures` triage list and Steps 4–5 | Order becomes reproduce, localize, reduce, **guard (the reproducing test, seen failing)**, **then fix**, verify. Step headings swap to match (no links point at them) |
| C3 | `debugging-failures` "Safe Fallback Patterns" | Replaced by one rule: a fallback is behaviour that the spec or design decides; never add one to get a check green |
| C12 | `debugging-failures`, `securing-code` | `debugging-failures` gains an "In this framework" line: in production you propose only, inside `aidlc-operate`. `securing-code`'s privacy-incident line points to `aidlc-operate` and `aidlc-feedback` |
| C16 | `aidlc-build` Stop if, `debugging-failures` | One stop wording everywhere: the same failure three times, the same failure after a different fix, or a newly broken test |
| S1 | `reviewing-code` | Loadable by the model; its "In this framework" line says `aidlc-build` step 9 and `aidlc-review` load it, and CI's AI review stays separate |
| S3 | `reviewing-code` | The reference to a skill that does not exist is replaced by "the Quality bar in AGENTS.md" |
| S4, C8 | `aidlc-operate` runbook template, `adding-observability` | One runbook format, the stage's template. Its step marks become "read-only" or "changes state"; a person runs every step. `adding-observability` points to that template for runbooks |
| C4 | `building-user-interfaces` | "In this framework": the approved UI design is the contract; with none, stop and route to `aidlc-design` |
| C5 | `building-user-interfaces` | "No accessibility warnings" becomes "no new serious or critical accessibility issue (the Quality bar in AGENTS.md)" |
| C14 | `testing-in-browser` | Screenshots at the smallest and largest breakpoints `building-user-interfaces` uses (320 and 1440 pixels) |
| C6 | `tuning-performance` | Budgets come from the AGENTS.md Quality bar; the numbers shown are examples |
| C7 | `aidlc-release` step 3 | The Tier 1 "revert of the merge" rollback holds unless the change alters data or a schema; then the rollback is the migration's own |
| C9 | `aidlc-review` review-record template, `reviewing-code`, reviewer agents | The single severity scheme (high, medium, low, question) |
| C10 | `reviewing-code` Review Process | Order matches the stage: context, evidence ("verify the verification"), tests, implementation, findings |
| C11 | `aidlc-release` readiness template, observability checklist | The gate stays in the stage ("monitoring in place"); its MONITORING column says it is checked against `adding-observability`'s pre-launch list, which stays in the practice only |
| C13 | `committing-changes`, `aidlc-plan` step 5 | One pull-request size, `reviewing-code`'s (about 300 changed lines acceptable, about 1,000 too large); `committing-changes` and plan cite it |
| C15 | `committing-changes` | "`aidlc-verify` drafts the description and `aidlc-review` completes it" |
| C17 | `reviewing-code` | Small cleanups only inside MAY CHANGE, as their own commit |

## Part 2: remove the duplication

| ID | Where | Change |
|---|---|---|
| D1 | `aidlc-build` step 6 | Technique moves out. The step keeps its gate: failing tests first, one per criterion or edge case, named with its ID; read the counts; a skipped test proves nothing; for a defect the reproducing test first and no fix until it fails for that reason. Then "Load the `writing-tests` skill", and for a change users see in a web page "Load the `testing-in-browser` skill" |
| D2 | `aidlc-build` step 7 | "Load the `committing-changes` skill for each commit." Keeps the method's own extras: the step number, any decision and who must confirm it, the commits as the progress record |
| D3 | `aidlc-plan` step 5 | Keeps its slice shapes and the green-at-both-ends rule; cites the pull-request size (C13) |
| D4 | `writing-tests` Checks | Boundaries start from the spec's edge cases (their IDs), then the generic list |
| D5 | `reviewer-tests` agent | Keeps its scope and method-specific points; the standard is `writing-tests` (preloaded); the snapshot line matches the practice |
| D6 | `reviewer-security` agent | The standard is `securing-code` and its checklist (preloaded); keeps the method's "weakened control" list |
| D7 | `reviewer-bug` agent | The standard is `reviewing-code`'s correctness axis (preloaded); keeps its short list |

Agents preload their standard with the `skills:` front matter field (Claude Code). The text also names the skill, so a
tool without preloading still knows the standard.

## Part 3: the loads, the map and the new practice

### Where each stage loads which practice

| Stage | Step → "Load the … skill" |
|---|---|
| `aidlc-start` | Before routing: `using-aidlc` |
| `aidlc-onboard` | 5: `building-ci-pipelines` (when there is no real CI) |
| `aidlc-discover` | 5: `designing-apis` (drafting a missing contract) · 6: `writing-tests` (characterisation tests) |
| `aidlc-design` | 2: `securing-code` (Tier 3, or a trust boundary changes: threat model), `migrating-safely` (data, schema or deprecation) · 3: `stress-testing-decisions` (Tier 2+), `checking-official-docs` (vendor behaviour) · 5: `designing-apis`, `writing-tests` · 6: `building-ci-pipelines` (when the enforcement is a CI check) · 8: `tuning-performance` or `adding-observability` (non-functional checks), `writing-documentation` (doc updates) |
| `aidlc-plan` | 4: `stress-testing-decisions` (Tier 2+), `checking-official-docs`, `writing-tests` (test level per criterion), `testing-in-browser` (UI criteria) · 7: `using-aidlc` (choose USE SKILLS from the practice map) |
| `aidlc-build` | 3: every USE SKILL · 4: `checking-official-docs` (unchecked framework behaviour) · 6: `writing-tests`; `testing-in-browser` for UI · 7: `committing-changes` · 8: `debugging-failures` (a failing check) · 9: `reviewing-code` (self-review of the diff) |
| `aidlc-review` | 3: `reviewing-code`, before the four reviewer agents · 6: `securing-code` (the security review draft) |
| `aidlc-release` | 1: `adding-observability` (the monitoring column) · 2: `migrating-safely` (data changes) · 5: `committing-changes` (version and changelog), `writing-documentation` (release notes and docs) |
| `aidlc-operate` | 5: `adding-observability` (a runbook change) |
| `aidlc-feedback` | 3: by the layer chosen: `writing-tests`, `building-ci-pipelines`, `adding-observability`, `writing-documentation` |
| `aidlc-intent`, `aidlc-specify`, `aidlc-verify` | None. Verify reads browser evidence; it does not load a practice |

`aidlc-plan` step 7's rule changes from "USE SKILLS holds only pack skills" to "pack skills AGENTS.md declares, and core
practices chosen from the `using-aidlc` practice map". `reviewer-compliance` checks that `Skills loaded` covers the
bundle's USE SKILLS and the build's commanded loads; other skills that loaded by description are listed, not findings.

### `using-aidlc`

Open format (not a stage, not a practice), loaded by description ("Use when deciding which aidlc stage or practice
applies, or what comes next") and by `aidlc-start` and `aidlc-plan`. Sections:

- **The lifecycle:** every stage in order, what it produces, where it runs (workspace root or repository), who approves,
  and the next stage.
- **The practice map:** the decision tree from the kind of work to the practice (UI → `building-user-interfaces`; API or
  contract → `designing-apis`; authentication, permissions, untrusted input or personal data → `securing-code`; schema,
  data or deprecation → `migrating-safely`; logs, metrics or alerts → `adding-observability`; a performance requirement
  → `tuning-performance`; a refactor → `simplifying-code`; docs → `writing-documentation`; and the rest), plus the
  practices each stage always loads.
- **How the two kinds relate:** a person starts stages; practices load by a stage step, by USE SKILLS, or by
  description outside the stages.

It lists every core practice exactly once in the practice map and every stage exactly once in the lifecycle. The
decision tree lives only here. The AGENTS.md template keeps its "How work runs here" block and adds "The full map: the
`using-aidlc` skill."

### `writing-documentation`

A practice in the practice format, written in our words: who reads it and what they must do next; README (what it is,
how to run and test it, where to look); API reference generated from or next to the contract; inline comments that say
why, not what; docs for agents (AGENTS.md and the codebase map stay accurate, changed in the same pull request as the
code); docs updated in the same pull request as the behaviour. It does not cover ADRs (`aidlc-design`) or changelogs
(`committing-changes`).

## Testing

- A new test file checks the loads: every "Load the `<name>` skill" in a stage names a core skill that exists and can be
  loaded by the model; each stage carries the loads in the table above; the old passing-mention phrasing is gone.
- `using-aidlc` names every core practice once and every stage once.
- Gate tests: `debugging-failures` has no "update the test" or "fix the test" and puts the guard before the fix;
  the review-record template uses the single severity scheme; the stop wording matches in build and debugging.
- `scripts/validate.py`, the unit tests and `claude plugin validate .`.
- Originality check (eight-word runs, against the third-party text, outside the repository) for `writing-documentation`
  and `using-aidlc`: 0.
- A live check: a build-like prompt with a failing test shows `writing-tests` and `debugging-failures` loading; a
  "which skill applies" prompt loads `using-aidlc`.

## Consequences

- Two more descriptions in every session (about 200 tokens), and `reviewing-code` now has one too.
- Practice text changes are targeted lines, in keeping with the light-rewording rounds.
- ADR 0014 records the principle and the decisions.

## Rejected alternatives

- **A session hook that forces the map into every session:** hosts that route skills natively would run two routers.
- **The build choosing slice practices on its own:** the choice would vary run to run and stay invisible until review.
- **Keeping `reviewing-code` manual:** no stage could load it, so the reviewer agents would keep their own copies.
