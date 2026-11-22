# Quickstart: Codex and Cursor

Both read the same `SKILL.md` folders and `AGENTS.md`.

| Tool | Skills folder | Rules |
|---|---|---|
| Codex | `.agents/skills/` in the repository; `~/.agents/skills/` for yourself | `AGENTS.md` |
| Cursor | `.cursor/skills/` or `.agents/skills/` | `AGENTS.md`, or a short `.cursor/rules/` file pointing to it |

1. Copy `skills/*` into the folder above, plus the starter's `AGENTS.md` and `CODEOWNERS`. aidlc has not been
   tested in these tools yet (ADR 0024); adapters are a later plan.
2. Ask the agent to use `aidlc-onboard` once, then `aidlc-start` for each piece of work.

The agents in `agents/` are written for Claude Code; in these tools, a skill that "sends the explorer agent" works as a
focused, read-only sub-task in the same session.

Next: [how to adopt aidlc](../operating-model/adoption.md), on a new system or an existing one in phases, and
[the nine routes](../operating-model/routes.md) `aidlc-start` chooses from.

The commands you type, stage by stage: [the README's table](../../README.md#commands-you-type).
