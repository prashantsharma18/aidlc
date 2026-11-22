# Verification: work routes, the part model and tracking (Plan 12, aidlc 4.0.0)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-12-aidlc-4-routes.md` · Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md`
Commits: `240ea5a..` the release commit on `docs/plan-12-aidlc-4-routes` (21 commits, the design and plan included).

## Checks
| Check | Result |
|---|---|
| `python3 scripts/validate.py` | validate: 2 plugin(s), 37 skill(s), 0 problem(s) |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 192 tests, OK (116 before Plan 12; 48 in `test_routes.py`, 28 in `test_story_status.py`) |
| `claude plugin validate .` | ✔ Validation passed |
| Existing test assertions changed | none; the `LOADS` table in `scripts/test_loads.py` is unchanged |

## Status script dry run
A sample workspace with `CURRENT spec v2 · contract tracking-api v1`: `shipments-api` merged on spec v1, `web-portal`
building on spec v2. `story_status.py SHIP-1 --check-release` printed `shipments-api | merged | … | re-plan: spec v1 < v2`
and `web-portal | waiting`, reported both folders as "not a git repository", printed `Release: not ready`, and exited 1.

## Weaknesses and the tests that pin them
| ID | Test |
|---|---|
| W2 | `test_a_pull_request_is_one_part`, `test_verify_writes_one_evidence_file_per_part` |
| W3 | `test_story_documents_are_exempt_from_the_scope_check`, `test_the_plan_approval_is_recorded_on_the_work_item` |
| W4 | `test_operate_and_feedback_need_no_story`, `test_the_workspace_root_may_write_incidents_and_feedback` |
| W5, W15 | `test_design_always_runs_and_only_discover_is_optional`, `test_discover_records_findings_instead_of_drafting`, `test_design_always_runs_in_the_onboarding_texts` |
| W6 | `test_start_sorts_defects_into_d1_and_d2`, `test_plan_has_a_brief_mode_that_writes_the_fix_brief`, `test_build_takes_the_confirmed_brief`, `test_a_d2_defect_starts_its_spec_with_the_reproduction`, `test_the_fast_path_brief_replaces_spec_and_plan_downstream` |
| W7 | `test_the_orphan_agents_are_gone`, `test_every_agent_is_named_by_a_core_skill`, `test_no_document_lists_the_removed_agents` |
| W8 | `test_the_progress_note_is_a_committed_file`, `test_a_fresh_session_per_slice_is_preferred_and_required_after_a_slip` |
| W9 | `test_no_stage_produces_only_in_the_reply`, `test_design_review_and_release_name_their_files` |
| W10, W12 | `test_start_routes_and_never_drafts_the_story`, `test_the_workspace_keeps_nothing_for_a_one_repository_story`, `test_a_new_requirement_gets_a_provisional_key` |
| W11 | `test_each_tracked_stage_marks_its_row`, `test_plan_writes_the_part_index_with_the_rows_the_status_script_reads`, `test_the_workspace_names_the_status_command`, `test_who_marks_merged_and_what_a_re_plan_resets`, and all of `test_story_status.py` |
| W13 | `test_design_amends_a_contract_at_the_story_level`, `test_review_sends_a_contract_change_to_design`, `test_bundles_pin_their_versions`, `test_release_checks_every_part_and_runs_the_integration_check`, `test_the_first_current_line_is_written` |
| W14 | `test_specify_classifies_each_part_by_its_state`, `test_a_merged_part_gets_a_revision_pull_request`, `test_amended_assertions_are_the_second_exception_everywhere`, `test_release_waits_for_every_part_at_the_current_spec` |
| W16 | `test_the_map_and_start_name_the_same_routes`, `test_every_route_names_only_stages_and_modes_that_exist`, `test_the_docs_match_the_kit` |
| UI | `test_design_records_a_ui_reference_or_drafts_a_wireframe` |

## Review Focus
| Case | Test |
|---|---|
| Hand-edited indexes (case, line endings, a byte-order mark, stage names in backticks) | `test_case_and_crlf_are_tolerated`, `test_a_byte_order_mark_is_tolerated`, `test_stage_names_in_backticks_or_capitals_are_read` |
| A pin on a contract the story dropped | `test_a_pin_on_a_contract_the_story_dropped_is_reported` |
| A part index with no PINS line, or no spec pin | `test_a_part_without_pins_is_reported`, `test_a_part_without_a_spec_pin_needs_a_re_plan` |
| An aidlc 3 pointer index at the root | `test_start_hands_over_an_old_pointer_index` |
| A fix brief with no SOURCE, a placeholder CONFIRMED line, or the wrong TIER or DESIGN | `test_build_stops_on_a_brief_with_no_source`, `test_review_minors_are_closed` |

## Final review
A fresh reviewer read the whole branch: 2 critical, 9 important and 9 minor findings, verdict "with fixes". Every one
was fixed in one pass, each with a test seen failing first: 13 new tests in `test_story_status.py` and 10 in
`test_routes.py`.

| Finding | Fix |
|---|---|
| C1 a new requirement looped between start and intent | `aidlc-start` writes the index under a provisional key `NEW-<slug>`; the person renames the folder once the item exists |
| C2 nothing wrote the first CURRENT line, so the release check was stuck or blind | `aidlc-specify` writes `CURRENT spec v1`; `aidlc-design` adds contract versions; `story_status.py` blocks release without a CURRENT spec |
| I1 the script passed lines it could not read | A missing spec pin, an unread PARTS row and an unread version item each become a stated need; dotted versions compare |
| I2 the script read any checked-out branch; nobody owned `merged` | `--check-release` requires each repository on its default branch; review marks `merged` in the final approved commit; a re-plan resets the later rows |
| I3 stage names in backticks or capitals were missed | Normalised; an index with no recognised rows is a need |
| I4 build's rules contradicted its own steps | Build may edit its row in the index; "no changed assertion" reads "outside AMENDED ASSERTIONS" |
| I5 the fast path stopped at plan, verify and review | The fix brief replaces spec and plan in all three |
| I6 route C had no index | A change request works in the original story's index |
| I7 a split part collided in one repository | `aidlc-design` decides a split; a second part in one repository uses `plans/<KEY>/part-<n>/`, which the script reads |
| I8 three texts still said design runs only when the tier asks | Corrected in the AGENTS.md template, the starter and the workspace guide |
| I9 tests missed two checks the design asked for | Every route's stages exist; the compliance reviewer checks PINS |
| M1–M9 | Root index points to `status.md` for parts; `progress-fix.md`; placeholder checks on the brief; "Amended assertions seen red" in the progress note and the compliance checks; the part index may be updated in place; the one-repository release rule; plans excluded from the PR size; doc and ADR notes (0009, 0012 amended by 0015); list indentation |

## Decisions made during the plan
| Where | Decision |
|---|---|
| Task 3 | The test for "in your reply" also caught build step 4, which the plan fixed in Task 8; that replacement was applied in Task 3 |
| Task 4 | The pointer-index sentence was reworded so the plan's test phrase reads mid-sentence |
| Task 13 | The Tier 1 cell was edited where it lives: `tiers-table.md` and the six asset copies |
| Task 13 | Brief mode is its own list after plan's step 9 |
| Task 14 | Design step 1 now continues to the UI step when a "none needed" change adds a screen or a flow |
| Task 15 | The README says "chooses the route" rather than "one of seven routes", since route G arrives in 4.1 |
| Final | I2 and I7 as in the table above; C1's provisional key |

Not covered here: behaviour under pressure and live routing (Plan 14's evals); greenfield (Plan 13).
