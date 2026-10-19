<!-- aidlc template: adr -->
# 0002 · Tool classes: read, edit, shell, mcp, external; unknown tools ask

Status: Accepted (2026-10-19) · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision, Plan 2 final review) · Tier: 2 (affects every installed repository's controls)
Supersedes: the class list in design spec §4.3 (`read | analyse | modify | execute | external`)

## Context

The guide (chapter 3, step 2) asks you to sort every tool call into a small set of classes, so
each control can reason about a class instead of a tool name. Design spec §4.3 named five classes:
`read | analyse | modify | execute | external`.

Building the harness in Plan 2 showed that this list does not match how the controls decide:

- Nothing in the guard treats "analyse" differently from "read". Both are allowed, and both are
  left to the permissions and the sandbox for secrets.
- MCP tools need their own class. They are decided by name against `tool_deny` and `tool_ask`,
  not by path or command.
- "modify" and "execute" map one-to-one to the two checks that matter: path and scope checks
  for edits, and command analysis for shell calls.

The final branch review also found that tools outside the hook matcher bypassed the guard
entirely. Background shell (`Monitor`) and new tools reached no hook at all.

## Decision

- **The wire classes are `read | edit | shell | mcp | external`.** Tool names live in `args`,
  never in `tool` ([adapter interface](../adapters/interface.md)).
- **Every tool reaches the pre-tool guard.** The Claude Code `PreToolUse` matcher is `.*`. The
  shim classifies each tool: read and control tools (`Read`, `Glob`, `Grep`, `TodoWrite`,
  `Task`, `Agent`, `BashOutput` and others) are `read`, `Monitor` is `shell`, and `mcp__*` is
  `mcp`.
- **An unknown tool asks a person** (rule `unknown-tool`). In unattended runs an ask is a deny,
  so unattended use still fails closed.
- **The post-tool hook covers modifying tools and background shell output.** For `BashOutput`
  it scans for credentials only.

## Consequences

- A new tool from a Claude Code upgrade never runs silently. It prompts a person until the
  adapter classifies it. Cost if wrong: an interactive prompt for a benign tool.
- Interactive use does not break when the tool adds a tool. A hard deny would have.
- Each adapter owns its `CLASSES` table and must keep it in step with the tool's tool names.
  Doctor D4 checks that the rendered matchers equal the adapter's constants.
- Design spec §4.3's class list is superseded by this ADR. The spec is not edited. This ADR is
  the reference.

## Sources

- Guide chapter 3, steps 2 and 5.
- Plan 2 final review, findings I1 and M7, and the controller's rulings
  (`.superpowers/sdd/2026-10-19-plan-02-harness/progress.md`, "Final:" lines).
- `core/hooks/claude_shim.py` (`CLASSES`), `cli/aidlc/adapters/claude_code.py` (`PRE_MATCHER`,
  `POST_MATCHER`).
