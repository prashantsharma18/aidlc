# Practice layer v2: seven new practices, a tests reviewer and the quality bar (Plan 9)

Status: draft for review (2026-11-06) · Owner: Prashant Sharma (framework owner)
Builds on: the practice rename (commit b5e2c15, aidlc 3.0.0). Out of scope: modernisation, the demo story,
rewriting the eight existing practices, CI check scripts and behaviour evals (later sub-projects).

## Why

The stage skills say which step you are in and who approves it. The practice skills say how to do a kind of work
well. Eight practices exist; seven kinds of everyday work have none:

- writing good tests (the build skill enforces the order, test first, but not the craft);
- shaping commits, pull requests, versions and changelogs;
- building a CI pipeline (the starter `ci.yml` holds placeholders, and the parked harness no longer generates one);
- simplifying working code without changing what it does;
- stress-testing a plan or design before it stands;
- checking a framework approach against current official documentation;
- testing a change in a real browser.

Separately, the rule "never lower the bar to get to green" covers only assertions and skipped tests today. An agent can
still add a lint suppression, leave a stub or lower a coverage threshold, and nothing names it.

## Decisions (owner, 2026-11-06)

| Decision | Choice |
|---|---|
| New practices | Seven, with gerund names (Anthropic's naming guidance): `writing-tests`, `committing-changes`, `building-ci-pipelines`, `simplifying-code`, `stress-testing-decisions`, `checking-official-docs`, `testing-in-browser` |
| New agent | `reviewer-tests`, read-only, named like the other reviewers |
| Quality bar | Folded into the stages, not a separate skill: defined once by `aidlc-onboard`, held on every change by AGENTS.md, `aidlc-build` and `reviewer-compliance` |
| Browser testing | The repository's own pinned browser test runner (Playwright as the worked example). No MCP server of any kind |
| Text | Written from general engineering practice and the stage skills, in our words. No `source` line, no credit, no change to `NOTICE` |
| Version | aidlc 3.1.0 (new skills, nothing renamed). `aidlc-modernize` stays at 0.1.2 (`^3.0` still matches) |

## The practice format

The new practices use a lean format of our own, so the whole package reads as one author:

```text
---
name: <gerund-name>                 # equals the folder
description: <what it does, third person>. Use when <the phrases people type> ..., even when the code is pasted inline.
metadata:
  kind: practice
  invocation: auto
  guide: ['<section>', ...]         # sections of "From Intent to Verified Change"
---
# <Title>

## When to use        what triggers it, and what belongs to another skill instead
## Steps              the procedure, numbered
## Checks             what "done well" means, each one checkable
## Stop if            when to stop and report
## Common excuses     excuse | reality
## Red flags          signs the practice is being skipped
## Rules              the practice Rules block, ending "You draft; you never approve."
```

- `SKILL.md` stays under about 200 lines. Longer checklists go to `references/<descriptive-name>.md`, linked one level
  deep from `SKILL.md`.
- A practice names no tool-specific command. It names "the repository's commands from AGENTS.md"; a worked example may
  show one common tool, marked as an example.
- The validator enforces these sections, in this order, on every skill with `metadata.kind: practice`, except the eight
  renamed practices, which it lists by name as exempt until their content is rewritten. The list only shrinks.

## The seven practices

| Practice | Does | Used by |
|---|---|---|
| `writing-tests` | Red, green, refactor; a reproducing test before a defect fix; one behaviour per test; the test pyramid and test sizes; tests that would fail if the code were wrong; anti-patterns (testing mocks, asserting implementation details, sleeping in tests) | `aidlc-build` steps 6 to 8; `reviewer-tests` |
| `committing-changes` | One logical change per commit; a subject with a type, a body that says why; splitting a mixed working tree; pull request size; semantic version bump and changelog entry | `aidlc-build` step 7; `aidlc-release` |
| `building-ci-pipelines` | Stages ordered from cheapest to costliest; required checks; pinned actions and tools; caching; flaky-test quarantine with an owner; least-privilege tokens; failures fed back as the build skill's input | `aidlc-onboard`; a team setting up CI |
| `simplifying-code` | Behaviour kept exactly; the existing tests run before and after; smaller functions, fewer branches, clearer names; any behaviour difference stated, never hidden | `reviewing-code`; refactoring work |
| `stress-testing-decisions` | A fresh-context pass (the `explorer` agent) that argues against a plan or design: assumptions, failure modes, rollback, cost; each objection answered or recorded as a risk | `aidlc-plan` and `aidlc-design` at Tier 2 and above |
| `checking-official-docs` | Find the official documentation for the version in use, cite it, flag deprecated or outdated patterns; an unverifiable claim is marked UNKNOWN, never guessed | `aidlc-plan`, `aidlc-design`, `aidlc-build`; `designing-apis` |
| `testing-in-browser` | Run the app locally; an end-to-end test per UI criterion; console errors and failed requests read; screenshots at desktop and mobile widths, looked at; an accessibility scan; the same tests in CI. With no runner in the repository, stop and propose one (a new dependency needs approval) | `aidlc-build` for UI criteria; evidence for `aidlc-verify` |

## The `reviewer-tests` agent

Read-only (Read, Glob, Grep), like the other reviewers. For each criterion and edge case of the slice it answers:

- Is there a test named with its ID?
- Would the test fail if the implementation were wrong (a constant return, an inverted condition, a missing branch)?
- Does it assert behaviour, not implementation detail? Does a mock hide the behaviour under test?
- Is anything skipped, weakened or untested?

It returns findings tagged `[tests]` with file, line and evidence, or "No findings." It never approves. `aidlc-review`
runs it beside `reviewer-bug`, `reviewer-security` and `reviewer-compliance`.

## The quality bar

Defined once per repository, held on every change.

- **`aidlc-onboard`** writes a `## Quality bar` section into AGENTS.md, in three parts:
  - **Floor**, always on: no new suppressions (lint, type or compiler), no skipped or deleted tests, no weakened
    assertion, no stub or placeholder left in, no lowered threshold or loosened check configuration.
  - **Enforced**: thresholds with numbers and the command that checks each (for example coverage, bundle size, an
    accessibility score, a latency budget). When the team has no number, onboard proposes a default and the team decides.
  - **Measured, not yet enforced**: what is tracked before it becomes a gate.
- **Exceptions** name the reason, an owner and an expiry date, next to the code (for a suppression) or in the Quality
  bar section (for a threshold). An exception without all three is a violation.
- **The AGENTS.md template's Boundaries** gains one line: "Never lower the bar to get to green: no new suppressions,
  skipped or deleted tests, weakened assertions, stubs or lowered thresholds. Stop and report." AGENTS.md is in every
  session, so this covers work done outside the stages too.
- **`aidlc-build`** checks the floor at step 9 and adds it to Stop if, Common excuses and Red flags.
- **`reviewer-compliance`** checks the same floor.
- A later CI script (the harness sub-project) becomes the mechanical check.

## Smaller folds

- `aidlc-design`: when a change alters a public API or behaviour users see, the design names the README, API reference
  and changelog updates.
- `aidlc-onboard`: keeps AGENTS.md short and specific (commands, boundaries, the map) and names when to start a fresh
  session (a new slice, or after the conversation was compacted).

## Originality

The new files are written from general engineering practice and aidlc's own skills. Upstream practice text is not open
while they are written. After writing, a check in the session scratchpad compares every new file against the upstream
agent-skills text for shared runs of eight or more words; the result is recorded in the verification record. Upstream
text never enters the repository.

## Testing

- `scripts/validate.py` with new tests: the practice sections and their order, the exempt list (and that it only lists
  existing skills), front matter `kind` and `invocation`.
- The unit tests and `claude plugin validate .`.
- A live check in a scratch repository: a few real prompts (add tests to a pasted function, write a commit message for
  a pasted diff, simplify a pasted function) to see the new practices fire, and one that must not fire.
- Behaviour evals (fires and stays-quiet pairs, pressure cases) belong to the evals sub-project.

## Consequences

- Seven more descriptions in every session: about 1,000 tokens.
- The eight renamed practices keep their old shape until their content is rewritten; the exempt list shows how many remain.
- ADR 0013 records the decisions above.

## Rejected alternatives

- **A separate quality-bar skill.** It would load only when routing picks it, while the floor must hold on every change;
  and two places stating one rule drift.
- **Browser testing through an MCP server.** External MCP servers are not allowed here, and the repository's own test
  runner gives the same evidence and runs in CI.
- **The full stage format for practices.** It forces empty Inputs, Produces and Gate sections on skills that advise
  inside a stage.
