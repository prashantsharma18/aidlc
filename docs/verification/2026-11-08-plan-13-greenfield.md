# Verification: greenfield entry, route G (Plan 13, aidlc 4.1.0)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-13-greenfield.md` · Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md` (Plan 13)
Commits: `e1a5096..` the release commit on `docs/plan-13-greenfield`. The version moved to 4.1.0 in the fix-pass commit.

## Checks
| Check | Result |
|---|---|
| `python3 scripts/validate.py` | validate: 2 plugin(s), 37 skill(s), 0 problem(s) |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 213 tests, OK (192 before; 21 in `test_greenfield.py`) |
| `claude plugin validate .` | ✔ Validation passed |
| Existing test assertions changed | none; the `LOADS` table is unchanged |

## Route G on paper
One repository: start in an empty repository (no `AGENTS.md`) chooses route G; intent, specify and design write their
documents, with `new-system.md`, and merge on their own; prepare reads the merged `new-system.md` and writes `AGENTS.md`
with commands marked `(not yet run)`; slice 0 skips build's step 1, runs the scaffold, adds only the approved
dependencies and writes `ci.yml`; verify and review find CI and the protected `AGENTS.md`; confirm runs on the skeleton
and clears the marks; the story's criteria follow as F1; release ends the story. Several repositories: the same, with
the repositories registered at the workspace root before prepare, a coordination plan holding one slice-0 part each,
and part indexes that `story_status.py` reads (setup rows ignored). No step stops on a missing input.

## Review Focus
| Case | Test |
|---|---|
| A home with only a README, a licence, a `.gitignore`, `.github/`, `docs/` or `plans/` counts as empty | `test_start_counts_config_only_folders_as_empty`, `test_review_minors_are_closed` (no source code and no build manifest) |
| A folder with `AGENTS.md` is never route G | `test_a_folder_with_agents_md_is_never_route_g` |
| A stack with no generator | `test_a_stack_without_a_generator_has_no_scaffold`, `test_slice_0_without_a_scaffold_is_written_by_hand` |
| Several repositories: one slice-0 part each | `test_several_repositories_get_one_slice_0_part_each`, `test_route_g_has_one_sequence_of_pull_requests` |
| A prepared command that fails at confirm stops onboard | `test_confirm_stops_on_a_command_that_fails` |

## Final review
A fresh reviewer read the branch: 2 critical, 9 important and 8 minor findings, verdict "with fixes". All were fixed in
one pass, each with a test seen failing first (8 tests).

| Finding | Fix |
|---|---|
| C1 onboard confirm stopped on the skeleton it needs | The stop names prepare only, with start's test for "no code" |
| C2 plan stopped on slice 0 for the missing map | On slice 0 of route G, the design and `new-system.md` take the map's place |
| I3 slice 0 against "no new dependency"; generators pull current versions | The bundle lists the approved DEPENDENCIES; a step pins each direct dependency; an unlisted package is a stop; compliance checks the manifest |
| I4 branch and merge order in one repository | Route G is a sequence: the design documents merge alone, then prepare, slice 0 and confirm, each its own pull request |
| I5 new repositories not registered in the workspace | The person creates them and re-runs `aidlc-onboard` at the root (WORKSPACE.md and deny rules) |
| I6 undecided that becomes one repository | At a workspace root the coordination plan is written even for one repository |
| I7 one stack per system | `new-system.md` holds one REPOSITORY block per repository (stack, dependencies, paths, commands, scaffold, CI) |
| I8 what the G spec covers; slice 0's evidence | The spec states the system and its first criteria; slice 0's evidence is its DONE WHEN checks; the criteria are built after confirm as F1 or F2, and the story ends with release |
| I9 CI ownership and branch protection | Slice 0 owns `ci.yml`; prepare copies `ai-review.yml` and asks the person for code-owner protection; confirm asks the person to make slice 0's checks required |
| I10 the `(scaffold)` guard | A `(scaffold)` trailer outside slice 0 of a route G story, or on a command that is not the RECIPE, is a high finding; such a commit changes no existing file |
| I11 slice 0's MAY CHANGE | The block's PATHS, the scaffold's files and `ci.yml`; MUST NOT names `AGENTS.md`, `CODEOWNERS`, `.claude/**`, `ai-review.yml` and the check scripts |
| M12–M18 | Setup rows in the index, and onboard marks its own; "no source code and no build manifest"; design's step 9 runs after the route G steps; the RECIPE rule names the scaffold exception and one trailer per tool; the AGENTS.md template note is a comment; start's description names the new system; onboard names where `new-system.md` lives |

The reviewer declined one point as older than Plan 13: build commits the progress note with the slice's first commit,
which sits awkwardly with a recipe commit that holds only tool output. It applies to every recipe and is left for a
later plan.

## Decisions made during the plan
| Where | Decision |
|---|---|
| Task 3 | Onboard names the starter scripts as `check_packs.py` and `check_recipe_commit.py` from aidlc's `starter/repo/`, because the validator reads a backticked `scripts/…` as a file in the skill's own folder |
| Final | Route G as one sequence of pull requests (I4–I6, I8); slice 0 owns `ci.yml` and a person sets branch protection (I9); setup rows before the part's rows, so a part never shows merged before confirm |

Not covered here: a live run of route G (Plan 14's route walk-throughs); evals under pressure (Plan 14).
