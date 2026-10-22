<!-- aidlc template: adr -->
# 0003 · Observability uses Claude Code's built-in telemetry; hook records stay local

Status: Accepted (2026-10-22). Amends design §10. · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (changes what every installed repository reports)

## Context

Design §10 planned harness emitters: `aidlc.hook.decision` and `aidlc.check.result` records,
shipped from the guard's local log at session end. Plan 4a v1 and v2 built that as a custom OTLP
sender in two new hook phases, with an outbox, a cursor, retries and a network exception for hooks.

On 2026-10-22 the owner ruled it out. The framework must not reinvent telemetry plumbing, and must
not put anything extra on a developer's machine.

What Anthropic documents supports that ruling. Every documented enterprise path ships Claude Code's
own telemetry:

- a managed-settings file that points Claude Code at the organisation's collector;
- the [Claude apps gateway](https://code.claude.com/docs/en/claude-apps-gateway), which receives
  the clients' exports and forwards them, stamped with the person's identity;
- Team and Enterprise plans, which add an adoption dashboard on claude.ai.

None of them ships data a hook wrote. Instead, the
[monitoring docs](https://code.claude.com/docs/en/monitoring-usage) say each event's `tool_use_id`
"matches the `tool_use_id` passed to hooks, allowing correlation between OTel events and
hook-captured data".

Claude Code's built-in events already record what matters centrally:

- `tool_decision` with `source="hook"` when the guard blocks a call;
- `hook_execution_complete`, with counts of blocking, failed and cancelled runs;
- `tool_result`, `api_request` (cost) and the session.

## Decision

1. **Observability uses Claude Code's built-in telemetry**, switched on centrally through managed
   settings or a gateway's `managed` block. The baseline is in
   [docs/observability/README.md](../observability/README.md).
2. **The framework emits nothing.** It has no sender, no telemetry hook phase, and no agent or
   collector on the developer's machine. Hooks make no network calls.
3. **Hook records stay local**, in the decision log. Every record carries `session` (Claude Code
   `session_id`) and `call` (`tool_use_id`), including fail-safe records whenever the payload
   parsed. A blocked call in Grafana leads to its local record through the
   [runbook](../observability/runbooks.md).
4. **Check results are read from GitHub CI** ([ADR 0002](0002-github-trusted-ci.md)). The metrics
   built on them come from `aidlc metrics` in Plan 6.
5. **Dashboards belong to the platform.** The framework keeps a metric catalogue
   (`core/observability/metrics.yaml`) and proposes alerts and panels to the platform owner. It
   never copies a dashboard.

## Consequences

- **Centrally, you see that a hook blocked a call**: which tool, in which session, and when. The
  rule name, reason and target stay on the developer's machine.
- **Cost per task has no central source.** Claude Code events carry no branch or ticket. They
  carry the repository only with `OTEL_METRICS_INCLUDE_REPOSITORY=true`, which would let
  "decisions stopped" become a query per repository. `metrics.yaml` records each gap and where to
  look instead.
- **Hooks gain no network code and no new failure modes.**
- **`aidlc.bundle`, `aidlc.tier` and the `aidlc.*` attribute namespace are not emitted.** The
  platform's allow-list needs no `aidlc.*` entry.

## Rejected alternatives

- **A custom OTLP sender in hook phases (Plan 4a v2).** It rebuilds a log shipper (cursor,
  rotation, queue, retries) that standard tools already provide.
- **A collector or log agent tailing the decision log on the developer's machine.** It is
  standard log shipping, but organisations do not commonly run one on developer laptops.
- **HTTP hooks posting each payload to a central service.** The payload carries commands and
  paths, so it needs a new service that strips content.
