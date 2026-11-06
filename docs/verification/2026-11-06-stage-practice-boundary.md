# Verification: the stage and practice boundary (Plan 11)

Date: 2026-11-06 · Claude Code: 2.1.296 (Claude Code) · Model for the probe and the live check: claude-sonnet-5-5
Plan: `docs/plans/2026-11-06-plan-11-stage-practice-boundary.md` · Design: `docs/design/2026-11-06-stage-practice-boundary.md`

## Checks
| Check | Result |
|---|---|
| `python3 scripts/validate.py` | validate: 2 plugin(s), 37 skill(s), 0 problem(s) |
| `python3 -m unittest discover -s scripts -p 'test_*.py'` | Ran 110 tests in 13.103s OK  |
| `claude plugin validate .` | ✔ Validation passed |

## Agent preload probe
`reviewer-bug` with `skills: [aidlc:reviewing-code]` in its front matter, asked to list the severity labels of the
preloaded skill, answered high, medium, low and question from `reviewing-code`'s table. The full plugin name works
for a plugin agent's preload; the three reviewer agents use it.

## Originality
`using-aidlc` and `writing-documentation`, compared outside the repository with the third-party text the earlier
practices came from: 0 shared 8-word runs each.

## Live routing check
Headless sessions in a new scratch repository, core plugin loaded with `--plugin-dir`, the user's other plugins also
loaded. Three runs per prompt.

| Prompt | Expected | Fired |
|---|---|---|
| "In aidlc, what stage comes after specify, and which practice applies to a database schema change?" | `using-aidlc` | 3 of 3 |
| "Document the public API of this module in the README." (module pasted) | `writing-documentation` | 3 of 3 |
| "Review this diff before I merge it." (diff pasted) | `reviewing-code` | 3 of 3 |
| "Write a commit message for this diff." (same diff) | `committing-changes`, not `reviewing-code` | 3 of 3; `reviewing-code` 0 of 3 |

Not covered here: the loads a stage commands while it runs (they are pinned by `scripts/test_loads.py`, not exercised
live); behaviour and pressure evals belong to the evals work.
