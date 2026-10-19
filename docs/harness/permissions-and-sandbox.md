# Permissions and sandbox

Permissions decide which tool calls the tool allows, asks about or refuses. The sandbox limits
what a command can touch once it runs. You need both, because they cover different routes.

The policy is `core/policy/permissions.yaml`. It owns every value: secret paths, protected
paths, and the deny, ask and allow lists. This page explains how they are rendered. It does not
repeat them.

## Precedence and defaults

Deny beats ask, and ask beats allow. A call that matches nothing falls to the default: ask when
a person is present, deny when nobody is. The policy file states both.

## What the Claude Code adapter renders

`aidlc render --tool claude-code` writes `.claude/settings.json` from the effective permissions.
The code is `cli/aidlc/adapters/claude_code.py`.

| Effective permissions | `.claude/settings.json` |
|---|---|
| `allow` read, edit, shell, tools | `permissions.allow` as `Read`, `Edit(./path)`, `Bash(pattern)` and mapped tool names |
| `ask` edit, shell, tools | `permissions.ask` |
| `deny` read and `secret_paths` | `permissions.deny` as `Read(path)`; also `sandbox.filesystem.denyRead` |
| `deny` edit and `protected_paths` | `permissions.deny` as `Edit(path)`; also `sandbox.filesystem.denyWrite` |
| `deny` shell and tools | `permissions.deny` as `Bash(pattern)` and mapped tool names |
| Profile and repository additions | `sandbox.filesystem.allowWrite`, `sandbox.network.allowedDomains` |
| Fixed hardening | `sandbox.enabled`, `failIfUnavailable`, `allowUnsandboxedCommands: false`, `disableBypassPermissionsMode` |
| Hook entries | `hooks.PreToolUse` and `hooks.PostToolUse`, see [hooks](hooks.md) |

Tool names such as `tracker.read_issue` are tool-neutral. The repository's `.aidlc/config.yaml`
maps them to the tool's names. An unmapped name is dropped from the rendered list, and doctor
check D7 warns about it.

## Secret paths are denied twice

The Read tool runs outside the sandbox. Commands run inside it. A single control therefore
covers only one route.

- `Read()` deny rules stop the Read tool.
- Sandbox `denyRead` stops commands such as `cat .env` and test runners.

This was verified live. See [the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md).
Doctor check D2 fails if either half is missing.

## What the sandbox enforces

These facts were verified live on 2026-10-19. The evidence is the addendum in
[the sandbox verification](../verification/2026-10-18-sandbox-wsl2.md) (see its subsection "2026-10-19, checks 3 and 4" for the ask-rule and missing-literal-file results) and the rows in [the
attack run](../verification/2026-10-19-harness-attacks.md).

- **`denyRead` enforces globs**, including `**`. Secret-path globs are rendered as they are.
- **`denyWrite` enforces only literal files and directories.** It also blocks the creation of
  a missing literal file.
- **Protected-path globs are therefore expanded to tracked files at render time.** A file that
  matches a glob but is new relies on the `Edit` rules and the guard until the next render.
  `aidlc render --check` and doctor D1 report that drift.
- **`.git/**` is denied for writes as `./.git/hooks` and `./.git/config`.** Denying all of `.git`
  would break commits, and these two are the paths that run code or change settings.
- **Untrusted workspaces ignore only `permissions.allow`.** Deny and ask rules, hooks and the
  sandbox all still apply.
- **Ask rules stay enforced** with `autoAllowBashIfSandboxed`. The sandbox auto-approves commands
  that pass the rules. It does not skip them.

> ⚠️ **Watch out:** After you add a file that matches a protected glob, such as a new
> `scripts/check-x.sh`, run `aidlc render --tool claude-code` and commit the result. Until then
> only the `Edit` rules and the guard protect it from a shell write.

## Narrowing in a repository

A repository may only tighten the baseline. It does this in `.aidlc/permissions.yaml`, validated
by `core/schemas/repo-permissions.schema.json`. The one way to loosen is `allow_add`, and it
needs a reason and an owner. Doctor D6 warns on each one.

```yaml
# .aidlc/permissions.yaml
deny_add:
  shell: ["terraform apply*"]       # agents plan, people apply
ask_add:
  edit: ["db/migrations/**"]        # a person confirms each migration edit
secret_paths_add: ["config/prod/**"]
allow_remove:
  shell: ["git commit *"]           # this repository commits by hand
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
