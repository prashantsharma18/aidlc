# Replay the shipment-tracking demo

This runbook rebuilds the demo from nothing and walks one story through every stage. What happened on
the first run, and what it found, is in [the evidence](../verification/2026-10-24-shipment-tracking-demo.md).

You need: Claude Code, Docker, .NET 10 SDK, Node 22 (nvm), Google Chrome, and the lab-jira MCP server
connected (`claude mcp list`). Commands assume this checkout is `~/demos/aidlc`.

## 1. The workspace and the two repositories

Keep the workspace out of any folder whose parents hold a `CLAUDE.md` meant for something else.

```bash
mkdir -p ~/work/shipment-tracking && cd ~/work/shipment-tracking && git init -q -b main
printf '/shipments-api/\n/customer-portal/\n' > .gitignore
```

Build the two baseline applications as Plan 6 Tasks 2 and 3 describe
([the plan](../plans/2026-10-23-plan-06-shipment-tracking-demo.md)): `shipments-api` with contract 1.6.0
(tag `api-v1.6.0`) and `customer-portal` with the shipment lookup and runtime flags.

```bash
~/demos/aidlc/bin/aidlc workspace init . --key SHIP-1 --title "Show customers an estimated delivery window" \
  --repo "shipments-api=Logistics team" --repo "customer-portal=Web team" \
  --disable-plugin superpowers@claude-plugins-official      # repeat for every user plugin you have
```

In each repository: `aidlc init-repo`, fill `AGENTS.md` and `docs/codebase-map.md`, then set in
`.aidlc/config.yaml`:

```yaml
harness:
  disable_user_plugins: [superpowers@claude-plugins-official]   # every enabled user plugin
  disable_claude_ai_connectors: true
  deny_skills: ["anthropic-skills *"]
tool_names:                                                      # lab-jira's names; read them from a session's init message
  tracker.read_issue: mcp__lab-jira__atlassian-rovo-getjiraissue
  tracker.search: mcp__lab-jira__atlassian-rovo-searchjiraissuesusingjql
  tracker.add_comment: mcp__lab-jira__atlassian-rovo-addoreditjiraissuecomment
  tracker.create_issue: mcp__lab-jira__atlassian-rovo-createjiraissue
  tracker.transition_issue: mcp__lab-jira__atlassian-rovo-transitionjiraissue
```

Name the Jira site and its cloudId in each `AGENTS.md`, so agents read issues without the site lookup.
Then `aidlc render --tool claude-code` and `CHECK_SCOPE=skip aidlc check` (no bundle exists yet), and commit.

Run the app: `docker compose up -d --build` with the workspace's `compose.yaml`; open <http://localhost:8080>.

Open `claude` once in each of the three folders and accept the trust prompt.

## 2. Prove the harness is clean

```bash
for d in ~/work/shipment-tracking ~/work/shipment-tracking/shipments-api ~/work/shipment-tracking/customer-portal; do
  (cd "$d" && claude -p "Reply OK." --plugin-dir ~/demos/aidlc/plugins/aidlc --plugin-dir ~/demos/aidlc/plugins/aidlc-practice \
     --output-format stream-json --verbose --max-turns 1 | head -1 | python3 ~/demos/aidlc/docs/demo/probe.py .claude/settings.json)
done
```

Expect `clean` three times.

## 3. Run the story

Every stage is one session. Start it in the folder named, with these flags:

```bash
AIDLC_UNATTENDED=1 claude -p "<prompt>" --plugin-dir ~/demos/aidlc/plugins/aidlc \
  --plugin-dir ~/demos/aidlc/plugins/aidlc-practice --permission-mode dontAsk --model sonnet --output-format json
```

Continue a session that asks questions with `--resume <session_id>`. Agents draft; you approve, save
drafts under `plans/`, and commit (the sandbox could not write `.git` in the first run, finding F13).

| Stage | Folder | Prompt | You then |
|---|---|---|---|
| Intent | shipments-api | `/aidlc:aidlc-intent SHIP-1` | set owner and priority; save `plans/SHIP-1/intent.md` |
| Spec | shipments-api | `/aidlc:aidlc-specify SHIP-1` | decide every edge case; approve; save `spec.md` |
| Discover | workspace root | `/aidlc:aidlc-discover SHIP-1 …` | set the level; proceed |
| Design | workspace root | `/aidlc:aidlc-design SHIP-1` | decide D1–D3; save the design note and ADRs |
| Plan | each repository | `/aidlc:aidlc-plan SHIP-1` | approve; add each bundle to `plans/approved-bundles.txt` on main; run `aidlc scope --branch <branch>` |
| Build | each repository | `/aidlc:aidlc-build-slice SHIP-1 <slice>` | apply protected-path changes (the contract) yourself; commit; tag `api-v1.7.0` after S2 |
| Verify | each repository | `/aidlc:aidlc-verify SHIP-1` | save the evidence table |
| Review | each repository | `/aidlc:aidlc-review SHIP-1` | decide each disposition; run one fix round |
| Release | shipments-api | `/aidlc:aidlc-release SHIP-1` | decide ship, limit or hold; roll out per the runbook |
| Operate | shipments-api | `/aidlc:aidlc-operate SHIP-1 <report>` | run the queries it names; confirm the cause; choose containment |
| Feedback | shipments-api | `/aidlc:aidlc-feedback SHIP-1` | route each lesson |

When a session reports the retry limit, read what failed, then `aidlc attempts --reset`. After merging
main into a story branch, run `aidlc scope` again.

## 4. Check what customers see

```bash
node ~/demos/aidlc/docs/demo/page-check.mjs http://localhost:8080/ SHP-1001 shot.png
```

It tracks a shipment in headless Chrome (Europe/London, en-GB) and prints the page text and the
delivery-window line. The compatibility matrix and the release used it for every page check.

> 🎯 **What this means for you:** The demo is a rehearsal for a real team. Each gate a person passed here
> is a gate a named owner passes there; each simulated item in the evidence is a real system there.
