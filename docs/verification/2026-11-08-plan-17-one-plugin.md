# Verification: aidlc as one plugin at the root (Plan 17, aidlc 5.0.0)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-17-one-plugin.md` · ADR: `docs/adr/0018-one-plugin-at-the-root.md`
Backup: the tag `aidlc-modernize-archive` on f8e093c (local; the owner pushes it with `git push origin aidlc-modernize-archive`).

## Checks
| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 285 tests, OK |
| `python3 scripts/validate.py` | validate: 1 plugin, 30 skill(s), 0 problem(s) |
| `python3 scripts/route_check.py` | 57 positive prompts, rank-1 rate 86% (unchanged) |
| `claude plugin validate .` | Validation passed with one warning: `CLAUDE.md` at the plugin root is not loaded as project context (expected; it is for contributors) |
| Local install, scratch `HOME` | `marketplace add` and `install aidlc@aidlc` succeeded; `plugin details`: 30 skills, 6 agents, 0 hooks, 0 MCP servers; always-on cost about 3,451 tokens |
| Move commit 53a54c5 | 241 pure renames; the other changes are path strings only (reviewer read every hunk) |

## Test changes
Before the branch: 304 tests (`main` at f8e093c, two of them failing to load after the owner deleted the pack folder).

| Test | Change | Approved |
|---|---|---|
| `test_parity.py` (11), `test_retarget.py` (8) | Deleted with the pack's scripts | Owner, in the plan |
| `test_check_packs.py` (14) | Deleted with `check_packs.py` | Owner, in the plan |
| `test_validate.py`: core and pack marketplace, unique names across plugins, core never names a pack, core requires nothing, pack stage skills keep the sections (5) | Deleted | Owner, in the plan |
| `test_validate.py`: `test_a_plugin_source_outside_plugins_is_a_problem` | Replaced by `test_the_plugin_source_must_be_the_root` | Owner, in the plan |
| `test_validate.py`: `test_a_dependency_must_be_in_the_marketplace` | Deleted; `test_the_plugin_requires_nothing` pins the rule that replaces it (and stands in for the approved `test_core_requires_nothing`) | Owner, by answer after the review |
| `test_validate.py`: `test_versions_are_semantic` | Assertion unchanged; its fixture gives the core plugin the bad version instead of a pack | Ruling |
| `test_greenfield.py`: the line "On route G there is no `AGENTS.md` yet: skip this step." | Deleted: it pinned a sentence of the removed pack step | Owner, by answer during Task 3 |
| `test_loads.py` | Unchanged: the plan and bundle keep the words "core practices" | n/a |
| Every other test naming `plugins/aidlc/` | Path only | Owner, in the plan |
| New: `test_one_plugin.py` (17), `test_validate.py` (3) | Added | n/a |

## Review Focus
| Case | Test |
|---|---|
| A teammate who installed `aidlc@aidlc` updates | `test_the_install_id_is_unchanged`, `test_m5_both_starters_keep_the_install_and_the_cache_paths`; the local install above |
| A component loaded from the new root by accident | `test_nothing_else_at_the_root_loads_as_a_component` |
| A stage skill still sending someone to a pack step; start's renumbering | `test_no_live_file_keeps_the_pack_contract`, `test_start_steps_are_numbered_in_order`; using-aidlc's reference moved to "step 6" |
| The starter CI still running the pack check | `test_the_starter_ci_runs_no_pack_check` |
| A live document naming the old path | `test_no_live_document_names_the_old_path` |

## Final review
A fresh reviewer read the branch up to 1cc11d8: 0 critical, 2 important and 8 minor findings, verdict "with fixes".

| Finding | Fix |
|---|---|
| I1 The archive test reads a local tag that CI's shallow checkout cannot see | `validate.yml` checks out with `fetch-depth: 0`; the archive note says the owner pushes the tag. Until the tag is pushed, CI's archive test fails, which is the right signal |
| I2 A validator test deleted without approval | The owner approved it (above) |
| M1 No upgrade note for repositories onboarded with aidlc 4 | ADR 0018 gains "Upgrading a repository onboarded with aidlc 4" |
| M4 Two validator branches had no fixture test | `test_m4_the_marketplace_lists_only_aidlc`, `test_m4_the_plugin_is_named_aidlc` (coverage of existing behaviour) |
| M5 The install-id test checked one starter | Both starters, the marketplace and the cache read paths |
| M6, M7 Stale wording; a duplicate Map line in `AGENTS.md` | Fixed, with `test_m6_m7_no_stale_wording` |
| M2 Every ADR is now history to the "live document" tests | Kept: ADR 0018 must name what it removed. The plan's constraint said ADRs 0001 to 0017; it now reads all ADRs |
| M3 b8d39fe was committed with a red suite (three failures once ADR 0018 was tracked) | Fixed by 1cc11d8 |
| M8 Vestigial `name` and `deps` parameters in a test helper | Left: renaming them adds no protection |

Declined to judge by the reviewer, and left open: whether Copilot CLI accepts a marketplace entry with `"source": "./"`;
how `claude plugin eval .` behaves now that the plugin root is the whole repository (a paid run); future Claude Code
versions reading other root folders.

## Decisions made during the plan
| Where | Decision |
|---|---|
| Task 1 | The "nothing names the pack" test split: documents in Task 1, code in Task 3 |
| Task 2 | The old-path test checks documents only (a validator test writes `./plugins/aidlc` to prove it is rejected); the two move commits were squashed into one, locally |
| Task 3 | Build's red flag reworded for practices rather than deleted; "core practices" kept where `test_loads` pins it |
| Task 4 | Every ADR counts as history |
| Final | The owner approved the extra validator test deletion |
