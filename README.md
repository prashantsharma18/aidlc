# aidlc

A skills package for AI-assisted software delivery: from a requirement to a verified, reviewed change, with a person
deciding at every gate. It implements the guide "From Intent to Verified Change".

One plugin, **`aidlc`**. The skills work in **Claude Code, GitHub Copilot, Codex and Cursor**: they are plain
`SKILL.md` folders in the open Agent Skills format.

## Install

| Tool | How |
|---|---|
| Claude Code | `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc` ([quickstart](docs/quickstart/claude-code.md)) |
| GitHub Copilot | Copy `skills/*` into your repository's `.github/skills/`, or install the plugin with Copilot CLI ([quickstart](docs/quickstart/copilot.md)) |
| Codex, Cursor | Copy `skills/*` into `.agents/skills/` (or `.cursor/skills/` for Cursor) ([quickstart](docs/quickstart/codex-cursor.md)) |

Then copy the starter files that fit (`starter/repo/` into a repository, `starter/workspace/` into a workspace) and run
the `aidlc-onboard` skill once.

## How work runs

```text
aidlc-start ──► intent ──► specify ──► discover ──► design ──► plan ──► build ──► verify ──► review ──► release
  (routes by      (story level: the workspace root, or the repository           (part level: inside each        (story level)
  kind and scope)   for a one-repository story)                                   repository that changes)
                                                     after an incident: operate ──► feedback
```

- **Start every piece of work with `aidlc-start`**: a new requirement, a story, a defect, a change request or an
  incident follow-up. It decides the kind of work and which repositories change, chooses the route (the `using-aidlc`
  skill lists them), and says where the next stage runs. A new system starts the same way, in an empty repository or a new workspace (route G).
- **One repository:** every stage runs there; documents in `plans/<KEY>/`.
- **Several repositories:** story-level stages run at the workspace root and keep their documents in `stories/<KEY>/`;
  each repository's part (plan, build, verify, review) runs inside that repository, on branch `feat/<KEY>-<part>`.
  The story stays one tracker item; its parts are rows of the coordination plan.
- **Gates:** each skill drafts and stops; people approve in the pull request and the tracker, or tell the AI, which
  records each decision after checking it (ADR 0023). Tests come first; an
  existing test assertion is never changed to make a test pass.

## Where the gates hold

The skills say what must hold. These controls make it hold:

| Control | Claude Code | GitHub Copilot, Codex, Cursor |
|---|---|---|
| Slice check in CI (scope, tests, manifests, suppressions, approved plans) | yes | yes |
| AI review in CI, required and fail-closed | yes | yes |
| Code-owner review, branch protection | yes | yes |
| Slice check before the session stops (Stop hook) | yes | no: prose only |
| Deny rules: secrets, settings, check scripts | yes | the tool's own settings, or prose only |
| Read-only reviewer agents | yes | the tool's own agents, or prose only |

CI runs the base branch's copy of the slice check, so a pull request cannot weaken the script. A pull request can
still edit `ci.yml` itself: that edit is held by `CODEOWNERS` (`.github/` belongs to the leads) and a required
code-owner review.

On GitHub Free, branch protection, rulesets and required checks work only on public repositories. A private
repository needs GitHub Pro (personal account) or Team (organisation). Never turn on auto-merge without required
checks: it would merge whatever is pushed.

The eight routes, drawn: [docs/operating-model/routes.md](docs/operating-model/routes.md). How to adopt aidlc on a new or an
existing system, and who approves what: [docs/operating-model/adoption.md](docs/operating-model/adoption.md). The
operating model: [docs/operating-model/workspace-and-repositories.md](docs/operating-model/workspace-and-repositories.md).

## Commands you type

The stage skills are the commands. Each drafts its documents and stops at a person's gate. In Claude Code, type
them as below; in Copilot, Codex or Cursor, ask for the skill by name ("use aidlc-start for SHIP-12").

| You type | When | It writes |
|---|---|---|
| `/aidlc:aidlc-onboard` | Once per repository or workspace; `new prepare` and `new confirm` for a new system | `AGENTS.md` and the codebase map |
| `/aidlc:aidlc-start SHIP-12` | Every new piece of work: a story, a defect, a change request, an incident follow-up, a new system | The story's index, with its route |
| `/aidlc:aidlc-intent SHIP-12` | No story yet, or a vague one | The intent, for the product owner |
| `/aidlc:aidlc-specify SHIP-12` | To write or amend the criteria | The spec |
| `/aidlc:aidlc-discover SHIP-12` | When the tier or an unknown asks what the change touches | The evidence pack |
| `/aidlc:aidlc-design SHIP-12` | Always before planning; most end at "none needed" | The design note, ADR drafts, contract changes |
| `/aidlc:aidlc-plan SHIP-12` | Once the spec is approved; on the fast paths, brief mode | The plan and one bundle per slice, or `fix.md` or `brief.md` |
| `/aidlc:aidlc-build SHIP-12 1` | One approved slice at a time | Commits and the slice's progress note |
| `/aidlc:aidlc-verify SHIP-12` | When the pull request's checks have run | The evidence table and the pull request description |
| `/aidlc:aidlc-review SHIP-12` | Before the code owner reviews | The review record |
| `/aidlc:aidlc-release SHIP-12` | When every part is merged | The readiness and change records, with stop criteria |
| `/aidlc:aidlc-operate INC-231` | When an alert fires | The incident record and a follow-up work item |
| `/aidlc:aidlc-feedback INC-231` | After an incident, or when findings repeat | Where each lesson goes |

Which stages a piece of work needs depends on its route: see [routes.md](docs/operating-model/routes.md).

## Skills

The skills (`skills/`):

| Stage skills | Practice skills |
|---|---|
| `aidlc-start`, `aidlc-onboard`, `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`, `aidlc-release`, `aidlc-operate`, `aidlc-feedback` | `designing-apis`, `reviewing-code`, `debugging-failures`, `migrating-safely`, `building-user-interfaces`, `adding-observability`, `tuning-performance`, `securing-code`, `writing-tests`, `committing-changes`, `building-ci-pipelines`, `simplifying-code`, `stress-testing-decisions`, `checking-official-docs`, `testing-in-browser`, `writing-documentation` |

The map of stages and practices, and the first skill to read: `using-aidlc`.

Agents the skills call: `explorer`, `reviewer-bug`, `reviewer-security`, `reviewer-compliance`, `reviewer-tests`,
`ops-diagnoser` (in `agents/`).

## Contributing

Check your change with `python3 scripts/validate.py`, `python3 -m unittest discover -s scripts -p 'test_*.py'` and
`claude plugin validate .`. Raise the plugin's version on every release.
Decisions are in [docs/adr/](docs/adr/). The earlier Python harness is parked under the tag `harness-v1`
([what it held](docs/archive/harness-v1.md)).
