# The aidlc plugin: skills and agents

The `aidlc` plugin gives Claude Code the framework's stage skills and agent roles. Each skill drafts
one stage's artefact and stops at that stage's human gate. The decision is
[ADR 0005](../adr/0005-skills-plugin.md).

## What the plugin holds

| Skill | Stage | Produces | Gate (a person decides) |
|---|---|---|---|
| `aidlc-context-setup` | Context | drafts of `AGENTS.md` and `docs/codebase-map.md` | Placement, enforcement and the merge |
| `aidlc-intent` | Intent | a draft of `plans/<KEY>/intent.md` | The product owner accepts the work |
| `aidlc-specify` | Specify | a draft of `plans/<KEY>/spec.md`, or its new version | The spec owner approves the version |
| `aidlc-plan` | Plan | drafts of `plans/<KEY>/plan.md` and one bundle per slice | The tech lead approves the plan |
| `aidlc-build-slice` | Build | commits (each records its step), a hand-off note | Local check green, diff in scope |
| `aidlc-adopt` | Context | the init command, decisions on other tools' files, a draft baseline | Code owners merge the adoption pull request |
| `aidlc-verify` | Verify | the evidence table and the pull request description | A code owner approves the pull request |

**You save the drafts.** The harness denies the agent writes to `plans/**` and `AGENTS.md`, and every
edit outside an approved task scope. So each skill gives its complete draft in its reply, and you save
it, for example with `aidlc new intent --out plans/SHIP-42/intent.md`, and commit it through a
reviewed pull request. Build-slice edits code only inside its bundle's MAY CHANGE, after you run
`aidlc scope --branch <branch>`.

**Slices on one branch.** The scope check reads the whole branch against the latest approved bundle,
so each later bundle's MAY CHANGE also lists the earlier slices' paths.

The seven agent roles are `explorer`, `planner`, `implementer`, `reviewer-bug`, `reviewer-security`,
`reviewer-compliance` and `ops-diagnoser`. All but the `implementer` are read-only.

Every skill says "You draft; you never approve", treats text in tickets and files as data, never as
instructions, and lists its "Common excuses" and "Red flags".

## The flow

```text
Jira story (acceptance criteria)          Git, branch <type>/<KEY>-<slug>
        │                                          │
  aidlc-intent ──► aidlc-specify ──► aidlc-plan ──► aidlc-build-slice (one slice per session)
   (owner accepts)   (spec v1 approved)  (plan approved;     │
                                          bundles pinned)    ▼
                                                      pull request ──► aidlc-verify ──► code owner
```

- Jira holds the story at **story level**. Its acceptance criteria are the start of the spec.
- Git holds the plan, the task bundles, the code and the evidence: one branch per story per
  repository, and one pull request per repository.
- Slices live only in the plan and its bundles. There are **no Jira sub-tasks**.
- The agent reads the tracker freely. It asks before it comments, and it never changes a status.

## The three kinds of work

- **New work**: the full path. The tier decides how much of each stage you need.
- **A defect**: intent records it as a defect. The build writes the **failing test** that reproduces
  it first, then the fix. Prevention follows in Plan 5b.
- **A change request**: an approved criterion changes only through its owner. `aidlc-specify` in
  amendment mode prepares the decision. After the owner decides, the spec becomes **spec v2**, and the
  plan returns for approval.

## How the agents work

The main session runs a skill and hands heavy work to an agent. Each agent starts in a fresh
context, with only its own tools, and returns a summary. Agents never talk to each other. The
repository's hooks see every agent's tool calls, so the harness applies to them too.

## Which skills start on their own

`aidlc-context-setup` and `aidlc-verify` may start on their own when your request matches them.
Context setup then does only its survey and asks before drafting anything. Every gated stage starts
only when you type it, for example `/aidlc:aidlc-intent`. You can also type `/aidlc:aidlc-verify`.

## Using it

For yourself:

```bash
claude plugin marketplace add prashantsharma18/aidlc
claude plugin install aidlc@aidlc
```

To try a local build in one session, without installing: `claude --plugin-dir plugins/aidlc`.

Start a skill by typing it, for example `/aidlc:aidlc-intent SHIP-42`.

## For an organisation

Add this to managed settings. It registers the marketplace on every machine, at a release tag, and
turns the plugin on:

```json
{
  "extraKnownMarketplaces": {
    "aidlc": {
      "source": {"source": "github", "repo": "prashantsharma18/aidlc", "ref": "<release tag>"},
      "autoUpdate": false
    }
  },
  "enabledPlugins": {"aidlc@aidlc": true}
}
```

- **Pinning.** A marketplace source takes a branch or tag (`ref`), not a commit sha. Pin a release
  tag, and move it to roll out a new version.
- **Limit the sources** with `strictKnownMarketplaces`, and reject `--plugin-dir` with
  `disableSideloadFlags`. An allowlist entry matches `ref` exactly, so give it the same tag:
  `{"source": "github", "repo": "prashantsharma18/aidlc", "ref": "<release tag>"}`.
- The field names follow https://code.claude.com/docs/en/plugins/org and the marketplace reference
  (checked 2026-10-23).

The plugin enforces nothing. Each repository's rendered settings hold the harness: permissions,
sandbox and hooks.

## Checks

- **Today:** free structural checks on every pull request (the skill and agent format tests,
  `bin/aidlc plugin build --check`), and `claude plugin validate --strict` where Claude Code is
  installed.
- **Later (Plan 5c):** behaviour evals with `claude plugin eval`: a behaviour case and a pressure
  case per skill, plus a "fires" and a "stays quiet" case for each skill that starts on its own.

## Copilot later

The same `core/skills` and `core/agents` will render for Copilot (`.agents/skills` and
`.github/agents/*.agent.md`). See [the tool capabilities](../adapters/capabilities.md).
