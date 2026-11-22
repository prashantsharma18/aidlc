# Plan 6 design: the shipment-tracking demo

Status: draft for review (2026-10-23) · Owner: Prashant Sharma (framework owner)
Amends: framework design D3 and §11 (workspace name and location; local git first).

## Purpose

Prove the framework on one real change that crosses two repositories. Every stage skill, hook and
check runs in a live Claude Code session started inside a repository. Every gap we hit becomes a
finding: fixed, or recorded with a ruling.

Keep it small. Two minimal repositories, one story, three slices.

## Decisions (user, 2026-10-23)

| Decision | Choice |
|---|---|
| Repositories | Two: `shipments-api` (backend) and `customer-portal` (frontend) |
| Workspace | `~/work/shipment-tracking`, named after the product area, not the tooling. Outside `~/demos`, whose `.claude/CLAUDE.md` (the playbook) every session below it would load |
| Hosting | Local git only. GitHub repositories and CI come later, with the framework PR |
| Story | [SHIP-1](https://prashantsharma18.atlassian.net/browse/SHIP-1), spanning both repositories (created 2026-10-23, label `aidlc-demo`) |
| Isolation | No harness but aidlc in the workspace or the repositories: no superpowers, no other user plugin, no foreign `CLAUDE.md`, no auto-memory |
| Runtime | The app runs in containers (Docker Compose), so the user can open it in a browser at any time |
| Driver | Claude drives headless `claude -p` sessions; the user approves at every gate |
| Cut | No third (adoption) repository, no OpenWiki comparison, no repository evals, no flag ramp |

## The workspace

```text
~/work/shipment-tracking/             the workspace repository (git): coordination files only
├── WORKSPACE.md                      repos, owners, rules; points to the coordination plan
├── compose.yaml                      runs both apps: portal :8080, API :8081
├── flags.env                         the "flag service": eta-in-api, show-delivery-window
├── .gitignore                        ignores the two product repositories below
├── .claude/settings.json             read-only harness: a session here can read, never write
├── shipments-api/      (git)         Logistics team · .NET 10 minimal API · xUnit · api/openapi.yaml
└── customer-portal/    (git)         Web team · React + TypeScript + Vite + Vitest · Node 22 (.nvmrc)
```

- **A session at the workspace root** is for discovery and design across both repositories. Its
  harness denies every write, so it can only read and draft in its reply.
- **A session inside a repository** writes only there. The neighbour is read-only.
- `aidlc workspace` generates `WORKSPACE.md` (from the existing `workspace.md` template) and the
  read-only harness. It never overwrites a file a person wrote.
- The workspace root is a small repository of its own, so `WORKSPACE.md`, `compose.yaml` and
  `flags.env` have history and review. It holds no product code.

## A clean harness

The demo must show aidlc alone. Today this machine adds three things that would interfere:

| Source | What it adds | How the demo excludes it |
|---|---|---|
| `~/demos/.claude/CLAUDE.md` | the playbook instructions, loaded by every session below `~/demos` | the workspace lives in `~/work`, which has no `CLAUDE.md` above it |
| User plugins (`~/.claude/settings.json`) | superpowers, skill-creator, platform, and five local packs, all enabled | each repository's and the workspace's `harness.disable_user_plugins` lists them, so the rendered project settings switch them off for interactive sessions too |
| User settings in headless runs | the same plugins and any user hooks | the driver also passes `--setting-sources project,local` |

Managed settings (`/etc/claude-code`) still load, as they must: they carry the organisation's
telemetry and MCP deny list, and they enable no plugin. Auto-memory is off (rendered
`autoMemoryEnabled: false`).

**Probe before the story.** One headless session at the workspace root and one in each repository
report their loaded plugins, skills, hooks, `CLAUDE.md` files and MCP servers. Pass: only `aidlc` and
`aidlc-practice`, the repository's own hooks and rules, and lab-jira. Anything else is a finding,
fixed before the story starts.

## Running the app

- Each repository has a multi-stage `Dockerfile`: the .NET SDK builds and the ASP.NET runtime runs
  the API; Node 22 builds and nginx serves the portal, proxying `/api` to the API.
- `compose.yaml` in the workspace runs both. The portal is at <http://localhost:8080>; the API at
  <http://localhost:8081> (with `/openapi.yaml`). Both ports are free on this machine today.
- Flags come from `flags.env`, read at container start (the portal reads a runtime `config.json`
  that nginx serves), so flipping a flag needs a restart, not a rebuild.
- Images are tagged by version (`shipments-api:1.6.0`, `1.7.0`; `customer-portal:<commit>`), so the
  compatibility matrix and a rollback are real container runs.
- Agents never run Docker. The driver builds and starts the containers, as the release person would.

## Baseline (before the story)

Each repository on `main`:

- **shipments-api:** `GET /shipments/{id}` returns status and carrier, contract `openapi.yaml`
  version 1.6.0, xUnit tests including a contract test. Seeded shipments include one with a carrier
  estimate, one without, and one whose estimate ends before it starts.
- **customer-portal:** one shipment-status page, a typed API client, Vitest tests.
- Both run in containers from the start: <http://localhost:8080> shows a shipment's status.
- `aidlc init-repo`, `aidlc render --tool claude-code`, a codebase map and `AGENTS.md`.
- `aidlc check` green.

The baseline code is written directly in the framework session and committed as "baseline". It
plays the existing product. The story's code is written only through the harness.

## The story

[SHIP-1](https://prashantsharma18.atlassian.net/browse/SHIP-1): **"Show customers an estimated
delivery window."** Proposed Tier 2: an additive contract change consumed by another team. Its four
acceptance criteria are in the story.

| Slice | Repository | Change |
|---|---|---|
| S1 contract | shipments-api | OpenAPI 1.6.0 → 1.7.0: optional `estimatedDelivery {earliest, latest}`. The portal team's consumer test lives here. |
| S2 provider | shipments-api | Map the carrier estimate; drop a window that ends before it starts; behind flag `eta-in-api` (off). |
| S3 consumer | customer-portal | Client from the pinned contract tag `api-v1.7.0`; tolerant reader (field may be absent); renders in the browser's time zone; behind flag `show-delivery-window`. |

```text
SHIP story ─► intent ─► specify ─► design (workspace root: contract first) ─► plan + coordination plan
                                                                                  │
                     ┌────────────────────────────────────────────────────────────┤
                     ▼                                                            ▼
          shipments-api: S1 ─► S2                                 customer-portal: S3 (after tag api-v1.7.0)
                     │                                                            │
                verify ─► review                                             verify ─► review
                     └──────────────► compatibility matrix ◄──────────────────────┘
                                             │
                                  release (simulated) ─► operate (simulated incident) ─► feedback
```

## Where each artefact lives

| Artefact | Place |
|---|---|
| Intent, spec | `shipments-api/plans/SHIP-1/` (the contract owner holds the shared spec) |
| Design note and ADR | `shipments-api/plans/SHIP-1/` and `docs/adr/` |
| Coordination plan, compatibility matrix | `shipments-api/plans/SHIP-1/`; `WORKSPACE.md` points to it |
| Plan and task bundles | each repository's `plans/SHIP-1/`, on its own branch `feat/SHIP-1-delivery-window` |
| Review records, release runbook, incident | each repository's `plans/SHIP-1/` |

The harness denies the agent writes to `plans/**`. A skill gives its draft in the reply. After the
user approves it, the driver saves it, acting as the person's hands, and says so in the commit.

## How a session runs

```text
cd <repo or workspace root>
claude -p "<skill invocation and inputs>" --setting-sources project,local \
  --plugin-dir ~/demos/aidlc/plugins/aidlc --plugin-dir ~/demos/aidlc/plugins/aidlc-practice
```

- `--plugin-dir` loads the plugins from the local framework checkout. The approved marketplace
  points at GitHub `main`, which does not have the 5b skills yet. After the framework PR merges, the
  marketplace replaces this flag.
- The repository's own `.claude/settings.json` and hooks load as usual, so the guard, scope and
  post-checks are live.
- lab-jira is read through the agentgateway. If it is unreachable, the user pastes the story text
  and the finding is recorded.
- At each gate the driver stops and shows the draft. The user replies "approved" or gives changes.

## Real versus simulated

| Real | Simulated (labelled) |
|---|---|
| Code, tests, the contract and consumer tests; the compatibility matrix as test runs (old and new API × old and new portal); hooks blocking in live sessions; scope; `aidlc check`; `aidlc ci` as a local preview; Jira reads; telemetry in Langfuse, Loki and Grafana where it arrives; the app in containers, the release as a container rollout and the rollback as a flag flip or image switch | Pull requests and trusted CI (local git); code-owner review and approvals (records the user signs); production (the containers run locally) and the flag service (`flags.env`); the incident for operate and feedback |

## Framework work (Plan 6 code)

1. `aidlc workspace init <dir> --repo <path>…`: `WORKSPACE.md` and the read-only harness, with
   tests. It honours `disable_user_plugins` like `render` does.
2. Demo runbook `docs/demo/shipment-tracking.md`: replay the demo step by step.
3. Evidence `docs/verification/<run date>-shipment-tracking-demo.md`: what ran, what blocked, what
   was simulated, with outputs.
4. Findings: each one fixed in the framework (test first) or ruled on.

## Success criteria

- The clean-harness probe passes in the workspace and both repositories.
- Both repositories green on `main` before the story, and on their story branches after it.
- <http://localhost:8080> shows the delivery window for the seeded shipment once both flags are on,
  and hides it for the shipments without a valid estimate.
- Every stage produced its artefact, and each gate has the user's approval recorded.
- The compatibility matrix passes, including the rollback states.
- At least one hook block observed in a live session (for example, a write outside scope).
- A findings list with every item fixed or ruled on.

## Out of scope

GitHub repositories and CI for the demo; adoption of an existing repository; OpenWiki; repository
evals (Plan 5c); `aidlc metrics`; the managed-settings telemetry fix (needs the user's sudo, raise
before a recorded run).

## Risks

| Risk | Response |
|---|---|
| Headless sessions cannot answer permission prompts | A prompt becomes a denial. Record it; adjust the repository's allow list only through `.aidlc/permissions.yaml` and a reviewed change |
| A skill misbehaves in a live session | That is the point of the demo: record it, fix it with a failing test first |
| Subscription usage | About 15 sessions. Each stage is one session; no retries without a reason |
