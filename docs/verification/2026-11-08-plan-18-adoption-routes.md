# Verification: adoption guide and routes documents (Plan 18)

Date: 2026-11-08 · Claude Code: 2.1.296 (Claude Code) · Final reviewer: a fresh Opus session, whole branch
Plan: `docs/plans/2026-11-08-plan-18-adoption-routes.md` · Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md`
(section "Plan 17: adoption guide and routes documents", renumbered Plan 18). Documents only: aidlc stays at 5.0.0.

## Checks
| Check | Result |
|---|---|
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 303 tests, OK (285 before; 18 in `test_docs.py`) |
| `python3 scripts/validate.py` | validate: 1 plugin, 30 skill(s), 0 problem(s) |
| `claude plugin validate .` | Validation passed, with the known warning about the root `CLAUDE.md` |
| Existing test assertions changed | none |
| Mermaid | 13 blocks (11 in `routes.md`, 2 in `adoption.md`) pass the safe-subset lint, and the reviewer read each one and judged it to render on GitHub. Not rendered here: the Mermaid CLI is a new tool, and the owner did not ask for it |

## Review Focus
| Case | Test |
|---|---|
| A route drawn with a stage, gate or approver the skills lack, or missing one | `test_every_route_in_using_aidlc_has_a_section`; the reviewer compared every diagram with `using-aidlc`, `aidlc-start` and the stage skills (findings below) |
| A Mermaid block that does not render | `test_mermaid_blocks_use_the_safe_subset`; reviewer read |
| A phase asking for something no skill supports | `test_each_phase_names_its_skills`; the reviewer checked each claim against the skills and starter files |
| The sheet naming the wrong approver | `test_the_sheet_never_lets_the_author_approve`, `test_i5_the_sheet_holds_every_stage_gate`, `test_i6_the_tech_lead_approves_the_plan_at_every_tier` |
| A link that points nowhere | `test_links_in_the_new_documents_resolve`, `test_anchors_in_the_new_documents_resolve` |

## Final review
0 critical, 6 important and 20 minor findings, verdict "with fixes". Both documents had been copied from the plan, so
each finding was also a defect in the plan's text. All were fixed in one pass; the eight failing tests in
`ReviewFixesTest` were seen red first.

| Finding | Fix |
|---|---|
| I1 "Unaffected" recorded on the tracker; `story_status.py` and `aidlc-release` read an `UNAFFECTED` line in the story index | Both documents name the line in the story index |
| I2 The status command needs `--write` to save `status.md` | `story_status.py <KEY> --write`; `--check-release` named |
| I3 The tree sent a defect with no reproduction to D2; `aidlc-start` asks the reporter and stops | A reproduction check before the fast-path question |
| I4 The tree showed `aidlc-start` choosing route I; `aidlc-operate` starts it | Seven routes through `aidlc-start`; I drawn from "An alert fires" |
| I5 The approvals sheet missed gates the stage skills define | Rows for the provisional tier, the discovery decision, a wireframe, each review finding, a Tier 3 specialist review, monitoring and rollback, the incident follow-up item, the rules file and map |
| I6 Tier 1 plan approval: `roles.md` said "in the PR description", `aidlc-plan`'s Gate says the tech lead | The owner ruled the tech lead approves at every tier; `roles.md` fixed |
| Minors 1–19 | Part 1 also re-plans in the F2 sequence; re-routing from plan and build, with each brief's triggers; the fast-path checks split by route; AI review needs a paid key and is not the reviewer agents; build writes the characterisation test first or stops; start asks before choosing G; release prepares, a person ships; brief MODE from Phase 1; recipe review recorded in the progress note; change management; the design note's APPROVED or RECORDED BY line and the ADR folder `AGENTS.md` names; the tracker optional for the agent; tech lead or architect for design; revision title; D2 decides repositories before intent; one explorer per repository; stage outputs; where the contract lives; the quickstart link |
| Minor 20 | Blank-line nits in `test_docs.py`; anchors now checked |

## Follow-ups (skill text, outside this documents-only plan)
- `using-aidlc` says "`aidlc-start` chooses one" of the routes, including I; `aidlc-start` and `aidlc-operate` say I
  starts at `aidlc-operate`.
- The tiers table's Approvals row names the tech lead's plan approval only from Tier 2, while `aidlc-plan`'s Gate and
  the owner's ruling say every tier.

## Decisions made during the plan
| Where | Decision |
|---|---|
| Recheck | Plan 18 rechecked against aidlc 5.0.0 before it ran: one stale test count fixed |
| Tasks 1–2 | Documents and test code copied from the plan by script, not retyped |
| Final | The owner ruled that the tech lead approves the plan at every tier |
