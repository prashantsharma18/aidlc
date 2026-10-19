# Hooks

These scripts are the enforcement layer of the harness (guide chapter 3). They are sources: `aidlc render` copies them into a repository's `.aidlc/hooks/`, next to the generated `harness.json`. Do not edit the rendered copies.

They must stay standard-library only. They run as standalone scripts in any repository, with no `aidlc` package, no `yaml`, no `jsonschema` and no network. Each run must finish in under one second, and every error path must fail closed.

## guard.py (pre-tool guard)

Decides `allow`, `ask` or `deny` for each agent tool call. "allow" means "no objection": permissions and the sandbox still apply.

Generic contract:

- stdin: `{"session": str, "call": str, "tool": "read|edit|shell|mcp|external", "args": {...}, "cwd": str}`
- stdout: `{"decision": "allow|ask|deny", "rule": str, "reason": str}`

Any other tool class asks a person (`unknown-tool`), which is `deny` when unattended. Unreadable input, missing or corrupt `harness.json`, and any internal error give `deny` (`fail-safe`).

What it checks:

- Edits: paths are resolved (symlinks, `..`, absolute paths) and must stay inside the repository. Protected paths are always denied. Otherwise the path must match the task scope for the current branch.
- Shell: each command in a chain, substitution or multi-line script is matched against `shell_deny`. Git commands that move the base branch (`harness.json` `base_branch`, default `main`) are denied (`base-ref`). Piping into a shell is denied. A nested shell (`bash -c`, `eval`) needs a person.
- MCP tools: matched against `tool_deny` (deny) and `tool_ask` (ask).
- External reach: always asks.

Every decision appends one JSON line to `decisions.jsonl`. Secret-shaped values are redacted.

## post_check.py (post-tool check)

Runs after `Edit`, `Write`, `MultiEdit`, `NotebookEdit`, `Bash`, `Monitor` and `BashOutput`. It cannot undo an action, so it flags. In order:

1. Output with a high-confidence credential shape (`BLOCK_SECRET_RE`: provider key prefixes, PEM private-key headers, long `Bearer` tokens, and quoted literals assigned to `password`, `secret`, `token` or `api_key`) flags `secret-in-output`. Read-class tools such as `BashOutput` stop here.
2. The base is `AIDLC_BASE_REF`, else the `base:` sha recorded in the scope file, else `base_branch`.
3. Any new or changed path (diff against the merge base, plus untracked files that are not ignored) that matches `protected_paths` or has a `.git` segment flags `protected-path`.
4. Then the scope, changed assertions and skipped tests.

### Retry limit (guide 8.8, 8.13)

`post_check.record_check` counts runs of the one-command check (`aidlc check` without a named check), and the guard enforces the limit. Claude Code does not fire `PostToolUse` for a Bash call that exits non-zero, so the shim also handles `PostToolUseFailure` (phase `post-failure`).

- A shell call counts only when some part of it runs the check, including inside a substitution, `bash -c` or `eval`.
- It is a PASS only when all hold: the whole command is exactly `aidlc check` (optionally `--repo <path>`, no assignment prefix, no wrapper) and its first word resolves (PATH for a bare word, the call's cwd for a path) to the framework's own entry point recorded in `$AIDLC_HOME_DIR/cli.json` by `aidlc render` (a missing, symlinked or malformed `cli.json` means no PASS); it exited 0; the last `check  result` line says `PASS`; no step line says `SKIPPED`; and the single `check  context` line names this repository, the base the post-check computes, the scope file the guard reads, and `mode=require`.
- Runs the parser cannot see (`python3 -m aidlc check`, `$A check`, make or npm wrappers) are still counted once: every check writes a fresh `run` id to `.check/result.json`, and an id the counter has not seen (`last_run` in the record) counts as one failing attempt on any shell call.
- Named checks (`context-drift`, `openwiki`) anywhere after `check`, other than as the value of `--repo`, are not the one-command check.
- Anything else that runs the check is a failing attempt. An unknown exit code (`None`) is never a PASS.
- A PASS resets the counter. Each failing attempt adds one. At `retry_cap` (`harness.json`, from `routing.yaml`, default 3) the post hook flags `retry-limit`, and the guard denies every `edit` and `shell` call with `retry-limit`. Reads stay allowed.
- Rule ids: `check-recorded` (post, pass) and `retry-limit` (post flag, pre deny).
- The record is `$AIDLC_HOME_DIR/attempts/<repo name>-<8 hex of the repo path hash>/<branch with / as __>.json`; a detached HEAD uses `__detached__.json`. Updates hold an exclusive `flock`, so parallel hooks lose no count.
- Fail closed: an unreadable record, a record, its directories (`attempts/`, `<repo>-<hash>/`) or its `.lock` being a symlink or not a regular file, counts as at the limit.
- Only hooks write the record. The sandbox denies `~/.aidlc` to agent shells, and `aidlc attempts*--reset*` is a shell deny rule, so an agent cannot reset its own counter. A person runs `aidlc attempts --reset`.

## claude_shim.py (Claude Code adapter shim)

Usage: `claude_shim.py pre|post|post-failure`. Post events carry `text` (stdout and stderr, or the error text) and `exit_code` (0 for `post`; parsed from `Exit code N` for `post-failure`, else `None`). Translates Claude Code hook payloads to the generic contract and back. `CLASSES` maps tool names to classes; an unlisted tool is `unknown`. On any internal error it exits 2 (a block) and writes one best-effort `fail-safe` record to the decision log.

## Environment

| Variable | Effect |
| --- | --- |
| `AIDLC_HARNESS_FILE` | Harness data file. Default: `harness.json` next to the script. |
| `AIDLC_UNATTENDED` | Any non-empty value except `0`, `false` or `no` (case-insensitive) makes every `ask` a `deny`. |
| `AIDLC_SCOPE=off` | Edit scope is not enforced. Refused when unattended. Logged. |
| `AIDLC_SCOPE_FILE` | Explicit scope file. Ignored if it lives inside the repository. |
| `AIDLC_HOME_DIR` | Base for scope files. Default: `~/.aidlc`. Scope files live at `scopes/<repo>/<branch with / as __>.scope`. The retry counter lives at `attempts/<repo>-<hash>/<branch>.json`, and `cli.json` records the framework's own `aidlc` entry point. |
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

Anything it cannot parse asks a person (denies when unattended). Unbalanced quotes are unparseable. So is a line continuation (backslash-newline) inside an operator, for example between the two `<` of `<<` or between `$` and `(`, because bash joins the lines first. A heredoc left open inside a substitution is unparseable too, because bash then takes its body from the next raw newline. So is a `'` inside `"${..}"`, which bash reads as a quote and `sh` (dash) as a plain character. A command longer than 65,536 characters, nested deeper than 40 levels, or taking more than 0.5 s to analyse is denied (`fail-safe`). The deadline is checked inside the scanner, the heredoc reader and the segment loop, so every input is decided well within one second. `SECRET_RE` is a broad, best-effort list of secret shapes. It only redacts the log and the returned reason, and it does not guarantee that no secret ever appears. Blocking uses the narrower `BLOCK_SECRET_RE`, so ordinary code such as `password: string;` or `const token = getToken();` is not flagged.

Edits are also denied for anything under `.git/`, for files with more than one hard link, and when the scope file lives inside the repository or names absolute, `..` or `.git` patterns.
