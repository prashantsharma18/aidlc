# Quickstart: GitHub Copilot

Copilot reads Agent Skills (`SKILL.md` folders) in agent mode in VS Code, the Copilot CLI, the Copilot coding agent and
Copilot code review. It looks for project skills in `.github/skills/`, `.claude/skills/` or `.agents/skills/`, and for
your own in `~/.copilot/skills/` (see GitHub's "Adding agent skills for GitHub Copilot").

1. **Add the skills** to the repository (shared with the team):
   ```bash
   mkdir -p .github/skills && cp -r /path/to/aidlc/skills/* .github/skills/
   ```
   For yourself only: copy the same folders into `~/.copilot/skills/`.
   Copilot CLI and the cloud agent can instead install the plugin from this repository's marketplace and switch it on
   in `.github/copilot/settings.json` (`enabledPlugins`).
2. **Add the agents** as Copilot custom agents: copy each `agents/<name>.md` to `.github/agents/<name>.agent.md`. Keep
   the `tools:` line: Copilot reads Claude's names as aliases (`Read` is `read`, `Grep` and `Glob` are `search`, `Edit`
   and `Write` are `edit`, `Bash` is `execute`). Without it, a custom agent gets every tool, and the read-only
   explorer and reviewers could edit files and run commands.
3. **Copy the starter files**: `AGENTS.md` (Copilot reads it) and `CODEOWNERS`. Copilot does not use
   `.claude/settings.json`; use your organisation's Copilot content exclusion for secrets. aidlc has not been
   tested in Copilot yet (ADR 0024); an adapter is a later plan.
4. **Onboard and work** in agent mode: ask "use the aidlc-onboard skill", then "use aidlc-start for SHIP-12". Copilot
   loads a skill when the request matches its description, or when you name it.

A skill's text names no tool-specific command, so the same skills run unchanged. Skills marked
`disable-model-invocation` in Claude Code may load on their own in Copilot; ask for stage skills by name.

Next: [how to adopt aidlc](../operating-model/adoption.md), on a new system or an existing one in phases, and
[the eight routes](../operating-model/routes.md) `aidlc-start` chooses from.

The commands you type, stage by stage: [the README's table](../../README.md#commands-you-type).
