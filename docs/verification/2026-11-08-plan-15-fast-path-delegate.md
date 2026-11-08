# Verification: feature fast path and build modes (Plan 15, aidlc 4.3.0)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-15-fast-path-delegate.md` · Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (Plan 15)
ADR: `docs/adr/0017-feature-fast-path-and-build-modes.md`

## Checks
| Check | Result |
|---|---|
| `python3 scripts/validate.py` | validate: 2 plugin(s), 37 skill(s), 0 problem(s) |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 304 tests, OK (238 before; 32 in `test_fast_path.py`, 34 in `test_run_slices.py`) |
| `python3 scripts/route_check.py` | 57 positive prompts, rank-1 rate 86% (unchanged) |
| `claude plugin validate .` | ✔ Validation passed |
| Existing test assertions changed | none; the `LOADS` table and the `GATES` set are unchanged |

## Review Focus
| Case | Test |
|---|---|
| A bundle written before 4.3, with no MODE or TIER line | `test_a_bundle_without_mode_runs_hands_on` (build), `test_a_bundle_without_mode_is_refused` (runner) |
| A delegated session that crashes or hits its turn limit | `test_a_session_that_leaves_doing_stops_the_run`, `test_a_missing_note_stops_the_run`, `test_a_failed_session_stops_the_run_even_when_done` |
| A finished slice named again | `test_a_done_slice_is_refused`; a paused one: `test_i3_a_paused_slice_needs_the_persons_confirmation` |
| A fast-path feature that needs a schema change or a second slice | `test_every_condition_failing_sends_the_feature_to_f1`, `test_i4_re_routing_is_a_step`; eval `gate-f0-data-change` |
| A delegate bundle at Tier 2 or 3 | `test_build_stops_on_a_mode_the_tier_does_not_allow`, `test_a_mode_above_its_tier_is_refused`; eval `gate-delegate-tier2` |

## Evals
| Case | Score | Note |
|---|---|---|
| `route-f0-start` | not yet run | Needs no Bash; waits for the owner's cap (about $0.50) |
| `gate-f0-data-change` | not yet run | Needs no Bash; waits for the owner's cap (about $0.50) |
| `gate-delegate-tier2` | not run here | Needs the Bash grant, which the sandbox refuses on this machine (see the Plan 14 record); runs in CI or a container |

## Final review
A fresh reviewer read the branch: 0 critical, 7 important and 14 minor findings, verdict "with fixes". All were fixed
in one pass, each with a test seen failing first, except where noted.

| Finding | Fix |
|---|---|
| I1 build marked the index after committing the note, so the runner stopped after every first slice | Step 10 marks the row, sets STATUS `done`, and commits the note and the index together as the session's last commit |
| I2 `--part` with the default prompt built part 1's bundle | The runner adds ` part <n>` to a prompt without `{part}`; build's Inputs read `plans/<KEY>/part-<n>/` |
| I3 a paused slice had no record of the person's confirmation | `- <pause> confirmed by <name>, <date>` under "Pauses confirmed" in the note; build and the runner refuse a pause without it |
| I4 re-routing was claimed, not built | Start has an "index already exists" branch (done rows kept, stopped rows reset or removed, ROUTE note, move to `stories/<KEY>/` when several repositories); every D1 and F0 stop in plan, and a route-changing STOP IF in build, name `aidlc-start` |
| I5 onboarded repositories lacked the runner line | Added to onboard's `agents-md.md` template, with `--part` |
| I6 `gate-f0-data-change` waited at the restatement | The prompt confirms the restatement in advance |
| I7 `route-f0-start` used untested `label()`, which the tier table rates Tier 2 | The case adds a test that pins `label()` and asks for a new `return_label()`, leaving `label()` unchanged |
| Minors | The runner refuses a branch without the key, a folder outside git, an agent that cannot start and an unknown prompt placeholder; `field()` stays on its line and reads backticks, bold and a colon; the default command denies `git push`; build checks the mode in step 2 and only reports a stop before the note exists; compliance flags a Tier 2 checkpoint bundle without a CHECKPOINT and exempts pre-4.3 notes; review and plan name the feature brief, and plan stops when the tier rises; stale lines in build's Produces and the codebase map; the Tier 2 case forbids the test file; both briefs say a brief has no CHECKPOINT |

## Not verified here
These need a live headless run, which this plan did not make. The runner fails safe on each: a refused tool leaves the
progress note's STATUS short of `done`, so the run stops.
- Whether `claude -p` treats a project `ask` rule as a refusal, and whether `--disallowedTools "Bash(git push*)"` takes
  that form on the command line.
- Whether `/aidlc:aidlc-build` starts the person-only skill in `-p` mode (Plan 14 started person-only stages this way
  in `claude plugin eval`).
- Whether `--permission-mode acceptEdits` covers the workspace's `../stories` folder.

## Decisions made during the plan
| Where | Decision |
|---|---|
| Plan | Route code F0; start checks what the work item shows, plan what needs the code; a feature brief is one slice; MODE and TIER in the bundle; recipe review in every mode; the STATUS line; the note committed first; the runner stops at anything short of `done` |
| Task 3 | The bundle's DO step 0 waits for confirmation only in hands-on |
| Task 5 | The paid smoke waits for the owner's cap |
| Final | The reviewer's cheap minors were fixed in the same pass, per the owner's standing rule |
