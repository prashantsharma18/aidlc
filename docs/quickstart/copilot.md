# Quickstart: GitHub Copilot

Copilot reads Agent Skills (`SKILL.md` folders) in agent mode in VS Code, the Copilot CLI, the Copilot coding agent and
Copilot code review. It looks for project skills in `.github/skills/`, `.claude/skills/` or `.agents/skills/`, and for
your own in `~/.copilot/skills/` (see GitHub's "Adding agent skills for GitHub Copilot").

1. **Add the skills** to the repository (shared with the team):
   ```bash
   mkdir -p .github/skills && cp -r /path/to/aidlc/skills/* .github/skills/
   ```
   or for yourself only: `cp -r /path/to/aidlc/skills/* ~/.copilot/skills/`.
2. **Add the agents** as Copilot custom agents: copy each `agents/<name>.md` to `.github/agents/<name>.agent.md`. Remove
   the `tools:` line (it uses Claude Code's tool names), or replace it with Copilot's tool names for read-only agents.
3. **Copy the starter files**: `AGENTS.md` (Copilot reads it), `.github/workflows/ci.yml`, `.github/CODEOWNERS`. Copilot
   does not use `.claude/settings.json`; use your organisation's Copilot content exclusion for secrets.
4. **Onboard and work** in agent mode: ask "use the aidlc-onboard skill", then "use aidlc-start for SHIP-12". Copilot
   loads a skill when the request matches its description, or when you name it.

A skill's text names no tool-specific command, so the same skills run unchanged. Skills marked
`disable-model-invocation` in Claude Code may load on their own in Copilot; ask for stage skills by name.
