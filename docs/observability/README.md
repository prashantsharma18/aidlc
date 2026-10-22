# Observability

The harness is observed through Claude Code's built-in OpenTelemetry. The framework sends nothing
itself ([ADR 0003](../adr/0003-observability-built-in-telemetry.md)).

## What you see centrally

Claude Code's events reach the platform's collector, then Loki and Grafana. The platform's
generated dashboards already show most of what you need.

| Question | Event | Where to look |
|---|---|---|
| Did a hook block a call? | `tool_decision`, `decision="reject"`, `source="hook"` | `agent-flow`: "Rejected actions by tool", "Hook refusals by hook" |
| Did a hook fail or time out? | `hook_execution_complete`, `hook_event="PreToolUse"` | the `guard_hook_health` query, and the `aidlc-guard-hook-health` alert |
| How slow are the hooks? | `hook_execution_complete`, `total_duration_ms` | `agent-flow`: "Hook time p95 by hook" |
| What did a session cost? | `api_request`, `cost_usd` | `ai-usage-overview`, and `agent-flow`: "Costliest sessions" |
| Which tool calls failed? | `tool_result`, `success="false"` | `agent-flow`: "Tool failure rate per day" |
| How often do people approve asks? | `tool_decision` from a user source | the `override_rate` query |

Every guide metric, with its source and query, is in
[`core/observability/metrics.yaml`](../../core/observability/metrics.yaml). Each entry has a
`status`:

- `platform-panel`: read the named panel;
- `query`: run the LogQL in Grafana Explore;
- `langfuse`: read the trace;
- `github-ci`: computed from GitHub runs (Plan 6);
- `local-log`: read the decision log;
- `not-available`: no source yet, and the `gap` says why.

## What never leaves the machine

The guard and the post-check write every decision to the decision log,
`~/.aidlc/logs/decisions.jsonl` (or `$AIDLC_LOG_DIR`). That log is the harness's audit trail. Its
rule names, reasons and targets never leave the machine. The framework does not rotate it; delete
it when you no longer need it.

Every record carries:

- `session`, Claude Code's `session_id`;
- `call`, Claude Code's `tool_use_id`.

So a blocked call in Grafana leads to its record. See
[From a Grafana rejection to the local record](runbooks.md#from-a-grafana-rejection-to-the-local-record).

Check results have their central record in GitHub CI
([ADR 0002](../adr/0002-github-trusted-ci.md)).

## The telemetry baseline

An organisation switches telemetry on centrally. A developer never sets it per repository.

| Setting | Why |
|---|---|
| `CLAUDE_CODE_ENABLE_TELEMETRY=1` | Turns on export. |
| `OTEL_LOGS_EXPORTER=otlp` | Events: tool decisions, hook runs, cost. Everything above needs it. |
| `OTEL_METRICS_EXPORTER=otlp` | Counters such as active time, commits and lines (platform panels). |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | Claude Code has no default; `http/protobuf` in this lab. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` and `otelHeadersHelper` | Where to send, and the bearer token. Not needed behind a gateway. |
| `OTEL_RESOURCE_ATTRIBUTES` | `team`, `cost_center`, `env`, `enduser.pseudonym`: the platform's slicing keys. |
| `OTEL_TRACES_EXPORTER=otlp` and `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1` | Optional. Traces in Langfuse, including how long a call waited for approval. |

`tool_use_id` and `session.id` are standard event attributes; they need no extra setting.

**Content flags.** `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`,
`OTEL_LOG_TOOL_DETAILS` and `OTEL_LOG_TOOL_CONTENT` send content: prompts, commands, file paths
and output. They are off by default. Switch them on only when the collector strips content, as
this lab's collector does for records outside the content cohort.

There are two routes for delivering the baseline:

- **A managed-settings file**, pushed by device management. This lab's is
  `/etc/claude-code/managed-settings.json`.
- **The Claude apps gateway's `managed` block**
  (https://code.claude.com/docs/en/claude-apps-gateway). Signed-in clients send their telemetry to
  the gateway, which forwards it to the organisation's collectors. This is the documented route
  for Amazon Bedrock, Google Cloud and Microsoft Foundry.

On Team and Enterprise plans, claude.ai also shows an adoption dashboard. It does not replace the
events above.

## Alerts and the platform

The framework proposes two alert rules and one dashboard panel. The platform owner applies them:
see [platform-patch.md](platform-patch.md) and [runbooks.md](runbooks.md).

## Retention and access

- **Local:** the decision log stays until you delete it.
- **Platform:** retention and access follow the platform's policy. In this lab, Loki keeps 720
  hours (30 days, `PC/lab/loki/loki.yaml`), and Langfuse's 30 days is a policy target.
