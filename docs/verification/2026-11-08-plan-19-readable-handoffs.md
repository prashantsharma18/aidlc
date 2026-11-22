# Verification: readable hand-offs (Plan 19)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-19-readable-handoffs.md` · Source: the template readability review the owner asked for,
and the owner's choice of its three changes worth doing. aidlc stays at 5.0.0 (unreleased).

## Checks
| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 329 tests, OK (308 before; 21 new) |
| `python3 scripts/validate.py` | validate: 1 plugin, 30 skill(s), 0 problem(s) |
| `python3 scripts/route_check.py` | 57 positive prompts, rank-1 rate 86% (unchanged) |
| `claude plugin validate .` | Validation passed, with the known warning about the root `CLAUDE.md` |
| Existing test assertions changed | none. `test_run_slices.py` and `test_story_status.py` gained tests only; every line inside a new fence is byte-identical to the base (the reviewer compared them) |
| Render on GitHub (`gh api markdown`, GFM) | Fix brief: 7 of 7 `{{…}}` and 14 of 14 `<…>` placeholders shown; PR description 24 of 24; spec 25 of 25. `CONFIRMED <engineer>, <YYYY-MM-DD>` now renders with its gaps instead of ", ". The reviewer rendered ten more and found every placeholder visible |

## What changed
| Change | Templates |
|---|---|
| Field blocks in ```` ```text ```` fences, placeholders kept and visible | intent, evidence pack, design note, new system, coordination plan, decision frame, plan, task bundle, fix brief, feature brief, explorer brief (both copies), security review, release runbook, runbook, story index header (both copies); after the review also the progress note's STATUS and MODE and the review record's DECISION |
| `<word>` outside code written `{{word}}` | ADR, agents-md, codebase map, compat matrix, progress note, spec, workspace, review record |
| `## For the reviewer` (who decides, where it is recorded, tier and main risk, what changed) | intent, spec, evidence pack, design note, new system, plan, task bundle, both briefs, PR description, review record, security review, readiness, change record; after the review also the ADR and the coordination plan |
| Rewritten as sections, lists and tables | PR description, evidence table, readiness (task list), change record, incident record (both copies) |
| Skills | verify says Unproved; release records each confirmation under its heading; feedback says Prevention section; intent, specify, plan and verify leave every approval slot for the person who approves |
| Scripts | `story_status.py` skips fence lines (and ends PARTS at one) and treats `{{` as a placeholder; `run_slices.py` treats `{{` as a placeholder in a field and in a pause confirmation |
| Rule | `AGENTS.md` states it; `test_m1_every_template_keeps_the_rule` guards every template |

## Review Focus
| Case | Test |
|---|---|
| A filled coordination plan with its PARTS block fenced | `test_parts_inside_a_fence_are_read`, `test_a_note_after_a_fenced_parts_block_is_not_a_part`; the reviewer ran `story_status.py` end to end on a fenced workspace |
| A filled bundle or brief with fenced fields | `test_fields_inside_a_fence_are_read`; the reviewer probed MODE, TIER, CONFIRMED and STATUS |
| A template still with a vanishing placeholder | `test_no_template_has_a_placeholder_that_vanishes`, `test_m1_every_template_keeps_the_rule` |
| A decision block naming someone other than the Gate | `test_each_decision_block_matches_its_gate` |
| A rewritten document losing a label a skill names | `test_rewritten_documents_keep_the_labels_skills_name` |

## Final review
0 critical, 2 important and 8 minor findings, verdict "with fixes". All fixed in one pass, each with a test seen
failing first.

| Finding | Fix |
|---|---|
| I1 The slice runner accepted `confirmed by {{name}}` as a person's confirmation of a pause: Task 1 taught `field()` about `{{`, but not `pause_confirmed` | `pause_confirmed` refuses a placeholder of either form; the test saw the runner start a session before the fix |
| I2 The review record's block named the engineer as the one asked, against its own "Reviewer: not the engineer" line | The block names the engineer for the findings, the reviewer for the DECISION, and the code owner for approval |
| M1 The rule in `AGENTS.md` was broader than the templates: unfenced STATUS, MODE and DECISION lines, `<...>` outside code, no block on the ADR and the coordination plan | All fixed; the guard now covers every template |
| M2 `read_parts` kept reading after a closing fence | A fence ends the PARTS block |
| M3 Feedback said "Prevention line" | "Prevention section" |
| M4 Approval slots look like the slots the agent fills | The four skills that say "replace each `{{FIELD}}`" now say to leave every approval slot for the person who approves |
| M5 The design note's and readiness's blocks were thinner than the Gate and the approvals sheet | "Tier 3 adds the specialists"; the owning team's confirmation recorded in readiness |
| M6, M7, M8 A line of `AGENTS.md` began with ```` ```text ````; a pasted ```` ``` ```` would end a fenced field; blank lines in tests | Rewrapped; a comment in the briefs and bundle says to indent pasted output; fixed |

Left as they are, with reasons: the duplicate title lines in fenced templates (they keep pinned lines byte-identical);
a second tier field in the block, and the PR description's evidence link position (layout preferences outside the
three changes). The reviewer's note that `AGENTS.md`'s Map names `plugins/aidlc/` is not true at HEAD.

## Out of scope (the owner's decision)
One standard header and approval line across all templates; tables for decision options and security areas;
explaining internal codes; moving authoring notes out of filled documents; splitting the task bundle; the front
matter of the coordination plan and the compat matrix; one variant of `tiers.md`; templates for the documents that
have none.
