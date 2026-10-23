# GitHub Copilot adapter: planned

Status: planned, not built. `aidlc render --tool copilot` exits 2 with a pointer to this page. The
facts below come from GitHub's and VS Code's docs, read 2026-10-23. The same facts, side by side
with the other tools, are in the generated [capabilities.md](capabilities.md), from
`core/adapters/copilot.yaml`.

## Three surfaces, three sets of files

"Copilot" is more than one agent. Each surface reads a different set of files, so the adapter
renders for each one.

| Surface | What it is | Reads |
|---|---|---|
| VS Code, Copilot harness (shared with the Copilot CLI) | The agent in VS Code's chat, and `copilot` in a terminal | `AGENTS.md`, `.github/copilot-instructions.md`, `.github/instructions/`, skills, `.github/agents/`, `.github/hooks/`, `.mcp.json`, and `.claude/settings.json` hooks |
| VS Code **Local** | VS Code's own agent mode | The same instructions and agents; MCP from `.vscode/mcp.json` |
| The **cloud agent** | Runs in a GitHub Actions VM and opens a pull request | Instructions, agents and only `.github/hooks/*.json`; MCP from repository settings |

## What changed since the first notes (2026-10-18)

- **Agents** are `.github/agents/<name>.agent.md`. Their `tools:` list uses aliases: `read`,
  `edit`, `execute`, `search`. That maps onto aidlc's tool classes.
- **Permissions are real.** An organisation's `managed-settings.json` sets `permissions` (deny beats
  ask, ask beats allow), generally available since 2026-07-01. The CLI also takes `--deny-tool`.
  `core/policy/permissions.yaml` can render to these, as it does to Claude Code's settings.
- **There is an OS sandbox.** VS Code has `chat.agent.sandbox`, and the CLI has `--sandbox`
  (bubblewrap on Linux). The cloud agent runs in a VM behind a firewall.
- **Hooks.** `.github/hooks/*.json` with a `preToolUse` event. A deny is `permissionDecision: deny`
  on stdout, or exit 2. A crash denies. A **timeout lets the call through (fail open)**. In the
  cloud agent, "ask" becomes "deny", which matches aidlc's unattended default.
- **Copilot also runs Claude Code's hooks.** The Copilot harness reads `.claude/settings.json`. In
  a repository rendered for both tools, the guard could run twice for one call. The Copilot render
  must prevent that, and a test must prove it (ADR 0006).
- **Organisation settings can switch other harnesses off.** Managed settings can turn off the Claude
  and Codex harnesses inside VS Code, so a team can standardise on one.

## Implementation outline

| Element | Copilot output |
|---|---|
| `render_rules` | `AGENTS.md` (read natively) and a pointer in `.github/copilot-instructions.md` |
| `render_folder_rules` | `.github/instructions/<name>.instructions.md` with `applyTo:` globs |
| `render_skills` | `.agents/skills/<name>/SKILL.md` (Copilot, Cursor and Codex all read it), or a Copilot plugin |
| `render_agents` | `.github/agents/<name>.agent.md`, tools from the descriptor's `tool_names` |
| `render_permissions` | managed-settings `permissions` (an organisation proposal, like ADR 0003's platform patch) and agent tool lists |
| `render_hooks` | `.github/hooks/aidlc.json` → a Copilot dialect of the shim (`core/hooks/claude_shim.py` `run`) |

Because timeouts fail open, the guard stays fast (under a second, no network). The declarative deny
rules, the sandbox and the trusted CI are the backstop.

## Acceptance test for the implementation

- The shared hook fixture suite passes through the Copilot dialect.
- `aidlc render --tool copilot --check` is clean on the demo repositories.
- Rendering Copilot after Claude Code keeps every Claude Code file (the manifest's owners).
- A repository rendered for both tools runs the guard once per call.
