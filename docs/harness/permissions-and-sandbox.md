# Permissions and sandbox

Permissions decide which tool calls the tool allows, asks about or refuses. The sandbox limits
what a command can touch once it runs. You need both, because they cover different routes.

The policy is `core/policy/permissions.yaml`. It owns every value: secret paths, protected
paths, and the deny, ask and allow lists. This page explains how they are rendered. It does not
repeat them.

> ⚠️ **Watch out:** Start Claude Code at the repository root. A session started in a
> subdirectory does not load the project settings, so no permissions, sandbox or hooks apply
> ([check 7](../verification/2026-10-18-sandbox-wsl2.md#2026-10-19-check-7)).
> The [root guard](root-guard.md), installed through managed settings, refuses such sessions.

## Precedence and defaults

Deny beats ask, and ask beats allow. A call that matches nothing falls to the default: ask when
a person is present, deny when nobody is. The policy file states both.

There is one exception. The Claude Code adapter sets `autoAllowBashIfSandboxed: true`, so a
shell command that matches no rule runs inside the sandbox without asking. Ask rules and deny
rules still apply to it (verified live, check 3), and the guard hook still judges it. The
sandbox is what makes this safe: the command cannot read secrets, write protected files or
reach unknown hosts.

## What the Claude Code adapter renders

`aidlc render --tool claude-code` writes `.claude/settings.json` from the effective permissions.
The code is `cli/aidlc/adapters/claude_code.py`.

| Effective permissions | `.claude/settings.json` |
|---|---|
| `allow` read, edit, shell, tools | `permissions.allow` as `Read`, `Edit(./path)`, `Bash(pattern)` and mapped tool names |
| `ask` edit, shell, tools | `permissions.ask` |
| `deny` read and `secret_paths` | `permissions.deny` as `Read(path)`; also `sandbox.filesystem.denyRead` (a bare name such as `.env.*` as both `./.env.*` and `./**/.env.*`) |
| `deny` edit and `protected_paths` | `permissions.deny` as `Edit(path)`; also `sandbox.filesystem.denyWrite` for the paths that exist at render time |
| `deny` shell and tools | `permissions.deny` as `Bash(pattern)` and mapped tool names |
| Profile and repository additions | `sandbox.filesystem.allowWrite`, `sandbox.network.allowedDomains` |
| Fixed hardening | `sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`, `disableBypassPermissionsMode` |
| Hook entries | `hooks.PreToolUse`, `hooks.PostToolUse` and `hooks.PostToolUseFailure`, see [hooks](hooks.md) |

Tool names such as `tracker.read_issue` are tool-neutral. The repository's `.aidlc/config.yaml`
maps them to the tool's names. An unmapped name is dropped from the rendered list, and doctor
check D7 warns about it.

## Secret paths are denied twice

The Read tool runs outside the sandbox. Commands run inside it. A single control therefore
covers only one route.

- `Read()` deny rules stop the Read tool.
- Sandbox `denyRead` stops commands such as `cat .env` and test runners. A bare-name secret
  pattern such as `.env.*` is rendered at the root and at any depth, so `cat apps/web/.env.local`
  in a monorepo is denied too.

This was verified live. See [the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md),
including check 5 for the nested `.env` case. Doctor check D2 fails if any entry is missing.

## Protected paths: who covers what

Protected paths are the files the agent must not change. Which layers cover a path depends on
whether it exists when you render.

| Path | Edit tools | Shell commands |
|---|---|---|
| Exists at render time (tracked, or present and not ignored) | `Edit()` deny rule, then the guard | Sandbox `denyWrite` blocks the write; the post-check would also flag it |
| Does not exist yet | `Edit()` deny rule, then the guard | The post-check flags the new file (`protected-path`) after the call |

So an existing protected file is covered three times. A new one is prevented for the Edit tools
and detected, not prevented, for the shell.

## What the sandbox enforces

These facts were verified live on 2026-10-19. The evidence is the addendum in
[the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md) (see its subsection "2026-10-19, checks 3 and 4" for the ask-rule and missing-literal-file results) and the rows in [the
attack run](../verification/2026-10-19-harness-attacks.md).

- **`denyRead` enforces globs**, including `**`. Secret-path globs are rendered as they are.
- **`denyWrite` enforces only literal files and directories.** It also blocks the creation of
  a missing literal file. But for a missing path the sandbox puts a placeholder at that path
  (check 6): it shows in the worktree as a character device and `git status` lists it as
  untracked. A missing `.git/packed-refs` placeholder even breaks every git command.
- **Literal entries are therefore rendered only for paths that exist at render time,** and
  protected-path globs are expanded to the existing files they match (`git ls-files --cached
  --others --exclude-standard`). A new matching file relies on the `Edit` rules, the guard and
  the post-check until the next render. `aidlc render --check` and doctor D1 report that drift.
- **Git refs are not pinned with `denyWrite`.** Git packs loose refs during auto-gc, and a
  pinned ref would then become an unreadable placeholder. The base branch is protected by the
  scope's recorded base commit and the guard's `base-ref` rule instead, see [hooks](hooks.md).
- **`.git/**` is denied for writes as `./.git/hooks` and `./.git/config`.** Denying all of `.git`
  would break commits, and these two are the paths that run code or change settings.
- **Untrusted workspaces ignore only `permissions.allow`.** Deny and ask rules, hooks and the
  sandbox all still apply.
- **Ask rules stay enforced** with `autoAllowBashIfSandboxed`. The sandbox auto-approves commands
  that pass the rules. It does not skip them.

> ⚠️ **Watch out:** After you add a file that matches a protected path, such as a new
> `scripts/check-x.sh` or a first `api/` contract, run `aidlc render --tool claude-code` and
> commit the result. Until then the post-check only detects a shell write; it does not prevent it.

> ⚠️ **Watch out:** Inside a sandboxed session, `git add -A` and `git add .` fail. Claude Code's
> own sandbox puts placeholders at protected dotfiles such as `.bashrc`, `.gitconfig`, `.vscode`,
> `.idea`, `.claude/settings.local.json` and `.mcp.json`, and git cannot read them. Stage
> explicit paths: `git add src/feature/a.ts test/feature/a.test.ts`. The evidence is check 6 in
> [the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md#2026-10-19-checks-5-and-6).

## Evidence the agent cannot write

The harness keeps its own evidence where agent shells cannot write it. Two `denyWrite` entries
carry most of the weight:

- **`~/.aidlc`** holds the task scopes, the decision log, the retry counter's attempts record and
  the recorded framework entry. A shell cannot rewrite its own audit trail, widen its scope or
  reset its counter.
- **`./.aidlc`** holds the rendered hooks, the manifest and the `aidlc ci` records in
  `.aidlc/ci-records/`. An agent cannot plant a passing CI record. The `Edit(.aidlc/**)` deny rule
  covers the Edit tools.

The shell deny rule `aidlc attempts*--reset*` closes the last route: the command that resets the
counter. Only a person runs it, after reading why the agent kept failing.

`aidlc ci` runs the change's own code in a second, stricter sandbox: bubblewrap with a private
home and no network outside the install step. That one is described in [trusted CI](../checks/ci.md#the-sandbox).

## Narrowing in a repository

A repository may only tighten the baseline. It does this in `.aidlc/permissions.yaml`, validated
by `core/schemas/repo-permissions.schema.json`. Three keys loosen: `allow_add`,
`network_allow_add` and `sandbox_allow_write_add`. Each entry needs a reason and an owner, and
doctor D6 warns on each one. Render refuses a sandbox write grant that would reach the harness or
your executables: `/`, `~`, anything under `~/.claude` or `~/.aidlc`, `~/.local/bin`, `~/bin`,
`/usr`, `/bin`, any parent of these, a symlink to any of them, and any path containing `..`,
a variable such as `$HOME`, or a `~user` form.

```yaml
# .aidlc/permissions.yaml
deny_add:
  shell: ["terraform apply*"]       # agents plan, people apply
ask_add:
  edit: ["db/migrations/**"]        # a person confirms each migration edit
secret_paths_add: ["config/prod/**"]
allow_remove:
  shell: ["git commit *"]           # this repository commits by hand
network_allow_add:
  - {value: cdn.playwright.dev, reason: "browser downloads for e2e tests", owner: "@web-team"}
sandbox_allow_write_add:
  - {value: "~/.cache/ms-playwright", reason: "browser cache for e2e tests", owner: "@web-team"}
```

Run `aidlc render --tool claude-code` after any change, and commit the rendered files.

## Unattended runs

When nobody can answer a prompt, an ask has no one to go to. Run unattended agents like this:

- Start the tool with `--permission-mode dontAsk`.
- Set `AIDLC_UNATTENDED=1`, so the guard turns every `ask` into `deny` as well.

Then nothing waits for a human, and nothing is approved by default.

> ⚠️ **Watch out:** In a workspace Claude Code has not trusted, project `permissions.allow` entries are ignored. `--permission-mode dontAsk` then refuses every Bash command that is not otherwise allowed. Run unattended sessions in a trusted workspace, such as the CI checkout. See [the attack run](../verification/2026-10-19-harness-attacks.md), notes on rows 2a-2c and 6. Details are in
[hooks](hooks.md).

> 🎯 **What this means for you:** Change the policy in `core/policy/permissions.yaml` only with
> a design change. Everything else is a repository narrowing.

Guide: 3 step 3, 3 step 4, 3.4.
