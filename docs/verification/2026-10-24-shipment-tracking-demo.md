# Shipment-tracking demo: SHIP-1 end to end (Plan 6)

Run 2026-10-23 to 2026-10-24. Design: [Plan 6 design](../design/2026-10-23-plan-06-demo-design.md).
Replay: [the demo runbook](../demo/shipment-tracking.md).

## What was proved

One story, [SHIP-1](https://prashantsharma18.atlassian.net/browse/SHIP-1) "Show customers an estimated
delivery window", went from a Jira story to a released, then contained, feature across two repositories.
Every stage ran in a headless Claude Code session started inside a repository (or, for discovery and
design, at the read-only workspace root), with only the aidlc harness loaded. Every gate was the user's.

| Item | Result |
|---|---|
| Workspace | `~/work/shipment-tracking` (its own repository) with `shipments-api` (.NET 10) and `customer-portal` (React 19), local git |
| Clean harness | Probe in all three folders: only `aidlc`, `aidlc-practice`, Claude Code's four built-in plugins and lab-jira. No playbook `CLAUDE.md`. Evidence: `docs/demo/evidence/` |
| Slices | S1 contract 1.6.0 → 1.7.0, S2 provider, S3 consumer, each red before green |
| Tests | API 9 → 68, portal 12 → 88; `aidlc check` PASS on both story branches |
| Review | Three advisory reviewer passes per repository found a real bug (impossible dates such as `2026-02-30` shown as a wrong date) and a test that could not fail; both fixed test-first |
| Compatibility matrix | 8 runs on real containers (API 1.6.0/1.7.0 × portal baseline/SHIP-1 × flags off/on), 32 cells, 0 unexpected, checked through headless Chrome |
| Release | Dark deploy, then one flag at a time, 9 watch probes, timed rollback rehearsal (2.9 s); the page showed "Estimated delivery: 24 Oct 2026, 10:00 – 14:00" |
| Operate | A simulated incident (carrier sends UK local time marked `Z`) diagnosed with five hypotheses, cause confirmed by a named person, contained by the pre-approved rollback in 4.5 s, recorded as a failed change |
| Feedback | 13 lessons routed to layers; six framework lessons below |
| Sessions | 31 headless sessions, about 15 USD API-equivalent on the user's subscription |

## Gates (all the user's)

| # | Gate | Decision |
|---|---|---|
| 1 | Intent | Owner Prashant Sharma, priority Medium, Tier 2; five open questions answered |
| 2 | Spec v1 | 12 criteria, 16 edge cases decided; E10 reworded to "after restart" |
| 3 | Discovery | Proceed at L1, Tier 2 |
| 4 | Design | D1 optional object, D2 drop invalid windows and omit nulls globally, D3 a pure portal module; three ADRs accepted |
| 5, 6 | Plans | S1 and S2 (API), S3 (portal), coordination plan |
| 7 | Review | Fix six findings test-first, document five, dismiss the rest with reasons |
| 8 | Release | Ship, with C3 (no second person) and S-F1 (sequential ids, spec E14) accepted; the skill had recommended limit |
| - | Incident | Contain with R2 (portal flag off) |

## The harness at work

From `~/.aidlc/logs/decisions.jsonl` (entries for the demo folders):

| Decision | Rule | Count | What it stopped |
|---|---|---|---|
| deny | `retry-limit` | 1 recorded (4 occurrences reported by sessions) | Further runs after three failing checks; a person reviewed and reset each time |
| deny | `outside-scope` | 1 | A new test file outside bundle S2's MAY CHANGE |
| deny | `outside-repo` | 1 | A write outside the repository |
| flag | `protected-path` | 47 | Noise: committed approved bundles and the contract (finding F14) |
| allow | `in-scope` | 43 | Edits inside the approved scope |

Claude Code's own permission rules also refused edits to the protected contract (`api/openapi.yaml`) and
to `plans/`; a person applied the approved contract change.

## Real and simulated

| Real | Simulated (labelled where it appears) |
|---|---|
| Code, tests, contract checks, hooks and scope in live sessions, the matrix and release on real containers, Jira reads | CI (local git: every trusted-CI cell says "no run"), a second person (the user signed as each team), production (the local stack), the incident's carrier reply |

## Findings

| ID | Finding | Layer | Outcome |
|---|---|---|---|
| F1 | `--setting-sources project,local` drops user-scope MCP servers such as lab-jira | harness use | Ruling: isolation comes from the rendered project settings instead |
| F2 | claude.ai connectors and the account's synced skills loaded in repository sessions | harness | Fixed (`770b1ea`): `harness.disable_claude_ai_connectors`, `harness.deny_skills`; workspace defaults |
| F3 | Four `@builtin` plugins load | - | Ruling: part of Claude Code, allowed and listed |
| F4 | Repository sessions inherit the workspace's `CLAUDE.md` | - | Ruling: kept; it carries the cross-repository rules |
| F5 | The Jira site lookup is not a mapped tracker read, so the intent session could not read SHIP-1 | context | Fixed in the demo's `AGENTS.md` (name the site) |
| F6 | Design at the read-only workspace root cannot see checks fail | skill | Fixed (`f45dd56`) |
| F7 | The sandbox's placeholders show in `git status` | - | Recorded; already documented |
| F8 | `aidlc scope` refused a planner's prose in MAY CHANGE | skill, template | Fixed (`703e885`) |
| F9 | `dotnet` cannot build, format or test in the sandbox (MSBuild node pipes, `.gitmodules` placeholder) | profile | Fixed (`703e885`): in-process MSBuild, no git queries, whitespace format |
| F10 | The scope step counted the sandbox's placeholders as changes | check | Fixed (`703e885`): character devices are skipped |
| F11 | A slice could not edit the protected contract its bundle listed | skill | Fixed (`f45dd56`): the plan marks protected paths "a person applies" |
| F12 | The demo's `AGENTS.md` test command crashed in the sandbox | context | Fixed in the demo's `AGENTS.md` |
| F13 | Sessions could not write `.git` (`index.lock`: read-only), so a person committed every slice | harness | **Open.** The docs say the working directory is writable; not reproduced in a scratch repository |
| F14 | `protected-path` flags fire on every call while an approved bundle is on the branch | hook | **Open** (= L11): compare against the approval commit |
| F15 | Claude Code matches `Edit(api/**)` and `Edit(./api/**)` at any depth; only `Edit(/api/**)` is root-anchored, so rendered protected-path rules also block `src/api/` | render | **Waiting for the owner's decision**: the fix narrows a rendered deny rule |
| F16 | The retry counter carries failures into the next session; a person's passing run is counted as a failure | hook | Ruling: by design (a PASS in the agent-writable `.check/result.json` could be forged); a person reviews and resets |
| F17 | After merging the base branch, the scope check fails until `aidlc scope` runs again | skill | Fixed (`f45dd56`) |
| L6 | Tests that cannot fail passed review (B1, F2) | guardrail | Backlog: a mutation check |
| L7 | Criterion IDs missing from test names | guardrail | Backlog: a traceability check |
| L8 | Evidence text overclaimed counts | eval | Deferred to Plan 5c |
| L9 | A release tag was cut before review | guardrail | Backlog: tags only from a reviewed commit on main |
| L10 | The Jira site lookup is reachable | guardrail | Ruling: unmapped tools already ask, so an unattended session is denied |
| L12 | The decision log has no repository or reason field | measure | Backlog |
