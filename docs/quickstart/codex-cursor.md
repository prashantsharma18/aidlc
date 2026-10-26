# Quickstart: Codex and Cursor

Both read the same `SKILL.md` folders and `AGENTS.md`.

| Tool | Skills folder | Rules |
|---|---|---|
| Codex | `.agents/skills/` in the repository; `~/.agents/skills/` for yourself | `AGENTS.md` |
| Cursor | `.cursor/skills/` or `.agents/skills/` | `AGENTS.md`, or a short `.cursor/rules/` file pointing to it |

1. Copy `plugins/aidlc/skills/*` into the folder above (and `plugins/aidlc-modernize/skills/*` in a repository
   being modernised), plus the starter's `AGENTS.md`, `scripts/`, CI workflow and CODEOWNERS. Declare any pack in
   AGENTS.md's `Packs used here`; `python3 scripts/check_packs.py` checks the copied folders against it.
2. Ask the agent to use `aidlc-onboard` once, then `aidlc-start` for each piece of work.

The agents in `plugins/*/agents/` are written for Claude Code; in these tools, a skill that "sends the explorer agent" works as a
focused, read-only sub-task in the same session.
