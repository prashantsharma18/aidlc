# 0029 · Tests first, when a test is practical

Status: Proposed (2026-11-22). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-22-connect-the-flow.md` (Part 5) · Plan:
`docs/plans/2026-11-22-plan-27-connect-the-flow.md` · Amends: the tests-first gate in `aidlc-build` and the rules
files (AGENTS.md's "Never weaken a gate in a skill (tests first, …) without a design change": this is that change)

## Context
aidlc asked for one failing test per criterion or edge case, before any code, every time. Some criteria have no
practical test: the test path is unclear, the test needs a harness far larger than the change, or there is nothing
sensible to assert. Then the rule pushes the AI to write a bad test, one that mostly tests mocks or the current
implementation, or to stop. pstack's `tdd` skill (MIT, Lauren Tan) writes the failing test first when the change has
a cheap local test, writes none when the test would be impractical, uses the closest executable check instead, and
says so: "prefer no new test over a bad test".

## Decision
- **Default.** Write the failing test first whenever the change has a cheap local test. A cheap local test is always
  written.
- **May write no test.** The AI may write no test for a criterion when it judges the test impractical: the test path
  is unclear, the test is expensive to build (a broad harness, slow end-to-end infrastructure, state only production
  has), or there is nothing sensible to assert. This case is called "no test for <criterion>", never "a skipped
  test": a test marked skip or disabled is still the Quality bar's stop.
- **When it writes no test.** It proves the criterion another way (a command's output, a live check, a screenshot)
  and writes one row in the decision log (ADR 0027), `no test for <criterion>`, with why a test is impractical and
  the proof it used instead, before it writes the code. For a defect, the reproduction still comes first and still
  fails first: a command or a live check that shows the failure, when a test is impractical.
- **Who sees it.** The tests reviewer lists every criterion with no test, with its reason. `aidlc-verify` lists the
  criterion under Unproved, with its proof, accepted at Merge by the code owner. The code owner reads them at Merge,
  inside that decision: a row adds no new stop and no new approval.
- **Unchanged.** Never editing an existing assertion; no new dependency without asking; every Stop if. A row is never
  a way around a stop: a criterion that is unclear is still a stop.

## Consequences
- The AI may call a test impractical to save effort. Each such criterion is visible three times: in the decision log,
  in the tests reviewer's list and in the evidence table's Unproved section, and the code owner reads them before
  merging.
- `scripts/test_connect_flow.py` checks the rule's wording in build, verify, the tests reviewer and the rules files.
  A behaviour case checks that a criterion with no test has its decision-log row; it runs when an API key or token
  is available.
