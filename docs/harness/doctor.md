# Doctor

`aidlc doctor [path]` checks that the harness in a repository is intact and enforceable. It
compares the rendered files with what render would write now, and checks them against the effective policy, so it catches edits and drift. The code is
`cli/aidlc/checks/doctor.py`. A FAIL exits non-zero. A WARN is information you should read.

Run it after every render, after upgrading Claude Code and in CI.

| Check | Level | What it checks | How to fix |
|---|---|---|---|
| D1 | FAIL | The rendered files (`CLAUDE.md`, rules, `.claude/settings.json`, `.aidlc/hooks/`) match what render would write now, and the effective permissions can be computed | Run `aidlc render --tool claude-code` and commit. If it cannot compute, fix the message it prints (usually `.aidlc/permissions.yaml`) |
| D2 | FAIL | Every secret path has a `Read()` deny and a sandbox `denyRead` entry | Render again. Never hand-edit settings |
| D3 | FAIL | Sandbox enabled, `failIfUnavailable` true, `allowUnsandboxedCommands` false, bypass mode disabled, no bare tool in `allow` | Render again. A bare tool rule means a stray hand edit |
| D4 | FAIL | Exactly one pre and one post hook entry, with the adapter's matcher and `onFailure: block`; all hook files exist; a self-test shows the guard denies `git push`, denies on unreadable data and denies garbage input | Render again. A failing self-test means the copy was tampered with |
| D5 | FAIL | `bwrap` and `socat` are on PATH (Linux) | Install them, for example `sudo apt install bubblewrap socat` |
| D6 | WARN | Each `allow_add` in `.aidlc/permissions.yaml` loosens the baseline | Confirm the reason and owner are still right, or remove the entry |
| D7 | WARN | A tool name in the policy has no mapping in `.aidlc/config.yaml` and is dropped | Add the mapping, or the rule does nothing |
| D8 | FAIL, WARN | `@` imports in `CLAUDE.md` stay inside the repository and resolve to a file. Over 200 lines fails, over 80 warns | Shorten the imported file, or link instead of importing |
| D9 | WARN | Each server in `.mcp.json` is in the tool register | Register the server, or remove it |
| D10 | FAIL, WARN | Claude Code is at least 2.1.295, which `onFailure` needs. Unknown version warns | Upgrade Claude Code |
| D11 | FAIL, WARN | Protected paths, see below | See below |

## D11: protected paths

Protected paths are the files the agent must not edit. D11 checks each one in the effective
permissions.

- **FAIL: no `Edit(<entry>)` deny rule.** The Edit tool could change the file. Render again.
- **FAIL: a literal entry has no sandbox `denyWrite` entry.** A command such as
  `echo >> AGENTS.md` could change the file. Render again.
- **WARN: a glob entry.** The sandbox cannot enforce globs for writes. It covers only files
  tracked at render time. A new matching file relies on the `Edit` rules and the guard. Run
  `aidlc render --tool claude-code` after you add one, so the new file is listed.

The reasons are in [permissions and sandbox](permissions-and-sandbox.md). If D11 cannot compute
the expected entries, it fails with the reason. The usual cause is a directory that is not a git
repository, because the expansion needs `git ls-files`.

## Reading the output

D1 is the first thing to fix, because the other checks read the rendered files. If D1 fails,
render, then run doctor again before you chase the rest.

> 💡 **Tip:** Doctor never changes anything. It is safe to run in CI and in a pre-commit hook.

Guide: 3 step 9, 3.7.
