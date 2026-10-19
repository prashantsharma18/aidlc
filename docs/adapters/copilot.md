# GitHub Copilot adapter: extension point

Status: not built (decision D8). `aidlc render --tool copilot` exits 2 with a pointer to this
page. Adding Copilot means one shim and the six render functions in the
[adapter interface](interface.md). Nothing in the core changes.

## Mapping to implement (locations verified 2026-10-18)

| Core element | Copilot location |
|---|---|
| Shared rules | `AGENTS.md` (read natively) plus a pointer in `.github/copilot-instructions.md` |
| Folder rules | `.github/instructions/<name>.instructions.md` with `applyTo:` globs |
| Skills | `.claude/skills/<name>/SKILL.md` (Copilot reads this location), or `.github/skills/` |
| Agent roles | `.github/agents/<name>.md`, which can restrict tools and set `mcp-servers` |
| Hooks | `.github/hooks/*.json`: `preToolUse` with `permissionDecision` `allow`, `deny` or `ask`; exit 2 denies |
| Permissions | custom-agent tool restrictions; there is no direct `permissions.yaml` equivalent, so CI and code owners are the backstop |

## Portability gaps to design around
- `preToolUse` timeouts fail open (crashes fail closed). Keep guards fast; rely on the sandbox
  and trusted CI as backstops.
- In cloud-agent and autopilot runs `ask` becomes `deny`, which matches the framework's unattended default.

## Acceptance test for a future implementation
The shared hook fixture suite (Plan 2) passes through the Copilot shim, and `aidlc render --tool
copilot --check` is clean on the demo repositories.
