# Quickstart: Codex and Cursor

Both read the same `SKILL.md` folders and `AGENTS.md`.

| Tool | Skills folder | Rules |
|---|---|---|
| Codex | `.agents/skills/` in the repository; `~/.agents/skills/` for yourself | `AGENTS.md` |
| Cursor | `.cursor/skills/` or `.agents/skills/` | `AGENTS.md`, or a short `.cursor/rules/` file pointing to it |

1. Copy `skills/` into the folder above, and the starter's `AGENTS.md`, CI workflow and CODEOWNERS.
2. Ask the agent to use `aidlc-onboard` once, then `aidlc-start` for each piece of work.

The agents in `agents/` are written for Claude Code; in these tools, a skill that "sends the explorer agent" works as a
focused, read-only sub-task in the same session.
