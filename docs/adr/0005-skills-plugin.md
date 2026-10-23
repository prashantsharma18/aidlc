<!-- aidlc template: adr -->
# 0005 · Skills and agents ship as a Claude Code plugin, generated from a tool-neutral core

Status: Accepted (2026-10-22; revised 2026-10-23 after ADR 0006). Implements design §4.3 and §5. · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (changes what every developer's agent loads)

## Context

- Design §4.3 names `render_skills` and `render_agents`, but leaves open how skills reach a session.
- Anthropic distributes skills and agents as **plugins**, from a git **marketplace**. An organisation
  installs them on every machine through managed settings (`extraKnownMarketplaces` registers the
  marketplace, `enabledPlugins` turns the plugin on, `strictKnownMarketplaces` limits the sources).
- `claude plugin eval` and `claude plugin validate` need a plugin.
- **A plugin cannot carry permission rules.** Only `agent` and `subagentStatusLine` take effect from a
  plugin's `settings.json`, and plugin subagents ignore `permissionMode`, `hooks` and `mcpServers`.
  The harness must stay in each repository's rendered settings, where the repository's hooks still
  see every subagent's tool call.
- Agent Skills is an open format. Copilot, Cursor and Codex read `SKILL.md` folders too
  (`docs/adapters/capabilities.md`).

## Decision

- **The tool-neutral source** is `core/skills/<skill>/SKILL.md` (front matter `name`, `description`,
  `metadata` only) and `core/agents/<role>.md` (tool classes `read`, `edit`, `shell`, a model tier).
- **The Claude Code plugin is generated** by `bin/aidlc plugin build` into `plugins/aidlc/`, with the
  marketplace file at `.claude-plugin/marketplace.json`. The generator is the Claude adapter's
  distribution output (ADR 0006): it lives in `cli/aidlc/adapters/claude_plugin.py` and reads Claude's
  tool names from `core/adapters/claude-code.yaml`. `--check` fails on any stale or hand-edited file.
- **The version carries a content hash** (`0.1.0+<12 hex>`). Users keep a cached plugin until the
  version string changes, so every content change reaches them.
- **Organisations pin a release.** Managed settings register the marketplace at a release tag
  (`ref`). A marketplace source takes a branch or tag, not a commit.
- **The harness stays in each repository's rendered settings.** The plugin adds skills and roles; it
  enforces nothing.
- **Skills declare how they start** (`metadata.invocation`). Only the read-only
  `aidlc-context-setup` (its survey) and `aidlc-verify` are `auto`. Every gated stage is `manual`,
  rendered as Claude's `disable-model-invocation: true`, so only a person starts it. An unknown value
  fails the build.
- **Every skill has "Common excuses" and "Red flags"**: the reasons an agent gives for skipping a gate,
  each with the reality, and the signs it is about to. The format test enforces both.
- **Seven roles stay tool-neutral** (explorer, planner, implementer, three reviewers, ops-diagnoser),
  so Copilot can have them too; Copilot has no `/code-review`. `eval-judge` is dropped.
- **Slices are never tracker sub-tasks.** They live in the plan and its task bundles.
- **Behaviour evals are deferred** to Plan 5c (the owner's decision of 2026-10-23): a pressure case
  per skill, and a "fires" and a "stays quiet" case for each `auto` skill, run with
  `claude plugin eval`. Until then, the skills rest on their text, the tracker policy, the harness
  and human review.
- **Credit.** The ideas of trigger pairs, pressure cases, "Common excuses" and "Red flags" come from
  addyosmani/agent-skills (MIT). Our text is our own, and nothing is installed from it.

## Consequences

- A repository's `config-policy` does not judge the plugin, which lives outside the repository. The
  framework's own CI does, with `plugin build --check` and `claude plugin validate --strict`.
- Skills write under `plans/<KEY>/`, which is outside the edit allow-list, so each write asks the person.
- Copilot later needs its own `render_skills` (`.agents/skills`) and `render_agents`
  (`.github/agents/*.agent.md`).

## Rejected alternatives

- **Skills committed into each repository** (`.claude/skills/`): every repository would carry a copy
  to keep in step, and a hand edit could weaken a gate unnoticed.
- **A plugin that also carries the harness**: plugins cannot carry permission rules.
