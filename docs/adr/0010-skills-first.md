# 0010 · Skills first; the harness parked

Status: Accepted (2026-10-25). · Decider: Prashant Sharma (framework owner)

## Context
The Python harness (a CLI, hooks, policy-as-code, a generator and about 12,000 lines of tests) made every change slow,
was built mostly for Claude Code, and was hard for engineers to adopt. The method itself (skills, agents, templates)
was already Markdown in the open Agent Skills format, which Claude Code, GitHub Copilot, Codex and Cursor all read.

## Decision
- aidlc is a skills package, like addyosmani/agent-skills: `skills/` (each with its templates in `assets/`), `agents/`,
  `starter/` files to copy, one Claude Code plugin at the repository root, and quickstarts per tool.
- The gates live in the skills' text (tests first, three attempts then stop, the diff checked against the task bundle,
  never editing an existing assertion) and in the team's pull-request review, CODEOWNERS and CI.
- Routing lives in AGENTS.md ("How work runs here") and `aidlc-start`; no auto-loading meta-skill.
- Agents write their drafts to files on the story branch; people review them in the pull request.
- One standard-library script, `scripts/validate.py`, checks the package.
- The harness is parked under the tag `harness-v1` (docs/archive/harness-v1.md).

## Consequences
- Enforcement by code is gone: a careless or manipulated agent is stopped by tool permissions, review and CI. Teams that
  need enforcement can bring the guardrails back from `harness-v1` as an add-on.
- Supersedes ADRs 0001, 0002 (trusted CI), 0003 to 0008 where they describe harness machinery; their reasoning stays.
