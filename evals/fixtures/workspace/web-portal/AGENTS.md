# web-portal: agent guide

Shows customers where their parcel is. Owner: platform team.
Node.js 22, no build step.

## How to work
- State your assumptions before a non-trivial change, and let the person correct them.
- Done means evidence: tests run, counts read, behaviour checked.

## How work runs here
- Start any new piece of work with the `aidlc-start` skill.
- Tests first: a failing test before any code; for a defect, a test that reproduces it.

## Map
Full map: `docs/codebase-map.md`.
- src/  the tracking page

## Commands
- Tests and lint, must pass before you report done: `node --test`

## Legacy
- none

## Quality bar
- Floor, always on: no new suppression, no skipped or deleted test, no weakened assertion, no stub left in.

## Boundaries
- No new dependencies without asking first.
- Never change an existing test assertion to make a test pass. Stop and report.
