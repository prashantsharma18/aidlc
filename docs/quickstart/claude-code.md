# Quickstart: Claude Code

1. **Install the plugin** (once per machine, or let the starter settings do it per repository):
   ```text
   /plugin marketplace add prashantsharma18/aidlc
   /plugin install aidlc@aidlc
   ```
   From a local checkout instead: `claude plugin marketplace add ~/path/to/aidlc`, then `claude plugin install aidlc@aidlc`.
2. **Copy the starter files** into the repository: `AGENTS.md`, `CLAUDE.md` (one line: `@AGENTS.md`),
   `.claude/settings.json` (secrets unreadable, the sandbox on, the plugin enabled), `.github/workflows/ci.yml`,
   `CODEOWNERS`. For a workspace holding several repositories, copy `starter/workspace/` to its root, and add one
   `Edit(/<repository>/**)` rule per repository to its `permissions.deny`: a session at the root then writes only
   under `stories/` (Edit deny rules also bind the sandbox, so a shell command cannot write there either).
3. **Onboard once:** open Claude Code at the repository root and run `/aidlc:aidlc-onboard`. Review the `AGENTS.md`
   and codebase map it writes, in a pull request.
4. **Work:** start every piece of work with `/aidlc:aidlc-start <KEY>` (or describe a new requirement). It tells you the
   next skill and where to run it.

**Let the agent read your tracker:** add your tracker's read-only tools to `permissions.allow` in `.claude/settings.json`
(for example `mcp__<server>__getjiraissue` and its search tool), deny its transition tool, and name the site and project in
`AGENTS.md` or `WORKSPACE.md` ("Tools"). Without the allow rule, a headless session cannot read the work item.

**Packs.** A repository being modernised also switches on `aidlc-modernize@aidlc` in `.claude/settings.json`
(`enabledPlugins`) and declares it in AGENTS.md's `Packs used here`; `python3 scripts/check_packs.py` (from the
starter) checks the two agree, at the start of work and in CI. Installing `aidlc-modernize` installs `aidlc` with it.
Cloud sessions and headless (`-p`) runs do not add a repository's marketplace, because that needs the folder-trust
dialog: in CI, install the plugins explicitly (`claude plugin marketplace add`, then `claude plugin install`).

Start Claude Code at a repository root or the workspace root, never in a subfolder: settings load from the folder you start in.
Stage skills run only when you ask for them by name; practice skills load on their own when relevant.
