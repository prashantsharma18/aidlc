# shipments: agent guide

Calculates delivery estimates and labels for parcels. Owner: platform team.
Python 3.12, standard library only.

## How to work
- State your assumptions before a non-trivial change, and let the person correct them.
- Done means evidence: tests run, counts read, behaviour checked.

## How work runs here
- Start any new piece of work with the `aidlc-start` skill.
- Tests first: a failing test before any code; for a defect, a test that reproduces it.

## Packs used here
- none

## Map
Full map: `docs/codebase-map.md`.
- src/shipments/  delivery estimates and labels

## Commands
- Tests and lint, must pass before you report done: `python3 -m unittest discover -s tests -t .`
- One test file: `python3 -m unittest tests.test_eta`

## Legacy
- none

## Quality bar
- Floor, always on: no new suppression, no skipped or deleted test, no weakened assertion, no stub left in.

## Boundaries
- No new dependencies without asking first.
- Never change an existing test assertion to make a test pass. Stop and report.
