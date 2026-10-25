# Design: skills-first aidlc (Plan 7)

Status: draft for review (2026-10-25) · Owner: Prashant Sharma (framework owner)
Replaces: the Python harness as the centre of the framework (kept under the tag `harness-v1`).
Folds in: the workspace working model (Plan 6b design, `docs/design/2026-10-24-workspace-working-model.md`).

## Why

The harness (a Python CLI, hooks, policy-as-code and about 12,000 lines of tests) made every change slow, was built
mostly for Claude Code, and is hard for engineers to adopt. The valuable part of aidlc is the method: the stage skills,
the agents, the templates and the operating model. They are already Markdown in the open Agent Skills format.

addyosmani/agent-skills shows the alternative: a folder of `SKILL.md` workflows, with the quality gates written into each
skill (verification steps, red flags, "excuses" tables), packaged for each tool. GitHub's documentation says Copilot
loads project skills from `.github/skills`, `.claude/skills` or `.agents/skills` (and personal skills from
`~/.copilot/skills`) in the coding agent, the CLI, code review and VS Code agent mode. Codex, Cursor and Gemini CLI read
the same format.

## Decisions (user, 2026-10-25)

| Decision | Choice |
|---|---|
| Direction | Skills-first, like agent-skills |
| Repository | This repository, restructured; the harness tagged `harness-v1` and removed from the main tree |
| Tools to check | Claude Code, GitHub Copilot, Codex or Cursor |

## The new shape

```text
aidlc/
  skills/                 one folder per skill: SKILL.md + assets/ (templates it fills)
    aidlc-start/          routes any work: kind (feature, defect, change, incident) and scope (one repo or several)
    aidlc-intent/  aidlc-specify/  aidlc-discover/  aidlc-design/          story level
    aidlc-plan/  aidlc-build/  aidlc-verify/  aidlc-review/                part level (in a repository)
    aidlc-release/  aidlc-operate/  aidlc-feedback/                        story level
    aidlc-onboard/        sets up a repository or a workspace (was context-setup and adopt)
    practice-*/           the eight engineering practices (adapted from agent-skills, MIT)
  agents/                 explorer, planner, implementer, reviewer-bug, reviewer-security, reviewer-compliance, ops-diagnoser
  starter/                files a team copies once
    repo/AGENTS.md, repo/.claude/settings.json, repo/.github/workflows/ci.yml, repo/CODEOWNERS
    workspace/WORKSPACE.md, workspace/stories/README.md, workspace/.claude/settings.json
  .claude-plugin/         marketplace.json and plugin.json (Claude Code)
  docs/                   quickstart per tool, the operating model, ADRs
  scripts/validate.py     checks every skill's format (one small script, standard library)
```

- **One source, no generator.** Skills are authored where tools read them. The Claude Code plugin points at `skills/`
  and `agents/`. Copilot, Codex and Cursor get the same folders by copying or linking them into a repository
  (`.github/skills`, `.agents/skills`, `.cursor/skills`) or a user folder (`~/.copilot/skills`).
- **Templates live with the skill that fills them** (`skills/aidlc-plan/assets/plan.md`), as the generated plugin already does.
- **Agents** are Markdown files with a name, description and tools. Claude Code uses them as subagents; Copilot uses
  them as custom agents (`.github/agents/<name>.agent.md`); the quickstart says how to copy them.

## How the gates work without the harness

| Gate | In the harness | Skills-first |
|---|---|---|
| Stay inside the slice's files | Guard hook + scope file | The task bundle's MAY CHANGE list; the build skill reads its diff against it before handing off; the reviewer-compliance agent and the code owner check it |
| Never weaken an existing test | `protected-tests` check | A rule in every build and review skill; the PR diff shows it; CODEOWNERS on test folders if a team wants it enforced |
| Tests pass | `aidlc check` and trusted CI | The repository's own commands from AGENTS.md; the repository's normal CI (a starter workflow is provided) |
| Secrets stay unreadable | Rendered deny rules and sandbox | The starter `.claude/settings.json` (deny `.env*`, keys; sandbox on); Copilot's own content exclusion; the secret scanning teams already run |
| Approvals | Lines in `approved-bundles.txt`, ADR status | The pull request (plans and designs are reviewed as files in a PR), the tracker for the story |
| Retry loops | The retry-limit hook | The build skill's rule: three attempts at the same failure, then stop and report |

What is lost: enforcement by code. A careless or manipulated agent is now stopped by tool permissions, review and CI,
not by a hook. That is the same trade agent-skills makes. The harness stays under `harness-v1` and can return as an
optional "enterprise guardrails" add-on for teams that need enforcement.

## Routing: how the agent knows which skill to use

agent-skills uses a meta-skill (`using-agent-skills`), loaded by a session-start hook in Claude Code, that maps requests
to skills before the agent acts. aidlc does the same in a tool-neutral way:

- **AGENTS.md** (from `starter/repo/AGENTS.md` and `starter/workspace/WORKSPACE.md`) carries a short "How work runs here"
  block: start any new work with `aidlc-start`; which skill handles which request; tests first; where each stage runs.
  Claude Code, Copilot, Codex and Cursor all read AGENTS.md, so routing works without a hook.
- **`aidlc-start`** is the explicit router a person runs: by kind of work and by scope.
- No separate auto-loading meta-skill: it would repeat AGENTS.md and cost context in every session (user decision, 2026-10-25).

## The feedback loops without the harness

| Loop | Speed | Where it is written | What stops a runaway |
|---|---|---|---|
| 1 Build | minutes | `aidlc-build`: failing test, code, run the repository's tests; on a failure name the cause and make one targeted fix (the debugging practice skill helps) | The skill's rule: the same failure three times, or a newly broken test, means stop and report. The engineer watching is the backstop |
| 2 Pull request | hours | `aidlc-verify` reads CI; a red run goes back to `aidlc-build` as a fix round with the CI log as input | CI stays red; the PR cannot merge |
| 3 Review | hours to days | `aidlc-review` with the three reviewer agents; the code owner decides each finding; fixes go back through `aidlc-build` | The code owner's approval and branch protection |
| 4 Production | days | `aidlc-operate`, then `aidlc-feedback` turns each lesson into a test, an AGENTS.md rule, a skill change or an eval case | People decide containment and which lesson goes where |

## Simpler documents

- Agents may write their drafts to files (`plans/<KEY>/…`, `stories/<KEY>/…`) on the story branch; the person reviews
  them in the pull request. No more "draft in the reply, the person saves it".
- The story stays in Jira. Small work keeps the documents short: the build skill can start from the story's acceptance
  criteria and a plan in the session, and the plan and spec files are needed only from Tier 2, or for several repositories.

## The workspace model (from Plan 6b, Markdown only)

`aidlc-start` at the workspace root routes every piece of work by kind and scope; story-level documents live in the
workspace repository's `stories/<KEY>/`; the coordination plan is the job sheet (one row per repository part, with
status); every branch and PR carries the story key; each skill says where it runs. No CLI: progress is the job sheet
and the Jira development panel.

## What happens to the current repositories

- `main` on GitHub has Plans 1 to 5a. The unmerged branches (adoption, 5b-A, 5b-B, 6, 6b) stay as they are, under the
  tag. The new layout is built on `docs/plan-7-skills-first` and becomes the one pull request to `main` when the user
  is ready to run CI.
- The demo workspace is re-baselined: rendered harness files and hooks removed, starter files copied, the plugin installed.

## Success criteria

- A new engineer can install aidlc in Claude Code with two commands, and in Copilot by copying one folder.
- One story runs end to end on the demo workspace in Claude Code using only skills, agents and starter files.
- The same skills load in Copilot (VS Code agent mode or the CLI); Codex or Cursor load them when installed.
- `scripts/validate.py` passes; the repository has no Python package, hooks or policy engine.
