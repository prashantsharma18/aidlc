# A workspace root

A workspace is a folder that holds several repositories, plus a `WORKSPACE.md` that says who owns
what. Think of it as the team room: you walk in to see everything, but you do your work at your
own desk. In the same way, a session started at the workspace root can read every repository and
write none. All writing happens in a session started inside one repository.

```text
~/work/shipment-tracking/          the workspace (its own small repository)
├── WORKSPACE.md                   repositories, owners, rules; points to the coordination plan
├── CLAUDE.md                      generated: imports WORKSPACE.md
├── .claude/settings.json          generated: the read-only harness
├── shipments-api/      (git)      its own .aidlc/, hooks and rules
└── customer-portal/    (git)      its own .aidlc/, hooks and rules
```

## When to start where

| Start at | Use it for | Can it write? |
|---|---|---|
| The workspace root | Discovery and design across repositories (`aidlc-discover`, `aidlc-design`) | No. Drafts go in the reply |
| A repository root | Everything that changes files: plans, slices, verification | Only in that repository |

## What the read-only harness does

- **Denies every file edit.** `Edit`, `Write` and `NotebookEdit` are denied, so no tool can change a file.
- **Denies writes from commands.** The sandbox's `denyWrite: ["./"]` covers the whole folder. Only
  read-only commands (`git status`, `git log`, `git show`, `git diff`, `ls`) run without a prompt.
  Commit, push, checkout, switch and reset are denied outright.
- **Keeps secrets unreadable,** with the same `secret_paths` as every repository.
- **Turns off auto-memory and bypass mode,** so nothing is remembered across sessions or approved
  by default.
- **Switches off user plugins** you name with `--disable-plugin`. A user plugin brings its own
  skills and hooks, which would compete with the aidlc stage skills.
- **Switches off the account's extensions.** claude.ai connectors (Gmail, Drive and the like) are
  disabled, and the account's synced skills (`anthropic-skills`) are denied.

## The same switches in a repository

A repository opts in through `.aidlc/config.yaml`, and `aidlc render` writes the project settings:

```yaml
harness:
  disable_user_plugins: [superpowers@claude-plugins-official]   # enabledPlugins: false
  disable_claude_ai_connectors: true                            # disableClaudeAiConnectors
  deny_skills: ["anthropic-skills *"]                           # permissions.deny Skill(...)
```

A denied skill is still listed in the session, but it cannot run. Removing it from the list needs
`syncClaudeAiSkills: false`, which only user or local settings honour, and which also moves the
synced skills out of every other session on that machine. That is the person's choice, not the
repository's.

## Set it up

```bash
aidlc workspace init ~/work/shipment-tracking --key SHIP-1 \
  --title "Show customers an estimated delivery window" \
  --repo "shipments-api=Logistics team" --repo "customer-portal=Web team" \
  --disable-plugin superpowers@claude-plugins-official
```

Each `--repo` must be a git repository directly inside the workspace. The command never
overwrites a file that exists. To regenerate a file, delete it and run the command again.

> 🎯 **What this means for you:** Open the workspace folder to look across repositories, and open a
> repository folder to change it. Never open a subfolder: a session started there loads no harness.

> ⚠️ **Watch out:** Claude Code also loads every `CLAUDE.md` in the folders above the one you
> start in. Keep a workspace out of a folder whose parent has instructions meant for something else.

Guide: 14.4, 2.11, 3.4.
