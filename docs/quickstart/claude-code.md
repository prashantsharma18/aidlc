# Quickstart: Claude Code

1. **Install the plugin** (once per machine, or let the starter settings do it per repository):
   ```text
   /plugin marketplace add prashantsharma18/aidlc
   /plugin install aidlc@aidlc
   ```
   From a local checkout instead: `claude plugin marketplace add ~/path/to/aidlc`, then `claude plugin install aidlc@aidlc`.
2. **Copy the starter files** into the repository: `AGENTS.md`, `CLAUDE.md` (one line: `@AGENTS.md`),
   `CODEOWNERS`, and, if you want them, the example `.claude/settings.json` (secrets unreadable, the sandbox on, the
   plugin enabled). aidlc ships no scripts and no CI workflows: your CI stays your own (ADR 0024). For a workspace holding several repositories, copy `starter/workspace/` to its root, and add one
   `Edit(/<repository>/**)` rule per repository to its `permissions.deny`: a session at the root then writes only
   under `stories/` (Edit deny rules also bind the sandbox, so a shell command cannot write there either).
3. **Onboard once:** open Claude Code at the repository root and run `/aidlc:aidlc-onboard`. Review the `AGENTS.md`
   and codebase map it writes, in a pull request.
4. **Work:** start every piece of work with `/aidlc:aidlc-start <KEY>` (or describe a new requirement). It tells you the
   next skill and where to run it. Or start `/aidlc:story-run <KEY>` once per decision: it runs the stages until the
   next one a person takes (ADR 0028).

**Let the agent read your tracker:** add your tracker's read-only tools to `permissions.allow` in `.claude/settings.json`
(for example `mcp__<server>__getjiraissue` and its search tool), deny its transition tool, and name the site and project in
`AGENTS.md` or `WORKSPACE.md` ("Tools"). Without the allow rule, a headless session cannot read the work item.

Cloud sessions and headless (`-p`) runs do not add a repository's marketplace, because that needs the folder-trust
dialog: in CI, install the plugin explicitly (`claude plugin marketplace add`, then `claude plugin install`).

Open a new repository or workspace in Claude Code interactively once and accept the folder-trust dialog: until then its
`.claude/settings.json` allow rules and `additionalDirectories` are ignored, and headless runs never show the dialog.

Start Claude Code at a repository root or the workspace root, never in a subfolder: settings load from the folder you start in.
Stage skills run only when you ask for them by name; practice skills load on their own when relevant.

Next: [how to adopt aidlc](../operating-model/adoption.md), on a new system or an existing one in phases, and
[the nine routes](../operating-model/routes.md) `aidlc-start` chooses from.

The commands you type, stage by stage: [the README's table](../../README.md#commands-you-type).
