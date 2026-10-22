# Live evidence: a guard block in Grafana leads to its local record (Plan 4a Task 5)

Date: 2026-10-22 · Claude Code 2.1.296 · Model: Haiku · Cost: 0.003 USD (list price)
Decision under test: [ADR 0003](../adr/0003-observability-built-in-telemetry.md)

## Setup

- **Fixture:** the live-harness fixture repository (`tests/harness_live/fixture.py`
  `build_repo`), built in a scratch folder and rendered for Claude Code.
- **Isolation:** the session had its own `AIDLC_HOME_DIR` and `AIDLC_LOG_DIR`.
- **Telemetry:** came only from the machine's managed settings
  (`/etc/claude-code/managed-settings.json`). The framework sent nothing.
- **Loki:** `/ready` answered `ready`.

```bash
claude -p --model haiku --setting-sources project,local --strict-mcp-config --max-turns 3 \
  --permission-mode default --output-format json "Run the shell command: git push origin HEAD"
```

## 1. The local hook record

Found with the runbook's command,
`grep '"call": "toolu_01917tLzXQLra8UqEEUCjhWy"' <log dir>/decisions.jsonl`:

```json
{"session": "804542a3-5cf0-462c-8590-05d565458780", "call": "toolu_01917tLzXQLra8UqEEUCjhWy",
 "hook": "pre-tool-guard", "tool": "shell", "decision": "deny", "rule": "shell-deny",
 "reason": "'git push origin HEAD' matches the denied pattern 'git push*'", "target": "git push origin HEAD"}
```

## 2. The same call in Loki (Claude Code's built-in telemetry)

About 20 seconds later, this query:

```bash
curl -s -G 127.0.0.1:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service_name="claude-code"} | event_name="tool_decision" | tool_use_id="toolu_01917tLzXQLra8UqEEUCjhWy"' \
  --data-urlencode "start=$(date -d '30 minutes ago' +%s)000000000"
```

returned:

```json
{"decision": "reject", "source": "hook", "tool_name": "Bash",
 "tool_use_id": "toolu_01917tLzXQLra8UqEEUCjhWy", "session_id": "804542a3-5cf0-462c-8590-05d565458780"}
```

The hook run for the same session
(`event_name="hook_execution_complete" | session_id="804542a3-…" | hook_event="PreToolUse"`):

```json
{"hook_event": "PreToolUse", "hook_name": "PreToolUse:Bash", "num_hooks": "1", "num_blocking": "1",
 "num_success": "0", "num_non_blocking_error": "0", "num_cancelled": "0", "total_duration_ms": "146"}
```

## Result

- The `tool_use_id` and `session_id` in Loki equal `call` and `session` in the local record.
- Grafana shows *that* the guard blocked a Bash call. The local record shows *which rule*
  (`shell-deny`) and *why*.
- The rule, reason and target did not reach Loki.

## Also checked (2026-10-22)

Every LogQL query in `core/observability/metrics.yaml` with status `query`, and both alert
expressions in `core/observability/alerting/aidlc.yaml`, ran as instant queries against this Loki
over 7 days. Each parsed and returned a value:

| Query | Value |
|---|---|
| `guard_denial_rate` | 0.028 |
| `override_rate` | 0.82 |
| `guard_hook_health` | 0 |
| `aidlc-session-cost` (max per session) | 7.16 USD, so the proposed 5 USD threshold would fire |

## Not verified

- **The alert rules and the proposed panel are not loaded.** The platform owner applies them
  ([platform-patch.md](../observability/platform-patch.md)).
- **Approval time** (Langfuse `claude_code.tool.blocked_on_user` spans) was not exercised. A `-p`
  session never waits for a person.
- **A fail-safe block** (the hook crashing) was not exercised live. The unit test
  `tests/unit/test_hook_record_ids.py::test_fail_safe_record_keeps_the_ids` covers it.
