# The parked harness (tag `harness-v1`)

On 2026-10-25 aidlc became a skills-first package (Plan 7, ADR 0010). The Python harness that enforced the method
was removed from the main tree. Nothing is lost: the tag `harness-v1` holds the last state with the harness, and any
file comes back with `git show harness-v1:<path>` or `git checkout harness-v1 -- <path>`.

## What moved, what was rewritten, what was parked

| Area | Decision | Where it is now |
|---|---|---|
| `core/skills/` (13 stage skills) | move | `skills/aidlc-*/` with their templates in `assets/` (from the generated plugin) |
| `core/practices/` (8 practice skills, NOTICE) | move | `skills/<practice>/`, `skills/NOTICE` |
| `core/agents/` (7 agents) | move | `agents/` |
| `core/templates/` | move | each template sits in the `assets/` of the skill that fills it; `agents-md`, `codebase-map` and `workspace` also seed `starter/` |
| `core/templates/working-agreement.md` | park | no skill uses it |
| `.claude-plugin/marketplace.json` | rewrite | one plugin, `aidlc`, pointing at `skills/` and `agents/` |
| `AGENTS.md`, `CLAUDE.md`, `README.md`, `docs/codebase-map.md` | rewrite | describe the skills package |
| `docs/operating-model/`, `docs/adr/`, `docs/design/`, `docs/plans/`, `docs/verification/` | keep | history and the method |
| `docs/skills/` | rewrite | the skills list and quickstarts |
| `cli/`, `bin/`, `Makefile` | park | the `aidlc` command-line tool |
| `core/hooks/`, `core/managed/` | park | guard, post-check, shims, the optional root guard |
| `core/policy/`, `core/policy-as-code/`, `core/schemas/` | park | policies, Rego, JSON schemas |
| `core/adapters/`, `core/context/`, `core/ci/`, `core/observability/` | park | tool descriptors, profiles and standards, the CI template, dashboards |
| `plugins/` | park | the generated plugin (the source is now authored directly) |
| `tests/` | park | unit, integration and live harness tests |
| `.aidlc/generated.json`, `docs/traceability.md` | park | generator manifest and trace output |
| `docs/harness/`, `docs/checks/`, `docs/observability/`, `docs/adapters/`, `docs/adoption/`, `docs/context-engineering/` | park | docs of parked machinery |
| `docs/demo/` | rewrite | the replay runbook follows the skills-first flow (Plan 7, Task 7) |
| `.github/workflows/framework-ci.yml` | rewrite | `validate.yml` checks the skills |
| `.github/workflows/ai-gates.yml` | rewrite | AI review of this repository's pull requests stays; the live harness evals go |

## If a team needs enforcement again

The harness can return as an optional "enterprise guardrails" add-on: the guard hook and scope from approved bundles,
the protected-tests and skips checks, the retry limit, and the trusted CI that runs gates from the base branch.
Start from `git checkout harness-v1 -- cli core/hooks core/policy`.
