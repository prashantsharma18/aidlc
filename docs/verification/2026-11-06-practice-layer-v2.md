# Verification: practice layer v2 (Plan 9)

Date: 2026-11-06 · Claude Code: 2.1.296 (Claude Code) · Model for the live check: claude-sonnet-5-5
Plan: `docs/plans/2026-11-06-plan-09-practice-layer-v2.md` · Design: `docs/design/2026-11-06-practice-layer-v2.md`

## Checks
| Check | Result |
|---|---|
| `python3 scripts/validate.py` | validate: 2 plugin(s), 35 skill(s), 0 problem(s) |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 74 tests in 8.908s OK  |
| `claude plugin validate .` | ✔ Validation passed |

## Originality
Every new file was compared, outside the repository, with the third-party text the earlier practices came from, for
shared runs of eight words or more. The check was first shown to detect copied text (a renamed earlier practice
shares 2,375 runs).

| File | Shared 8-word runs |
|---|---|
| `skills/writing-tests/SKILL.md` | 0 |
| `skills/committing-changes/SKILL.md` | 0 |
| `skills/building-ci-pipelines/SKILL.md` | 0 |
| `skills/simplifying-code/SKILL.md` | 0 |
| `skills/stress-testing-decisions/SKILL.md` | 0 |
| `skills/checking-official-docs/SKILL.md` | 0 |
| `skills/testing-in-browser/SKILL.md` | 0 |
| `agents/reviewer-tests.md` | 0 |

## Live routing check
Headless sessions in a new scratch repository, core plugin loaded with `--plugin-dir`, the user's other plugins
also loaded, so the new practices competed with their skills. Three runs per prompt, a short
function or diff pasted after each prompt. Routing varies between runs, so these are counts, not a pass mark.

| Prompt | Expected | Fired |
|---|---|---|
| "Add unit tests for this function." | `writing-tests` | 3 of 3 |
| "Write a commit message for this diff." | `committing-changes` | 3 of 3 |
| "Simplify this function; it works but it is hard to read." | `simplifying-code` | 3 of 3 |
| "Make this function faster." | none of the new practices | 0 of 3 (no skill fired) |
| "This test fails, why?" (added after the final review) | not `writing-tests` | 0 of 3; another installed plugin's debugging skill fired in all three, aidlc's `debugging-failures` in none |

Finding: where another plugin carries a debugging skill, it outcompetes `debugging-failures` on this phrasing. Its
description is one of the eight earlier practices, to be rewritten with their content.

Not covered here: `building-ci-pipelines`, `stress-testing-decisions`, `checking-official-docs` and
`testing-in-browser` had no live prompt; behaviour and pressure evals for all seven belong to the evals work.
