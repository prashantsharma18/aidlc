# aidlc

A skills package for AI-assisted software delivery: from a requirement to a verified, reviewed change, with a person
deciding at every gate. It implements the guide "From Intent to Verified Change".

The same `skills/` folder works in **Claude Code, GitHub Copilot, Codex and Cursor**: skills are plain `SKILL.md` folders
in the open Agent Skills format.

## Install

| Tool | How |
|---|---|
| Claude Code | `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc` ([quickstart](docs/quickstart/claude-code.md)) |
| GitHub Copilot | Copy `skills/` into your repository's `.github/skills/` (or `~/.copilot/skills/` for yourself) ([quickstart](docs/quickstart/copilot.md)) |
| Codex, Cursor | Copy `skills/` into `.agents/skills/` (or `.cursor/skills/` for Cursor) ([quickstart](docs/quickstart/codex-cursor.md)) |

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
  incident follow-up. It decides the kind of work and which repositories change, and says where the next stage runs.
- **One repository:** every stage runs there; documents in `plans/<KEY>/`.
- **Several repositories:** story-level stages run at the workspace root and keep their documents in `stories/<KEY>/`;
  each repository's part (plan, build, verify, review) runs inside that repository, on branch `feat/<KEY>-<part>`.
  The story stays one tracker item; its parts are rows of the coordination plan.
- **Gates:** each skill drafts and stops; people approve in the pull request and the tracker. Tests come first; an
  existing test assertion is never changed to make a test pass.

The operating model: [docs/operating-model/workspace-and-repositories.md](docs/operating-model/workspace-and-repositories.md).

## Skills

| Stage skills | Practice skills (adapted from [addyosmani/agent-skills](https://github.com/addyosmani/agent-skills), MIT) |
|---|---|
| `aidlc-start`, `aidlc-onboard`, `aidlc-intent`, `aidlc-specify`, `aidlc-discover`, `aidlc-design`, `aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review`, `aidlc-release`, `aidlc-operate`, `aidlc-feedback` | `api-and-interface-design`, `code-review-and-quality`, `debugging-and-error-recovery`, `deprecation-and-migration`, `frontend-ui-engineering`, `observability-and-instrumentation`, `performance-optimization`, `security-and-hardening` |

Agents the skills call: `explorer`, `planner`, `implementer`, `reviewer-bug`, `reviewer-security`, `reviewer-compliance`,
`ops-diagnoser` (in `agents/`).

## Contributing

Check your change with `python3 scripts/validate.py` and `python3 -m unittest discover -s scripts -p 'test_*.py'`.
Decisions are in [docs/adr/](docs/adr/). The earlier Python harness is parked under the tag `harness-v1`
([what it held](docs/archive/harness-v1.md)).
