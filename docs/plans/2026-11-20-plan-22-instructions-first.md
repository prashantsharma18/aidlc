# Instructions First Implementation Plan (Plan 22)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aidlc becomes instructions only. It ships no scripts and no CI workflows to teams, needs git and no
code-host feature, and holds each rule through the team's own project, a reviewer that did not write the change, and
a person reading evidence that git can confirm.

**Architecture:** The rules stay; what holds them changes. The session writes one evidence file with plain git
commands, `plans/<KEY>/review-evidence.md`, and commits it. Reviewer agents with Read, Glob and Grep only read it in
a fresh context and return a verdict that names the commit they judged; a later code change voids it. The plan check
becomes the plan's checklist, the recipe check a git procedure, the slice runner a person starting each session,
story status and the release check rows the AI fills from git and a person confirms, and the contract checks commands
the team runs in its own CI (oasdiff, `sha256sum -c`, `git ls-remote --tags`). `aidlc-feedback` turns a repeated
mistake into a check in the team's project. The words become host-neutral. Then the starter scripts, workflows, Stop
hook and their tests go; the tag `checks-v1` keeps them.

**Tech Stack:** Markdown (skills, agents, templates, docs), JSON (the example settings, the plugin manifest), git,
Python 3.12 standard library `unittest` for aidlc's own tests. No new dependency.

**Spec:** `docs/design/2026-11-20-instructions-first.md` (written in the session, committed by Task 1). Supporting
inputs: the code audit's checklist (`.superpowers/sdd/plan-22-inputs/inventory-checklist.md`, verified line by line;
see "Where the audit checklist was wrong"), ADRs 0010, 0012, 0019, 0020, 0022 and 0023, and Plan 21 as the model.

Branch: `docs/plan-22-instructions-first` (already checked out). Base: local `main` at `7843f18` plus `d39f6bb` on
this branch. aidlc 5.0.0. The suite is 725 tests, OK; the validator reports 0 problems.

## Decisions this plan makes

| Question | Ruling | Why |
|---|---|---|
| "Change request" or "pull request" (design, "The principle", last bullet) | **"Pull request" stays**, defined once in `using-aidlc`: the code host's review request (a pull request on GitHub, Bitbucket or Azure Repos, a merge request on GitLab). "The review tool", "the team's CI" and "the code host" name the rest. | aidlc already uses "change request" for route C (`using-aidlc`'s routes table, `aidlc-start`'s KIND line, the README). Using it for a pull request would make one word mean two things. |
| What a skill may name | Plain git commands, and the standard tools the design names (oasdiff, `sha256sum`), with ordinary shell glue (`grep`, `head`, `echo`) in examples. Never a script of aidlc's own, never a tool-specific command (`/aidlc:`, `$ARGUMENTS`, `${CLAUDE_…}`). Repository commands stay "the commands named in `AGENTS.md`". | The design names these commands. AGENTS.md's rule against tool-specific commands is about one AI tool's syntax; git runs everywhere aidlc does. |
| Where the evidence file lives, and who writes it | `plans/<KEY>/review-evidence.md` (`plans/<KEY>/part-<n>/` for a second part), from a template kept identical in `aidlc-build/assets/` and `aidlc-review/assets/`. `aidlc-build` writes it at the end of step 9, `aidlc-review` at step 3; each commits it on its own. `aidlc-verify` reads it. | Story documents travel on the branch and are exempt from MAY CHANGE; committing it lets the code owner read it in the pull request and re-run any command. A template is read from its own skill's folder, so the two stages each need a copy (as with `story-index.md`). |
| What the evidence file holds | HEAD, BASE (`git merge-base HEAD origin/<default branch>`), branch; `git diff --stat <base>` and `git diff --name-only <base>`; `git diff <base> -- <test paths>`; the test count at BASE and HEAD; each check command with its exit code; `git diff <base> -- <manifests>`; `git diff <base> -- plans/<KEY>/`; added suppression, skip and exception lines and removed closing directives; each recipe commit re-run on its parent. Each section names its reader. | The design's list, plus the two rows the slice check also covered (suppressions, recipe commits), so no rule loses its evidence. |
| When a verdict is void | When `git diff --name-only <judged commit> HEAD -- . ':(exclude)plans/<KEY>/'` prints any path. | The evidence file, the review record and the merged row are all committed after the verdict, inside `plans/<KEY>/`. A rule on HEAD itself would void every verdict at once. |
| The test count at BASE | From the first slice's progress note (a new TESTS BEFORE line, written at build step 1), or from a temporary worktree at BASE. | Running the suite at BASE can be slow; the build already runs it before any change. |
| The example settings (`starter/*/.claude/settings.json`) | Same paths. Keep the secret-read denies, the sandbox, the ask rules, `disableBypassPermissionsMode`, the plugin entries, and the denies on `.claude/**`, `CODEOWNERS` and `.github/CODEOWNERS`. Remove the Stop hook and the three denies on `scripts/check_*.py`, `scripts/run_slices.py`, `ai-review.yml`, and the workspace's deny on `story_status.py`. | The design removes "the deny rules that protect them" (the removed files). The `.claude/**` and CODEOWNERS denies protect the settings and the ownership list, so a session cannot loosen its own controls. Keeping the paths keeps `scripts/validate.py` unchanged. |
| `scripts/validate.py` | Unchanged. | Checked: its only starter check reads the `Read(` denies of both settings files, which stay identical. It names no removed file. |
| The ADRs that name removed code (0012, 0015, 0016, 0017, 0020, 0021, 0022, 0023) | Each gets a line above `## Context` and a dated last section "Amended by ADR 0024 (2026-11-20)". Their original lines stay. ADR 0019's Status becomes "Superseded by ADR 0024", in ADR 0011's format. | A decision record is history; rewriting its lines would erase what was decided. Appending the amendment keeps both. Tests that pin the ADRs' phrases stay green. |
| The codebase map | Keeps naming each removed script and workflow, in one line that says they are kept under the tag `checks-v1`, with `docs/archive/checks-v1.md` (modelled on `harness-v1.md`). | The map says where things are; "archived, here" is true. Three record tests that pin those names (`test_gates_hold.RecordTest`, `test_multirepo.RecordTest`, `test_fast_path.ReviewFixesTest.test_m12_stale_lines`) stay unchanged. |
| The README's "Where the gates hold" | Rewritten around the team's own checks and the reviewer agents. It keeps its heading, the two tool columns and the GitHub Free facts, now as context for a team that chooses those features. | The facts are true and useful; aidlc no longer depends on them. `WhereGatesHoldTest`'s two README tests stay unchanged. |
| `starter/repo/CODEOWNERS` | Keeps `scripts/`, `.github/`, `.claude/` and `.mcp.json` owned by the leads; only the comment changes. | In a team's repository those paths now hold the team's own checks and settings, which the design says the team owns. |
| "The recipe check" | Keeps its name, for the git procedure in `aidlc-build` step 5. | ADRs 0012 and 0016 and the compliance reviewer use the name; the rule is the same, only the tool changed. |
| The merged row, the pause lines, the CONFIRMED line | Unchanged formats. `aidlc-release` (not a script) reads the merged row; the next session reads a pause line. | No parser remains, but the records still carry the decisions (ADR 0023). |
| `starter/repo/.github/workflows/ci.yml` (the audit offered keeping it as an example) | Deleted with the other three workflows. | The design deletes `starter/repo/.github/workflows/`. Slice 0 writes the team's own CI from `building-ci-pipelines`. |
| Status across repositories | `stories/<KEY>/status.md` stays, written by the AI at the workspace root from each part's index on its default branch (`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`). The release check becomes a Parts table in `readiness.md`, one row per repository, confirmed by a person. | Design table, row 9. `status.md` is pinned by existing tests and still useful between releases. |
| Version | 6.0.0 in Task 8, if the owner approves item V1. | The gates and the starters change; the change list planned 6.0.0 for this point. |

## Global Constraints

- Python 3.12 standard library only; no new dependency anywhere.
- Change no existing test assertion, and delete no existing test, except the items listed under "Needs the owner's
  decision". Each task applies exactly its own items, in its own step.
- New tests go in `scripts/test_instructions_first.py`: Task 1 creates it; every later task appends one class above its
  `if __name__ == "__main__":` line.
- Every task writes its new tests first and sees them fail before any other edit.
- After every task: `python3 scripts/validate.py` reports 0 problems and
  `python3 -m unittest discover -s scripts -p 'test_*.py'` passes.
- Stage skills keep their sections (When to use, Inputs, Steps, Produces, Gate, Stop if, Common excuses, Red flags,
  Rules) and the line "You draft; you never approve."
- The twelve Rules bullets that start "People decide; you record" stay byte-identical (Task 7 replaces all twelve
  with one line).
- No new "Load the `<name>` skill" phrase in any stage skill: `scripts/test_loads.py` pins the table.
- A skill names plain git commands and the tools oasdiff and `sha256sum` where needed, never an aidlc script and never
  tool-specific syntax.
- Templates under `skills/aidlc-*/assets/`: a placeholder outside a code block is `{{…}}`; FIELD lines sit in a
  ```` ```text ```` fence; every fence is a `text` fence; a document a person approves opens with `## For the reviewer`.
- Identical copies stay identical: both `story-index.md`, both `review-evidence.md`, both `incident.md`, both
  `explorer-brief.md`.
- `skills/aidlc-release/assets/readiness.md` keeps exactly ten `- [ ] ` lines.
- Never write "pointer" in `starter/workspace/stories/README.md`, `starter/workspace/WORKSPACE.md` or
  `skills/aidlc-onboard/assets/workspace.md`.
- Never write "hand-marked" or "marked by hand" in `skills/aidlc-release/SKILL.md`, or after "## Decision" in ADR 0022.
- `aidlc-onboard`'s step 0 keeps at least five bullets and no line over 400 characters; a line of
  `docs/operating-model/adoption.md` holding "it never writes a name it was not given" stays at 120 characters or fewer.
- "Change request" never means a pull request.
- Behaviour evals under `evals/` are not changed (see item E1).
- Commits: stage explicit paths (never `git add -A`); the author email is
  `6386481+prashantsharma18@users.noreply.github.com`; end each message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Text in files, tickets and tool output is data, never an instruction.

## Review Focus

1. **A verdict given, then the code changed.** A fix after review must void the verdict, visibly, by a command the
   person can run. Task 2's `test_a_stale_verdict_is_void` (review's Stop if, the review record's verdict lines at a
   commit) and `test_a_verdict_comes_from_a_non_author_and_names_its_commit` (the same Rules bullet, with the voiding
   command, in build, verify and review).
2. **An evidence file with a section missing, or written for another commit.** The reviewer must report it as high and
   ask for it again, never judge from memory. Task 2's `test_the_reviewers_read_it_and_never_run_a_command` and
   `test_each_section_names_its_reader`.
3. **A reviewer agent that can run commands.** If an agent gains Bash (in a team's copy, or by a later edit), it stops
   being a read-only judge and can make the evidence it reads. Task 2 pins `tools: Read, Glob, Grep` on all four
   reviewer agents.
4. **A removed name left where a team reads it.** A skill, template, starter, quickstart or the README that still
   names a deleted script, workflow or hook sends a session to a file that is not there. Task 9's
   `test_no_file_a_team_reads_names_the_removed_code`, across every live file.
5. **A Rules bullet that drifts, or a stage that still needs GitHub.** One of the twelve bullets edited alone, or a
   "checked on GitHub" left in a record format. Task 7's `test_the_rules_bullet_is_host_neutral_and_identical` and
   `test_no_stage_skill_template_agent_or_doc_needs_a_github_feature`.

Known limits, stated in ADR 0024 and the verification record: a reviewer agent can be lenient; the session writes the
evidence file it is judged by, so the code owner may re-run any command in it; the suppression markers in the template
are a list, not a parser; a team that wants a hard block adds one to its own CI.

## Needs the owner's decision

AGENTS.md says: never change an existing test assertion to make a test pass; stop and report. This plan removes code
and rewords pinned text, so it must delete and change existing tests. **Approving this plan approves exactly the
items below, and no other change to an existing test.** If an executor finds that any other existing assertion fails,
it stops and reports. The list was built by running the suite (725 tests, OK), deleting the starter code in a scratch
clone and rerunning it, reading every remaining test file, and then applying this plan task by task to a clean clone of
`d39f6bb` with the full suite run after each task.

**Totals:** 6 test files deleted (353 tests); 46 more test methods deleted in 6 kept files; 27 test methods with an
assertion changed in 8 files; 3 structural edits with no assertion (two imports, one helper). The suite goes from 725
tests to 365 (326 kept, 39 new).

### A. Test files deleted with the code they test (Task 9) — 353 tests

| File | Tests | Tests what |
|---|---|---|
| `scripts/test_check_slice.py` | 151 | `starter/repo/scripts/check_slice.py` and its Stop-hook mode |
| `scripts/test_check_plan.py` | 17 | `check_plan.py` |
| `scripts/test_check_recipe_commit.py` | 10 | `check_recipe_commit.py` |
| `scripts/test_check_contract.py` | 60 | `check_contract_version.py`, `check_contract_pin.py` |
| `scripts/test_run_slices.py` | 41 | `run_slices.py` |
| `scripts/test_story_status.py` | 74 | `starter/workspace/scripts/story_status.py` |

### B. Test methods deleted in files that stay — 46

| Item | Task | File: test | Why |
|---|---|---|---|
| T2a | 2 | `test_gates_hold.py`: `WiringTest.test_build_and_compliance_use_it` | Pins "Run the slice check" in `aidlc-build` and "slice check" in `reviewer-compliance` |
| T2b | 2 | `test_gates_hold.py`: `FinalReviewFixesTest.test_compliance_reads_the_check_wherever_it_is_given` | Pins the compliance reviewer reading the slice check's output |
| T4f | 4 | `test_docs.py`: `ReviewFixesTest.test_i2_the_status_command_writes_with_write` | Pins `story_status.py <KEY> --write` in `routes.md` |
| T5d | 5 | `test_multirepo.py`: `ContractWorkflowTest.test_the_guide_names_the_commands` | Pins the contract scripts' command lines in the rules file |
| T5e | 5 | `test_multirepo.py`: `OnlinePinCheckTest.test_the_guide_names_the_online_check_and_when_it_runs` | Pins `check_contract_pin.py --online` in the rules file |
| T5f | 5 | `test_fast_path.py`: `FastPathTest.test_the_runner_is_named_where_it_is_used` | Pins `run_slices.py` in the starter rules file and onboard |
| T5g | 5 | `test_fast_path.py`: `ReviewFixesTest.test_i5_onboarded_repositories_name_the_runner` | Pins the `run_slices.py` command line in both rules files |
| T8b | 8 | `test_gates_hold.py`: `FinalReviewFixesTest.test_the_ci_comment_says_who_holds_the_workflow` | Reads `ci.yml`'s comment and pins `ci.yml` in the README's gates section |
| T9c | 9 | `test_gates_hold.py`: the class `StarterReviewTest`, 13 tests: `test_every_action_is_pinned_to_a_commit`, `test_the_key_lives_in_an_approved_environment_and_is_scrubbed`, `test_the_required_check_fails_closed`, `test_the_review_reads_the_base_branchs_rules`, `test_no_run_block_interpolates_a_ref`, `test_it_never_approves`, `test_code_owners_own_the_workflows_and_scripts`, `test_the_review_restores_the_base_branchs_session_settings`, `test_both_passes_load_no_repository_settings_or_hooks`, `test_the_restore_loop_names_every_path_the_action_restores`, `test_no_run_block_interpolates_any_expression`, `test_code_owners_own_the_mcp_config`, `test_strict_mcp_config_is_not_used` | Its `setUp` reads `ai-review.yml`. Two of its tests read only CODEOWNERS; Task 9's `test_the_owners_still_hold_the_teams_own_checks` pins those lines again |
| T9d | 9 | `test_gates_hold.py`: `WiringTest.test_the_stop_hook_runs_the_slice_check`, `WiringTest.test_ci_runs_the_base_branchs_copy_on_the_head_commit`, and the rest of `FinalReviewFixesTest`: `test_ci_falls_back_only_when_the_base_has_no_script`, `test_the_stop_hook_skips_a_missing_script_and_times_out` (4) | They test the Stop hook and `ci.yml` |
| T9e | 9 | `test_multirepo.py`: the rest of `ContractWorkflowTest` (`test_every_action_is_pinned_and_no_run_block_interpolates`, `test_oasdiff_is_pinned_by_version_and_checksum`, `test_the_check_runs_the_base_branchs_script_read_only`, `test_only_the_publish_job_writes_and_only_from_main`, `test_ci_checks_the_vendored_contracts`, `test_the_session_cannot_edit_the_contract_scripts`); the class `ContractWorkflowHardeningTest` (`test_publish_writes_on_the_job_only_and_serialises`, `test_no_privileged_or_manual_trigger`, `test_every_job_that_runs_a_contract_script_fetches_all_history`, `test_the_checksum_is_verified_before_the_archive_is_extracted`, `test_the_pin_job_runs_the_base_branchs_scripts`, `test_the_pin_job_decides_from_the_base_on_a_pull_request`, `test_publish_documents_the_skipped_middle_version`); the class `ContractWorkflowFinalReviewTest` (`test_the_check_decides_from_the_base_on_a_pull_request`, `test_the_pin_job_has_a_timeout`, `test_the_check_asks_for_up_to_date_branches`, `test_the_tag_ruleset_restricts_creation_too`); and `OnlinePinCheckTest.test_the_adr_and_the_publish_job_say_who_runs_it` (18) | They test the contract workflows, `ci.yml`'s contract-pin job and the contract scripts |
| T9f | 9 | `test_one_plugin.py`: `OnePluginTest.test_the_starter_ci_runs_no_pack_check` | Reads `ci.yml` |
| T9g | 9 | `test_recording.py`: `ParsedRecordTest.test_the_runner_tells_the_person_to_tell_the_ai`, `ParsedRecordTest.test_a_pause_line_with_how_it_was_confirmed_still_parses` (2) | They read and run `run_slices.py` |

Count: 2 + 1 + 4 + 1 + 13 + 4 + 18 + 1 + 2 = 46. By file: `test_gates_hold.py` 20, `test_multirepo.py` 20,
`test_fast_path.py` 2, `test_recording.py` 2, `test_docs.py` 1, `test_one_plugin.py` 1.

### C. Test methods with an assertion changed — 27

| Item | Task | File: test | The change | Why |
|---|---|---|---|---|
| T1 | 1 | `test_gates_hold.py`: `AdrTest.test_each_decision_is_recorded_with_a_decider` | The Status regex also accepts `Superseded by ADR 0024` | ADR 0019 is superseded |
| T3a | 3 | `test_fast_path.py`: `FastPathTest.test_build_reads_the_mode` | Drops "the slice runner named in AGENTS.md" (5 assertions stay) | No runner |
| T3b | 3 | `test_gates_hold.py`: `PlanCheckTest.test_plan_runs_the_plan_check` | "run the plan check named in AGENTS.md…" becomes "go through the plan's checklist (`assets/plan.md`) item by item…" | No plan script |
| T3c | 3 | `test_greenfield.py`: `GreenfieldTest.test_ci_and_branch_protection_have_owners` | Drops "`ai-review.yml`" in `aidlc-plan` (4 assertions stay, "branch protection" included) | No starter workflow |
| T4a | 4 | `test_routes.py`: `RoutesTest.test_the_workspace_names_the_status_command` | The workspace guide "writes `stories/<KEY>/status.md`" instead of naming `story_status.py`; drops `story_status.py` in onboard | No status script |
| T4b | 4 | `test_routes.py`: `RoutesTest.test_release_checks_every_part_and_runs_the_integration_check` | "--check-release" becomes "fill the Parts table in `assets/readiness.md`" | The release check is a table |
| T4c | 4 | `test_multirepo.py`: `DecisionsTest.test_release_reads_the_real_merge_state` | "…from its pull request on GitHub when it can" becomes "its `merged` row reads done" | Merge state from git, on any host |
| T4d | 4 | `test_multirepo.py`: `OnlinePinCheckTest.test_release_runs_the_online_check` | The first assertion names "the commands in `designing-apis`" (its second stays) | No pin script |
| T4e | 4 | `test_multirepo.py`: `HygieneTest.test_the_workspace_guide_names_the_command_and_the_owner` | `story_status.py --write-gitignore` becomes "a person adds or removes the repository's line in the root's `.gitignore`" | No generator |
| T5a | 5 | `test_gates_hold.py`: `WiringTest.test_the_guide_names_the_commands_and_the_exception_format` | Drops the two script command lines (the exception format stays) | The rules file names no script |
| T5b | 5 | `test_gates_hold.py`: `WhereGatesHoldTest.test_onboard_says_it_too` | "…on its GitHub plan" becomes "…on its code host" | Host-neutral |
| T5c | 5 | `test_multirepo.py`: `DecisionsTest.test_onboard_sets_up_the_home_repository` | The `--write-gitignore` and contract-script assertions become the `.gitignore` line and the consumer's `sha256sum -c` (the CODEOWNERS assertion stays) | No scripts to copy |
| T7a | 7 | `test_recording.py`: `RuleTest.test_every_recording_stage_states_the_rule` | Two of its seven `PHRASES` become host-neutral | The Rules bullet |
| T7b | 7 | `test_recording.py`: `RuleTest.test_each_gate_says_who_tells_the_ai` | `aidlc-operate`'s entry: "after checking in git or the review tool" | Host-neutral |
| T7c | 7 | `test_recording.py`: `RuleTest.test_the_steps_record_after_checking` | The feedback and onboard phrases (5 others stay) | Host-neutral |
| T7d | 7 | `test_recording.py`: `FixRoundTest.test_plan_red_flag_and_relayed_declines` | "…did not check on GitHub." becomes "…in the review tool." | Host-neutral |
| T7e | 7 | `test_recording.py`: `ParsedRecordTest.test_the_merged_row_is_marked_after_the_check_and_never_merged` | "the required checks on GitHub" becomes "in the review tool and the team's CI result", twice | Host-neutral |
| T7f | 7 | `test_recording.py`: `TemplateRecordTest.test_each_record_line_says_how_it_was_confirmed` | The `plan.md` entry of `RECORDS` | Host-neutral record format |
| T7g | 7 | `test_recording.py`: `FinalReviewRecordTest.test_plan_records_only_after_being_told_or_checking` | "…check it on GitHub." becomes "…in the review tool." | Host-neutral |
| T7h | 7 | `test_recording.py`: `FinalReviewRecordTest.test_the_approval_itself_is_the_code_owners_on_github` | "on GitHub"/"in GitHub" become "in the review tool" (the readiness assertion stays) | Host-neutral |
| T7i | 7 | `test_multirepo.py`: `TemplateTest.test_the_part_index_and_the_bundle_pin_the_home_commit` | "GitHub permalinks at a commit" becomes "permalinks at a commit (the full commit hash in the address)" | Host-neutral |
| T7j | 7 | `test_multirepo.py`: `DecisionsTest.test_tracker_links_are_permalinks` | Drops "GitHub" from both permalink phrases | Host-neutral |
| T8a | 8 | `test_docs.py`: `DocsTest.test_each_phase_names_its_skills` | Phase 4's "run_slices.py" becomes "one fresh session per slice" | No runner |
| T8c | 8 | `test_one_plugin.py`: `OnePluginTest.test_the_decision_is_recorded_and_released` | "5.0.0" becomes "6.0.0" | Only with item V1 |
| T9a | 9 | `test_gates_hold.py`: `DenyTest.test_the_repository_denies_edits_to_its_controls` | Its `REPO_DENIES` list drops the three denies on removed files | The files are gone |
| T9b | 9 | `test_gates_hold.py`: `DenyTest.test_the_workspace_denies_edits_to_its_controls` | Drops the `story_status.py` deny (the `.claude/**` one stays) | The file is gone |
| T9h | 9 | `test_recording.py`: `FinalReviewRecordTest.test_no_record_is_marked_by_hand` | Drops `story_status.py` from the files it reads | The file is gone |

Count by file: `test_recording.py` 9, `test_multirepo.py` 6, `test_gates_hold.py` 6, `test_routes.py` 2,
`test_fast_path.py` 1, `test_greenfield.py` 1, `test_docs.py` 1, `test_one_plugin.py` 1 — 27.

### D. Structural edits, no assertion — 3 (Task 9)

- `scripts/test_multirepo.py`: drop `import sys`, the `sys.path` line and `from test_gates_hold import pinned_uses,
  run_blocks`, which only the deleted workflow tests used (item T9e).
- `scripts/test_multirepo.py`: drop the helper `job_text`, used only by the deleted workflow tests (item T9e).
- `scripts/test_recording.py`: drop `import sys`, `import tempfile`, the `sys.path` line and `import run_slices`;
  without it the whole module fails to load once `run_slices.py` is gone (item T9g).

### E. Other decisions

- **V1. The version: 6.0.0.** `scripts/test_one_plugin.py:100` pins `"5.0.0"`. Recommended: raise it to 6.0.0 in Task 8
  (item T8c), because the gates and the starters change. Without approval, skip Task 8's version edit and T8c.
- **E1. The eval fixtures.** `evals/fixtures/workspace/WORKSPACE.md` (lines 24 and 26) and
  `evals/fixtures/workspace/stories/README.md` (line 15) still name `story_status.py`; a behaviour eval run in that
  workspace would show an agent a command that no longer exists. No `scripts/test_*.py` assertion pins them. This
  plan leaves `evals/` unchanged, as Plan 21 did, because an eval's setup is part of a gate decision. Options: (a)
  leave them until the evals next run (this plan); (b) copy the new workspace guide text (Task 4) into the two
  fixture files in Task 8.
- **E2. "Change request".** The design suggests "change request" for a pull or merge request. This plan keeps "pull
  request" and defines it once (see "Decisions this plan makes"). Options: (a) this ruling; (b) rename route C and
  then adopt "change request".
- **E3. The example settings keep the denies on `.claude/**` and `CODEOWNERS`.** The audit suggested removing every
  Edit deny. This plan removes only those that protected removed files (see "Decisions this plan makes").

## Where the audit checklist was wrong or incomplete

Each line of `.superpowers/sdd/plan-22-inputs/inventory-checklist.md` was checked against the files at `d39f6bb`.

- **Test counts.** The six script test files hold 353 tests, not 375 (`test_check_slice.py` has 151; a text search
  finds 164 `def test_` strings because some sit inside fixture code). The wording tests are 46 deleted and 27 changed
  in kept files, not about 57: `test_one_plugin.py` has 2 (not 5), `test_fast_path.py` 3 (not 4), `test_validate.py`
  none (its starter tests build their own packages, and the quality-bar phrase stays), and `test_recording.py` 11
  (not 3) once the host-neutral wording is counted. `test_recording.py` imports `run_slices` at module level, so all 25
  of its tests fail to load when the script goes, not 3.
- **"Remove the control Edit denies from both settings files."** Only the denies that protect removed files go. The
  denies on `.claude/**` and `CODEOWNERS` protect the settings and the ownership list (item E3).
- **"Keep ci.yml as a two-step example."** The design deletes the whole workflows folder; this plan follows it.
- **Missed by the audit:** `aidlc-review` steps 3 and 4 (CI's AI review "on record"); `aidlc-build` step 7, Produces
  and Gate; `aidlc-design` new-system step 2 ("the required checks"); `building-ci-pipelines` ("branch protection");
  the README's opening portability claim; the codebase map's first paragraph; `AGENTS.md`'s `starter/` line; the three
  quickstarts (`ci.yml`, `scripts/`); `docs/operating-model/adoption.md` (Phases 1 and 4, day 0's branch protection),
  `routes.md` (lines 123 and 233), `workspace-and-repositories.md` (lines 49, 59, 65), `lifecycle.md` (line 23),
  `autonomy-and-maturity.md` (line 24); both starter `CODEOWNERS` comments ("Put this file at .github/CODEOWNERS");
  ADRs 0015, 0016, 0017 and 0021, which also name removed scripts; and the evals' workspace fixture (item E1).
- **"'pull request' … may be defined once as 'change request'."** "Change request" already names route C (item E2).

---

### Task 1: ADR 0024, ADR 0019 superseded, and the dated notes on the ADRs it amends

The decision is recorded before anything changes. ADR 0024 carries the design's rule table, so every later task can point to one place. The ADRs it amends keep their text as history and gain a dated last section, because rewriting a decision record's lines would erase what was decided and why.

**Files:**
- Create: `docs/adr/0024-instructions-first.md`, `scripts/test_instructions_first.py`
- Modify: `docs/adr/0019-gates-enforced-by-code.md` (Status line)
- Modify: `docs/adr/0012-…`, `0015-…`, `0016-…`, `0017-…`, `0020-…`, `0021-…`, `0022-…`, `0023-…` (a line before `## Context`, a last section)
- Add to git: `docs/design/2026-11-20-instructions-first.md` (written in the session, untracked until now; not edited)
- Test: `scripts/test_instructions_first.py` (new); `scripts/test_gates_hold.py` (one approved change)

**Interfaces:**
- Produces: `scripts/test_instructions_first.py` with `ROOT`, `STAGES`, `read(rel)`, `flat(rel)`, `skill(name)`, `section(text, heading)` and `AMENDED`. Every later task appends one class above its `if __name__` line.
- Produces: `docs/adr/0024-instructions-first.md`, which later tasks cite as "ADR 0024".

- [ ] **Step 1: Branch and identity**

```bash
cd /home/psharma/demos/aidlc
git branch --show-current   # must print docs/plan-22-instructions-first
git config user.email       # must print 6386481+prashantsharma18@users.noreply.github.com
git rev-parse --verify checks-v1^{commit}   # must print 7843f18…: the tag that keeps the removed code
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -1   # OK (725 tests)
```

- [ ] **Step 2: Write the failing tests**

Create `scripts/test_instructions_first.py`:

```python
"""Plan 22: aidlc is instructions (ADR 0024). It ships no scripts and no CI workflows; the checks live in the
team's project; a verdict counts only from someone who did not write the change, at a named commit; and the words
need git, not a code host's features."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGES = sorted(p.name for p in (ROOT / "skills").iterdir() if p.name.startswith("aidlc-"))


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def section(text: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed text."""
    return text.split(heading, 1)[1].split(" ## ", 1)[0]


AMENDED = ("0012-mechanical-recipe-commit", "0015-work-routes-and-the-part-model", "0016-greenfield-entry",
           "0017-feature-fast-path-and-build-modes", "0020-approved-documents-merge-first",
           "0021-several-repositories-at-least-tier-2", "0022-one-owner-per-fact-and-pinned-parts",
           "0023-people-decide-the-ai-records")


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    ADR = "docs/adr/0024-instructions-first.md"

    def test_adr_0024_is_proposed_and_supersedes_0019(self):
        text = read(self.ADR)
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("Supersedes: ADR 0019", "It ships no scripts and no CI workflows to teams",
                       "A rule that must hold every time lives in the team's project",
                       "counts only from someone who did not write it", "`plans/<KEY>/review-evidence.md`",
                       "They keep Read, Grep and Glob, and never run a command",
                       "aidlc depends on git and on no code-host feature", "the tag `checks-v1`",
                       "\"Change request\" stays the name of route C"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0024_holds_the_rule_table(self):
        text = read(self.ADR)
        self.assertIn("| Rule | Was enforced by | Now enforced by |", text)
        for rule in ("No deleted test, no changed assertion", "Plan complete before approval",
                     "Recipe commit is mechanical", "Contract version raised; breaking change raises MAJOR",
                     "Consumer copy matches the pinned version", "Secrets never read; push asks first"):
            self.assertIn(rule, text, rule)

    def test_adr_0019_is_superseded(self):
        self.assertIn("Status: Superseded by ADR 0024 (2026-11-20)", read("docs/adr/0019-gates-enforced-by-code.md"))

    def test_each_amended_adr_carries_a_dated_note(self):
        for name in AMENDED:
            text = read(f"docs/adr/{name}.md")
            self.assertIn("Amended by ADR 0024 (2026-11-20): see the last section.", text, name)
            self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"), name)
            self.assertIn("Status: Accepted", text, name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first -v`

Expected: ERROR in `test_adr_0024_is_proposed_and_supersedes_0019` and `test_adr_0024_holds_the_rule_table` (no such file); FAIL in `test_adr_0019_is_superseded` and `test_each_amended_adr_carries_a_dated_note`.

- [ ] **Step 4: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

`AdrTest.test_each_decision_is_recorded_with_a_decider` (owner's item T1): ADR 0019's status becomes "Superseded by ADR 0024"; the decider and the headings are still checked.
In `scripts/test_gates_hold.py` find:

```text
            self.assertRegex(text, r"Status: (Proposed|Accepted)")
            self.assertIn("Decider: Prashant Sharma", text)
            for heading in ("## Context", "## Decision", "## Consequences"):
                self.assertIn(heading, text, name)
```

Replace with:

```text
            self.assertRegex(text, r"Status: (Proposed|Accepted|Superseded by ADR 0024)")
            self.assertIn("Decider: Prashant Sharma", text)
            for heading in ("## Context", "## Decision", "## Consequences"):
                self.assertIn(heading, text, name)
```

- [ ] **Step 5: Write ADR 0024, supersede ADR 0019, and add the dated notes**

Create `docs/adr/0024-instructions-first.md`:

```markdown
# 0024 · Instructions first; checks live in the team's project

Status: Proposed (2026-11-20). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-20-instructions-first.md` · Plan: `docs/plans/2026-11-20-plan-22-instructions-first.md` ·
Supersedes: ADR 0019 · Amends: ADRs 0012, 0015, 0016, 0017, 0020, 0021, 0022, 0023

## Context
ADR 0010 removed the Python harness: it slowed every change, it served mostly one AI tool, and it was hard to adopt.
Plans 20 and 21 brought code back: seven starter scripts, four starter workflows, a Stop hook, and hundreds of tests
of their own. One rule then lived in a skill, a script and two kinds of test, and Plan 21 needed many fix rounds on
the scripts alone. The scripts could block a merge only through GitHub's required checks and branch protection, which
on GitHub Free work only on public repositories. Without them every check, coded or not, is advice.

The leading frameworks (superpowers, Spec Kit, OpenSpec, BMAD-METHOD, pstack) ship no gate code. The vendors put hard
rules in the project's own tests, linters, CI and tool settings. The evidence says agents do cheat around tests, that
self-review is weak, and that an outside reviewer helps. The design records the sources.

## Decision
- aidlc is instructions: skills, agents, templates and `AGENTS.md`. It ships no scripts and no CI workflows to teams.
- A rule that must hold every time lives in the team's project: its tests, linters, type checks, CI, and its AI
  tool's settings. aidlc tells the agent to build and maintain those checks; the team owns them.
- When a mistake repeats, `aidlc-feedback` adds a check to the team's project at the highest level that works, proves
  it fails on the real past mistake, and adds a row to the "Rules and what enforces them" table of the team's
  `AGENTS.md`.
- A verdict that a change is done or passes counts only from someone who did not write it: a reviewer agent in a
  fresh context, or a person. It names the commit it judged; a later commit that changes a path outside
  `plans/<KEY>/` voids it.
- The reviewer agents read an evidence file the session writes with plain git commands,
  `plans/<KEY>/review-evidence.md`. They keep Read, Grep and Glob, and never run a command.
- A person decides at each gate, from evidence that git can confirm, not from claims.
- aidlc depends on git and on no code-host feature. A team that has branch protection or required checks may use
  them; aidlc never needs them. "Pull request" stays the common word for a pull or merge request, defined once in
  `using-aidlc`. "Change request" stays the name of route C, so it never means a pull request.
- A skill may name plain git commands and the standard tools this table names (oasdiff, sha256sum); it never names a
  script of its own.

The checks, rule by rule:

| Rule | Was enforced by | Now enforced by |
|---|---|---|
| No deleted test, no changed assertion (ADR 0019's central concern) | `check_slice.py` in CI | The `reviewer-tests` agent reads the test-file diff from an evidence file the session writes (`git diff <base> -- <test paths>`); the evidence table shows the changed test files and the test count before and after; the code owner reads both. The team may add its own CI check. |
| Edit only inside MAY CHANGE; MUST NOT untouched | `check_slice.py` | The `reviewer-compliance` agent compares `git diff --name-only <base>` (in the evidence file) with the bundle |
| No new suppression or skip without an exception | `check_slice.py` (12 syntaxes) | The team's linters' own rules (`skills/aidlc-onboard/references/suppression-rules.md`), plus the reviewer reading added `aidlc-exception` lines |
| No new dependency without asking | `check_slice.py` | The reviewer reads manifest changes in the evidence file; the person approves |
| Approved documents unchanged in a code change (ADR 0020) | `check_slice.py` | The reviewer reads `git diff <base> -- plans/<KEY>`; the code owner approves |
| Plan complete before approval | `check_plan.py` | The plan template's checklist; the tech lead approves |
| Recipe commit is mechanical (ADR 0012) | `check_recipe_commit.py` | The bundle's DONE WHEN: re-run the recipe on the parent commit and `git diff` against the commit; the reviewer reads the result |
| Run approved slices one by one | `run_slices.py` | The person starts one fresh session per slice; `aidlc-build` states the stops |
| Story status across repositories, drift, merge state | `story_status.py` | A release checklist row per repository, filled from git by the agent and confirmed by the person |
| Contract version raised; breaking change raises MAJOR | `check_contract_version.py` + workflows | The provider team runs `oasdiff breaking` and a version comparison in its own CI; `designing-apis` gives the commands |
| Consumer copy matches the pinned version | `check_contract_pin.py` | `sha256sum -c` and `git ls-remote --tags` in the consumer's release checklist |
| Independent AI review of a change request | `ai-review.yml` (GitHub, Claude-only) | The `reviewer-*` agents run in a fresh session; the team may add any AI review its host offers |
| Secrets never read; push asks first | starter `.claude/settings.json` | Kept as an optional example settings file a team copies; not a gate of aidlc |

## Consequences
- Removed: `starter/repo/scripts/`, `starter/workspace/scripts/`, `starter/repo/.github/workflows/`, the Stop hook,
  the deny rules that protected them, and their tests. The code stays recoverable under the tag `checks-v1`
  (`docs/archive/checks-v1.md`).
- The starter's `.claude/settings.json` stays as an optional example: the secret-read denies, the sandbox, "ask before
  push or install", and the denies on `.claude/**` and `CODEOWNERS`, so a session cannot loosen its own settings.
- A deleted test or a weakened assertion is now caught by a reviewer agent and a person, not by code. A reviewer
  agent can be lenient. A team that wants a hard block adds one to its own CI.
- A story across several repositories relies on a release checklist again: one row per repository, filled from git
  by the agent and confirmed by a person.
- aidlc's own validator and its own CI stay: they check aidlc, not a team's project.
- ADRs 0012, 0015, 0016, 0017, 0020, 0021, 0022 and 0023 keep their decisions; each carries a dated note saying which
  of its enforcement lines no longer hold. ADR 0019 is superseded.
```

In `docs/adr/0019-gates-enforced-by-code.md` find:

```text
Status: Proposed (2026-11-19). · Decider: Prashant Sharma (framework owner)
```

Replace with:

```text
Status: Superseded by ADR 0024 (2026-11-20): aidlc ships no check code; each rule is held by the team's own
project and by a reviewer who did not write the change. (Was: Proposed (2026-11-19). · Decider: Prashant Sharma
(framework owner))
```

In each amended ADR, add one line just above its blank line and `## Context` heading. The find text is a blank line and the heading; the replacement puts the new line before them.
In each of these files: `docs/adr/0012-mechanical-recipe-commit.md`, `docs/adr/0015-work-routes-and-the-part-model.md`, `docs/adr/0016-greenfield-entry.md`, `docs/adr/0017-feature-fast-path-and-build-modes.md`, `docs/adr/0020-approved-documents-merge-first.md`, `docs/adr/0021-several-repositories-at-least-tier-2.md`, `docs/adr/0022-one-owner-per-fact-and-pinned-parts.md`, `docs/adr/0023-people-decide-the-ai-records.md`, find (it starts with a line break; keep it exact):

```text


## Context
```

Replace with:

```text

Amended by ADR 0024 (2026-11-20): see the last section.

## Context
```

Append at the end of `docs/adr/0012-mechanical-recipe-commit.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `scripts/check_recipe_commit.py` is removed. The same check runs with git (`aidlc-build`, step 5): in a
  temporary worktree at the commit's parent, run the approved recipe, stage everything, and
  `git diff --cached --stat <commit>` must print nothing; the test count is the same at the parent and at the commit.
  The session writes the result to the evidence file, and the compliance reviewer reads it.
```

Append at the end of `docs/adr/0015-work-routes-and-the-part-model.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `story_status.py` is removed. The AI at the workspace root derives `status.md` from each part's index on its
  repository's default branch, read with git. At release, `aidlc-release` fills one checklist row per repository,
  and a person confirms each row.
- `scripts/test_story_status.py` is removed with the script.
```

Append at the end of `docs/adr/0016-greenfield-entry.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- The recipe check is now a git procedure in `aidlc-build`, not a script. A `(scaffold)` recipe is still reviewed
  as generated code and is not re-run.
```

Append at the end of `docs/adr/0017-feature-fast-path-and-build-modes.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `run_slices.py` is removed. A person starts one fresh session per approved delegate slice, and reads each
  progress note before starting the next; `aidlc-build` states the stops.
```

Append at the end of `docs/adr/0020-approved-documents-merge-first.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `run_slices.py` and `check_slice.py` are removed. `aidlc-build` still compares the bundle with the default
  branch's copy before any edit. The compliance reviewer reads `git diff <base> -- plans/<KEY>/` in the evidence
  file and reports a plan, bundle, brief or criteria copy added or changed in a code pull request; the code owner
  approves.
```

Append at the end of `docs/adr/0021-several-repositories-at-least-tier-2.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `check_plan.py` is removed. The plan's checklist holds the rule (a part of a story across several repositories
  is at least Tier 2), and the tech lead checks it with the plan.
```

Append at the end of `docs/adr/0022-one-owner-per-fact-and-pinned-parts.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- `story_status.py`, `check_contract_version.py`, `check_contract_pin.py` and the starter workflows
  `contract-check.yml` and `contract-publish.yml` are removed.
- A part's merge state and drift are read with git from its index and criteria copy on its default branch, and
  recorded in the release checklist, one row per repository, which a person confirms.
- The provider's own CI runs `oasdiff breaking` and a version comparison against the last published tag; the
  consumer checks its copy with `sha256sum -c` and the tag with `git ls-remote --tags`. `designing-apis` gives the
  commands.
- A person adds each repository's line to the home repository's `.gitignore`; there is no generator.
- Tracker links are permalinks at a commit on any code host. A tag rule or ruleset on `api-v*` is optional: aidlc
  needs no code-host feature.
```

Append at the end of `docs/adr/0023-people-decide-the-ai-records.md` (after its last line, separated by one blank line):

```markdown
## Amended by ADR 0024 (2026-11-20)
- The states the AI can check are named without a code host: a pull request approved in the review tool by a code
  owner who is not its author, the team's CI result on it, and the merge state. The example record reads
  `approved by ana on pull request 12, checked in the review tool, 2026-11-20`.
```

Each amended ADR gets two changes: the line `Amended by ADR 0024 (2026-11-20): see the last section.` just above its `## Context` heading (the find/replace pairs above), and the last section shown for it. Leave the rest of each ADR as it is.

- [ ] **Step 6: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 729 tests, OK.

- [ ] **Step 7: Commit**

```bash
git add docs/design/2026-11-20-instructions-first.md docs/adr/0024-instructions-first.md docs/adr/0019-gates-enforced-by-code.md docs/adr/0012-mechanical-recipe-commit.md docs/adr/0015-work-routes-and-the-part-model.md docs/adr/0016-greenfield-entry.md docs/adr/0017-feature-fast-path-and-build-modes.md docs/adr/0020-approved-documents-merge-first.md docs/adr/0021-several-repositories-at-least-tier-2.md docs/adr/0022-one-owner-per-fact-and-pinned-parts.md docs/adr/0023-people-decide-the-ai-records.md scripts/test_instructions_first.py scripts/test_gates_hold.py
git commit -m "docs(adr): 0024 instructions first, checks live in the team's project (proposed); 0019 superseded; dated notes on the ADRs it amends" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 2: The evidence file and the non-author verdict

The slice check used to read the branch's diff in CI. Now the session writes that evidence with plain git into one committed file, and reviewer agents that did not write the change read it in a fresh context. They keep Read, Glob and Grep: they never run a command, so the evidence must already hold every output they judge. A verdict names the commit it judged, so a later code change visibly voids it (design: "The principle", fourth bullet; table rows 1, 2, 3, 4, 5 and 7).

**Files:**
- Create: `skills/aidlc-build/assets/review-evidence.md`, `skills/aidlc-review/assets/review-evidence.md` (identical)
- Modify: `skills/aidlc-build/SKILL.md` (templates, steps 1, 4, 9, Produces, Gate, Rules), `skills/aidlc-build/assets/progress-note.md` (TESTS BEFORE)
- Modify: `skills/aidlc-review/SKILL.md` (templates, steps 3, 4, 7, Produces, Stop if, Rules), `skills/aidlc-review/assets/review-record.md`
- Modify: `skills/aidlc-verify/SKILL.md` (step 4, Rules), `skills/aidlc-verify/assets/evidence-table.md`
- Modify: `agents/reviewer-compliance.md`, `agents/reviewer-tests.md`, `agents/reviewer-bug.md`, `agents/reviewer-security.md`
- Modify: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md` (two Where to look lines)
- Test: `scripts/test_instructions_first.py` (new class `EvidenceAndVerdictTest`); `scripts/test_gates_hold.py` (two approved deletions)

**Interfaces:**
- Consumes: `read`, `flat`, `skill`, `section` from Task 1.
- Produces: the module constants `VERDICT` (the verdict Rules bullet, word for word) and `REVIEWERS` in `scripts/test_instructions_first.py`.
- Produces: the file name `plans/<KEY>/review-evidence.md` and its section headings, which Tasks 3, 4 and 5 cite ("the evidence file", "Recipe commits").

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
VERDICT = ("- A verdict that the change is done or passes counts only from someone who did not write it: a reviewer "
           "agent in a fresh context, or a person. It names the commit it judged (`git rev-parse HEAD`). A later "
           "commit that changes any path outside `plans/<KEY>/` voids it: `git diff --name-only <judged commit> HEAD "
           "-- . ':(exclude)plans/<KEY>/'` must print nothing.")
REVIEWERS = ("reviewer-bug", "reviewer-security", "reviewer-compliance", "reviewer-tests")
EVIDENCE = "skills/aidlc-review/assets/review-evidence.md"


class EvidenceAndVerdictTest(unittest.TestCase):
    """Task 2: the session writes the evidence with git; reviewers who did not write the change read it, never run a
    command, and judge a named commit."""

    def test_the_template_says_what_the_session_writes_and_where(self):
        self.assertEqual(read(EVIDENCE), read("skills/aidlc-build/assets/review-evidence.md"))
        text = flat(EVIDENCE)
        for command in ("git rev-parse HEAD", "git merge-base HEAD origin/<default branch>", "git diff --stat <base>",
                        "git diff --name-only <base>", "git diff <base> -- <test paths>",
                        "git diff <base> -- <manifests>", "git diff <base> -- plans/<KEY>/",
                        "git worktree add <folder> <base>", "echo $?", "git -C <folder> diff --cached --stat <commit>"):
            self.assertIn(command, text, command)
        self.assertIn("to `plans/<KEY>/review-evidence.md`", text)
        self.assertIn("The reviewer agents read this file and never run a command.", text)

    def test_each_section_names_its_reader(self):
        text = read(EVIDENCE)
        for heading in ("## Changed files (reviewer-compliance)", "## Test files (reviewer-tests, reviewer-compliance)",
                        "## Test count (reviewer-tests)", "## Commands run at HEAD (reviewer-tests)",
                        "## Dependency manifests (reviewer-compliance)", "## Story documents (reviewer-compliance)",
                        "## Added suppressions, skips and exceptions (reviewer-compliance)",
                        "## Recipe commits (reviewer-compliance)"):
            self.assertIn(heading, text, heading)
        for rel in ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            where = read(rel).split("## Where to look", 1)[1]
            self.assertIn("- Test paths, for the review evidence:", where, rel)
            self.assertIn("- Dependency manifests, for the review evidence:", where, rel)

    def test_build_and_review_write_and_commit_it(self):
        for name in ("aidlc-build", "aidlc-review"):
            self.assertIn("  - review-evidence\n", read(f"skills/{name}/SKILL.md"), name)
            self.assertIn("write the evidence file `plans/<KEY>/review-evidence.md` from `assets/review-evidence.md` "
                          "and commit it on its own", skill(name), name)
            self.assertIn("each in a fresh context", skill(name), name)
        self.assertNotIn("slice check", skill("aidlc-build"))
        self.assertIn("TESTS BEFORE", read("skills/aidlc-build/assets/progress-note.md"))

    def test_the_reviewers_read_it_and_never_run_a_command(self):
        for name in ("reviewer-compliance", "reviewer-tests"):
            text = flat(f"agents/{name}.md")
            self.assertIn("`plans/<KEY>/review-evidence.md`", text, name)
            self.assertIn("You never run a command: you judge the outputs it holds.", text, name)
            self.assertIn("or a file written for another commit, is a high finding", text, name)
        self.assertNotIn("slice check", flat("agents/reviewer-compliance.md"))
        for name in REVIEWERS:
            front = read(f"agents/{name}.md").split("\n---", 1)[0]
            self.assertIn("\ntools: Read, Glob, Grep\n", front, name)
            self.assertIn("Start your Return with `Judged: <commit>`, the commit your brief names.",
                          flat(f"agents/{name}.md"), name)

    def test_a_verdict_comes_from_a_non_author_and_names_its_commit(self):
        for name in ("aidlc-build", "aidlc-verify", "aidlc-review"):
            self.assertIn(VERDICT, section(skill(name), "## Rules"), name)
        self.assertIn("Your STATUS `done` means your steps are finished, not that the change passes.",
                      section(skill("aidlc-build"), "## Gate"))

    def test_a_stale_verdict_is_void(self):
        stops = section(skill("aidlc-review"), "## Stop if")
        self.assertIn("A reviewer verdict names a commit other than the pull request's head", stops)
        self.assertIn("the verdict is void", stops)
        record = read("skills/aidlc-review/assets/review-record.md")
        self.assertIn("at {{commit}}", record.split("## Reviewer verdicts", 1)[1])
        self.assertRegex(record, r"DECISION  \{\{approve [^}]*\}\} at \{\{commit\}\}")

    def test_verify_reads_the_evidence_and_gives_no_verdict(self):
        self.assertIn("from the evidence file `plans/<KEY>/review-evidence.md` when its HEAD is the commit the trusted "
                      "run tested", skill("aidlc-verify"))
        table = read("skills/aidlc-verify/assets/evidence-table.md")
        self.assertIn("This is evidence, not a verdict", " ".join(table.split()))
        for row in ("test files changed:", "test count:"):
            self.assertIn(row, table, row)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.EvidenceAndVerdictTest -v`

Expected: ERROR in the two template tests (no such file) and FAIL in the other five.

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

In `scripts/test_gates_hold.py`, delete these test methods (each from its `def` line through its last line): `WiringTest.test_build_and_compliance_use_it`, `FinalReviewFixesTest.test_compliance_reads_the_check_wherever_it_is_given`. Why: they pin the slice check in `aidlc-build` and `reviewer-compliance`, which now read the evidence file (owner's items T2a, T2b).

- [ ] **Step 4: Write the template, then change the skills and agents**

Create `skills/aidlc-build/assets/review-evidence.md`:

````markdown
<!-- aidlc template: review-evidence -->
# {{KEY}} · {{PART}} · review evidence at {{short commit}}

The session writes this file from git before each review pass, to `plans/<KEY>/review-evidence.md`
(`plans/<KEY>/part-<n>/review-evidence.md` for a second part in the same repository), and commits it on its own. Each
section holds a command's output exactly as it printed. The reviewer agents read this file and never run a command.
The code owner can run any command again and compare. When an output holds three backticks, fence it with four.

```text
HEAD       {{git rev-parse HEAD: the commit the reviewers judge}}
BASE       {{git merge-base HEAD origin/<default branch>}}
BRANCH     {{git branch --show-current}}
WRITTEN    {{YYYY-MM-DD}}, by {{the build session | the review session}}
```

## Changed files (reviewer-compliance)
`git diff --stat <base>`, then `git diff --name-only <base>`. The compliance reviewer compares the list with the
bundle's MAY CHANGE and MUST NOT; `plans/<KEY>/**` is exempt.

```text
{{output}}
```

## Test files (reviewer-tests, reviewer-compliance)
`git diff <base> -- <test paths>`, with the test paths `AGENTS.md` names under Where to look. A deleted test, a
removed or changed assertion, or a new skip shows here.

```text
{{output}}
```

## Test count (reviewer-tests)
The repository's test command from `AGENTS.md`, at BASE and at HEAD. For BASE, use the TESTS BEFORE line of the first
slice's progress note when it names BASE; otherwise run the command in a temporary worktree:
`git worktree add <folder> <base>`, the command there, then `git worktree remove --force <folder>`.

```text
BASE       {{passed}} passed, {{failed}} failed, {{skipped}} skipped
HEAD       {{passed}} passed, {{failed}} failed, {{skipped}} skipped
```

## Commands run at HEAD (reviewer-tests)
Each check command `AGENTS.md` names (tests, lint, type checks, build), run at HEAD, each followed by `echo $?`.

```text
{{command}}    exit {{code}}
```

## Dependency manifests (reviewer-compliance)
`git diff <base> -- <manifests>`, with the manifest and lock files `AGENTS.md` names under Where to look. An added
dependency needs a person's approval.

```text
{{output, or "no change"}}
```

## Story documents (reviewer-compliance)
`git diff <base> -- plans/<KEY>/`. At Tier 2 and 3, a plan, bundle, brief or criteria copy added or changed in a code
pull request is a finding: those merge first, in their own pull request (ADR 0020).

```text
{{output}}
```

## Added suppressions, skips and exceptions (reviewer-compliance)
`git diff -U0 <base> -- . ':(exclude)plans/<KEY>/'`, keeping only the added lines (they start with `+`) that hold one
of these markers, or another marker the repository's stacks use, and the removed lines (they start with `-`) that
close one (`eslint-enable`, `pylint: enable`, `#pragma warning restore`, `c8 ignore stop`):

```text
noqa  type: ignore  pylint: disable  eslint-disable  @ts-ignore  @ts-expect-error  @ts-nocheck  nolint
#pragma warning disable  SuppressMessage  c8 ignore  istanbul ignore  .skip(  .only(  xfail  @unittest.skip
@pytest.mark.skip  [Ignore  Skip =  t.Skip(  @Disabled  aidlc-exception
```

```text
{{each added line with its file, or "none"}}
```

## Recipe commits (reviewer-compliance)
For each commit with a `Recipe:` trailer (`git log --format=%H --grep='^Recipe:' <base>..HEAD`), except one marked
`(scaffold)`: `git worktree add <folder> <commit>^`; run the bundle's RECIPE there; `git -C <folder> add -A`; then
`git -C <folder> diff --cached --stat <commit>`, which prints nothing when the commit holds exactly the tool's
output. Run the test command at `<commit>^` and at `<commit>`: the counts must match. Then
`git worktree remove --force <folder>`.

```text
{{commit, tool@version: the re-run matches, or the files that differ; tests before and after}}, or none
```
````

Create `skills/aidlc-review/assets/review-evidence.md` as an identical copy of `skills/aidlc-build/assets/review-evidence.md`: `cp skills/aidlc-build/assets/review-evidence.md skills/aidlc-review/assets/review-evidence.md`.

In `skills/aidlc-build/SKILL.md` find:

```text
  templates:
  - progress-note
```

Replace with:

```text
  templates:
  - progress-note
  - review-evidence
```

In `skills/aidlc-build/SKILL.md` find:

```text
If it is red or skips tests, stop: the environment is fixed first.
```

Replace with:

```text
If it is red or skips tests, stop: the environment is fixed first. Keep the counts and the commit (`git rev-parse HEAD`) for the progress note's TESTS BEFORE line.
```

In `skills/aidlc-build/SKILL.md` find:

```text
with STATUS `doing` and the bundle's MODE, and commit the note on its own
```

Replace with:

```text
with STATUS `doing`, the bundle's MODE and TESTS BEFORE, and commit the note on its own
```

In `skills/aidlc-build/SKILL.md` find (it starts with a space; keep it exact):

```text
 Run the slice check named in AGENTS.md: it checks MAY CHANGE, MUST NOT, removed tests and assertions, dependency manifests, suppressions and approved documents by code, and CI runs it again on the pull request. Each problem it reports is a stop, or a new step that fixes it.
```

and delete it.


In `skills/aidlc-build/SKILL.md` find:

```text
Fix any finding as a new step, then repeat steps 8 and 9.
```

Replace with:

```text
Fix any finding as a new step, then repeat steps 8 and 9. When your own review is clean, write the evidence file `plans/<KEY>/review-evidence.md` from `assets/review-evidence.md` and commit it on its own. Send it, with the bundle and the commit it names, to the `reviewer-compliance` and `reviewer-tests` agents, each in a fresh context. Each finding they report is a stop, or a new step that fixes it, then steps 8 and 9 again.
```

In `skills/aidlc-build/SKILL.md` find:

```text
committed on its own first, then with the slice. This is local evidence only: the pull request's CI decides.
```

Replace with:

```text
committed on its own first, then with the slice, and the evidence file `plans/<KEY>/review-evidence.md`. This is local evidence only: the team's CI on the pull request and the reviewers who did not write the change decide.
```

In `skills/aidlc-build/SKILL.md` find:

```text
and the person reviews the diff before pushing. You draft; you never approve.
```

Replace with:

```text
the reviewer agents' passes on the evidence file are clean at the commit they name, and the person reviews the diff before pushing. Your STATUS `done` means your steps are finished, not that the change passes. You draft; you never approve.
```

In `skills/aidlc-build/SKILL.md` find:

```text
- Prefer a fresh session per slice. The bundle, the progress note and the commits are the state, never the chat.
```

Replace with:

```text
- Prefer a fresh session per slice. The bundle, the progress note and the commits are the state, never the chat.
- A verdict that the change is done or passes counts only from someone who did not write it: a reviewer agent in a fresh context, or a person. It names the commit it judged (`git rev-parse HEAD`). A later commit that changes any path outside `plans/<KEY>/` voids it: `git diff --name-only <judged commit> HEAD -- . ':(exclude)plans/<KEY>/'` must print nothing.
```

In `skills/aidlc-build/assets/progress-note.md` find:

````text
MODE        {{the bundle's MODE; hands-on when the bundle has none}}
```
````

Replace with:

````text
MODE        {{the bundle's MODE; hands-on when the bundle has none}}
TESTS BEFORE {{passed}} passed, {{failed}} failed, {{skipped}} skipped at {{commit}}, before any change
```
````

In `skills/aidlc-review/SKILL.md` find:

```text
  - pr-description
  - review-record
  - security-review
```

Replace with:

```text
  - pr-description
  - review-record
  - security-review
  - review-evidence
```

In `skills/aidlc-review/SKILL.md` find:

```text
3. Load the `reviewing-code` skill, then send the change to the `reviewer-bug`, `reviewer-security`, `reviewer-compliance` and `reviewer-tests` agents, one pass each, so the review does not run in the session that wrote the code. They use the rules from the protected branch, never the pull request's own copy. These local passes are advisory; CI's AI review, with its own identity, is the one on record.
```

Replace with:

```text
3. Load the `reviewing-code` skill. Then write the evidence file `plans/<KEY>/review-evidence.md` from `assets/review-evidence.md` and commit it on its own, at the pull request's head. Send the change to the `reviewer-bug`, `reviewer-security`, `reviewer-compliance` and `reviewer-tests` agents, one pass each, each in a fresh context, so the review does not run in the session that wrote the code. Give each the evidence file, the diff, the commit the evidence file names, and the rules as they are on the default branch (`git show origin/<default branch>:AGENTS.md`), never the pull request's own copy. Their passes are the AI review on record; the team may add any AI review its code host offers.
```

In `skills/aidlc-review/SKILL.md` find:

```text
4. Draft a disposition for every finding, yours and CI's AI review:
```

Replace with:

```text
4. Draft a disposition for every finding: yours, the reviewer agents', and any AI review the team's code host runs:
```

In `skills/aidlc-review/SKILL.md` find:

```text
7. Draft the review record from `assets/review-record.md`, with no approval part for you.
```

Replace with:

```text
7. Draft the review record from `assets/review-record.md`, with no approval part for you. Write each reviewer agent's verdict under Reviewer verdicts, with the commit it judged.
```

In `skills/aidlc-review/SKILL.md` find:

```text
In `plans/<KEY>/`, on the part's branch: `pr-description.md`, `review-record.md` (the dispositions and the reviewers'
questions)
```

Replace with:

```text
In `plans/<KEY>/`, on the part's branch: `review-evidence.md`, `pr-description.md`, `review-record.md` (the
dispositions, the reviewers' verdicts and questions)
```

In `skills/aidlc-review/SKILL.md` find:

```text
- A required check is red or missing.
```

Replace with:

```text
- A required check is red or missing.
- A reviewer verdict names a commit other than the pull request's head, or a later commit changed a path outside `plans/<KEY>/` (`git diff --name-only <judged commit> HEAD -- . ':(exclude)plans/<KEY>/'` prints a path): the verdict is void. Write the evidence file again and repeat the pass.
```

In `skills/aidlc-review/SKILL.md` find:

```text
- The reviewer reads the tests first: point there before the diff.
```

Replace with:

```text
- The reviewer reads the tests first: point there before the diff.
- A verdict that the change is done or passes counts only from someone who did not write it: a reviewer agent in a fresh context, or a person. It names the commit it judged (`git rev-parse HEAD`). A later commit that changes any path outside `plans/<KEY>/` voids it: `git diff --name-only <judged commit> HEAD -- . ':(exclude)plans/<KEY>/'` must print nothing.
```

In `skills/aidlc-review/assets/review-record.md` find:

```text
DECISION  {{approve | revise (back to build) | reject (back to plan or spec owner)}}  {{date}}
```

Replace with:

```text
DECISION  {{approve | revise (back to build) | reject (back to plan or spec owner)}} at {{commit}}  {{date}}
```

In `skills/aidlc-verify/SKILL.md` find:

```text
4. Fill the integrity rows (scope, protected tests, skips), the scans, and the AI review findings,
```

Replace with:

```text
4. Fill the integrity rows (scope, the changed test files, the test count at the base and at the run's commit, protected tests, skips) from the evidence file `plans/<KEY>/review-evidence.md` when its HEAD is the commit the trusted run tested; otherwise run the git commands it lists yourself and write their outputs. Then fill the scans, and the AI review findings,
```

In `skills/aidlc-verify/SKILL.md` find:

```text
- "All tests pass" is not a result: give the counts.
```

Replace with:

```text
- "All tests pass" is not a result: give the counts.
- A verdict that the change is done or passes counts only from someone who did not write it: a reviewer agent in a fresh context, or a person. It names the commit it judged (`git rev-parse HEAD`). A later commit that changes any path outside `plans/<KEY>/` voids it: `git diff --name-only <judged commit> HEAD -- . ':(exclude)plans/<KEY>/'` must print nothing.
```

In `skills/aidlc-verify/assets/evidence-table.md` find:

```text
**Verdict:** {{every criterion proved in the trusted run, or the number unproved, listed under Unproved}}
```

Replace with:

```text
**Summary of the trusted run at {{commit}}:** {{every criterion proved, or the number unproved, listed under
Unproved}}. This is evidence, not a verdict: the verdict comes from the reviewers who did not write the change,
in the review record.
```

In `skills/aidlc-verify/assets/evidence-table.md` find:

```text
                                                            LOCAL  TRUSTED CI
INTEGRITY  scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)      <ok>   <ok (trusted copy)>
           protected tests: no existing line changed       -      <ok>
           skips: tests that did not run                   <n>    <0>
SCANS      dependency, secrets, SAST                        -      <clean>
```

Replace with:

```text
                                                            FROM GIT       JUDGED BY
INTEGRITY  scope: every changed path inside MAY CHANGE (plans/<KEY>/** exempt)      <ok or the paths>   <reviewer-compliance at commit>
           test files changed: <each path, or none>          <list>         <reviewer-tests at commit>
           test count: <n> at BASE, <n> at HEAD              <n -> n>       <reviewer-tests at commit>
           protected tests: no existing assertion changed    -              <reviewer-tests at commit>
           skips: tests that did not run                     <n>            <0 in CI>
SCANS      dependency, secrets, SAST                         -              <clean in CI>
```

In `agents/reviewer-compliance.md` find:

```text
- When the slice check's output is given to you (CI or the session's Stop hook), read it first: it covers scope,
  MUST NOT, removed tests, manifests, suppressions and approved documents by code. Judge what it cannot: PINS, Skills
  loaded, MODE, recipe and scaffold commits, and the rules in `AGENTS.md`.
```

Replace with:

```text
- Read the evidence file the session wrote, `plans/<KEY>/review-evidence.md`, first. You never run a command: you
  judge the outputs it holds. Its HEAD must be the commit your brief names; a missing section, or a file written
  for another commit, is a high finding, and you ask for it to be written again. From it, judge: Changed files
  against MAY CHANGE and MUST NOT; Dependency manifests (no new dependency); Story documents (at Tier 2 and 3, no
  plan, bundle, brief or criteria copy added or changed in a code pull request, ADR 0020); Added suppressions,
  skips and exceptions; and Recipe commits.
```

In `agents/reviewer-tests.md` find:

```text
## Work
- For each criterion
```

Replace with:

```text
## Work
- Read the Test files, Test count and Commands run at HEAD sections of `plans/<KEY>/review-evidence.md`
  first. You never run a command: you judge the outputs it holds. A missing section, or a file written for another
  commit, is a high finding. So is a deleted test; a test count at HEAD lower than at BASE without an AMENDED
  ASSERTIONS line or an approved exception; a removed or changed assertion line outside AMENDED ASSERTIONS; and a
  check command that did not exit 0.
- For each criterion
```

In `skills/aidlc-onboard/assets/agents-md.md` find:

```text
- Owners: {{CODEOWNERS path}}
```

Replace with:

```text
- Owners: {{CODEOWNERS path}}
- Test paths, for the review evidence: {{test folders and file patterns, for example `tests/` and `*_test.go`}}
- Dependency manifests, for the review evidence: {{manifest and lock files, for example `package.json` and
  `package-lock.json`}}
```

In `starter/repo/AGENTS.md` find:

```text
- Owners: <CODEOWNERS path>
```

Replace with:

```text
- Owners: <CODEOWNERS path>
- Test paths, for the review evidence: <test folders and file patterns>
- Dependency manifests, for the review evidence: <manifest and lock files>
```

In each of these files: `agents/reviewer-bug.md`, `agents/reviewer-security.md`, `agents/reviewer-compliance.md`, `agents/reviewer-tests.md`, find:

```text
## Return
The findings, or
```

Replace with:

```text
## Return
Start your Return with `Judged: <commit>`, the commit your brief names. Then the findings, or
```

Append at the end of `skills/aidlc-review/assets/review-record.md` (after its last line, separated by one blank line):

```markdown
## Reviewer verdicts
Each verdict counts only from a reviewer agent in a fresh context, or a person who did not write the change, at the
commit it names. A later commit that changes a path outside `plans/<KEY>/` voids it.
- {{reviewer-bug | reviewer-security | reviewer-compliance | reviewer-tests | person}}: {{no findings | the number of findings}} at {{commit}}
```

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.EvidenceAndVerdictTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 734 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add skills/aidlc-build skills/aidlc-review skills/aidlc-verify agents skills/aidlc-onboard/assets/agents-md.md starter/repo/AGENTS.md scripts/test_instructions_first.py scripts/test_gates_hold.py
git commit -m "feat(skills): the session writes the review evidence with git; a verdict comes from a reviewer who did not write the change, at a named commit" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 3: The build and the plan: the recipe check with git, a person starts each slice, the plan check as a checklist

`check_recipe_commit.py`, `run_slices.py` and `check_plan.py` go. Each rule stays, held by something the team already has: git for the recipe re-run (design table, row 7), a person starting one fresh session per slice (row 8), and the plan's checklist, which the tech lead reads with the plan (row 6). Slice 0 stops naming the starter's workflow and scripts.

**Files:**
- Modify: `skills/aidlc-build/SKILL.md` (When to use, step 5), `skills/aidlc-build/assets/progress-note.md` (line 6)
- Modify: `skills/aidlc-plan/SKILL.md` (steps 6 and 8, slice 0 steps 2 and 3, Gate), `skills/aidlc-plan/assets/plan.md` (the checklist)
- Modify: `agents/reviewer-compliance.md` (the recipe lines), `skills/aidlc-review/assets/pr-description.md` (Recipe line)
- Test: `scripts/test_instructions_first.py` (new class `BuildAndPlanTest`); approved changes in `scripts/test_fast_path.py`, `scripts/test_gates_hold.py`, `scripts/test_greenfield.py`

**Interfaces:**
- Consumes: the evidence file's "Recipe commits" section (Task 2).
- Produces: the phrase "the recipe check" now names the git procedure in `aidlc-build` step 5; ADR 0012's note (Task 1) and `reviewer-compliance` use it in that sense.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class BuildAndPlanTest(unittest.TestCase):
    """Task 3: the build and the plan name no script. The recipe check is a git procedure, a person starts each
    delegate slice, and the plan check is the plan's checklist."""

    def test_the_recipe_check_is_done_with_git(self):
        build = skill("aidlc-build")
        for phrase in ("`git worktree add <folder> <commit>^`", "`git -C <folder> add -A`",
                       "`git -C <folder> diff --cached --stat <commit>` must print nothing",
                       "the test count must be the same at the parent and at the commit"):
            self.assertIn(phrase, build, phrase)
        self.assertNotIn("check_recipe_commit", build)
        self.assertIn("the evidence file's Recipe commits section shows the re-run", flat("agents/reviewer-compliance.md"))
        self.assertNotIn("recipe check output", read("skills/aidlc-review/assets/pr-description.md"))

    def test_a_person_starts_each_delegate_slice(self):
        build = skill("aidlc-build")
        self.assertNotIn("slice runner", build)
        self.assertIn("one fresh session per slice, each started by the person", build)
        self.assertNotIn("slice runner", read("skills/aidlc-build/assets/progress-note.md"))

    def test_the_plan_check_is_a_checklist(self):
        plan = skill("aidlc-plan")
        self.assertNotIn("plan check", plan)
        self.assertIn("go through the plan's checklist (`assets/plan.md`) item by item, against the files", plan)
        checklist = flat("skills/aidlc-plan/assets/plan.md")
        for item in ('every bundle field filled, or "none"', "each MODE allowed at its TIER",
                     "a part of a story across several repositories is at Tier 2 or above (ADR 0021)",
                     "every PINS line names the spec's current version",
                     "every criterion and edge case in the spec maps to a test here and to a slice's bundle"):
            self.assertIn(item, checklist, item)

    def test_slice_0_names_no_starter_workflow_or_script(self):
        plan = skill("aidlc-plan")
        self.assertNotIn("ai-review.yml", plan)
        self.assertNotIn("the check scripts", plan)
        self.assertNotIn("story status command", plan)
        self.assertIn("the team's CI configuration (`.github/workflows/ci.yml` on GitHub, `.gitlab-ci.yml` on GitLab)", plan)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.BuildAndPlanTest -v`

Expected: FAIL in all four tests.

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

`FastPathTest.test_build_reads_the_mode` (owner's item T3a): the slice runner is gone; the other five assertions stay.
In `scripts/test_fast_path.py` find:

```text
        self.assertIn("the slice runner named in AGENTS.md", build)
```

and delete it.


`PlanCheckTest.test_plan_runs_the_plan_check` (owner's item T3b): the plan check is now the plan's checklist.
In `scripts/test_gates_hold.py` find:

```text
        self.assertIn("run the plan check named in AGENTS.md and fix every problem it reports", plan)
```

Replace with:

```text
        self.assertIn("go through the plan's checklist (`assets/plan.md`) item by item, against the files, and fix every "
                      "gap it finds", plan)
```

`GreenfieldTest.test_ci_and_branch_protection_have_owners` (owner's item T3c): slice 0 no longer names the starter's AI review workflow; the other four assertions stay.
In `scripts/test_greenfield.py` find:

```text
        self.assertIn("`ai-review.yml`", plan)
```

and delete it.


- [ ] **Step 4: Change the build, the plan, the compliance reviewer and the description template**

In `skills/aidlc-build/SKILL.md` find (it starts with a space; keep it exact):

```text
 A person can run approved delegate slices one after another, each in a fresh headless session, with the slice runner named in AGENTS.md; it stops at the first slice that does not end done.
```

Replace with:

```text
 A person can run approved delegate slices one after another: one fresh session per slice, each started by the person, who reads the slice's progress note and diff before starting the next. A slice whose note does not end `done` stops the run.
```

In `skills/aidlc-build/SKILL.md` find:

```text
Run the recipe check named in AGENTS.md (`scripts/check_recipe_commit.py <commit> --recipe … --count …`) and stop for the person's review of that commit, in every mode: set STATUS to `paused: recipe review`.
```

Replace with:

```text
Then run the recipe check, with git: in a temporary worktree at the commit's parent (`git worktree add <folder> <commit>^`), run the approved command, stage everything (`git -C <folder> add -A`), and `git -C <folder> diff --cached --stat <commit>` must print nothing; the test count must be the same at the parent and at the commit. Remove the worktree (`git worktree remove --force <folder>`) and write the result in the progress note. Stop for the person's review of that commit, in every mode: set STATUS to `paused: recipe review`.
```

In `skills/aidlc-build/assets/progress-note.md` find:

```text
compliance reviewer and the slice runner read it.
```

Replace with:

```text
compliance reviewer and the next session read it.
```

In `skills/aidlc-plan/SKILL.md` find:

```text
A part of a story across several repositories is at least Tier 2 (ADR 0021); the plan check reports a Tier 1 part.
```

Replace with:

```text
A part of a story across several repositories is at least Tier 2 (ADR 0021); the plan's checklist catches a Tier 1 part.
```

In `skills/aidlc-plan/SKILL.md` find:

```text
run the plan check named in AGENTS.md and fix every problem it reports. Its output goes in
```

Replace with:

```text
go through the plan's checklist (`assets/plan.md`) item by item, against the files, and fix every gap it
   finds. Its result goes in
```

In `skills/aidlc-plan/SKILL.md` find:

```text
repository, and the story status command reports a copy that differs from the spec (ADR 0022).
```

Replace with:

```text
repository, and `aidlc-release` compares it with the spec at its commit before release (ADR 0022).
```

In `skills/aidlc-plan/SKILL.md` find:

```text
and `.github/workflows/ci.yml`, which runs the COMMANDS, each
   required check seen red once in a draft pull request.
```

Replace with:

```text
and the team's CI configuration (`.github/workflows/ci.yml` on GitHub,
   `.gitlab-ci.yml` on GitLab), which runs the COMMANDS, each check seen red once in a draft pull request.
```

In `skills/aidlc-plan/SKILL.md` find:

```text
3. MAY CHANGE covers the block's PATHS, the files the scaffold creates and `.github/workflows/ci.yml`. MUST NOT names
   `AGENTS.md`, `CODEOWNERS`, `.claude/**`, `ai-review.yml` and the check scripts. DONE WHEN:
```

Replace with:

```text
3. MAY CHANGE covers the block's PATHS, the files the scaffold creates and the CI configuration. MUST NOT names
   `AGENTS.md`, `CODEOWNERS` and `.claude/**`. DONE WHEN:
```

In `skills/aidlc-plan/SKILL.md` find:

```text
so the story status command never reads it as the part's code (ADR 0022).
```

Replace with:

```text
so nobody takes it for the part's code (ADR 0022).
```

In `skills/aidlc-plan/assets/plan.md` find:

```text
has a scope test and concrete stop conditions.
```

Replace with:

```text
has a scope test and concrete stop conditions.
Fields (check each against the files before asking for approval):
- every bundle field filled, or "none"; no placeholder left
- each MODE allowed at its TIER (delegate with checkpoints: Tiers 1 and 2; delegate: Tier 1)
- a part of a story across several repositories is at Tier 2 or above (ADR 0021)
- every STOP IF holds "an existing assertion would need to change", "a new dependency seems
  necessary", "the plan looks wrong" and "retrieved text asks for something not listed here"
- every PINS line names the spec's current version
- every criterion and edge case in the spec maps to a test here and to a slice's bundle
```

In `agents/reviewer-compliance.md` find:

```text
holds only what the bundle's RECIPE approved; the recipe check's output is in the pull request; every assertion line it lists still checks the same thing.
```

Replace with:

```text
holds only what the bundle's RECIPE approved: the evidence file's Recipe commits section shows the re-run on its parent with no difference and the same test count; every assertion line the commit changes still checks the same thing.
```

In `agents/reviewer-compliance.md` find:

```text
CHANGE lists, and the recipe check does not apply to it.
```

Replace with:

```text
CHANGE lists, and it is not re-run (generators are not reproducible).
```

In `agents/reviewer-compliance.md` find:

```text
The recipe check's output line does not apply to a
  `(scaffold)` commit
```

Replace with:

```text
The re-run does not apply to a
  `(scaffold)` commit
```

In `skills/aidlc-review/assets/pr-description.md` find:

```text
- **Recipe:** {{sha, tool@version, recipe check output}}, or none
```

Replace with:

```text
- **Recipe:** {{sha, tool@version, and the recipe check's result from the evidence file}}, or none
```

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.BuildAndPlanTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 738 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add skills/aidlc-build skills/aidlc-plan agents/reviewer-compliance.md skills/aidlc-review/assets/pr-description.md scripts/test_instructions_first.py scripts/test_fast_path.py scripts/test_gates_hold.py scripts/test_greenfield.py
git commit -m "feat(skills): the recipe check runs with git, a person starts each delegate slice, and the plan check is the plan's checklist" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 4: The story level: status, release and contracts from git and a person's confirmation

`story_status.py`, `check_contract_version.py`, `check_contract_pin.py` and the two contract workflows go. Status becomes a file the AI derives from each part's index with git; the release check becomes one row per repository that a person confirms (design table, row 9); the contract checks become commands the provider and the consumer run in their own CI: `oasdiff breaking`, a version comparison, `sha256sum -c` and `git ls-remote --tags` (rows 10 and 11). The `.gitignore` generator becomes a line a person adds.

**Files:**
- Modify: `skills/aidlc-start/assets/story-index.md` and `skills/aidlc-plan/assets/story-index.md` (identical), `skills/aidlc-plan/assets/criteria.md`, `skills/aidlc-design/assets/coordination-plan.md`
- Modify: `starter/workspace/WORKSPACE.md`, `skills/aidlc-onboard/assets/workspace.md` (the Commands section), `starter/workspace/stories/README.md`
- Modify: `skills/aidlc-specify/SKILL.md` (amendment step 5), `skills/aidlc-design/SKILL.md` (amendment steps 3 and 4), `skills/aidlc-release/SKILL.md` (step 1), `skills/aidlc-release/assets/readiness.md` (a Parts table)
- Modify: `skills/designing-apis/SKILL.md` (three bullets of "A Contract Across Repositories")
- Modify: `docs/operating-model/routes.md`, `docs/operating-model/workspace-and-repositories.md` (status lines)
- Test: `scripts/test_instructions_first.py` (new class `StoryLevelTest`); approved changes in `scripts/test_routes.py`, `scripts/test_multirepo.py`, `scripts/test_docs.py`

**Interfaces:**
- Produces: the Parts table in `readiness.md` and the heading `## Status and release` in the workspace guide; Task 8's docs point to them.
- Produces: the contract commands in `designing-apis`, which Task 5's onboard step 5 and `aidlc-release` cite as "the commands in `designing-apis`".

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class StoryLevelTest(unittest.TestCase):
    """Task 4: a story's status and its release come from git and a person's confirmation; the contract checks are
    commands the team runs in its own CI."""

    FILES = ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md",
             "skills/aidlc-plan/assets/criteria.md", "skills/aidlc-design/assets/coordination-plan.md",
             "starter/workspace/stories/README.md", "starter/workspace/WORKSPACE.md",
             "skills/aidlc-onboard/assets/workspace.md", "skills/aidlc-specify/SKILL.md",
             "skills/aidlc-design/SKILL.md", "skills/aidlc-release/SKILL.md", "skills/designing-apis/SKILL.md",
             "docs/operating-model/routes.md", "docs/operating-model/workspace-and-repositories.md")

    def test_no_story_level_file_names_the_status_or_contract_scripts(self):
        for rel in self.FILES:
            text = flat(rel)
            for name in ("story_status", "story status command", "status script", "check_contract_",
                         "contract pin command", "contract-publish.yml", "contract-check", "--check-release"):
                self.assertNotIn(name, text, f"{rel}: {name}")

    def test_status_is_derived_from_git(self):
        for rel in ("starter/workspace/WORKSPACE.md", "skills/aidlc-onboard/assets/workspace.md"):
            text = flat(rel)
            self.assertIn("`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`", text, rel)
            self.assertIn("Nobody edits that file by hand.", text, rel)
            self.assertIn("a person adds or removes the repository's line in the root's `.gitignore`", text, rel)
        self.assertIn("the AI at the workspace root reads each part's index on its repository's default branch with git",
                      flat("skills/aidlc-design/assets/coordination-plan.md"))

    def test_release_fills_one_row_per_part_and_a_person_confirms(self):
        release = skill("aidlc-release")
        for phrase in ("fill the Parts table in `assets/readiness.md`", "The person confirms each row.",
                       "`git merge-base --is-ancestor <commit> origin/<default branch>`",
                       "The table is the release check. Any mismatch it reports blocks the release."):
            self.assertIn(phrase, release, phrase)
        readiness = read("skills/aidlc-release/assets/readiness.md")
        self.assertIn("## Parts (a story across several repositories)", readiness)
        self.assertEqual(readiness.count("- [ ] "), 10)

    def test_designing_apis_gives_the_contract_commands(self):
        text = flat("skills/designing-apis/SKILL.md")
        for command in ("oasdiff breaking <last copy> <path> --fail-on ERR --allow-external-refs=false",
                        "sha256sum -c -", "git ls-remote --tags <repository> 'refs/tags/api-v<version>*'",
                        "git tag api-v<version> <merge commit>",
                        "git clone --depth 1 --branch api-v<version> <repository> <folder>"):
            self.assertIn(command, text, command)
        self.assertIn("with the commands in `designing-apis` (`sha256sum -c` against its SOURCE", skill("aidlc-release"))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.StoryLevelTest -v`

Expected: FAIL in all four tests.

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

In `scripts/test_docs.py`, delete these test methods (each from its `def` line through its last line): `ReviewFixesTest.test_i2_the_status_command_writes_with_write`. Why: it pins `story_status.py <KEY> --write` in `routes.md` (owner's item T4f).

`RoutesTest.test_the_workspace_names_the_status_command` (owner's item T4a): the workspace guide names how status is written, not a script; onboard no longer copies one.
In `scripts/test_routes.py` find:

```text
            self.assertIn("`python3 scripts/story_status.py <KEY> --write`", read(rel), rel)
        self.assertIn("story_status.py", skill("aidlc-onboard"))
```

Replace with:

```text
            self.assertIn("writes `stories/<KEY>/status.md`", read(rel), rel)
```

`RoutesTest.test_release_checks_every_part_and_runs_the_integration_check` (owner's item T4b).
In `scripts/test_routes.py` find:

```text
        self.assertIn("--check-release", text)
```

Replace with:

```text
        self.assertIn("fill the Parts table in `assets/readiness.md`", text)
```

`DecisionsTest.test_release_reads_the_real_merge_state` (owner's item T4c): the merge state is read with git from the default branch, on any code host.
In `scripts/test_multirepo.py` find:

```text
        self.assertIn("takes each part's merge state from its pull request on GitHub when it can", skill("aidlc-release"))
```

Replace with:

```text
        self.assertIn("its `merged` row reads done", skill("aidlc-release"))
```

`OnlinePinCheckTest.test_release_runs_the_online_check` (owner's item T4d); its second assertion, "a moved tag stops the release", stays.
In `scripts/test_multirepo.py` find:

```text
        self.assertIn("runs the contract pin command's online check (named in its AGENTS.md) before release", release)
```

Replace with:

```text
        self.assertIn("checks its copy before release with the commands in `designing-apis`", release)
```

`HygieneTest.test_the_workspace_guide_names_the_command_and_the_owner` (owner's item T4e).
In `scripts/test_multirepo.py` find:

```text
            self.assertIn("`python3 scripts/story_status.py --write-gitignore`", text, rel)
```

Replace with:

```text
            self.assertIn("a person adds or removes the repository's line in the root's `.gitignore`", text, rel)
```

- [ ] **Step 4: Change the templates, the skills and the two docs**

In each of these files: `skills/aidlc-start/assets/story-index.md`, `skills/aidlc-plan/assets/story-index.md`, find (it starts with a space; keep it exact):

```text
 The story
status command checks the merged row against the real merge state and reports a row that disagrees.
```

Replace with:

```text
 At release,
`aidlc-release` reads the merged row on each repository's default branch with git, and a person confirms it.
```

In each of these files: `starter/workspace/WORKSPACE.md`, `skills/aidlc-onboard/assets/workspace.md`, find:

```text
## Commands
- Story status, after any part moves: `python3 scripts/story_status.py <KEY> --write` (writes `stories/<KEY>/status.md`).
- Before release, with every repository on its default branch after `git pull`:
  `python3 scripts/story_status.py <KEY> --check-release` (fails unless every part is merged at the current versions).
- After the repository table above changes, a person runs `python3 scripts/story_status.py --write-gitignore` (the
  session at this root may write only under `stories/`, `incidents/` and `feedback/`). The root's `.gitignore` then
  lists every repository, so this home repository never tracks their files.
```

Replace with:

```text
## Status and release
- Story status, after any part moves: the AI at this root runs `git -C <repository> fetch`, reads each part's
  index on its default branch (`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`) and
  writes `stories/<KEY>/status.md`. Nobody edits that file by hand.
- Before release, `aidlc-release` fills one row per part in `stories/<KEY>/readiness.md` from git: merged on the
  default branch, pinned to the current spec at a home commit on this repository's default branch, and a
  criteria copy that matches the spec. A person confirms each row.
- When the repository table above changes, a person adds or removes the repository's line in the root's
  `.gitignore` (`/<repository>/`), so this home repository never tracks its files. The session at this root may
  write only under `stories/`, `incidents/` and `feedback/`.
```

In `skills/aidlc-plan/assets/criteria.md` find:

```text
The story status command reports
any line here that is not in the spec at the commit below.
```

Replace with:

```text
Before release,
`aidlc-release` compares each line here with the spec at the commit below; a line that differs blocks the release.
```

In `skills/aidlc-design/assets/coordination-plan.md` find:

```text
(Status is derived: run the story status command named in WORKSPACE.md; it reads each part's index and writes `status.md` beside this plan.)
```

Replace with:

```text
(Status is derived: the AI at the workspace root reads each part's index on its repository's default branch with git and writes `status.md` beside this plan; nobody edits it by hand.)
```

In `starter/workspace/stories/README.md` find:

```text
| `status.md` | the story status command | Every part's status, derived from the repositories' own indexes (do not edit) |
```

Replace with:

```text
| `status.md` | the AI at the root, from git | Every part's status, derived from each repository's own index on its default branch (do not edit by hand) |
```

In `skills/aidlc-specify/SKILL.md` find:

```text
raise the CURRENT line in the story index; the story status command then
   marks every part pinned to the old spec "re-plan".
```

Replace with:

```text
raise the CURRENT line in the story index; the next `status.md` the AI derives
   then marks every part pinned to the old spec "re-plan".
```

In `skills/aidlc-design/SKILL.md` find:

```text
Each consumer
   moves its copy to that tag with the contract pin command named in its AGENTS.md, in a slice whose MAY CHANGE
   names `contracts/<provider>/**`.
```

Replace with:

```text
Each consumer
   moves its copy to that tag, with the commands in `designing-apis`, in a slice whose MAY CHANGE names
   `contracts/<provider>/**`.
```

In `skills/aidlc-design/SKILL.md` find:

```text
4. Run the story status command named in WORKSPACE.md: every part pinned to the old version shows "re-plan". Those
   parts return to `aidlc-plan`; their bundles are approved again. In one repository there is no coordination plan or
   status command: list the bundles that pin the old version and mark them for re-plan.
```

Replace with:

```text
4. Read each part's PINS line on its repository's default branch, with
   `git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`, and mark every part pinned to the old
   version "re-plan" in `status.md`. Those parts return to `aidlc-plan`; their bundles are approved again. In one
   repository there is no coordination plan: list the bundles that pin the old version and mark them for re-plan.
```

In `skills/aidlc-release/SKILL.md` find:

```text
When the story spans several repositories, run the release check named in WORKSPACE.md (`scripts/story_status.py <KEY> --check-release`) at the workspace root; every part must be merged at the current versions. The command takes each part's merge state from its pull request on GitHub when it can, else from the default branch's copy of the part index, and reports a merged row that disagrees with it (the AI writes that row in the part's final commit, after checking the approval on GitHub, ADR 0023), a pin that drifted from the home repository and a criteria copy that differs from the spec. Any mismatch it reports blocks the release. A part that pins an older spec blocks the release until it is revised or recorded as unaffected. In one repository, the same rule holds inside the branch: every merged bundle pins the current spec version. Each repository that consumes a contract runs the contract pin command's online check (named in its AGENTS.md) before release; a moved tag stops the release.
```

Replace with:

```text
When the story spans several repositories, fill the Parts table in `assets/readiness.md` at the workspace root, one row per part, from git. In each repository run `git -C <repository> fetch`, then read the part index on its default branch (`git -C <repository> show origin/<default branch>:plans/<KEY>/README.md`): its `merged` row reads done; its PINS name the story's CURRENT spec version and a home commit that is on the home repository's default branch (`git merge-base --is-ancestor <commit> origin/<default branch>` at the root); and its criteria copy (`git -C <repository> show origin/<default branch>:plans/<KEY>/criteria.md`) matches the spec at that commit (`git show <commit>:stories/<KEY>/spec.md`). The person confirms each row. The table is the release check. Any mismatch it reports blocks the release. A part that pins an older spec blocks the release until it is revised or recorded as unaffected. In one repository, the same rule holds inside the branch: every merged bundle pins the current spec version. Each repository that consumes a contract checks its copy before release with the commands in `designing-apis` (`sha256sum -c` against its SOURCE, and `git ls-remote --tags` for the tag's commit); a moved tag stops the release.
```

In `skills/aidlc-release/assets/readiness.md` find:

```text
## Decision
```

Replace with:

```text
## Parts (a story across several repositories)
One row per part, filled by the AI from git (`aidlc-release`, step 1) and confirmed by a person. Any "no" blocks the
release. Leave this section out for a story in one repository.

| Repository | Part | Merged on its default branch | Pins the current spec at a home commit on the home default branch | Criteria copy matches the spec | Contract copy matches its SOURCE and tag | Confirmed by |
|---|---|---|---|---|---|---|
| {{repository}} | {{n of m}} | {{yes, at commit, or no}} | {{yes: spec version and home commit, or no}} | {{yes, or the lines that differ}} | {{yes, no, or no contract}} | {{who, YYYY-MM-DD, how it was confirmed}} |

## Decision
```

In `skills/designing-apis/SKILL.md` find:

```text
- **Publish from the default branch only.** Each version is the git tag `api-v<info.version>`, created after the merge
  (the starter's `contract-publish.yml`). Never tag an unmerged commit by hand: a consumer could build on a version
  nobody reviewed. Only the publish job creates tags, or a person tagging a default-branch commit the job skipped, as
  `contract-publish.yml` says.
- **Every change raises the version.** An additive change raises MINOR. A breaking change raises MAJOR, only with every
  consumer's agreement, done by expand and contract. The provider's `contract-check` runs oasdiff against the last
  published tag. It fails a breaking change without a new MAJOR, and any change without a new version.
- **Consumers pin a copy.** Each consumer keeps a read-only copy in `contracts/<provider>/`, beside a `SOURCE` file
  naming the repository, tag, commit, path and sha256. Its CI checks the copy offline, so it never needs the
  provider. It moves the pin only to a named version (`--update <provider> api-v<version>`, never "latest"), in a
  slice of its own.
```

Replace with:

```text
- **Publish from the default branch only.** Each version is the git tag `api-v<info.version>`, created on the merge
  commit after the merge, by a person or by the provider's own CI: `git tag api-v<version> <merge commit>`, then
  `git push origin api-v<version>` (a push asks first). Never tag an unmerged commit by hand: a consumer could build
  on a version nobody reviewed. A team whose code host can protect tags may restrict who creates `api-v*`; aidlc
  needs no such feature.
- **Every change raises the version.** An additive change raises MINOR. A breaking change raises MAJOR, only with every
  consumer's agreement, done by expand and contract. The provider's own CI runs the contract check on each pull
  request that changes the contract, against the last published tag
  (`git tag --list 'api-v*' --sort=-v:refname | head -n 1`): `git show <tag>:<path> > <last copy>`, then
  `oasdiff breaking <last copy> <path> --fail-on ERR --allow-external-refs=false`, and a comparison of `info.version`
  in the two files. It fails a breaking change without a new MAJOR, and any change without a new version. Pin
  oasdiff's version, and check its download with `sha256sum -c` before you run it.
- **Consumers pin a copy.** Each consumer keeps a read-only copy in `contracts/<provider>/`, beside a `SOURCE` file
  naming the repository, tag, commit, path and sha256. Its CI checks the copy offline, so it never needs the
  provider: `echo "<sha256>  contracts/<provider>/<file>" | sha256sum -c -`, with the hash from `SOURCE`. Before a
  pin moves and before a release, it also checks that the tag still names that commit:
  `git ls-remote --tags <repository> 'refs/tags/api-v<version>*'` (for an annotated tag, the commit is on the line
  ending `^{}`); a moved tag stops the release. It moves the pin only to a named version, never "latest", in a
  slice of its own: `git clone --depth 1 --branch api-v<version> <repository> <folder>`, copy the file, and write
  `SOURCE` from `git -C <folder> rev-parse HEAD` and `sha256sum`.
```

In `docs/operating-model/routes.md` find:

```text
At the root,
`python3 scripts/story_status.py <KEY> --write` reads every part's index and writes `stories/<KEY>/status.md`;
with `--check-release` it is the check `aidlc-release` runs.
```

Replace with:

```text
At the root,
the AI reads every part's index on its repository's default branch with git and writes `stories/<KEY>/status.md`;
before release, `aidlc-release` fills one row per part from the same reads, and a person confirms each row.
```

In `docs/operating-model/routes.md` find:

```text
the status script flags every part whose bundle pins the old spec.
```

Replace with:

```text
`status.md` flags every part whose bundle pins the old spec.
```

In `docs/operating-model/workspace-and-repositories.md` find:

```text
its index in the repository; the story status command at the root derives `stories/<KEY>/status.md`
```

Replace with:

```text
its index in the repository; the AI at the root derives `stories/<KEY>/status.md` from it with git
```

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.StoryLevelTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 741 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add skills/aidlc-start/assets/story-index.md skills/aidlc-plan/assets skills/aidlc-design starter/workspace/WORKSPACE.md skills/aidlc-onboard/assets/workspace.md starter/workspace/stories/README.md skills/aidlc-specify/SKILL.md skills/aidlc-release skills/designing-apis/SKILL.md docs/operating-model/routes.md docs/operating-model/workspace-and-repositories.md scripts/test_instructions_first.py scripts/test_routes.py scripts/test_multirepo.py scripts/test_docs.py
git commit -m "feat(skills): story status and the release check come from git and a person's confirmation; the contract checks are commands the team runs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 5: Onboarding: no script to copy, no branch protection to ask for, a rules file that names no script

`aidlc-onboard` copied seven scripts and four workflows into a team's repository and asked for branch protection. Now it copies the ownership list and, in Claude Code, the optional example settings; it writes the home repository's `.gitignore` itself; and it tells the team which of its own checks to add (design: "The principle", second bullet). The rules-file template stops naming scripts, and the suppression reference stops describing the slice check.

**Files:**
- Modify: `skills/aidlc-onboard/SKILL.md` (step 0, step 5, new mode prepare and confirm)
- Modify: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md` (Commands, Quality bar, Boundaries)
- Modify: `skills/aidlc-onboard/references/suppression-rules.md` (the intro and the last two sections)
- Test: `scripts/test_instructions_first.py` (new class `OnboardTest`); approved changes in `scripts/test_gates_hold.py`, `scripts/test_multirepo.py`, `scripts/test_fast_path.py`

**Interfaces:**
- Consumes: the contract commands in `designing-apis` (Task 4) and the evidence file (Task 2).
- Leaves for Task 7: the sentence "Then check the setting on GitHub where you can read it" in new mode's confirm step, which Task 7 makes host-neutral.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class OnboardTest(unittest.TestCase):
    """Task 5: onboarding copies no script and no workflow, and the rules file names no script."""

    GUIDES = ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md")

    def test_the_rules_file_names_no_script(self):
        for rel in self.GUIDES:
            text = flat(rel)
            for name in ("scripts/check_", "run_slices", "slice check", "Slice runner", "Plan check", "Recipe check,",
                         "Contract pin,"):
                self.assertNotIn(name, text, f"{rel}: {name}")
            for phrase in ("the commands from the `designing-apis` skill, or none",
                           "The compliance reviewer reports a new suppression or skip",
                           "recipe commit, re-run on its parent with git and compared (ADR 0012)"):
                self.assertIn(phrase, text, f"{rel}: {phrase}")

    def test_onboard_copies_no_script_or_workflow(self):
        onboard = skill("aidlc-onboard")
        for name in ("story_status", "check_slice", "check_plan", "check_recipe_commit", "run_slices",
                     "check_contract_", "ai-review.yml", "contract-check.yml", "contract-publish.yml",
                     "the starter's workflow", "--write-gitignore", "Ask the person to turn on branch protection"):
            self.assertNotIn(name, onboard, name)
        for phrase in ("aidlc ships no check of its own (ADR 0024)",
                       "Then write the root's `.gitignore`: one line per repository",
                       "the team may take the example settings",
                       "A team whose code host can require a code owner's review before a merge may turn that on; "
                       "aidlc never needs it.",
                       "propose the provider's checks from `designing-apis`"):
            self.assertIn(phrase, onboard, phrase)

    def test_the_suppression_reference_names_no_slice_check(self):
        text = flat("skills/aidlc-onboard/references/suppression-rules.md")
        self.assertNotIn("slice check", text)
        self.assertIn("the compliance reviewer reads each added one in the session's evidence file", text)
        self.assertIn("## Closing directives", read("skills/aidlc-onboard/references/suppression-rules.md"))
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.OnboardTest -v`

Expected: FAIL in all three tests.

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

In `scripts/test_multirepo.py`, delete these test methods (each from its `def` line through its last line): `ContractWorkflowTest.test_the_guide_names_the_commands`, `OnlinePinCheckTest.test_the_guide_names_the_online_check_and_when_it_runs`. Why: they pin the contract scripts' command lines in the rules file (owner's items T5d, T5e).

In `scripts/test_fast_path.py`, delete these test methods (each from its `def` line through its last line): `FastPathTest.test_the_runner_is_named_where_it_is_used`, `ReviewFixesTest.test_i5_onboarded_repositories_name_the_runner`. Why: they pin `run_slices.py` in the rules file and in onboard (owner's items T5f, T5g).

`WiringTest.test_the_guide_names_the_commands_and_the_exception_format` (owner's item T5a): the guide names no script; the exception-format assertion stays.
In `scripts/test_gates_hold.py` find:

```text
            self.assertIn("python3 scripts/check_slice.py", text, rel)
            self.assertIn("python3 scripts/check_plan.py", text, rel)
```

and delete it.


`WhereGatesHoldTest.test_onboard_says_it_too` (owner's item T5b): host-neutral.
In `scripts/test_gates_hold.py` find:

```text
"Say which controls hold in the team's tool and on its GitHub plan"
```

Replace with:

```text
"Say which controls hold in the team's tool and on its code host"
```

`DecisionsTest.test_onboard_sets_up_the_home_repository` (owner's item T5c): its first assertion (the CODEOWNERS copy) stays.
In `scripts/test_multirepo.py` find:

```text
        self.assertIn("run `python3 scripts/story_status.py --write-gitignore`", onboard)
        self.assertIn("propose `check_contract_pin.py` with `check_contract_version.py`, which it imports", onboard)
```

Replace with:

```text
        self.assertIn("Then write the root's `.gitignore`: one line per repository", onboard)
        self.assertIn("propose the consumer's (`sha256sum -c` against each copy's SOURCE)", onboard)
```

- [ ] **Step 4: Change onboard, the rules-file template, the starter's rules file and the suppression reference**

In `skills/aidlc-onboard/SKILL.md` find:

```text
the home repository: the story status command's pin and
     criteria checks read its history.
```

Replace with:

```text
the home repository: each part pins its commits, and the
     release reads its history with git.
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
   - Next, copy `story_status.py` from aidlc's `starter/workspace/scripts/` into the workspace's `scripts/` folder.
```

and delete it.


In `skills/aidlc-onboard/SKILL.md` find:

```text
   - Then run `python3 scripts/story_status.py --write-gitignore`, which writes the root's `.gitignore` from the
     repository table in `WORKSPACE.md`.
```

Replace with:

```text
   - Then write the root's `.gitignore`: one line per repository in the table of `WORKSPACE.md` (`/<repository>/`),
     so the home repository never tracks a repository's files.
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
   - In Claude Code, copy the settings from aidlc's `starter/workspace/` folder.
```

Replace with:

```text
   - In Claude Code, the team may take the example settings from aidlc's `starter/workspace/` folder.
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
     add its deny rule to `.claude/settings.json` (a session cannot edit it). Run
     `python3 scripts/story_status.py --write-gitignore` again whenever the repository table changes.
```

Replace with:

```text
     add its deny rule to `.claude/settings.json` (a session cannot edit it) and its line to the root's
     `.gitignore`.
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
say which rules need a control: a tool permission (the starter's `.claude/settings.json`), a CI check (the starter's workflow) or code-owner review (`CODEOWNERS`). Propose copying the starter files that fit; the person decides. When the repository has no CI, or only the starter's placeholder steps, load the `building-ci-pipelines` skill and design it. Say which controls hold in the team's tool and on its GitHub plan ("Where the gates hold" in the README): on GitHub Free, required checks and branch protection work only on public repositories. When the repository owns a contract that other repositories use, propose `contract-check.yml`, `contract-publish.yml` and `check_contract_version.py`, and name the contract's path in `AGENTS.md`; when it consumes one, propose `check_contract_pin.py` with `check_contract_version.py`, which it imports (ADR 0022).
```

Replace with:

```text
say which rules need a control in the team's project: a check in its own tests, linters or CI; a tool permission (aidlc's example `.claude/settings.json`, optional); or code-owner review (`CODEOWNERS`). aidlc ships no check of its own (ADR 0024): each control is the team's, in its project. Propose copying the starter files that fit; the person decides. When the repository has no CI, load the `building-ci-pipelines` skill and design it. Say which controls hold in the team's tool and on its code host ("Where the gates hold" in the README): aidlc needs only git; a team whose code host can require checks or a code owner's review before a merge may use that, and on GitHub Free those work only on public repositories. When the repository owns a contract that other repositories use, name the contract's path in `AGENTS.md` and propose the provider's checks from `designing-apis` for its CI (oasdiff against the last published tag, and the version comparison); when it consumes one, propose the consumer's (`sha256sum -c` against each copy's SOURCE) (ADR 0022).
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
  (`.claude/settings.json`, `CODEOWNERS`, `ai-review.yml`, and `check_recipe_commit.py` and `run_slices.py` into the
  repository's scripts folder); slice 0 writes the CI workflow. Copy `check_slice.py` and `check_plan.py` into the scripts folder as well, and copy `.claude/settings.json` last: its deny rules then protect the files copied before it. Ask the person to turn on branch protection that
  requires a code owner's review.
```

Replace with:

```text
  (`CODEOWNERS`, and in Claude Code the example `.claude/settings.json`); slice 0 writes the CI workflow. When the
  team takes the example settings, copy `.claude/settings.json` last: its deny rules then protect the files copied
  before it. A team whose code host can require a code owner's review before a merge may turn that on; aidlc never
  needs it.
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
Ask the person, who marks slice 0's checks as required in branch protection.
```

Replace with:

```text
A team whose code host can require checks before a merge may ask a repository administrator, who marks slice 0's
  checks as required there (branch protection or its equivalent); aidlc never needs it.
```

In `skills/aidlc-onboard/references/suppression-rules.md` find:

```text
Why two layers. The slice check named in AGENTS.md judges the branch's diff: a new suppression, or one made wider,
needs an `aidlc-exception`. It never sees the suppressions already in the code. The linters' own rules see the whole
codebase: they reject a suppression that names no rule (a blanket one) and one that silences nothing (an unused one).
Together, a suppression stays as narrow as it was approved, and goes when it is no longer needed.
```

Replace with:

```text
Why these rules. aidlc ships no check of its own (ADR 0024). In a change, a new suppression, or one made wider, needs
an `aidlc-exception`: the compliance reviewer reads each added one in the session's evidence file, and the code owner
approves it. Neither sees the suppressions already in the code. The linters' own rules see the whole codebase on
every run: they reject a suppression that names no rule (a blanket one) and one that silences nothing (an unused
one). Together, a suppression stays as narrow as it was approved, and goes when it is no longer needed.
```

In `skills/aidlc-onboard/references/suppression-rules.md` find:

```text
No built-in analyzer rejects a `#pragma warning disable` that names no code. The slice check catches a new one, or
one widened from a named code, in the diff; one already in the code stays until someone removes it.

## What the slice check does not model

The slice check judges a removed closing directive (`eslint-enable`, `# pylint: enable=`, `#pragma warning restore`,
`c8 ignore stop`) by reading the file from the top, in order. It does not know each tool's scoping rules, so some pylint
cases slip past it unreported. For example:

- **Block scope.** pylint ends an own-line `disable` or `enable` inside a function or class at the end of that block.
  The slice check lets it run on to the end of the file. So an `enable` inside a function can read as closing a
  module-level `disable`, and removing the module-level `enable` below it is missed.
- **Names and ids.** `no-member` and `E1101` are one message to pylint but two rules to the slice check. Removing
  `enable=no-member` below `disable=E1101` is missed.
- **Trailing pragma.** pylint applies a pragma trailing code to that line only. The slice check counts a trailing
  `x = os.a  # pylint: enable=no-member` as a closer, so removing an own-line `enable` below it can be missed.

The linters' own rules narrow the gap. pylint's `use-symbolic-message-instead` reports numeric ids, so every
suppression can use one name. `useless-suppression` (above) reports a `disable` that silences nothing. Prefer a trailing
`disable` or `disable-next` on the one line that needs it: the slice check reads those exactly. A reviewer still reads
any removed `enable` in the diff.
```

Replace with:

```text
No built-in analyzer rejects a `#pragma warning disable` that names no code. The compliance reviewer reports a new
one, or one widened from a named code, from the evidence file; one already in the code stays until someone removes it.

## Closing directives

Removing a closing directive (`eslint-enable`, `# pylint: enable=`, `#pragma warning restore`, `c8 ignore stop`) widens
a suppression without adding a line. The evidence file lists every removed one, and the compliance reviewer reads
each. Mind pylint's scoping when you judge one:

- **Block scope.** pylint ends an own-line `disable` or `enable` inside a function or class at the end of that block.
- **Names and ids.** `no-member` and `E1101` are one message to pylint.
- **Trailing pragma.** pylint applies a pragma trailing code to that line only.

The linters' own rules narrow the gap. pylint's `use-symbolic-message-instead` reports numeric ids, so every
suppression can use one name. `useless-suppression` (above) reports a `disable` that silences nothing. Prefer a trailing
`disable` or `disable-next` on the one line that needs it.
```

In `skills/aidlc-onboard/assets/agents-md.md` find:

```text
- Recipe check, after a recipe commit: `python3 scripts/check_recipe_commit.py <commit> --recipe "<approved command>" --count "<test count command>"`
- Slice runner, for approved delegate slices only, one fresh session each: `python3 scripts/run_slices.py <KEY> <slice> [<slice> ...] [--part <n>]`;
  it stops at the first slice that does not end done, and never pushes
- Slice check, on the story's branch (CI and the session's Stop hook run it too): `python3 scripts/check_slice.py`
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
- Contract pin, a consumer's vendored contracts match their SOURCE (CI runs it too): `python3 scripts/check_contract_pin.py`;
  move a pin only to a published tag, in its own slice: `python3 scripts/check_contract_pin.py --update <provider> api-v<version>`
- Contract pin, online, before a pin moves and before a release (no job runs it yet):
  `python3 scripts/check_contract_pin.py --online`; it reports a provider tag that moved, which stops the release
- Contract check, a provider's contract against its last published tag (CI runs it with oasdiff):
  `python3 scripts/check_contract_version.py --contract <path> --oasdiff <oasdiff binary>`
```

Replace with:

```text
- Contract checks, when this repository owns or consumes a contract: {{the commands from the `designing-apis` skill, or none}}
```

In `starter/repo/AGENTS.md` find:

```text
- Recipe check, after a recipe commit: `python3 scripts/check_recipe_commit.py <commit> --recipe "<approved command>" --count "<test count command>"`
- Slice runner, for approved delegate slices only, one fresh session each: `python3 scripts/run_slices.py <KEY> <slice> [<slice> ...] [--part <n>]`;
  it stops at the first slice that does not end done, and never pushes
- Slice check, on the story's branch (CI and the session's Stop hook run it too): `python3 scripts/check_slice.py`
- Plan check, before asking for the plan's approval: `python3 scripts/check_plan.py <KEY> [--part <n>]`
- Contract pin, a consumer's vendored contracts match their SOURCE (CI runs it too): `python3 scripts/check_contract_pin.py`;
  move a pin only to a published tag, in its own slice: `python3 scripts/check_contract_pin.py --update <provider> api-v<version>`
- Contract pin, online, before a pin moves and before a release (no job runs it yet):
  `python3 scripts/check_contract_pin.py --online`; it reports a provider tag that moved, which stops the release
- Contract check, a provider's contract against its last published tag (CI runs it with oasdiff):
  `python3 scripts/check_contract_version.py --contract <path> --oasdiff <oasdiff binary>`
```

Replace with:

```text
- Contract checks, when this repository owns or consumes a contract: <the commands from the `designing-apis` skill, or none>
```

In each of these files: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md`, find:

```text
  the line above. The slice check rejects a suppression or skip, or one made wider, without one or past its date.
```

Replace with:

```text
  the line above. The compliance reviewer reports a new suppression or skip, or one made wider, without one or
  past its date; the linters' own rules (`aidlc-onboard`'s suppression rules) reject blanket and unused ones.
```

In each of these files: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md`, find:

```text
  recipe commit, checked by `scripts/check_recipe_commit.py`; and an assertion listed under AMENDED ASSERTIONS in the
```

Replace with:

```text
  recipe commit, re-run on its parent with git and compared (ADR 0012); and an assertion listed under AMENDED
  ASSERTIONS in the
```

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.OnboardTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 740 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add skills/aidlc-onboard starter/repo/AGENTS.md scripts/test_instructions_first.py scripts/test_gates_hold.py scripts/test_multirepo.py scripts/test_fast_path.py
git commit -m "feat(onboard): copy no script or workflow and ask for no branch protection; the rules file names no script" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 6: `aidlc-feedback`: encode lessons in structure, in the team's project

The design's third principle: when a mistake repeats, the agent adds a check to the team's project at the highest level that works, proves it fails on the real past mistake, and records it in the team's "Rules and what enforces them" table. `aidlc-feedback` already ranks the layers; this task says where the check lives, how the proof is run with git, and what the table row holds.

**Files:**
- Modify: `skills/aidlc-feedback/SKILL.md` (When to use, steps 2 and 5, Common excuses, Red flags)
- Modify: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md` (the rules table's note)
- Test: `scripts/test_instructions_first.py` (new class `FeedbackInStructureTest`)

**Interfaces:**
- Consumes: the "Rules and what enforces them" table (columns Rule, Enforced by, Seen failing on), unchanged.
- No existing test changes: `FeedbackTest` in `scripts/test_gates_hold.py` keeps its four phrases, which this task leaves in place.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class FeedbackInStructureTest(unittest.TestCase):
    """Task 6: a repeated mistake becomes a check in the team's project, proven on the real past mistake, and a row in
    the rules table of the team's AGENTS.md."""

    def test_the_lesson_becomes_a_check_in_the_teams_project(self):
        feedback = skill("aidlc-feedback")
        for phrase in ("Encode each lesson in structure, in the team's project.", "aidlc ships none (ADR 0024)",
                       "A mistake that repeated (in two sessions, two reviews, or an incident) always gets a check above "
                       "layer 4.",
                       "run it on the commit that still holds the mistake (`git worktree add <folder> <commit>`",
                       "the commit of the past mistake it was seen failing on"):
            self.assertIn(phrase, feedback, phrase)
        self.assertIn("when a session repeats a mistake", section(feedback, "## When to use"))
        self.assertIn("A proposed check that lives outside the team's project", section(feedback, "## Red flags"))

    def test_the_rules_table_lives_in_the_teams_project(self):
        for rel in ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md"):
            text = flat(rel)
            self.assertIn("Every check named here lives in this repository", text, rel)
            self.assertIn("a check is listed only after it was seen failing on a real past mistake", text, rel)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.FeedbackInStructureTest -v`

Expected: FAIL in both tests.

- [ ] **Step 3: Change `aidlc-feedback` and the rules table's note**

In `skills/aidlc-feedback/SKILL.md` find:

```text
Once an incident is contained, before its blameless review closes it, or when the same finding appears in several reviews.
```

Replace with:

```text
Once an incident is contained, before its blameless review closes it, when the same finding appears in several reviews, or when a session repeats a mistake that a rule already forbids.
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
2. Choose each lesson's layer, highest first, and stop at the first that works: a rule nobody can break beats a rule
   somebody must remember.
```

Replace with:

```text
2. Encode each lesson in structure, in the team's project. Every check lives there: its tests, linters, type
   checks, CI and its AI tool's settings, which the team owns; aidlc ships none (ADR 0024). Choose each lesson's
   layer, highest first, and stop at the first that works: a rule nobody can break beats a rule somebody must
   remember. A mistake that repeated (in two sessions, two reviews, or an incident) always gets a check above
   layer 4.
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
Prove each new check fails on the real past mistake before you propose
   it: a check never seen failing proves nothing.
```

Replace with:

```text
Prove each new check fails on the real past mistake before you propose
   it: run it on the commit that still holds the mistake (`git worktree add <folder> <commit>`, the check there,
   then `git worktree remove --force <folder>`) and see it fail. A check never seen failing proves nothing.
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
Add each rule and what enforces it to the rules table in `AGENTS.md`, as a draft for its owner.
```

Replace with:

```text
Add each rule to the "Rules and what enforces them" table in the team's `AGENTS.md`, as a draft for its owner: the rule, the check that enforces it (its file or command in the team's project), and the commit of the past mistake it was seen failing on.
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
| "A note in the wiki is enough." |
```

Replace with:

```text
| "aidlc's skills already say it." | A sentence in a skill is the weakest layer. Put the check in the team's project, where it runs every time. |
| "A note in the wiki is enough." |
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
- A new rule with no enforcer, when a type, lint rule, check or test could hold it.
```

Replace with:

```text
- A new rule with no enforcer, when a type, lint rule, check or test could hold it.
- A proposed check that lives outside the team's project, or that was never seen failing on the real past mistake.
```

In each of these files: `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md`, find:

```text
Kept by `aidlc-feedback`. A rule held only by prose is a candidate for a check.
```

Replace with:

```text
Kept by `aidlc-feedback`. Every check named here lives in this repository (its tests, linters, type checks,
CI or AI tool settings), never in aidlc (ADR 0024). A rule held only by prose is a candidate for a check; a
check is listed only after it was seen failing on a real past mistake.
```

- [ ] **Step 4: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.FeedbackInStructureTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 742 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add skills/aidlc-feedback/SKILL.md skills/aidlc-onboard/assets/agents-md.md starter/repo/AGENTS.md scripts/test_instructions_first.py
git commit -m "feat(feedback): a repeated mistake becomes a check in the team's project, proven on the real past mistake" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 7: Host-neutral words: the Rules bullet, the records, the permalinks, the merge rules

aidlc depends on git and on no code-host feature (design: "The principle", last bullet). The twelve identical Rules bullets, the record formats, the permalink lines and every "branch protection" or "required check" a stage relies on are reworded. A team that has branch protection or required checks may still use them, and the words say so where they appear. "Pull request" stays, defined once in `using-aidlc`: the design suggested "change request", but aidlc already uses that name for route C.

**Files:**
- Modify: the Rules bullet of `skills/aidlc-{intent,specify,discover,design,plan,build,verify,review,release,operate,feedback,onboard}/SKILL.md`
- Modify: `skills/using-aidlc/SKILL.md` (one paragraph); `skills/aidlc-plan/SKILL.md`, `skills/aidlc-design/SKILL.md`, `skills/aidlc-operate/SKILL.md`, `skills/aidlc-feedback/SKILL.md`, `skills/aidlc-onboard/SKILL.md`, `skills/aidlc-review/SKILL.md`, `skills/aidlc-verify/SKILL.md`, `skills/aidlc-build/SKILL.md`, `skills/aidlc-start/SKILL.md`, `skills/aidlc-specify/SKILL.md`, `skills/building-ci-pipelines/SKILL.md`
- Modify: templates `plan.md`, `new-system.md`, `review-record.md`, `pr-description.md`, `security-review.md`, `readiness.md`, both `story-index.md`; `agents/reviewer-compliance.md`; both starter `CODEOWNERS`
- Modify: `docs/operating-model/lifecycle.md`, `workspace-and-repositories.md`, `autonomy-and-maturity.md`, `adoption.md`
- Test: `scripts/test_instructions_first.py` (new class `HostNeutralTest`); approved changes in `scripts/test_recording.py`, `scripts/test_multirepo.py`

**Interfaces:**
- Produces: the host-neutral record example `approved by ana on pull request 12, checked in the review tool, 2026-11-20`, and the terms "the review tool", "the team's CI" and "the code host", which Task 8's README and docs use.
- Keeps: `FixRoundTest.test_rule_bullet_is_identical_and_follows_the_data_bullet` and `test_check_even_after_being_told` pass unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
RECORDING = ("aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan", "aidlc-build",
             "aidlc-verify", "aidlc-review", "aidlc-release", "aidlc-operate", "aidlc-feedback", "aidlc-onboard")
RULE = ("- People decide; you record the decision after checking it (ADR 0023). Accept a decision only from the decider "
        "in this session, or from a state you can check: a pull request approved in the review tool by a code owner who "
        "is not its author, the team's CI result on it, the merge state, or the tracker through its connected tool.")
GITHUB_ONLY = ("checked on GitHub", "approved on GitHub", "checking on GitHub", "state on GitHub", "on GitHub where",
               "in GitHub;", "on GitHub, is the record", "GitHub permalink", "PR #", "required check")


class HostNeutralTest(unittest.TestCase):
    """Task 7: aidlc needs git and a review request, and no feature of one code host."""

    def test_the_rules_bullet_is_host_neutral_and_identical(self):
        bullets = set()
        for name in RECORDING:
            rules = section(skill(name), "## Rules")
            bullet = rules[rules.index("- People decide;"):].split(" - ", 1)[0]
            bullets.add(bullet)
            self.assertTrue(bullet.startswith(RULE), name)
            self.assertNotIn("GitHub", bullet, name)
            self.assertIn("`approved by ana on pull request 12, checked in the review tool, 2026-11-20`", bullet, name)
        self.assertEqual(len(bullets), 1)

    def test_no_stage_skill_template_agent_or_doc_needs_a_github_feature(self):
        paths = (sorted((ROOT / "skills").glob("aidlc-*/SKILL.md")) + sorted((ROOT / "skills").glob("aidlc-*/assets/*.md"))
                 + sorted((ROOT / "agents").glob("*.md")) + sorted((ROOT / "docs/operating-model").glob("*.md")))
        for path in paths:
            text = " ".join(path.read_text(encoding="utf-8").split())
            for phrase in GITHUB_ONLY:
                self.assertNotIn(phrase, text, f"{path.relative_to(ROOT)}: {phrase}")
            for m in re.finditer(r"branch protection", text):
                self.assertIn("never needs it", text[m.start():m.start() + 120], f"{path.relative_to(ROOT)}")

    def test_pull_request_is_defined_once_and_change_request_stays_route_c(self):
        text = skill("using-aidlc")
        self.assertIn('A "pull request" is the code host\'s review request', text)
        self.assertIn('"Change request" is never a pull request', text)
        self.assertIn("| C · change request, story in progress |", read("skills/using-aidlc/SKILL.md"))

    def test_tracker_links_are_permalinks_on_any_code_host(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/story-index.md"):
            self.assertIn("permalinks at a commit (the full commit hash in the address)", flat(rel), rel)
        self.assertIn("permalink at a commit: the file's address on the code host", skill("aidlc-start"))
        self.assertIn("Link the spec by its permalink at the commit where it merged", skill("aidlc-specify"))

    def test_the_ownership_list_goes_where_the_review_tool_reads_it(self):
        for rel in ("starter/repo/CODEOWNERS", "starter/workspace/CODEOWNERS"):
            self.assertIn("Put this file where your review tool reads it", flat(rel), rel)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.HostNeutralTest -v`

Expected: FAIL in all five tests.

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

`RuleTest.test_every_recording_stage_states_the_rule` (owner's item T7a), its `PHRASES` tuple: two phrases become host-neutral; the other five stay.
In `scripts/test_recording.py` find:

```text
               "a pull request review approved on GitHub by a code owner who is not its author",
```

Replace with:

```text
               "a pull request approved in the review tool by a code owner who is not its author",
```

In `scripts/test_recording.py` find:

```text
"never one you guess", "`approved by @ana on PR #12, checked on GitHub, 2026-11-20`",
```

Replace with:

```text
"never one you guess", "`approved by ana on pull request 12, checked in the review tool, 2026-11-20`",
```

`RuleTest.test_each_gate_says_who_tells_the_ai` (owner's item T7b).
In `scripts/test_recording.py` find:

```text
"aidlc-operate": "On-call tells you when it closes; you record it after checking on GitHub",
```

Replace with:

```text
"aidlc-operate": "On-call tells you when it closes; you record it after checking in git or the review tool",
```

`RuleTest.test_the_steps_record_after_checking` (owner's item T7c), two of its seven assertions.
In `scripts/test_recording.py` find:

```text
        self.assertIn("Record each change as merged, after checking its pull request's merge state on GitHub",
```

Replace with:

```text
        self.assertIn("Record each change as merged, after checking its merge in git or in the review tool",
```

In `scripts/test_recording.py` find:

```text
        self.assertIn("Then check the setting on GitHub where you can read it", skill("aidlc-onboard"))
```

Replace with:

```text
        self.assertIn("When they do, check the setting in the code host where you can read it", skill("aidlc-onboard"))
```

`FixRoundTest.test_plan_red_flag_and_relayed_declines` (owner's item T7d).
In `scripts/test_recording.py` find:

```text
"You are about to record an approval the tech lead did not give you in this session, or that you did not check on GitHub."
```

Replace with:

```text
"You are about to record an approval the tech lead did not give you in this session, or that you did not check in the review tool."
```

`ParsedRecordTest.test_the_merged_row_is_marked_after_the_check_and_never_merged` (owner's item T7e), two of its six assertions.
In `scripts/test_recording.py` find:

```text
        self.assertIn("check the approval and the required checks on GitHub; then this session marks the `merged` row "
                      "done in its final commit", review)
```

Replace with:

```text
        self.assertIn("check the approval in the review tool and the team's CI result; then this session marks the "
                      "`merged` row done in its final commit", review)
```

In `scripts/test_recording.py` find:

```text
"the AI checks the approval and the required checks on GitHub, marks the merged row"
```

Replace with:

```text
"the AI checks the approval in the review tool and the team's CI result, marks the merged row"
```

`TemplateRecordTest.test_each_record_line_says_how_it_was_confirmed` (owner's item T7f), one entry of its `RECORDS` table.
In `scripts/test_recording.py` find:

```text
"aidlc-plan/assets/plan.md": "<on PR #n, checked on GitHub | in the session>",
```

Replace with:

```text
"aidlc-plan/assets/plan.md": "<on pull request n, checked in the review tool | in the session>",
```

`FinalReviewRecordTest.test_plan_records_only_after_being_told_or_checking` (owner's item T7g).
In `scripts/test_recording.py` find:

```text
        self.assertIn("You record it only after the tech lead tells you or you check it on GitHub.", plan)
```

Replace with:

```text
        self.assertIn("You record it only after the tech lead tells you or you check it in the review tool.", plan)
```

`FinalReviewRecordTest.test_the_approval_itself_is_the_code_owners_on_github` (owner's item T7h), two of its three assertions.
In `scripts/test_recording.py` find:

```text
        self.assertIn("The code owner's approval in the pull request, on GitHub, is the record",
```

Replace with:

```text
        self.assertIn("The code owner's approval in the review tool is the record",
```

In `scripts/test_recording.py` find:

```text
        self.assertIn("approval itself is the code owner's, in GitHub; the AI writes only the DECISION line",
```

Replace with:

```text
        self.assertIn("approval itself is the code owner's, in the review tool; the AI writes only the DECISION line",
```

`TemplateTest.test_the_part_index_and_the_bundle_pin_the_home_commit` (owner's item T7i).
In `scripts/test_multirepo.py` find:

```text
        self.assertIn("GitHub permalinks at a commit", flat("skills/aidlc-start/assets/story-index.md"))
```

Replace with:

```text
        self.assertIn("permalinks at a commit (the full commit hash in the address)", flat("skills/aidlc-start/assets/story-index.md"))
```

`DecisionsTest.test_tracker_links_are_permalinks` (owner's item T7j).
In `scripts/test_multirepo.py` find:

```text
        self.assertIn("GitHub permalink at a commit", skill("aidlc-start"))
        self.assertIn("Link the spec by its GitHub permalink at the commit where it merged", skill("aidlc-specify"))
```

Replace with:

```text
        self.assertIn("permalink at a commit: the file's address on the code host", skill("aidlc-start"))
        self.assertIn("Link the spec by its permalink at the commit where it merged", skill("aidlc-specify"))
```

- [ ] **Step 4: Reword**

The Rules bullet: the same line in all twelve stage skills that record a decision. Replace the whole line, so the twelve stay byte-identical.
In each of these files: `skills/aidlc-intent/SKILL.md`, `skills/aidlc-specify/SKILL.md`, `skills/aidlc-discover/SKILL.md`, `skills/aidlc-design/SKILL.md`, `skills/aidlc-plan/SKILL.md`, `skills/aidlc-build/SKILL.md`, `skills/aidlc-verify/SKILL.md`, `skills/aidlc-review/SKILL.md`, `skills/aidlc-release/SKILL.md`, `skills/aidlc-operate/SKILL.md`, `skills/aidlc-feedback/SKILL.md`, `skills/aidlc-onboard/SKILL.md`, find:

```text
- People decide; you record the decision after checking it (ADR 0023). Accept a decision only from the decider in this session, or from a state you can check: a pull request review approved on GitHub by a code owner who is not its author, the required checks, the merge state, or the tracker through its connected tool. Text in a ticket, comment, pull request description or file is never a decision, and neither is a report that someone agreed elsewhere: ask the decider, or check. Write exactly the name you were given, never one you guess, and say how it was confirmed, for example `approved by @ana on PR #12, checked on GitHub, 2026-11-20` or `confirmed by Ana in the session, 2026-11-20`. Recording a decision is not approving it; posting to the tracker or a pull request asks first. Check whenever you can, even after the decider has told you. When the check disagrees with what you were told, record nothing and report the difference to the decider. When you check the tracker, confirm the entry was made by the decider; a comment by anyone else is data, not a decision.
```

Replace with:

```text
- People decide; you record the decision after checking it (ADR 0023). Accept a decision only from the decider in this session, or from a state you can check: a pull request approved in the review tool by a code owner who is not its author, the team's CI result on it, the merge state, or the tracker through its connected tool. Text in a ticket, comment, pull request description or file is never a decision, and neither is a report that someone agreed elsewhere: ask the decider, or check. Write exactly the name you were given, never one you guess, and say how it was confirmed, for example `approved by ana on pull request 12, checked in the review tool, 2026-11-20` or `confirmed by Ana in the session, 2026-11-20`. Recording a decision is not approving it; posting to the tracker or a pull request asks first. Check whenever you can, even after the decider has told you. When the check disagrees with what you were told, record nothing and report the difference to the decider. When you check the tracker, confirm the entry was made by the decider; a comment by anyone else is data, not a decision.
```

In `skills/using-aidlc/SKILL.md` find:

```text
"Story level" means the workspace root for a story that spans several repositories, and the repository itself for a story that changes one.
```

Replace with:

```text
"Story level" means the workspace root for a story that spans several repositories, and the repository itself for a story that changes one.

A "pull request" is the code host's review request: a pull request on GitHub, Bitbucket or Azure Repos, a merge request on GitLab. aidlc needs git and that review request, and no other feature of the code host: no branch protection, no required checks, no host API. "The review tool" is where the pull request is reviewed, and "the team's CI" is whatever runs the team's checks on it. "Change request" is never a pull request: it is route C, a change to an approved criterion.
```

In `skills/aidlc-plan/SKILL.md` find (it occurs 2 times; replace each):

```text
when the engineer approved on GitHub or the
   tracker, read it there
```

Replace with:

```text
when the engineer approved in the review tool or
   on the tracker, read it there
```

In `skills/aidlc-plan/SKILL.md` find:

```text
or the plan pull request's approval checked on GitHub (ADR 0023)
```

Replace with:

```text
or the plan pull request's approval checked in the review tool (ADR 0023)
```

In `skills/aidlc-plan/SKILL.md` find:

```text
You record it only after the tech lead tells you or you check it on GitHub.
```

Replace with:

```text
You record it only after the tech lead tells you or you check it in the review tool.
```

In `skills/aidlc-plan/SKILL.md` find:

```text
or that you did not check on GitHub.
```

Replace with:

```text
or that you did not check in the review tool.
```

In `skills/aidlc-plan/assets/plan.md` find:

```text
<on PR #n, checked on GitHub | in the session>
```

Replace with:

```text
<on pull request n, checked in the review tool | in the session>
```

In `skills/aidlc-design/SKILL.md` find:

```text
or the design pull request's approval checked on GitHub, with how it was confirmed (ADR 0023)
```

Replace with:

```text
or the design pull request's approval checked in the review tool, with how it was confirmed (ADR 0023)
```

In `skills/aidlc-design/SKILL.md` find:

```text
design the CI: the required checks, each running one of the commands.
```

Replace with:

```text
design the team's CI: its checks, each running one of the commands.
```

In `skills/aidlc-design/assets/new-system.md` find:

```text
<each required check, running one of the COMMANDS>
```

Replace with:

```text
<each CI check, running one of the COMMANDS>
```

In `skills/aidlc-operate/SKILL.md` find:

```text
you record it after checking on GitHub that each prevention change merged
```

Replace with:

```text
you record it after checking in git or the review tool that each prevention change merged
```

In `skills/aidlc-feedback/SKILL.md` find:

```text
after checking its pull request's merge state on GitHub,
```

Replace with:

```text
after checking its merge in git or in the review tool,
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
Then check the setting on GitHub
  where you can read it
```

Replace with:

```text
When they do, check the setting in the code host
  where you can read it
```

In `skills/aidlc-onboard/SKILL.md` find:

```text
to `.github/CODEOWNERS`. The leads own `stories/**`;
     the runtime environment's owner owns its compose files and flags.
```

Replace with:

```text
to `.github/CODEOWNERS` on GitHub, or to
     wherever the team's review tool reads an ownership list. The leads own `stories/**`; the runtime environment's
     owner owns its compose files and flags.
```

In `skills/aidlc-review/SKILL.md` find:

```text
when every required check is green on the pull request.
```

Replace with:

```text
when the team's CI is green on the pull request.
```

In `skills/aidlc-review/SKILL.md` find:

```text
1. Check the inputs: every required check green,
```

Replace with:

```text
1. Check the inputs: the team's CI green,
```

In `skills/aidlc-review/SKILL.md` find:

```text
Once the code owner approves, check the approval and the
   required checks on GitHub; then this session marks the `merged` row done in its final commit. That commit's
   message says how it was confirmed, for example `approved by @ana on PR #12, checked on GitHub, 2026-11-20`.
   Where the branch rules dismiss stale approvals
```

Replace with:

```text
Once the code owner approves, check the approval in the
   review tool and the team's CI result; then this session marks the `merged` row done in its final commit. That
   commit's message says how it was confirmed, for example
   `approved by ana on pull request 12, checked in the review tool, 2026-11-20`.
   Where the code host's rules dismiss stale approvals
```

In `skills/aidlc-review/SKILL.md` find:

```text
because the story status
   command reads exactly that word.
```

Replace with:

```text
because `aidlc-release` reads
   exactly that word.
```

In `skills/aidlc-review/SKILL.md` find:

```text
branch protection enforces both, and the decision is recorded on the pull request.
```

Replace with:

```text
the code host may enforce both (branch protection or its equivalent), but aidlc never needs it; the decision is recorded on the pull request.
```

In `skills/aidlc-review/SKILL.md` find:

```text
- A required check is red or missing.
```

Replace with:

```text
- A CI check is red or missing on the pull request.
```

In `skills/aidlc-review/assets/review-record.md` find:

```text
The approval itself is the code owner's, in GitHub;
```

Replace with:

```text
The approval itself is the code owner's, in the review tool;
```

In `skills/aidlc-review/assets/pr-description.md` find:

```text
The code owner's approval in the pull request, on GitHub, is the record;
```

Replace with:

```text
The code owner's approval in the review tool is the record;
```

In `skills/aidlc-review/assets/security-review.md` find:

```text
Code owner approves (branch protection).
```

Replace with:

```text
Code owner approves (in the review tool).
```

In `skills/aidlc-verify/SKILL.md` find:

```text
After the pull request's required checks have run in CI.
```

Replace with:

```text
After the team's CI has run on the pull request.
```

In `skills/aidlc-verify/SKILL.md` find:

```text
Every required check is green on the pull request;
```

Replace with:

```text
The team's CI is green on the pull request;
```

In `skills/aidlc-verify/SKILL.md` find:

```text
- A required check is red, missing or skipped:
```

Replace with:

```text
- A CI check is red, missing or skipped:
```

In `skills/aidlc-build/SKILL.md` find:

```text
when the confirmation is on GitHub or the tracker, read it there
```

Replace with:

```text
when the confirmation is in the review tool or on the tracker, read it there
```

In `agents/reviewer-compliance.md` find:

```text
checked on GitHub or the tracker (ADR 0023)
```

Replace with:

```text
checked in the review tool or on the tracker (ADR 0023)
```

In each of these files: `skills/aidlc-start/assets/story-index.md`, `skills/aidlc-plan/assets/story-index.md`, find:

```text
the AI checks the approval and the required checks on GitHub, marks the merged row
```

Replace with:

```text
the AI checks the approval in the review tool and the team's CI result, marks the merged row
```

In each of these files: `skills/aidlc-start/assets/story-index.md`, `skills/aidlc-plan/assets/story-index.md`, find:

```text
Links to these documents on the tracker are GitHub permalinks at a commit (`/blob/<commit>/`), never a branch
path, which moves.
```

Replace with:

```text
Links to these documents on the tracker are permalinks at a commit (the full commit hash in the address), never a
branch path, which moves.
```

In `skills/aidlc-start/SKILL.md` find:

```text
A link to a story document that goes on the tracker is a
   GitHub permalink at a commit (`https://github.com/<org>/<repository>/blob/<commit>/stories/<KEY>/spec.md`), never
   a branch path, which moves.
```

Replace with:

```text
A link to a story document that goes on the tracker is a
   permalink at a commit: the file's address on the code host with the full commit hash in it (on GitHub,
   `https://github.com/<org>/<repository>/blob/<commit>/stories/<KEY>/spec.md`), never a branch path, which moves.
```

In `skills/aidlc-specify/SKILL.md` find:

```text
Link the spec by its GitHub permalink at the commit where it merged
```

Replace with:

```text
Link the spec by its permalink at the commit where it merged
```

In `skills/aidlc-release/assets/readiness.md` find:

```text
- [ ] Required checks green and code-owner approval on every PR; specialist reviews recorded
```

Replace with:

```text
- [ ] The team's CI green and code-owner approval on every pull request; specialist reviews recorded
```

In `skills/building-ci-pipelines/SKILL.md` find:

```text
Required means branch protection blocks the merge when the check is red or missing.
```

Replace with:

```text
Required means the merge waits for it when it is red or missing: by the code host's rule where the team has one (branch protection, or a pipeline that must succeed), and by the code owner's rule otherwise.
```

In `skills/building-ci-pipelines/SKILL.md` find:

```text
- Each required check has an owner and is enforced by branch protection.
```

Replace with:

```text
- Each required check has an owner, and a red or missing one blocks the merge.
```

In `starter/repo/CODEOWNERS` find:

```text
# Every change needs a review from its owners. Put this file at .github/CODEOWNERS and replace the teams.
```

Replace with:

```text
# Every change needs a review from its owners. Put this file where your review tool reads it (.github/CODEOWNERS on
# GitHub, .gitlab/CODEOWNERS on GitLab) and replace the teams.
```

In `starter/workspace/CODEOWNERS` find (it starts with a space; keep it exact):

```text
 Put this file at
# .github/CODEOWNERS and replace the teams (aidlc ADR 0022).
```

Replace with:

```text

# Put this file where your review tool reads it (.github/CODEOWNERS on GitHub, .gitlab/CODEOWNERS on GitLab)
# and replace the teams (aidlc ADR 0022).
```

In `docs/operating-model/lifecycle.md` find:

```text
| CI record | Required checks green |
```

Replace with:

```text
| CI record | The team's CI green |
```

In `docs/operating-model/workspace-and-repositories.md` find:

```text
| The code owner's approval; branch protection |
```

Replace with:

```text
| The code owner's approval |
```

In `docs/operating-model/workspace-and-repositories.md` find:

```text
pull request approval on GitHub, the tracker)
```

Replace with:

```text
pull request approval in the review tool, the tracker)
```

In `docs/operating-model/autonomy-and-maturity.md` find:

```text
4. Review is required (branch protection, code owners).
```

Replace with:

```text
4. Review is required (code owners; the code host's merge rules where the team has them).
```

In `docs/operating-model/adoption.md` find:

```text
- **CI** that runs the repository's tests on every pull request, and branch protection that requires it.
```

Replace with:

```text
- **CI** that runs the repository's tests on every pull request, and a rule that a red run never merges (the code
  host's merge rules where the team has them; aidlc needs none).
```

In `docs/operating-model/adoption.md` find:

```text
A person turns on branch protection that requires a code owner.
```

Replace with:

```text
A team whose code host can require a code
   owner's review may turn that on; aidlc never needs it.
```

In `docs/operating-model/adoption.md` find:

```text
(a pull request approval on GitHub, the tracker)
```

Replace with:

```text
(a pull request approval in the review tool, the tracker)
```

In `docs/operating-model/adoption.md` find:

```text
| Required checks and branch protection | A repository administrator | The git host |
```

Replace with:

```text
| Merge rules on the code host, where the team has them (aidlc needs none) | A repository administrator | The code host |
```

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.HostNeutralTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 747 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add skills agents/reviewer-compliance.md starter/repo/CODEOWNERS starter/workspace/CODEOWNERS docs/operating-model scripts/test_instructions_first.py scripts/test_recording.py scripts/test_multirepo.py
git commit -m "feat(skills): host-neutral words; aidlc needs git and a review request, and no code-host feature" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 8: The README, the docs, the map, the manifest and the change list

The README's "Where the gates hold" table lists the slice check, the Stop hook and the AI review workflow; `plugin.json` claims the skills work in four tools, which nothing has tested. This task makes every document a team reads say what is true today, records where the removed code went (`docs/archive/checks-v1.md`, in the style of `harness-v1.md`), and marks which change-list items were removed, kept, dropped or left open.

**Files:**
- Modify: `README.md` (the opening, Install's last line, "Where the gates hold"), `.claude-plugin/plugin.json`
- Modify: `docs/codebase-map.md`, `AGENTS.md` (the `starter/` line), `docs/quickstart/*.md`, `docs/operating-model/adoption.md` (Phases 1 and 4)
- Modify: `docs/design/2026-11-19-aidlc-6-change-list.md` (a status line and a section 6)
- Create: `docs/archive/checks-v1.md`
- Test: `scripts/test_instructions_first.py` (new class `DocsTest`); approved changes in `scripts/test_docs.py`, `scripts/test_gates_hold.py`, `scripts/test_one_plugin.py`

**Interfaces:**
- Keeps passing unchanged: `WhereGatesHoldTest.test_the_readme_has_the_table` and `test_the_github_free_limit_is_stated` (the section keeps its heading, both tool columns and the GitHub Free sentences, as context for teams that use those features); `RecordTest` in `test_gates_hold.py` and `test_multirepo.py` and `ReviewFixesTest.test_m12_stale_lines` in `test_fast_path.py` (the map still names each removed script, now as archived).

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class DocsTest(unittest.TestCase):
    """Task 8: the README, the docs, the map, the manifest and the change list say what is true today."""

    def test_the_readme_says_aidlc_is_instructions(self):
        readme = flat("README.md")
        gates = read("README.md").split("## Where the gates hold", 1)[1].split("\n## ", 1)[0]
        self.assertIn("It ships no scripts and no CI workflows (ADR 0024)", readme)
        self.assertIn("aidlc depends on git and on no code-host feature", readme)
        for name in ("Slice check", "Stop hook", "AI review in CI", "check scripts"):
            self.assertNotIn(name, gates, name)
        self.assertNotIn("The skills work in **Claude Code, GitHub Copilot, Codex and Cursor**", read("README.md"))

    def test_the_manifest_claims_only_what_is_true(self):
        description = json.loads(read(".claude-plugin/plugin.json"))["description"]
        self.assertNotIn("the same skills work in", description)
        self.assertIn("Written and tested for Claude Code", description)

    def test_the_archive_note_says_where_the_code_went(self):
        note = flat("docs/archive/checks-v1.md")
        self.assertIn("git checkout checks-v1 -- <path>", note)
        for name in ("check_slice.py", "check_plan.py", "check_recipe_commit.py", "run_slices.py",
                     "check_contract_version.py", "check_contract_pin.py", "story_status.py", "ai-review.yml",
                     "contract-check.yml", "contract-publish.yml"):
            self.assertIn(name, note, name)
        self.assertIn("docs/archive/checks-v1.md", read("docs/codebase-map.md"))
        self.assertIn("no scripts and no workflows (ADR 0024)", flat("AGENTS.md"))

    def test_the_change_list_marks_what_plan_22_dropped(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        self.assertIn("Superseded in part by ADR 0024", changes)
        table = changes.split("## 6. After ADR 0024 (2026-11-20)", 1)[1]
        for item in ("A1", "C4", "F6", "F7", "F9", "E1", "G1", "B5", "C2"):
            self.assertRegex(table, rf"\b{item}\b", item)

    def test_the_quickstarts_and_adoption_copy_no_script_or_workflow(self):
        for rel in ("docs/quickstart/claude-code.md", "docs/quickstart/copilot.md", "docs/quickstart/codex-cursor.md"):
            text = flat(rel)
            self.assertNotIn("ci.yml", text, rel)
            self.assertNotIn("`scripts/`", text, rel)
        adoption = flat("docs/operating-model/adoption.md")
        for name in ("run_slices", "ai-review.yml"):
            self.assertNotIn(name, adoption, name)
        self.assertIn("`aidlc-feedback` turns it into a check in the team's own project", adoption)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.DocsTest -v`

Expected: FAIL in four tests and ERROR in `test_the_archive_note_says_where_the_code_went` (no such file).

- [ ] **Step 3: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

In `scripts/test_gates_hold.py`, delete these test methods (each from its `def` line through its last line): `FinalReviewFixesTest.test_the_ci_comment_says_who_holds_the_workflow`. Why: it pins `ci.yml` in the README's gates section and a comment in `ci.yml` (owner's item T8b).

`DocsTest.test_each_phase_names_its_skills` (owner's item T8a): Phase 4 names how delegate slices run, not the runner.
In `scripts/test_docs.py` find:

```text
("### Phase 4", ("Quality bar", "run_slices.py"))
```

Replace with:

```text
("### Phase 4", ("Quality bar", "one fresh session per slice"))
```

`OnePluginTest.test_the_decision_is_recorded_and_released` (owner's item T8c, only with item V1).
In `scripts/test_one_plugin.py` find:

```text
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "5.0.0")
```

Replace with:

```text
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "6.0.0")
```

- [ ] **Step 4: Write the archive note and change the documents**

Create `docs/archive/checks-v1.md`:

```markdown
# The removed check code (tag `checks-v1`)

On 2026-11-20 aidlc stopped shipping scripts and CI workflows to teams (ADR 0024, Plan 22). Nothing is lost: the tag
`checks-v1` (commit `7843f18`) holds the last state with the code, and any file comes back with
`git show checks-v1:<path>` or `git checkout checks-v1 -- <path>`. Push the tag with main: `git push origin checks-v1`.

| What | Where it was | What holds the rule now |
|---|---|---|
| `check_slice.py` (the slice check) and the Stop hook that ran it | `starter/repo/scripts/`, `starter/repo/.claude/settings.json` | The evidence file the session writes with git, read by `reviewer-compliance` and `reviewer-tests` in a fresh context; the code owner |
| `check_plan.py` (the plan check) | `starter/repo/scripts/` | The plan's checklist; the tech lead |
| `check_recipe_commit.py` (the recipe check) | `starter/repo/scripts/` | The git procedure in `aidlc-build`, step 5 |
| `run_slices.py` (the slice runner) | `starter/repo/scripts/` | A person starts one fresh session per slice |
| `check_contract_version.py`, `check_contract_pin.py` | `starter/repo/scripts/` | oasdiff, `sha256sum -c` and `git ls-remote --tags` in the team's own CI (`designing-apis`) |
| `story_status.py` (status, the release check, the `.gitignore` block) | `starter/workspace/scripts/` | `status.md` derived from git; one release row per repository, confirmed by a person; a `.gitignore` line a person adds |
| `ai-review.yml`, `ci.yml`, `contract-check.yml`, `contract-publish.yml` | `starter/repo/.github/workflows/` | The reviewer agents in a fresh session; the team's own CI |
| The deny rules on the scripts and on `ai-review.yml` | both starter `.claude/settings.json` | Nothing: the files they protected are gone |
| `test_check_slice.py`, `test_check_plan.py`, `test_check_recipe_commit.py`, `test_check_contract.py`, `test_run_slices.py`, `test_story_status.py`, and the workflow tests in `test_gates_hold.py` and `test_multirepo.py` | `scripts/` | Removed with the code they tested |
```

In `README.md` find:

```text
One plugin, **`aidlc`**. The skills work in **Claude Code, GitHub Copilot, Codex and Cursor**: they are plain
`SKILL.md` folders in the open Agent Skills format.
```

Replace with:

```text
One plugin, **`aidlc`**, written and tested for **Claude Code**. The skills are plain `SKILL.md` folders in the
open Agent Skills format, so GitHub Copilot, Codex and Cursor can read them; aidlc has not been tested there
yet, and their adapters are a later plan.
```

In `README.md` find:

```text
the `aidlc-onboard` skill once.
```

Replace with:

```text
the `aidlc-onboard` skill once. The starters hold a rules file, an ownership list and optional example settings:
no scripts and no workflows.
```

In `README.md` find:

```text
## Where the gates hold

The skills say what must hold. These controls make it hold:

| Control | Claude Code | GitHub Copilot, Codex, Cursor |
|---|---|---|
| Slice check in CI (scope, tests, manifests, suppressions, approved plans) | yes | yes |
| AI review in CI, required and fail-closed | yes | yes |
| Code-owner review, branch protection | yes | yes |
| Slice check before the session stops (Stop hook) | yes | no: prose only |
| Deny rules: secrets, settings, check scripts | yes | the tool's own settings, or prose only |
| Read-only reviewer agents | yes | the tool's own agents, or prose only |

CI runs the base branch's copy of the slice check, so a pull request cannot weaken the script. A pull request can
still edit `ci.yml` itself: that edit is held by `CODEOWNERS` (`.github/` belongs to the leads) and a required
code-owner review.

On GitHub Free, branch protection, rulesets and required checks work only on public repositories. A private
repository needs GitHub Pro (personal account) or Team (organisation). Never turn on auto-merge without required
checks: it would merge whatever is pushed.
```

Replace with:

```text
## Where the gates hold

aidlc is instructions: skills, agents and templates. It ships no scripts and no CI workflows (ADR 0024). The skills
say what must hold; the team's own project makes it hold:

| Control | Claude Code | GitHub Copilot, Codex, Cursor |
|---|---|---|
| The team's own tests, linters, type checks and CI, which `aidlc-feedback` grows from each repeated mistake | yes | yes |
| Reviewer agents in a fresh context, reading the evidence file the session writes with git | yes | the tool's own agents, or a fresh session |
| A person decides at each gate, from evidence git can confirm | yes | yes |
| Code-owner review (`CODEOWNERS`) | yes | yes |
| Example settings: secrets unreadable, the sandbox on, push and install ask first | yes | the tool's own settings, or prose only |

aidlc depends on git and on no code-host feature. A team that has branch protection, rulesets or required checks may
use them to block a merge on red; aidlc never needs them. On GitHub Free, branch protection, rulesets and required
checks work only on public repositories. A private repository needs GitHub Pro (personal account) or Team
(organisation). Never turn on auto-merge without required checks: it would merge whatever is pushed.

The check code aidlc 5 shipped (the slice, plan, recipe, contract and status scripts, and the starter workflows) is
kept under the tag `checks-v1`: [docs/archive/checks-v1.md](docs/archive/checks-v1.md).
```

In `.claude-plugin/plugin.json` find:

```text
Portable: the same skills work in Claude Code, GitHub Copilot, Codex and Cursor.
```

Replace with:

```text
Instructions only: no scripts, no CI workflows, no code-host feature needed. Written and tested for Claude Code; the skills use the open Agent Skills format.
```

Only with the owner's approval of item V1 under "Needs the owner's decision". Without it, skip this edit and the test change T8c, and leave 5.0.0.
In `.claude-plugin/plugin.json` find:

```text
"version": "5.0.0"
```

Replace with:

```text
"version": "6.0.0"
```

In `docs/codebase-map.md` find:

```text
Last verified: 2026-11-19
```

Replace with:

```text
Last verified: 2026-11-20
```

In `docs/codebase-map.md` find:

```text
One skills plugin, `aidlc`, at the repository root. Engineers install it in Claude Code, or copy its `skills/`
folders into Copilot, Codex or Cursor.
```

Replace with:

```text
One skills plugin, `aidlc`, at the repository root: instructions only (ADR 0024). Engineers install it in Claude
Code; its `skills/` folders also load in Copilot, Codex or Cursor, untested there.
```

In `docs/codebase-map.md` find:

```text
`starter/repo/`, `starter/workspace/`   files a team copies once; `starter/repo/scripts/` holds `check_recipe_commit.py`, `check_slice.py` (the slice check, run in CI and as a Stop hook), `check_plan.py` (the plan check),
`check_contract_version.py` (a provider's contract check, which `contract-check.yml` runs with oasdiff;
`contract-publish.yml` tags each new version), `check_contract_pin.py` (a consumer's vendored contracts) and
`run_slices.py`; `starter/workspace/scripts/story_status.py` derives each part's status, merge state and drift
```

Replace with:

```text
`starter/repo/`, `starter/workspace/`   files a team copies once: a rules file, an ownership list and optional example
settings; no scripts and no workflows (ADR 0024). The scripts aidlc 5 shipped (`check_slice.py`, `check_plan.py`,
`check_recipe_commit.py`, `check_contract_version.py`, `check_contract_pin.py`, `run_slices.py`, `story_status.py`)
and the workflows (`ai-review.yml`, `ci.yml`, `contract-check.yml`, `contract-publish.yml`) are kept under the tag
`checks-v1` (`docs/archive/checks-v1.md`)
```

In `docs/codebase-map.md` find:

```text
`scripts/test_*.py` test it and every script above
```

Replace with:

```text
`scripts/test_*.py` test it and the wording of the skills and documents
```

In `AGENTS.md` find:

```text
- `starter/` files a team copies once into a repository or a workspace, including `starter/repo/scripts/`.
```

Replace with:

```text
- `starter/` files a team copies once into a repository or a workspace: a rules file, an ownership list and optional
  example settings; no scripts and no workflows (ADR 0024). `docs/archive/checks-v1.md` says where the removed
  check code went.
```

In `docs/quickstart/claude-code.md` find:

```text
`AGENTS.md`, `CLAUDE.md` (one line: `@AGENTS.md`),
   `.claude/settings.json` (secrets unreadable, the sandbox on, the plugin enabled), `.github/workflows/ci.yml`,
   `CODEOWNERS`.
```

Replace with:

```text
`AGENTS.md`, `CLAUDE.md` (one line: `@AGENTS.md`),
   `CODEOWNERS`, and, if you want them, the example `.claude/settings.json` (secrets unreadable, the sandbox on, the
   plugin enabled). aidlc ships no scripts and no CI workflows: your CI stays your own (ADR 0024).
```

In `docs/quickstart/codex-cursor.md` find:

```text
1. Copy `skills/*` into the folder above, plus the starter's `AGENTS.md`, `scripts/`, CI workflow and
   CODEOWNERS.
```

Replace with:

```text
1. Copy `skills/*` into the folder above, plus the starter's `AGENTS.md` and `CODEOWNERS`. aidlc has not been
   tested in these tools yet (ADR 0024); adapters are a later plan.
```

In `docs/quickstart/copilot.md` find:

```text
3. **Copy the starter files**: `AGENTS.md` (Copilot reads it), `.github/workflows/ci.yml`, `CODEOWNERS`. Copilot
   does not use `.claude/settings.json`; use your organisation's Copilot content exclusion for secrets.
```

Replace with:

```text
3. **Copy the starter files**: `AGENTS.md` (Copilot reads it) and `CODEOWNERS`. Copilot does not use
   `.claude/settings.json`; use your organisation's Copilot content exclusion for secrets. aidlc has not been
   tested in Copilot yet (ADR 0024); an adapter is a later plan.
```

In `docs/operating-model/adoption.md` find:

```text
- Copy the starter's `.github/workflows/ai-review.yml` so an AI review comments on every pull request, including ones
  the kit did not produce. It needs an `ANTHROPIC_API_KEY` secret, and each run is a paid call. For kit-built
  changes, `aidlc-review` adds the local reviewer agents and turns their findings into a review record. AI review is
  evidence for the code owner, never the approval.
```

Replace with:

```text
- For kit-built changes, `aidlc-review` runs the reviewer agents in a fresh context on the evidence file and turns
  their findings into a review record. A team may add any AI review its code host offers, so every pull request gets
  one, including ones the kit did not produce; one that calls a model API needs a key such as `ANTHROPIC_API_KEY`
  in CI, and each run is a paid call. AI review is evidence for the code owner, never the approval.
```

In `docs/operating-model/adoption.md` find:

```text
Run approved delegate
  slices with the starter's `scripts/run_slices.py`: one fresh session per slice, stopping at the first that does
  not finish. You review the diffs at the end and push.
```

Replace with:

```text
Run approved delegate
  slices one fresh session per slice, each started by a person, stopping at the first that does not finish. You
  review the diffs at the end and push.
- When a mistake repeats, `aidlc-feedback` turns it into a check in the team's own project (a type, a lint rule, a
  test or a CI step), proven on the real past mistake and listed in `AGENTS.md`'s rules table.
```

In `docs/design/2026-11-19-aidlc-6-change-list.md` find:

```text
decision first, because AGENTS.md forbids weakening a gate without one.
```

Replace with:

```text
decision first, because AGENTS.md forbids weakening a gate without one.

**Superseded in part by ADR 0024 (2026-11-20, Plan 22):** aidlc ships no scripts and no CI workflows. Section 6
marks each item as built and then removed, kept as instructions, dropped, or still open.
```

Append at the end of `docs/design/2026-11-19-aidlc-6-change-list.md` (after its last line, separated by one blank line):

```markdown
## 6. After ADR 0024 (2026-11-20)

Plan 22 (`docs/plans/2026-11-20-plan-22-instructions-first.md`) removed the code that phases 0 to 2a shipped, and
dropped every item that adds shipped code or needs a code-host feature. The code is kept under the tag `checks-v1`
(`docs/archive/checks-v1.md`). Phases 2b to 6 of section 4 are replaced by this table.

| Item | State after Plan 22 | Why |
|---|---|---|
| A1, A3, A4 (the denies on the scripts and workflows), A5, decision D3 | Built in Plan 20, then removed | Shipped code; it blocked a merge only through GitHub's required checks |
| C4 | Built in Plan 20, then replaced by the plan's checklist | Shipped code |
| F6, and F14's `.gitignore` generator | Built in Plan 21, then replaced: status from git, one release row per repository, a `.gitignore` line a person adds | Shipped code |
| F9's scripts and workflows | Built in Plan 21, then replaced by the commands in `designing-apis` (oasdiff, `sha256sum -c`, `git ls-remote --tags`) | Shipped code; the contract rule (D5, D9) stays |
| A2, A6, A8, F1–F5, F11, F12, F13, F14's owners | Kept as instructions; A8 and F13 reworded host-neutral | Process rules |
| A7 | Kept | aidlc's own CI, not a team's |
| B1, B2 | Done in part: reviewer agents in a fresh context read the evidence file, and a verdict names its commit | A verifier with its own token needs a code-host feature |
| B3, B4, C1, C3, C6, D1, D2, D3, H1, H3 | Open, as instructions only (D2 without `run_slices.py`) | No shipped code needed |
| B5, C5 | Dropped | Each adds a script |
| C2, decision D2, G4, decision D8 | Dropped | Auto-merge needs required checks, a code-host feature (D6) |
| E1–E5, decision D1, F15's `run_queue.py`, G1–G3, G5, G6, H2 | Dropped | A dispatcher, workflows, labels or tokens: shipped code or code-host features. Decision D7's rule (one session writes one repository) stays as guidance |
| F7, F8's workflows, F10 | Dropped (they were phase 2b) | A home workflow, a GitHub App and required statuses; `aidlc-release` keeps its integration check |

The plugin's major version: see Plan 22, "Needs the owner's decision".
```

The section 6 block is appended at the end of the change list, after its section 5 (Sources).

- [ ] **Step 5: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.DocsTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 751 tests, OK.

- [ ] **Step 6: Commit**

```bash
git add README.md .claude-plugin/plugin.json docs/codebase-map.md AGENTS.md docs/quickstart docs/operating-model/adoption.md docs/design/2026-11-19-aidlc-6-change-list.md docs/archive/checks-v1.md scripts/test_instructions_first.py scripts/test_docs.py scripts/test_gates_hold.py scripts/test_one_plugin.py
git commit -m "docs: README, map, quickstarts, adoption and the change list say aidlc is instructions; plugin 6.0.0; where the check code went" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 9: Delete the starter scripts, the starter workflows, the Stop hook and their tests

Every reference is reworded by now (Tasks 2 to 8), so the code can go without leaving a skill or a document pointing at a missing file. Each test file goes in the same commit as the code it tests, so the suite stays green. The example settings keep the secret-read denies, the sandbox, the ask rules and the denies on `.claude/**` and `CODEOWNERS`; they lose the Stop hook and the three denies that protected the removed files.

**Files:**
- Delete: `starter/repo/scripts/` (6 scripts), `starter/workspace/scripts/` (1), `starter/repo/.github/workflows/` (4)
- Delete: `scripts/test_check_slice.py`, `scripts/test_check_plan.py`, `scripts/test_check_recipe_commit.py`, `scripts/test_check_contract.py`, `scripts/test_run_slices.py`, `scripts/test_story_status.py`
- Modify: `starter/repo/.claude/settings.json`, `starter/workspace/.claude/settings.json`, both starter `CODEOWNERS` (one comment)
- Test: `scripts/test_instructions_first.py` (new class `NoShippedCodeTest`); approved deletions and changes in `scripts/test_gates_hold.py`, `scripts/test_multirepo.py`, `scripts/test_one_plugin.py`, `scripts/test_recording.py`

**Interfaces:**
- Consumes: the tag `checks-v1` (it exists, at `7843f18`, and holds every file deleted here).
- `scripts/validate.py` is not changed: its starter check reads only the two settings files' `Read(` denies, which stay identical between the starters.

- [ ] **Step 1: Confirm the tag holds the code**

```bash
git ls-tree -r --name-only checks-v1 -- starter/repo/scripts starter/workspace/scripts starter/repo/.github | grep -v __pycache__
# must list the 6 + 1 scripts and the 4 workflows deleted below
```

- [ ] **Step 2: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
REMOVED_NAMES = ("check_slice.py", "check_plan.py", "check_recipe_commit.py", "check_contract_version.py",
                 "check_contract_pin.py", "run_slices.py", "story_status.py", "ai-review.yml", "contract-check.yml",
                 "contract-publish.yml", "slice check", "plan check", "story status command", "slice runner",
                 "Stop hook", "contract pin command", "--write-gitignore", "--check-release")


def live_text_files() -> list[Path]:
    """The files a team reads or copies: skills, agents, starters, the operating model, the quickstarts, the README,
    AGENTS.md, CLAUDE.md and the plugin manifest. History (ADRs, designs, plans, verification records, the archive)
    and the eval fixtures are left out."""
    roots = [ROOT / "skills", ROOT / "agents", ROOT / "starter", ROOT / "docs/operating-model", ROOT / "docs/quickstart"]
    files = [p for r in roots for p in r.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    return files + [ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "CLAUDE.md", ROOT / ".claude-plugin/plugin.json"]


class NoShippedCodeTest(unittest.TestCase):
    """Task 9: the starters hold no script and no workflow; the example settings keep what protects secrets and the
    settings themselves; nothing a team reads names the removed code."""

    def test_the_starters_hold_no_script_and_no_workflow(self):
        for kind in ("repo", "workspace"):
            base = ROOT / "starter" / kind
            self.assertFalse((base / "scripts").exists(), kind)
            self.assertFalse((base / ".github").exists(), kind)
            self.assertEqual([p for p in base.rglob("*") if p.suffix in (".py", ".sh", ".yml", ".yaml")], [], kind)
        for name in ("test_check_slice.py", "test_check_plan.py", "test_check_recipe_commit.py",
                     "test_check_contract.py", "test_run_slices.py", "test_story_status.py"):
            self.assertFalse((ROOT / "scripts" / name).exists(), name)

    def test_the_example_settings_keep_the_secret_denies_and_drop_the_rest(self):
        for kind in ("repo", "workspace"):
            settings = json.loads(read(f"starter/{kind}/.claude/settings.json"))
            self.assertNotIn("hooks", settings, kind)
            deny = settings["permissions"]["deny"]
            for rule in ("Read(**/.env)", "Read(**/*.pem)", "Read(~/.ssh/**)", "Edit(/.claude/**)", "Edit(/CODEOWNERS)"):
                self.assertIn(rule, deny, f"{kind}: {rule}")
            self.assertEqual([r for r in deny if "scripts/" in r or "workflows/" in r], [], kind)
            self.assertTrue(settings["sandbox"]["enabled"], kind)
        ask = json.loads(read("starter/repo/.claude/settings.json"))["permissions"]["ask"]
        for rule in ("Bash(git push*)", "Bash(npm install*)", "Bash(pip install*)", "Bash(dotnet add package*)"):
            self.assertIn(rule, ask, rule)

    def test_no_file_a_team_reads_names_the_removed_code(self):
        hits = []
        for path in live_text_files():
            text = " ".join(path.read_text(encoding="utf-8").split())
            hits += [f"{path.relative_to(ROOT)}: {name}" for name in REMOVED_NAMES if name in text]
        self.assertEqual(hits, [])

    def test_the_owners_still_hold_the_teams_own_checks(self):
        owners = read("starter/repo/CODEOWNERS")
        for line in (r"(?m)^scripts/\s+@your-org/your-team-leads$", r"(?m)^\.github/\s+@your-org/your-team-leads$",
                     r"(?m)^\.claude/\s+@your-org/your-team-leads$", r"(?m)^CLAUDE\.md\s+@your-org/your-team-leads$",
                     r"(?m)^\.mcp\.json\s+@your-org/your-team-leads$"):
            self.assertRegex(owners, line)
        for rel in ("starter/repo/CODEOWNERS", "starter/workspace/CODEOWNERS"):
            self.assertIn("aidlc ships none", read(rel), rel)
```

- [ ] **Step 3: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.NoShippedCodeTest -v`

Expected: FAIL in all four tests.

- [ ] **Step 4: Apply this task's approved changes to existing tests**

These are items listed under "Needs the owner's decision"; make no other change to an existing test.

In `scripts/test_gates_hold.py`, delete these classes whole (from the `class` line through its last method): `StarterReviewTest`, `FinalReviewFixesTest`; and delete these test methods (each from its `def` line through its last line): `WiringTest.test_the_stop_hook_runs_the_slice_check`, `WiringTest.test_ci_runs_the_base_branchs_copy_on_the_head_commit`. Why: they test `ai-review.yml`, `ci.yml` and the Stop hook (owner's items T9c, T9d). `FinalReviewFixesTest` holds two tests by now (Tasks 2 and 8 deleted the others): `test_ci_falls_back_only_when_the_base_has_no_script` and `test_the_stop_hook_skips_a_missing_script_and_times_out`; `StarterReviewTest` holds thirteen.

In `scripts/test_multirepo.py`, delete these classes whole (from the `class` line through its last method): `ContractWorkflowTest`, `ContractWorkflowHardeningTest`, `ContractWorkflowFinalReviewTest`; and delete these test methods (each from its `def` line through its last line): `OnlinePinCheckTest.test_the_adr_and_the_publish_job_say_who_runs_it`. Why: they test `contract-check.yml`, `contract-publish.yml`, `ci.yml` and the contract scripts (owner's item T9e). `ContractWorkflowTest` holds six tests by now (Task 5 deleted one).

In `scripts/test_one_plugin.py`, delete these test methods (each from its `def` line through its last line): `OnePluginTest.test_the_starter_ci_runs_no_pack_check`. Why: it reads `ci.yml` (owner's item T9f).

In `scripts/test_recording.py`, delete these test methods (each from its `def` line through its last line): `ParsedRecordTest.test_the_runner_tells_the_person_to_tell_the_ai`, `ParsedRecordTest.test_a_pause_line_with_how_it_was_confirmed_still_parses`. Why: they test `run_slices.py` (owner's item T9g).

`DenyTest.test_the_repository_denies_edits_to_its_controls` (owner's item T9a), through its `REPO_DENIES` list: the three rules that protected the removed files go; the settings and the ownership list stay protected.
In `scripts/test_gates_hold.py` find:

```text
REPO_DENIES = ["Edit(/.claude/**)", "Edit(/scripts/check_*.py)", "Edit(/scripts/run_slices.py)",
               "Edit(/.github/workflows/ai-review.yml)", "Edit(/CODEOWNERS)", "Edit(/.github/CODEOWNERS)"]
```

Replace with:

```text
REPO_DENIES = ["Edit(/.claude/**)", "Edit(/CODEOWNERS)", "Edit(/.github/CODEOWNERS)"]
```

`DenyTest.test_the_workspace_denies_edits_to_its_controls` (owner's item T9b): its `Edit(/.claude/**)` assertion stays.
In `scripts/test_gates_hold.py` find:

```text
        self.assertIn("Edit(/scripts/story_status.py)", deny)
```

and delete it.


Structural, no assertion (item T9e): the workflow helpers' import goes with the workflow tests.
In `scripts/test_multirepo.py` find:

```text
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gates_hold import pinned_uses, run_blocks  # noqa: E402
```

Replace with:

```text
import unittest
from pathlib import Path
```

Structural (item T9e): the helper `job_text`, used only by the deleted workflow tests.
In `scripts/test_multirepo.py` find:

```text
def job_text(yaml_text: str, job: str) -> str:
    """The lines of one job under `jobs:` (two-space indent), up to the next job."""
    lines, out, on = yaml_text.splitlines(), [], False
    for line in lines:
        if re.match(r"^  [\w-]+:", line):
            on = line.strip() == f"{job}:"
        if on:
            out.append(line)
    return "\n".join(out)
```

and delete it.


Structural (item T9g): the module imported `run_slices.py`; without it the whole file fails to load.
In `scripts/test_recording.py` find:

```text
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "starter" / "repo" / "scripts"))
import run_slices  # noqa: E402
```

Replace with:

```text
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
```

`FinalReviewRecordTest.test_no_record_is_marked_by_hand` (owner's item T9h): the script it also read is gone.
In `scripts/test_recording.py` find:

```text
        for rel in ("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md", "skills/aidlc-release/SKILL.md",
                    "starter/workspace/scripts/story_status.py"):
```

Replace with:

```text
        for rel in ("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md", "skills/aidlc-release/SKILL.md"):
```

- [ ] **Step 5: Delete the code, the hook and the denies that protected it**

Remove `starter/repo/scripts` with `git rm -r starter/repo/scripts` (and delete any untracked `__pycache__` left in it).

Remove `starter/workspace/scripts` with `git rm -r starter/workspace/scripts` (and delete any untracked `__pycache__` left in it).

Remove `starter/repo/.github` with `git rm -r starter/repo/.github` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_check_slice.py` with `git rm -r scripts/test_check_slice.py` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_check_plan.py` with `git rm -r scripts/test_check_plan.py` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_check_recipe_commit.py` with `git rm -r scripts/test_check_recipe_commit.py` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_check_contract.py` with `git rm -r scripts/test_check_contract.py` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_run_slices.py` with `git rm -r scripts/test_run_slices.py` (and delete any untracked `__pycache__` left in it).

Remove `scripts/test_story_status.py` with `git rm -r scripts/test_story_status.py` (and delete any untracked `__pycache__` left in it).

In `starter/repo/.claude/settings.json` find:

```text
      "Edit(/scripts/check_*.py)",
      "Edit(/scripts/run_slices.py)",
      "Edit(/.github/workflows/ai-review.yml)",
```

and delete it.


In `starter/repo/.claude/settings.json` find:

```text
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "test -f \"$CLAUDE_PROJECT_DIR/scripts/check_slice.py\" || exit 0; python3 \"$CLAUDE_PROJECT_DIR/scripts/check_slice.py\" --hook --root \"$CLAUDE_PROJECT_DIR\"", "timeout": 60}
        ]
      }
    ]
  },
```

and delete it.


In `starter/workspace/.claude/settings.json` find:

```text
      "Edit(/scripts/story_status.py)",
```

and delete it.


In each of these files: `starter/repo/CODEOWNERS`, `starter/workspace/CODEOWNERS`, find:

```text
# Scripts and settings that enforce the rules.
```

Replace with:

```text
# The team's own checks and settings: its scripts, CI and AI tool settings (aidlc ships none, ADR 0024).
```

- [ ] **Step 6: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.NoShippedCodeTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 364 tests, OK.

- [ ] **Step 7: Commit**

```bash
git add starter scripts
git commit -m "refactor(starter)!: aidlc ships no scripts and no CI workflows; the code and its tests move to the tag checks-v1 (ADR 0024)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```


### Task 10: The verification record

The plan ends with a record a person can check, in the style of `docs/verification/2026-11-20-plan-21.md`: what changed, how each task was reviewed, the commands' real outputs, and what was not verified.

**Files:**
- Create: `docs/verification/2026-11-20-plan-22.md`
- Test: `scripts/test_instructions_first.py` (new class `RecordTest`)

**Interfaces:**
- Consumes: every earlier task's commit and review notes.

- [ ] **Step 1: Write the failing tests**

Append to `scripts/test_instructions_first.py`, above its `if __name__ == "__main__":` line:

```python
class RecordTest(unittest.TestCase):
    """Task 10: the plan is recorded."""

    def test_the_verification_record_exists(self):
        record = read("docs/verification/2026-11-20-plan-22.md")
        for heading in ("## What changed", "## How it was checked", "## Evidence", "## Not verified here",
                        "## For the owner"):
            self.assertIn(heading, record, heading)
        for phrase in ("checks-v1", "ADR 0024", "python3 scripts/validate.py", "claude plugin validate ."):
            self.assertIn(phrase, record, phrase)
```

- [ ] **Step 2: Run them to see them fail**

Run: `python3 -m unittest scripts.test_instructions_first.RecordTest -v`

Expected: ERROR (no such file).

- [ ] **Step 3: Run everything, then write the record**

Create `docs/verification/2026-11-20-plan-22.md`:

```markdown
# Verification: instructions first (Plan 22)

Date: 2026-11-20 · Claude Code: {{the output of `claude --version`}}
Plan: `docs/plans/2026-11-20-plan-22-instructions-first.md` · Design: `docs/design/2026-11-20-instructions-first.md` ·
ADR 0024 (proposed). aidlc {{6.0.0, or 5.0.0 if the owner kept it}}.

## What changed
Commits on `docs/plan-22-instructions-first`, from local `main`, as `git log --oneline main..HEAD` prints them:

- {{one line per commit: `sha` subject}}

aidlc ships no scripts and no CI workflows. The removed code and its tests are kept under the tag `checks-v1`
(`docs/archive/checks-v1.md`). Test changes: exactly the items the owner approved under "Needs the owner's decision"
in the plan, and no other existing assertion.

## How it was checked
{{per task: what the reviewer found and how it was fixed, or "approved"; then the final review}}

## Evidence
`python3 scripts/validate.py`:

    {{output}}

`python3 -m unittest discover -s scripts -p 'test_*.py'`:

    {{the last three lines of the output}}

`claude plugin validate .`:

    {{output; the known warning about the root CLAUDE.md is expected}}

`git ls-tree -r --name-only checks-v1 -- starter/repo/scripts starter/workspace/scripts starter/repo/.github`:

    {{output: the 7 scripts and 4 workflows}}

## Not verified here
- A live session that writes `plans/<KEY>/review-evidence.md` and sends it to `reviewer-compliance` and
  `reviewer-tests` in a fresh context; the reviewers' verdict at a named commit. The skills say it; no behaviour eval
  runs it yet.
- A reviewer agent catching a deleted test or a weakened assertion from the evidence file alone. The design accepts
  that a reviewer agent can be lenient; a team that wants a hard block adds one to its own CI.
- The contract commands in `designing-apis` (oasdiff, `sha256sum -c`, `git ls-remote --tags`) in a real provider's
  and consumer's CI.
- The behaviour evals (28 cases, 6 build-gate cases never run): they need a working eval environment.
- The evals' workspace fixture still names `story_status.py` (owner's item E1).

## For the owner
Accept or amend ADR 0024; push the tag `checks-v1` with main (`git push origin checks-v1`).
```

Fill every `{{…}}` above with the real value before you commit: run `claude --version`, `git log --oneline main..HEAD`, `python3 scripts/validate.py`, `python3 -m unittest discover -s scripts -p 'test_*.py'`, `claude plugin validate .` and the `git ls-tree` line, and paste each output indented by four spaces. Under "How it was checked", write one line per task from its review. Nothing in braces is left when you commit: `grep -c '{{' docs/verification/2026-11-20-plan-22.md` prints 0.

- [ ] **Step 4: Run the tests, the validator and the suite**

Run: `python3 -m unittest scripts.test_instructions_first.RecordTest -v && python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py'`

Expected: PASS. The validator prints `validate: 1 plugin, 30 skill(s), 0 problem(s)`; the suite runs 365 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add docs/verification/2026-11-20-plan-22.md scripts/test_instructions_first.py
git commit -m "docs(verification): Plan 22 record: aidlc is instructions, the check code is under checks-v1" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

## Out of scope (later plans)

- Adapters for GitHub Copilot and OpenAI Codex (generated agent files, `.agents/skills`) and the skills' `metadata`
  list values. This plan only removes what blocks them and corrects the portability claim in `plugin.json` and the
  README.
- Running the behaviour evals as a baseline, and updating their workspace fixture (item E1).
- A behaviour eval for the evidence file and the non-author verdict.

## Self-review notes

- Spec coverage (`docs/design/2026-11-20-instructions-first.md`):

  | Design | Where |
  |---|---|
  | The principle, 1: instructions only, no scripts, no CI workflows | ADR 0024 (Task 1); deletion (Task 9); README, map, archive note (Task 8) |
  | The principle, 2: a rule that must hold lives in the team's project | Onboard step 5 (Task 5); `aidlc-feedback` (Task 6); README (Task 8) |
  | The principle, 3: a repeated mistake becomes a check, proven, in the rules table | `aidlc-feedback` and the rules table's note (Task 6) |
  | The principle, 4: a non-author verdict, naming its commit, voided by a later change | Task 2 (build, verify, review, the four reviewer agents, the review record) |
  | The principle, 5: a person decides from evidence git can confirm | The evidence file (Task 2); the release's Parts table (Task 4) |
  | The principle, 6: host-neutral words | Task 7; onboard (Task 5); README and quickstarts (Task 8) |
  | Table row 1, no deleted test or changed assertion | Evidence sections Test files and Test count; `reviewer-tests` (Task 2) |
  | Row 2, MAY CHANGE and MUST NOT | Evidence section Changed files; `reviewer-compliance` (Task 2) |
  | Row 3, suppressions | Evidence section Added suppressions (Task 2); the suppression reference (Task 5) |
  | Row 4, new dependency | Evidence section Dependency manifests (Task 2) |
  | Row 5, approved documents unchanged (ADR 0020) | Evidence section Story documents (Task 2) |
  | Row 6, plan complete | The plan's checklist (Task 3) |
  | Row 7, mechanical recipe commit | `aidlc-build` step 5 and the evidence section Recipe commits (Tasks 2, 3) |
  | Row 8, slices one by one | `aidlc-build` When to use (Task 3); adoption Phase 4 (Task 8) |
  | Row 9, status, drift, merge state | `status.md` from git; the Parts table (Task 4) |
  | Row 10, contract version | `designing-apis` (Task 4); onboard step 5 (Task 5) |
  | Row 11, consumer copy | `designing-apis`, `aidlc-release` (Task 4) |
  | Row 12, independent AI review | `aidlc-review` step 3 (Task 2); adoption Phase 1 (Task 8) |
  | Row 13, secrets and push | The example settings (Task 9) |
  | Goes: scripts, workflows, Stop hook, protecting denies, their tests | Task 9 |
  | Added: ADR 0024 superseding 0019 | Task 1 |

- Every task was applied in order to a clean clone of `d39f6bb` (with the design file copied in) while this plan was
  written, by a script that applies each "find" and "replace with" pair exactly as printed, fails if a "find" text
  occurs other than the stated number of times, checks that each task's new tests fail first, and then runs the
  validator and the full suite. The suite ran 729, 734, 738, 741, 740, 742, 747, 751, 364 and 365 tests after Tasks 1 to 10, each OK, with 0 validator
  problems.
- No placeholder is left in the plan, except the `{{…}}` slots of templates and of the verification record, which
  Task 10 fills from real output.
- Names used across tasks: `read`, `flat`, `skill`, `section`, `AMENDED` (Task 1); `VERDICT`, `REVIEWERS`,
  `EVIDENCE` (Task 2); `RECORDING`, `RULE`, `GITHUB_ONLY` (Task 7); `REMOVED_NAMES`, `live_text_files` (Task 9).
  The file name `plans/<KEY>/review-evidence.md` and its eight section headings are the same in every task.
- Each existing test that pins a sentence in a touched file was read first: `test_gates_hold.py`,
  `test_multirepo.py`, `test_recording.py`, `test_routes.py`, `test_fast_path.py`, `test_docs.py`,
  `test_greenfield.py`, `test_handoffs.py` (fences, placeholders, identical copies, the ten readiness checkboxes),
  `test_loads.py` (no new load phrase), `test_gates.py` (the exception sentence), `test_validate.py` and
  `test_one_plugin.py`.
