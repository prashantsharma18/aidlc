# aidlc

A skills package for AI-assisted software delivery: from a requirement to a verified, reviewed change, with a person
deciding at every gate. It implements the guide "From Intent to Verified Change".

One plugin, **`aidlc`**, written and tested for **Claude Code**. The skills are plain `SKILL.md` folders in the
open Agent Skills format, so GitHub Copilot, Codex and Cursor can read them; aidlc has not been tested there
yet, and their adapters are a later plan.

## Install

| Tool | How |
|---|---|
| Claude Code | `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc` ([quickstart](docs/quickstart/claude-code.md)) |
| GitHub Copilot | Copy `skills/*` into your repository's `.github/skills/`, or install the plugin with Copilot CLI (untested) ([quickstart](docs/quickstart/copilot.md)) |
| Codex, Cursor | Copy `skills/*` into `.agents/skills/` (or `.cursor/skills/` for Cursor) ([quickstart](docs/quickstart/codex-cursor.md)) |

Then copy the starter files that fit (`starter/repo/` into a repository, `starter/workspace/` into a workspace) and run
the `aidlc-onboard` skill once. The starters hold a rules file, an ownership list and optional example settings:
no scripts and no workflows.

## How work runs

```text
aidlc-start ──► intent ──► specify ──► discover ──► design ──► plan ──► build ──► verify ──► review ──► release
  (routes by      (story level: the workspace root, or the repository           (part level: inside each        (story level)
  kind and scope)   for a one-repository story)                                   repository that changes)
                                                     after an incident: operate ──► feedback
```

- **Start every piece of work with `aidlc-start`**: a new requirement, a story, a defect, a change request or an
  incident follow-up. It decides the kind of work and which repositories change, chooses the route (the route table in
  the `using-aidlc` skill is the one source of which stages each route runs), and says where the next stage runs. A new system starts the same way, in an empty repository or a new workspace (route G). A standard change the team lists in its `AGENTS.md` takes route S: a brief the engineer confirms, then build, verify and review.
- **One repository:** every stage runs there; documents in `plans/<KEY>/`.
- **Several repositories:** story-level stages run at the workspace root and keep their documents in `stories/<KEY>/`;
  each repository's part (plan, build, verify, review) runs inside that repository, on branch `feat/<KEY>-<part>`.
  The story stays one tracker item; its parts are rows of the coordination plan.
- **Gates:** each skill drafts, and stops only where the tiers file's decisions table lists a decision for the tier
  (at Tier 1, Ready and Merge, and Release only when users see the change; ADR 0026); a plan with independent slices is still approved; people approve in the pull request and the tracker, or tell the AI, which
  records each decision after checking it (ADR 0023). Tests come first (when a test is practical; a criterion with no test is a logged
  decision, ADR 0029); an existing test assertion is never changed to make a test pass.
- **One start per decision:** the `story-run` workflow skill runs one story's stages one after another, in one session,
  and stops at the next person's decision, with the wait written in the index and a hand-off (ADR 0028).
- **Several at once:** the `parallel-lanes` workflow skill runs lanes, each in its own git worktree, from a
  `QUEUE.md` the coordinator drafts and a person merges. A lane releases at every person's decision, and the next ready row starts (ADR 0025).
  A lane is `lane-run`: it claims one row's worktree and runs `story-run` there; the coordinator schedules a plan's independent slices from the plan, watches the lanes and their CI, and never merges (ADR 0030).

## Where the gates hold

aidlc is instructions: skills, agents and templates. It ships no scripts and no CI workflows (ADR 0024). The skills
say what must hold; the team's own project makes it hold:

| Control | Claude Code | GitHub Copilot, Codex, Cursor |
|---|---|---|
| The team's own tests, linters, type checks and CI, which `aidlc-feedback` grows from each repeated mistake | yes | yes |
| Reviewer agents in a fresh context, reading the evidence file the session writes with git | yes | the tool's own agents, or a fresh session |
| A person decides at each gate, from evidence git can confirm | yes | yes |
| Code-owner review (`CODEOWNERS`) | yes | yes |
| Example settings: secrets unreadable, the sandbox on, push and install ask first | yes | the tool's own settings, or prose only |

aidlc needs git and a pull request (a review request), and no other code-host feature. Reading the review tool is
optional: without it, a person confirms the approval and the CI result in the session. A team that has branch
protection, rulesets or required checks may use them to block a merge on red; aidlc never needs them. On GitHub Free, branch protection, rulesets and required
checks work only on public repositories. A private repository needs GitHub Pro (personal account) or Team
(organisation). Never turn on auto-merge without required checks: it would merge whatever is pushed.

The check code aidlc 5 shipped (the slice, plan, recipe, contract and status scripts, and the starter workflows) is
kept under the tag `checks-v1`: [docs/archive/checks-v1.md](docs/archive/checks-v1.md).

The nine routes, drawn: [docs/operating-model/routes.md](docs/operating-model/routes.md). How to adopt aidlc on a new or an
existing system, and who approves what: [docs/operating-model/adoption.md](docs/operating-model/adoption.md). The
operating model: [docs/operating-model/workspace-and-repositories.md](docs/operating-model/workspace-and-repositories.md).

## Commands you type

The stage skills are the commands. Each drafts its documents and stops where the decisions table puts a person's decision. In Claude Code, type
them as below; in Copilot, Codex or Cursor, ask for the skill by name ("use aidlc-start for SHIP-12").

| You type | When | It writes |
|---|---|---|
| `/aidlc:aidlc-onboard` | Once per repository or workspace; `new prepare` and `new confirm` for a new system | `AGENTS.md` and the codebase map |
| `/aidlc:aidlc-start SHIP-12` | Every new piece of work: a story, a defect, a change request, an incident follow-up, a new system | The story's index, with its route; on route S, the standard brief |
| `/aidlc:aidlc-intent SHIP-12` | No story yet, or a vague one | The intent, for the product owner |
| `/aidlc:aidlc-specify SHIP-12` | To write or amend the criteria | The spec |
| `/aidlc:aidlc-discover SHIP-12` | When the tier or an unknown asks what the change touches | The evidence pack |
| `/aidlc:aidlc-design SHIP-12` | Always before planning; most end at "none needed" | The design note, ADR drafts, contract changes |
| `/aidlc:aidlc-plan SHIP-12` | Once the spec is approved; on the fast paths, brief mode | The plan and one bundle per slice, or `fix.md` or `brief.md` |
| `/aidlc:aidlc-build SHIP-12 1` | One slice at a time, from its approved bundle (at Tier 1, the stated one, or the approved one for independent slices) | Commits and the slice's progress note |
| `/aidlc:aidlc-verify SHIP-12` | When the pull request's checks have run | The evidence table |
| `/aidlc:aidlc-review SHIP-12` | Before the code owner reviews | The pull request description and the review record |
| `/aidlc:aidlc-release SHIP-12` | When every part is merged | The readiness and change records, with stop criteria |
| `/aidlc:aidlc-operate INC-231` | When an alert fires | The incident record and a follow-up work item |
| `/aidlc:aidlc-feedback INC-231` | After an incident, or when findings repeat | Where each lesson goes |
| `/aidlc:story-run SHIP-12` | Once per person's decision: it runs the next stages until one is needed | What each stage it runs writes, and the wait in the index |
| `/aidlc:lane-run SHIP-12` | To run one queue row by hand, in its own worktree, up to the next person's decision | The row's worktree, the stages' files, the wait in the row's index |
| `/aidlc:parallel-lanes coordinator` | To work through `QUEUE.md` with several lanes at once; `lane` starts one lane by hand | Nothing but drafts (for reviewer passes it claims a row's worktree and writes nothing in it); each lane writes its own row's files |

Which stages a piece of work needs depends on its route: the route table in the `using-aidlc` skill is the one
source of which stages each route runs, and [routes.md](docs/operating-model/routes.md) draws each route.

## Skills

The skills (`skills/`):

| Stage skills | Practice skills | Workflow skills |
|---|---|---|
| `aidlc-start`, `aidlc-onboard`, `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`, `aidlc-release`, `aidlc-operate`, `aidlc-feedback` | `designing-apis`, `reviewing-code`, `debugging-failures`, `migrating-safely`, `building-user-interfaces`, `adding-observability`, `tuning-performance`, `securing-code`, `writing-tests`, `committing-changes`, `building-ci-pipelines`, `simplifying-code`, `unslop`, `technical-writing`, `in-your-own-words`, `how`, `why`, `stress-testing-decisions`, `checking-official-docs`, `testing-in-browser`, `writing-documentation` | `lane-run`, `parallel-lanes`, `story-run` |

The map of the four kinds of skill (stage, practice, workflow and map), and the first skill to read: `using-aidlc`.

Agents the skills call: `explorer`, `reviewer-bug`, `reviewer-security`, `reviewer-compliance`, `reviewer-tests`,
`ops-diagnoser` (in `agents/`).

## Contributing

Check your change with `python3 scripts/validate.py`, `python3 -m unittest discover -s scripts -p 'test_*.py'` and
`claude plugin validate .`. Raise the plugin's version on every release.
Decisions are in [docs/adr/](docs/adr/). The earlier Python harness is parked under the tag `harness-v1`
([what it held](docs/archive/harness-v1.md)).
