# Hooks

These scripts are the enforcement layer of the harness (guide chapter 3). They are sources: `aidlc render` copies them into a repository's `.aidlc/hooks/`, next to the generated `harness.json`. Do not edit the rendered copies.

They must stay standard-library only. They run as standalone scripts in any repository, with no `aidlc` package, no `yaml`, no `jsonschema` and no network. Each run must finish in under one second, and every error path must fail closed.

## guard.py (pre-tool guard)

Decides `allow`, `ask` or `deny` for each agent tool call. "allow" means "no objection": permissions and the sandbox still apply.

Generic contract:

- stdin: `{"session": str, "call": str, "tool": "read|edit|shell|mcp|external", "args": {...}, "cwd": str}`
- stdout: `{"decision": "allow|ask|deny", "rule": str, "reason": str}`

Any other tool class is denied (`unknown-tool`). Unreadable input, missing or corrupt `harness.json`, and any internal error give `deny` (`fail-safe`).

What it checks:

- Edits: paths are resolved (symlinks, `..`, absolute paths) and must stay inside the repository. Protected paths are always denied. Otherwise the path must match the task scope for the current branch.
- Shell: each command in a chain, substitution or multi-line script is matched against `shell_deny`. Piping into a shell is denied. A nested shell (`bash -c`, `eval`) needs a person.
- MCP tools: matched against `tool_deny` (deny) and `tool_ask` (ask).
- External reach: always asks.

Every decision appends one JSON line to `decisions.jsonl`. Secret-shaped values are redacted.

## Environment

| Variable | Effect |
| --- | --- |
| `AIDLC_HARNESS_FILE` | Harness data file. Default: `harness.json` next to the script. |
| `AIDLC_UNATTENDED=1` | Every `ask` becomes `deny`. |
| `AIDLC_SCOPE=off` | Edit scope is not enforced. Refused when unattended. Logged. |
| `AIDLC_SCOPE_FILE` | Explicit scope file. Ignored if it lives inside the repository. |
| `AIDLC_HOME_DIR` | Base for scope files. Default: `~/.aidlc`. Scope files live at `scopes/<repo>/<branch with / as __>.scope`. |
| `AIDLC_LOG_DIR` | Log directory. Default: `~/.aidlc/logs`. |
