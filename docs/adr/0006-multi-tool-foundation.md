<!-- aidlc template: adr -->
# 0006 · A multi-tool foundation before the second tool

Status: Accepted (2026-10-23). Amends design §4.3. · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (changes how every installed repository is rendered and judged)

## Context

aidlc renders for Claude Code only. Copilot, Cursor and Codex should be quick to add later. A review
of the code on 2026-10-23 found four things that would turn that into a rewrite:

- **One manifest for all tools.** `.aidlc/generated.json` lists every generated file. A render
  deletes, or reports as orphaned, every listed file it did not produce itself. So a render for a
  second tool would delete Claude Code's files.
- **Four of six functions.** Design §4.3 names six render functions. The adapter contract had four,
  and the same four-call list was copied into `aidlc render`, doctor D1 and the trusted CI judge.
- **Claude-only judging.** The CI judge treated only `.claude/`, `.mcp.json` and `claude.local.md`
  as agent configuration. A hand-written `.cursor/` or `.github/agents/` file passed unjudged.
- **A Claude-shaped shim.** The hook shim mixed the shared flow (guard, post-check, fail-safe) with
  Claude Code's payload and output formats.

The official docs (read 2026-10-23) show the tools converging: all read `AGENTS.md`, most read
`.agents/skills`, and the hooks look like Claude Code's. They differ where it matters most, in what
happens when a hook breaks:

| Tool | Hook error | Hook timeout | Also runs Claude Code's hooks |
|---|---|---|---|
| Claude Code | fail-closed (exit 2, `onFailure: block`) | fail-closed | n/a |
| Copilot | fail-closed | fail-open | yes (`.claude/settings.json`) |
| Cursor | fail-open unless `failClosed: true` | the same | yes |
| Codex | fail-open | fail-open | no |

## Decision

1. **Every manifest entry has an owner.** `.aidlc/generated.json` keeps its `files` map unchanged
   and adds `owners`: the adapter that rendered each file, or `shared` for a file every tool renders
   the same way (the CI workflow). A render only claims, checks and cleans up its own and shared
   entries. Two tools claiming one path is an error. A manifest with no `owners` was written by
   Claude Code, the only tool before this ADR, and is read that way.
2. **The full contract.** The adapter Protocol has all six functions. `render_skills` and
   `render_agents` return nothing for Claude Code, whose skills and agents come from the aidlc
   plugin (ADR 0005). `render_outputs(adapter, repo)` is the one list of everything an adapter
   renders, used by render, doctor and the judge.
3. **Capabilities are data.** `core/adapters/<tool>.yaml`, validated by
   `core/schemas/adapter.schema.json`, records what each tool reads and enforces: rule and skill
   locations, the agent format and tool names, the hook event, its failure behaviour (`on_error`,
   `on_timeout`), which other tool's hooks it also runs (`also_runs`), permissions, sandbox, MCP,
   and which paths are its agent configuration. Each one cites its sources and the date they were
   verified. `bin/aidlc trace` generates the comparison in
   [capabilities.md](../adapters/capabilities.md).
4. **The judge knows every tool.** Agent configuration is the union of every descriptor's
   `agent_config`. The judge compares the head with the files of every tool the trusted
   configuration lists, together, so one tool's files are never another's extras. Unmanaged
   configuration from any known tool FAILs.
5. **The shim has dialects.** `run(argv, dialect)` is the shared flow. A dialect decodes the tool's
   payload and encodes its answer. `CLAUDE` is the first dialect; `main` is `run(argv, CLAUDE)`.

## Rules for adding a tool

1. Write or update its descriptor first, from the tool's official docs.
2. Make its hooks fail closed where the tool allows it (Cursor `failClosed: true`). Where it does not
   (Copilot timeouts, Codex), back the hook with the tool's declarative deny rules and the sandbox.
3. Each tool reads only its own rendered files. A tool that also runs Claude Code's hooks
   (`also_runs`) needs a test proving the guard does not run twice for one call.
4. Run the shared hook fixtures through its dialect.
5. Decide whether the tool-neutral hook files (`guard.py`, `post_check.py`) become `shared`. Today
   Claude Code's render owns them, so a second tool that renders them is refused as a conflict.
6. Make protected paths independent of render order. Claude Code's `denyWrite` list is read from
   the folders that exist, so rendering a second tool that creates a new top-level folder (such as
   `.github/`) makes Claude Code's settings stale until it is rendered again. Render every listed
   tool in one pass, or derive the list from every tool's outputs.

## Consequences

- Adding Copilot means its renderers, a dialect and doctor checks. The descriptor already exists.
- A repository holding hand-written Cursor, Copilot or Codex configuration now fails the CI judge
  until that configuration is imported. The Adoption plan adds the import.
- Descriptors go stale as tools change. Each one carries `verified` and a `review_by` date.

## Rejected alternatives

- **One manifest per tool.** It would hide the conflict when two tools write the same path, and it
  needs a migration. Owners in one manifest keep the existing format and catch the conflict.
- **Tool facts in Python.** Constants in each adapter would repeat across the judge, the docs and
  the plugin build. One data file per tool is read by all of them.
- **Build Copilot now.** The plan order puts the skills and agents (Plan 5a) first. This foundation
  only removes what would block a second tool.
