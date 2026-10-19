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
| `AIDLC_UNATTENDED` | Any non-empty value except `0`, `false` or `no` (case-insensitive) makes every `ask` a `deny`. |
| `AIDLC_SCOPE=off` | Edit scope is not enforced. Refused when unattended. Logged. |
| `AIDLC_SCOPE_FILE` | Explicit scope file. Ignored if it lives inside the repository. |
| `AIDLC_HOME_DIR` | Base for scope files. Default: `~/.aidlc`. Scope files live at `scopes/<repo>/<branch with / as __>.scope`. |
| `AIDLC_LOG_DIR` | Log directory. Default: `~/.aidlc/logs`. |

## Deliberate limits

The guard is a fast, pattern-based layer, not a shell. One scanner (`_lex`) reads the whole command once, left to right, with a stack of nesting levels, and follows bash 5.2 parsing rules:

- Quotes: single, double, `$'..'` (backslash escapes do not end it) and `$".."`. Backslashes, and backslash-newline line continuations.
- Comments: an unquoted `#` at the start of a word, up to the newline.
- Operators and redirections, including `N>` and `{var}>`. A redirection and its target are dropped.
- Heredocs: `<<` and `<<-`, several on one line, read in order. A `<<` opens a heredoc only when it is unquoted, outside a comment and outside `(( ))`, `$(( ))` and `${..}`. A body with a quoted delimiter is data. An unquoted body is scanned for substitutions.
- Arithmetic: `(( ))` and `$(( ))`, where `<<` is a shift and `#` is not a comment. A `((` that `))` does not close is read again as subshells or a command substitution, as bash does.
- `${..}`: blanks, `#`, `<<`, `;` and `)` inside it are literal.
- `case` patterns inside `$(..)`: their `)` does not end the substitution.

Substitutions (`$(..)`, backticks, `<(..)`, `>(..)`) are found wherever bash expands them, not inside single quotes, and each is analysed as a command. `bash -c` and `eval` strings are analysed recursively. Wrappers (`env`, `timeout`, `xargs`, `coproc` and similar), absolute paths, git global options and function bodies are normalised before `shell_deny` is matched.

It deliberately cedes these to the permissions and the sandbox backstop:

- Escape sequences inside ANSI-C quoting, for example `git $'\x70ush'`. The extent of the quote is modelled, but its escapes are not decoded.
- Brace expansion such as `git {push,x}`.
- Variable indirection, for example `X=push; git $X` or `${IFS}` tricks, and the output of a substitution used as a word, such as `$(echo git) push`.
- Interpreters running code, for example `python3 -c`, `node -e`.
- Parsing differences between bash and other shells such as zsh or `sh`. The one known case that could hide a command, a `'` inside `"${..}"`, asks instead.

Anything it cannot parse asks a person (denies when unattended). Unbalanced quotes are unparseable. So is a line continuation (backslash-newline) inside an operator, for example between the two `<` of `<<` or between `$` and `(`, because bash joins the lines first. A heredoc left open inside a substitution is unparseable too, because bash then takes its body from the next raw newline. So is a `'` inside `"${..}"`, which bash reads as a quote and `sh` (dash) as a plain character. A command longer than 65,536 characters, nested deeper than 40 levels, or taking more than 0.5 s to analyse is denied (`fail-safe`). The deadline is checked inside the scanner, the heredoc reader and the segment loop, so every input is decided well within one second. `SECRET_RE` is a best-effort list of secret shapes. It redacts the log and the returned reason. It does not guarantee that no secret ever appears.

Edits are also denied for anything under `.git/`, for files with more than one hard link, and when the scope file lives inside the repository or names absolute, `..` or `.git` patterns.
