# Doctor

`aidlc doctor [path]` checks that the harness in a repository is intact and enforceable. It
compares the rendered files with what render would write now, and checks them against the effective policy, so it catches edits and drift. The code is
`cli/aidlc/checks/doctor.py`. A FAIL exits non-zero. A WARN is information you should read.

Run it after every render, after upgrading Claude Code and in CI.

| Check | Level | What it checks | How to fix |
|---|---|---|---|
| D1 | FAIL | The rendered files (`CLAUDE.md`, rules, `.claude/settings.json`, `.aidlc/hooks/`) match what render would write now, and the effective permissions can be computed | Run `aidlc render --tool claude-code` and commit. If it cannot compute, fix the message it prints (usually `.aidlc/permissions.yaml`) |
| D2 | FAIL | Every secret path has a `Read()` deny and its sandbox `denyRead` entries (a bare name such as `.env` needs both `./.env` and `./**/.env`) | Render again. Never hand-edit settings |
| D3 | FAIL | Sandbox enabled, `failIfUnavailable` true, `allowUnsandboxedCommands` false, bypass mode disabled, no bare tool in `allow` | Render again. A bare tool rule means a stray hand edit |
| D4 | FAIL | Exactly one hook entry for each of `PreToolUse`, `PostToolUse` and `PostToolUseFailure`, with the adapter's matcher (pre `.*`, so every tool reaches the guard; both post events share the post matcher) and `onFailure: block`; all hook files exist; a self-test shows the guard denies `git push`, denies on unreadable data and denies garbage input. The self-test runs with `python -I -B`, so it leaves no `__pycache__` | Render again. A failing self-test means the copy was tampered with |
| D5 | FAIL | `bwrap` and `socat` are on PATH (Linux) | Install them, for example `sudo apt install bubblewrap socat` |
| D6 | WARN | Each `allow_add`, `network_allow_add` and `sandbox_allow_write_add` entry in `.aidlc/permissions.yaml` loosens the baseline; the warning names the value, reason and owner | Confirm the reason and owner are still right, or remove the entry |
| D7 | WARN | A tool name in the policy has no mapping in `.aidlc/config.yaml` and is dropped | Add the mapping, or the rule does nothing |
| D8 | FAIL, WARN | `@` imports in `CLAUDE.md` stay inside the repository and resolve to a file. Over 200 lines fails, over 80 warns | Shorten the imported file, or link instead of importing |
| D9 | WARN | Each server in `.mcp.json` is in the tool register | Register the server, or remove it |
| D10 | FAIL, WARN | Claude Code is at least 2.1.295, which `onFailure` needs. Unknown version warns | Upgrade Claude Code |
| D11 | FAIL, WARN | Protected paths, see below | See below |
| D12 | FAIL | The base branch (`harness.base_branch`, default `main`) exists | Commit on the base branch, or set `harness.base_branch` in `.aidlc/config.yaml` |
| D13 | FAIL, WARN | Settings files that override the harness, see below | Remove the override, or move the need into `.aidlc/permissions.yaml` |
| D14 | FAIL | With `ci: [github]`, the toolchain file the workflow reads exists at the repository root: `.nvmrc` for node, `global.json` for dotnet | Add the file and commit it |

## D11: protected paths

Protected paths are the files the agent must not edit. D11 checks each one in the effective
permissions.

- **FAIL: no `Edit(<entry>)` deny rule.** The Edit tool could change the file. Render again.
- **FAIL: a literal entry that exists has no sandbox `denyWrite` entry.** A command such as
  `echo >> AGENTS.md` could change the file. Render again. A literal entry that does not exist
  gets no `denyWrite` entry on purpose: the sandbox would put a placeholder in the worktree.
- **WARN: a glob entry.** The sandbox cannot enforce globs for writes. It covers only files
  that exist at render time (tracked, or present and not ignored). A new matching file relies on
  the `Edit` deny rule, the guard (Edit tools) and the post-check (shell). Run
  `aidlc render --tool claude-code` after you add one, so the new file is listed.

The reasons are in [permissions and sandbox](permissions-and-sandbox.md). If D11 cannot compute
the expected entries, it fails with the reason. The usual cause is a directory that is not a git
repository, because the expansion needs `git ls-files`.

## D13: settings that override the harness

Claude Code merges several settings files. Three can weaken what render wrote:
`.claude/settings.local.json`, user settings (under `CLAUDE_CONFIG_DIR` when it is set) and
managed settings. D13 reads each one that exists. It fails when a file:

- turns the sandbox off or makes it optional, allows unsandboxed commands, or re-enables bypass
  mode (local and managed settings only: those outrank the project file);
- sets `disableAllHooks`, or `permissions.defaultMode: bypassPermissions`;
- sets an `env` variable that redirects or disables the harness, such as `AIDLC_HOME_DIR`,
  `AIDLC_HOME`, `AIDLC_TOOLS_DIR`, `AIDLC_USER_SETTINGS`, `AIDLC_MANAGED_SETTINGS` or
  `PYTHONPATH`, which could load another `aidlc` package (the full list is `HARNESS_ENV` in the
  doctor code);
- sets `sandbox.excludedCommands`;
- grants a sandbox `allowWrite` that reaches the harness;
- grants an `allowWrite` or `additionalDirectories` entry that overlaps the framework: its root
  (the directory above the recorded `bin/aidlc`), anything under it such as `cli/` or
  `core/hooks/`, or any parent of it. An agent that can write the framework's code could forge a
  passing check;
- holds a grant containing `$`. Doctor cannot resolve it, and a grant it cannot resolve counts
  as reaching.

It warns when a file cannot be read, allows a bare tool, defines its own hooks, or sets `PATH` in
`env`. A `PATH` that puts a writable directory first changes which tools the agent's commands run.

## What doctor cannot see

Doctor reads the repository. It cannot see how a session starts.

- **Where the session starts.** A session started in a subdirectory does not load the project
  settings, so no permissions, sandbox or hooks apply (check 7 in
  [the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md#2026-10-19-check-7)).
  Start Claude Code at the repository root. The optional [root guard](root-guard.md) can enforce
  it; the framework does not require it.
- **Options given when a session starts.** D13 reads the settings files. It cannot see a
  `--settings` file or a permission mode passed on the command line.

## Reading the output

D1 is the first thing to fix, because the other checks read the rendered files. If D1 fails,
render, then run doctor again before you chase the rest.

> 💡 **Tip:** Doctor never changes anything. It is safe to run in CI and in a pre-commit hook.

Guide: 3 step 9, 3.7.
