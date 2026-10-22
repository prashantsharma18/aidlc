# Observability runbooks

Owner: harness owners. The alert rules are in
[`core/observability/alerting/aidlc.yaml`](../../core/observability/alerting/aidlc.yaml).

## From a Grafana rejection to the local record

Grafana shows that a hook blocked a call. The local decision log says which rule blocked it and why.

1. In Grafana Explore (datasource Loki), run:
   `{service_name="claude-code"} | event_name="tool_decision" | decision="reject" | source="hook"`
2. Copy the record's `tool_use_id`, for example `toolu_01AbC…`.
3. On the machine that ran the session, run:
   `grep '"call": "toolu_01AbC…"' ~/.aidlc/logs/decisions.jsonl`
4. Read the record:
   - `rule` is the deciding control;
   - `reason` is why;
   - `fail-safe` means the hook itself failed, so read its reason and fix the hook.

If nothing matches, one of these is true:

- the session ran on another machine, or with another `AIDLC_LOG_DIR`;
- the log was deleted;
- the hook could not parse its input. That fail-safe record has no ids, so look for `fail-safe`
  records at the same time.

## aidlc-hook-health

- **Fires when** any PreToolUse hook run errored without blocking, or was cancelled (timed out), in
  the last 15 minutes.
- **Owner:** harness owners.
- **It means** some PreToolUse hook did not decide on some calls. It counts every PreToolUse hook:
  the aidlc guard, plugin hooks, and hooks in other repositories.
- **It does not see a guard crash.** The guard's shim turns any internal error into exit 2, a
  fail-safe block. Claude Code counts that in `num_blocking` and records the call as a
  `tool_decision` with `source="hook"`, the same as a deliberate deny. Only the local record says
  `rule: fail-safe` ([from a Grafana rejection to the local record](#from-a-grafana-rejection-to-the-local-record)).
- **First checks:**
  1. Run `bin/aidlc doctor` in the repository: are the hooks wired and the rendered files current?
  2. Look at `agent-flow`, "Hook time p95 by hook". A guard near its timeout is cancelled.
  3. Read the local decision log around that time for `fail-safe` records.
- **Close it** when the cause is fixed and no new errors appear for 15 minutes.

## aidlc-session-cost

- **Fires when** a single Claude Code session spent more than 5 USD (list price) in the last 24
  hours.
- **Owner:** harness owners.
- **It means** a session is unusually expensive; it is a prompt to read, not a limit.
- **First checks:**
  1. Open the session from `agent-flow`, "Costliest sessions", in Langfuse.
  2. Look for retries: the same check failing again and again.
  3. Check the model tier and context size (guide 12.16).
- **Close it** when you know why. Raise the threshold in the rule if this cost is normal for your
  work.
