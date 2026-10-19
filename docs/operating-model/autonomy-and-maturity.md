# Autonomy and the maturity path

Autonomy increases only when validation increases.

## The ladder

| Rung | What surrounds the agent |
|---|---|
| 1 Prompt-only | The conversation and nothing else |
| 2 Guided agent | A clear task plus project context (rules file, codebase map) |
| 3 Harnessed agent | Tools, a one-command check, repeatable workflows |
| 4 Governed loop | Permissions, a sandbox, quality gates, required review |
| 5 Engineering system | Agent-configuration evals, observability, lessons fed back into context |

This framework installs rungs 2–5.

## The autonomy check

Before an agent gets more responsibility in a repository, all four must hold; if any is false, hold:

1. Context is explicit (rules file, map, bundle).
2. Tools are scoped (permissions, sandbox, no production credentials).
3. Tests are runnable (one-command check, green on main, no unexpected skips).
4. Review is required (branch protection, code owners).

## Rollout stages

Start with one repository, one workflow and one observable use case; prove it against a baseline
(ROI pilot); then scale. Governance first (approved routes, agent identity, sandbox, secrets
unavailable), then the shared platform (harness templates, skills, eval set), then delegation per
repository once its autonomy check passes. Alert-triggered agents come last. Tier 3 stays
human-gated at every stage, and usage is never a target.

Guide: 1.1, 1.5, 16.4, 16.5, 12.14.
