# 0013 · Practice layer v2: our practice format, seven practices and the quality bar

Status: Accepted (2026-11-06). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-06-practice-layer-v2.md`

## Context
- Eight practices covered API design, review, debugging, migration, interfaces, observability, performance and
  security. Everyday work with no practice: writing tests, shaping commits and versions, CI, simplifying code,
  challenging a decision, checking official documentation, and testing in a browser.
- With the harness parked (ADR 0010), the starter CI holds placeholders, so teams build CI themselves.
- The floor against weakening tests covered changed assertions and skipped tests only.
- External MCP servers are not allowed, so browser testing cannot depend on one.

## Decision
- Seven practices, gerund names: `writing-tests`, `committing-changes`, `building-ci-pipelines`, `simplifying-code`,
  `stress-testing-decisions`, `checking-official-docs`, `testing-in-browser`; and the `reviewer-tests` agent, which
  `aidlc-review` runs beside the other three reviewers.
- A practice format of our own, enforced by `scripts/validate.py` for every skill with `metadata.kind: practice`:
  When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules. The eight earlier practices are exempt by
  name until their content is rewritten; the list only shrinks.
- The quality bar lives in AGENTS.md (Floor, Enforced, Measured), written by `aidlc-onboard` and held by AGENTS.md's
  Boundaries, `aidlc-build` and `reviewer-compliance`. An exception carries a reason, an owner and an expiry date.
- Browser testing uses the repository's own pinned runner; no MCP server.
- This supersedes ADR 0008 where it left CI and browser testing out and let practices keep only the open format.

## Consequences
- About 1,000 more tokens of skill descriptions in every session.
- A later CI check can make the quality-bar floor mechanical.
- Behaviour evals for the new practices come with the evals work.

## Rejected alternatives
- A separate quality-bar skill: it would load only when routing picks it, and the floor must hold on every change.
- Browser testing through an MCP server: not allowed here, and the repository's runner gives the same evidence in CI.
