# Plan 4a: Observability. Implementation plan (v3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** You can see what the harness does through Claude Code's built-in OpenTelemetry. Every guard block in Grafana leads to the local hook record that explains it. The framework adds no telemetry plumbing of its own.

**Architecture.** Observability uses only what Claude Code and the platform already provide:
- **Claude Code's built-in telemetry, switched on centrally.** It reaches the platform's collector, Loki and Grafana. On a laptop it is switched on through managed settings; in an enterprise, through managed settings or the Claude apps gateway. It records:
  - every tool decision, including `source=hook` when our guard blocked;
  - tool results, hook executions, cost and sessions.
- **The hooks' own record stays on the machine.** The guard and post-check keep writing `~/.aidlc/logs/decisions.jsonl`, as they have since Plan 2. Each record carries Claude Code's `session_id` and `tool_use_id`. That is the correlation Anthropic documents: "`tool_use_id` matches the `tool_use_id` passed to hooks, allowing correlation between OTel events and hook-captured data."
- **Check results.** Their central record is GitHub CI (ADR 0002). The metrics built on them belong to Plan 6's `aidlc metrics`.
- **What this plan adds:**
  - a fix so every hook record, including a fail-safe one, carries both ids;
  - a metric catalogue that maps each guide metric to its real source;
  - two alert rules and one dashboard panel, proposed to the platform owner;
  - docs, a runbook and ADR 0003;
  - one live proof of the match.

**Tech Stack:** Python 3.12 standard library and the existing CLI (PyYAML, jsonschema); LogQL (Loki 3.7); Grafana file provisioning (alerting).

**Spec:**
- design §10 (`docs/design/2026-10-18-aidlc-framework-design.md`), amended by ADR 0003 in this plan;
- ADR 0002;
- the user's decisions:
  - 2026-10-20: Plan 4 is split into 4a and 4b, and platform changes are made only as proposed patches.
  - 2026-10-22: use no custom telemetry sender and nothing extra on the developer's machine. Use Claude Code's built-in telemetry only. Hook records stay local and are matched by `tool_use_id`.
- Anthropic's monitoring docs (https://code.claude.com/docs/en/monitoring-usage) and Claude apps gateway docs (https://code.claude.com/docs/en/claude-apps-gateway).

**Supersedes:** v1 (`b4a12ca`) and v2 (`c7eb8db`) of this plan. Their custom OTLP sender, session hooks, outbox and network ADR are dropped.

## Facts this plan relies on (verified 2026-10-22, read-only)

- **The managed settings on this machine** (`/etc/claude-code/managed-settings.json`) already switch on built-in telemetry:
  - `CLAUDE_CODE_ENABLE_TELEMETRY=1`, with metrics, logs and traces sent over OTLP;
  - `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`;
  - `OTEL_RESOURCE_ATTRIBUTES` set to team, cost centre, environment, pseudonym and cohort;
  - `otelHeadersHelper`;
  - the content flags (prompts, responses, tool details and content) are on. The collector strips content from non-cohort records; that is the platform's choice.
- **The collector's metadata allow-list** (`PC/policy/telemetry/metadata-allowlist.yaml`) already keeps everything this plan reads:
  - `decision`, `source`, `tool_name`, `tool_use_id`;
  - `success`, `error_type`, `cost_usd`;
  - `hook_event`, `hook_name`, `num_blocking`, `num_non_blocking_error`, `num_cancelled`, `total_duration_ms`;
  - `session.id` and `session.key`.

  No platform change is needed for the data itself.
- **Live data in Loki** (`service_name="claude-code"`):
  - `tool_decision` with `decision="reject"`, `source="hook"` and `tool_use_id="toolu_…"`, from the 2026-10-20 live attack runs;
  - `hook_execution_complete`, with `hook_event`, `hook_name`, `num_blocking`, `num_non_blocking_error` and `num_cancelled`;
  - the labels are `session_id` and `session_key`, with dots becoming underscores in LogQL. Claude Code events carry no `branch`, `repo` or `ticket_key`.
- **The platform's generated dashboards** (`PC/grafana/dashboards/`, produced by `PC/tools/grafana_dashboards.py`; the platform's tests pin the set):
  - `ai-usage-overview`: people, sessions, cost, cost by model;
  - `agent-flow`: "Costliest sessions", "Hook refusals by hook", "Rejected actions by tool", "Failed tool calls by tool (M7)", "Tool failure rate per day", "Hook time p95 by hook".

  The framework does not duplicate them.
- **Grafana has no alert provisioning directory** today. `PC/lab/grafana/provisioning/alerting/` would already be mounted with the provisioning folder.
- **The framework's hook records.**
  - `guard._log` (`core/hooks/guard.py:1117`) writes `session` and `call` from the event, and `claude_shim.to_generic` (`core/hooks/claude_shim.py:62`) fills them from `session_id` and `tool_use_id`.
  - **Gap:** the shim's fail-safe path (`claude_shim.py`, in the `except` block of `main`) logs `{"hook": …, "tool": None}`, with no `session` and no `call`. A crash blocks the call: Grafana shows a hook rejection, but the local record cannot be found by its `tool_use_id`.
  - **Gap:** the unit tests don't all isolate `AIDLC_LOG_DIR`. Running the suite has written fail-safe records into the real `~/.aidlc/logs/decisions.jsonl`, which pollutes the person's audit trail.

## Global Constraints

- **No telemetry plumbing:**
  - no code that sends data;
  - no new hook phase;
  - no agent, collector or daemon on the developer's machine;
  - no network use in the hooks.
- **Dependencies.** Hooks use the standard library only. The CLI uses the standard library plus PyYAML and jsonschema. Add no new dependency.
- **The platform.** The framework edits no platform file. Platform changes are a proposed kit in `docs/observability/platform-patch.md`, plus `core/observability/alerting/aidlc.yaml`.
- **What reaches Grafana** is only what Claude Code's built-in telemetry sends and the platform's collector keeps. The hook records (rule, reason, target) never leave the machine.
- **Tests.**
  - Unit tests never write the real `~/.aidlc/logs`, never use the network, and never call a model.
  - Never change an assertion in a test older than this plan.
- **Commits** use the repo-local identity (`prashantsharma18`, noreply) and stage explicit paths. `main` is protected: the work lands through a pull request with green `unit`, `sandbox` and `policy` checks.
- **Every observability file with a `meta`** declares `guide:`. Run `bin/aidlc trace` after adding or changing one.
- **Run before every commit:**
  - `make test`;
  - `bin/aidlc trace --check`;
  - `bin/aidlc check context-drift .`;
  - `bin/aidlc policy validate`.

## Review Focus

1. **A hook crash (fail-safe) on a call whose payload parsed.** The local record still carries `session` and `call`, so the Grafana rejection can be traced. Pinned by Task 1 `test_fail_safe_record_keeps_the_ids`.
2. **A payload that is not JSON.** There are no ids to keep. The fail-safe record is still written and the hook still exits 2, so nothing changes for the session. Pinned by Task 1 `test_unparseable_payload_still_logs_fail_safe`.
3. **The test suite run on a developer's machine** leaves the real decision log untouched. Pinned by Task 0 `test_the_suite_uses_its_own_decision_log`, plus the size check in Task 0 Step 4.
4. **A metric with no central source** (rule names, check results). The catalogue says so, with the reason and where to look instead; it never invents a query. Pinned by Task 2 `test_every_metric_names_a_real_source`.
5. **An alert that cannot evaluate,** such as a range query or a missing reduce step. Each rule is an instant query, then a reduce, then a threshold. Pinned by Task 3 `test_every_alert_is_complete_and_evaluable`.

---

### Task 0: Keep the test suite out of the real decision log

**Files:**
- Modify: `tests/__init__.py` (currently empty)
- Test: `tests/unit/test_suite_isolation.py`

**Interfaces:** Produces a suite-wide temporary `AIDLC_LOG_DIR`, unless the caller has already set one. Existing tests that set their own (`GuardEnv`, the live harness) keep doing so.

- [ ] **Step 1: Write the failing test.**

```python
# tests/unit/test_suite_isolation.py
import os
import unittest
from pathlib import Path


class SuiteIsolationTest(unittest.TestCase):
    def test_the_suite_uses_its_own_decision_log(self):
        log_dir = Path(os.environ["AIDLC_LOG_DIR"])
        self.assertNotEqual(log_dir.resolve(), (Path.home() / ".aidlc" / "logs").resolve())
        self.assertTrue(log_dir.name.startswith("aidlc-test-logs-"))
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_suite_isolation -v`. Expected: FAIL with `KeyError: 'AIDLC_LOG_DIR'`.
- [ ] **Step 3: Implement.** Write `tests/__init__.py`:

```python
"""Suite-wide default: tests never write the person's real decision log (~/.aidlc/logs).
A test that needs a specific log directory sets AIDLC_LOG_DIR itself (e.g. GuardEnv)."""
import atexit
import os
import shutil
import tempfile

if "AIDLC_LOG_DIR" not in os.environ:
    _logs = tempfile.mkdtemp(prefix="aidlc-test-logs-")
    os.environ["AIDLC_LOG_DIR"] = _logs
    atexit.register(shutil.rmtree, _logs, True)
```

- [ ] **Step 4: Run it and watch it pass.** Run the Step 2 command. Then compare the size of `~/.aidlc/logs/decisions.jsonl` before and after `make test`: `stat -c %s ~/.aidlc/logs/decisions.jsonl; make test; stat -c %s ~/.aidlc/logs/decisions.jsonl` (if the file does not exist, check that it still does not). Expected: the test passes, `make test` passes, and both sizes are equal.
- [ ] **Step 5: Commit.** Commit with `test: the suite uses its own decision log, never the person's ~/.aidlc/logs`.

### Task 1: Every hook record carries the session and tool-use ids, fail-safe included

**Files:**
- Modify: `core/hooks/claude_shim.py` (`main`: keep the parsed payload so the fail-safe record carries `session` and `call`)
- Test: `tests/unit/test_hook_record_ids.py`

**Interfaces:**
- Consumes `guard._log(event, result, version=None)`, which writes `session` and `call` from `event`.
- Produces this guarantee: every record written by the Claude shim carries `session` (Claude Code `session_id`) and `call` (Claude Code `tool_use_id`) whenever the payload parsed as a JSON object. The docs and runbook (Task 4) rely on it.

- [ ] **Step 1: Write the tests.** The first three pin behaviour that works today; the fourth fails today.

```python
# tests/unit/test_hook_record_ids.py
"""The local hook record is matched to Claude Code's telemetry by tool_use_id (Anthropic: "tool_use_id
matches the tool_use_id passed to hooks, allowing correlation between OTel events and hook-captured
data"). Every record the shim writes must carry the session and tool-use ids it was given."""
import json
import os
import unittest
from pathlib import Path

from tests.unit.test_claude_shim import run
from tests.unit.test_guard import GuardEnv, repo_on_branch

IDS = {"session_id": "5f0c1a2b-1111-2222-3333-444455556666", "tool_use_id": "toolu_01AbCdEfGhIjKlMn"}


def records(env) -> list[dict]:
    path = env.base / "logs" / "decisions.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


class HookRecordIdsTest(unittest.TestCase):
    def assert_ids(self, record):
        self.assertEqual(record["session"], IDS["session_id"])
        self.assertEqual(record["call"], IDS["tool_use_id"])

    def test_a_guard_decision_keeps_the_ids(self):
        with GuardEnv() as env:
            run("pre", {**IDS, "tool_name": "Bash", "tool_input": {"command": "git push"}, "cwd": os.getcwd()})
            [record] = records(env)
            self.assertEqual(record["decision"], "deny")
            self.assert_ids(record)

    def test_a_post_check_flag_keeps_the_ids(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                run("post", {**IDS, "tool_name": "Bash", "tool_input": {"command": "x"}, "cwd": str(root),
                             "tool_response": {"stdout": "AKIA" + "ABCDEFGHIJKLMNOP"}})
                flagged = [r for r in records(env) if r["decision"] == "flag"]
                self.assertTrue(flagged)
                for record in flagged:
                    self.assert_ids(record)
        finally:
            repo.__exit__(None, None, None)

    def test_a_post_failure_record_keeps_the_ids(self):
        repo, root = repo_on_branch()
        try:
            with GuardEnv() as env:
                run("post-failure", {**IDS, "tool_name": "Bash", "tool_input": {"command": "x"}, "cwd": str(root),
                                     "error": "Exit code 1\nboom"})
                logged = records(env)
                self.assertTrue(logged)
                for record in logged:
                    self.assert_ids(record)
        finally:
            repo.__exit__(None, None, None)

    def test_fail_safe_record_keeps_the_ids(self):
        with GuardEnv() as env:
            out = run("pre", {**IDS, "tool_name": "Bash", "tool_input": "not an object", "cwd": os.getcwd()})
            self.assertEqual(out.returncode, 2)
            [record] = records(env)
            self.assertEqual(record["rule"], "fail-safe")
            self.assert_ids(record)

    def test_unparseable_payload_still_logs_fail_safe(self):
        with GuardEnv() as env:
            out = run("pre", "not json")
            self.assertEqual(out.returncode, 2)
            [record] = records(env)
            self.assertEqual(record["rule"], "fail-safe")
            self.assertIsNone(record["session"])
            self.assertIsNone(record["call"])
```

`test_unparseable_payload_still_logs_fail_safe` asserts that the keys exist with value `None`. Today the fail-safe record has no `session` or `call` key at all, so this test also fails today, with a `KeyError`.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_hook_record_ids -v`. Expected: the first three pass. `test_fail_safe_record_keeps_the_ids` and `test_unparseable_payload_still_logs_fail_safe` fail with `KeyError: 'session'`.

  To prove the three passing tests can fail, temporarily change `"call": payload.get("tool_use_id")` in `to_generic` to `"call": None`, re-run them, see them fail, and revert.
- [ ] **Step 3: Implement.** In `core/hooks/claude_shim.py` `main`:
  - set `payload = None` next to `guard = None`, before the `try:`;
  - in the `except` block, replace the fail-safe `guard._log(...)` call with:

```python
                ids = payload if isinstance(payload, dict) else {}
                session, call = ids.get("session_id"), ids.get("tool_use_id")
                guard._log({"hook": "pre-tool-guard" if pre else "post-tool-check", "tool": None,
                            "session": session if isinstance(session, str) else None,
                            "call": call if isinstance(call, str) else None},
                           {"decision": "deny" if pre else "flag", "rule": "fail-safe",
                            "reason": f"aidlc hook failed ({detail}); blocked to be safe"})
```

  `payload` is assigned by the existing `payload = json.loads(sys.stdin.read())` line, inside the `try`. Nothing else changes, and the shim still exits 2.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_claude_shim -v` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `fix(hooks): a fail-safe record keeps the session and tool_use_id, so a Grafana hook rejection can be traced locally`.

### Task 2: The metric catalogue

**Files:**
- Create: `core/observability/metrics.yaml`
- Modify:
  - `cli/aidlc/trace.py`: `collect` also scans `core/observability/*.yaml` `meta.guide`, with kind `observability`;
  - `tests/unit/test_trace.py` (one new test);
  - `docs/traceability.md` (regenerated).
- Test: `tests/unit/test_observability_assets.py`

**Interfaces:** Produces `core/observability/metrics.yaml`. Each entry has the keys `id`, `guide`, `definition`, `status`, `source`, `read_with` and `action`, plus the key its status needs:

| `status` | Extra key |
|---|---|
| `platform-panel` | `panel`: `"<dashboard uid>/<panel title>"` |
| `query` | `query`: LogQL |
| `langfuse` | `where` |
| `github-ci` | `where` |
| `local-log` | `where` |
| `not-available` | `gap` |

The docs (Task 4) and the platform kit read it.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_observability_assets.py
import re
import unittest

import yaml

from aidlc.paths import framework_root

OBS = framework_root() / "core" / "observability"
STATUS_KEY = {"platform-panel": "panel", "query": "query", "langfuse": "where", "github-ci": "where",
              "local-log": "where", "not-available": "gap"}
# Attribute names the platform collector keeps on Claude Code events (metadata-allowlist.yaml), in LogQL form.
KEPT = {"service_name", "event_name", "decision", "source", "tool_name", "tool_use_id", "success", "error_type",
        "cost_usd", "hook_event", "hook_name", "num_blocking", "num_non_blocking_error", "num_cancelled",
        "total_duration_ms", "session_id", "session_key", "team", "__error__"}
GUIDE_METRICS = {"first_attempt_green_rate", "retries_per_task", "p95_time_to_green", "guard_denial_rate",
                 "override_rate", "approval_time", "cost_per_session", "cost_per_task", "retry_limit_hits",
                 "fail_safe_blocks", "guard_hook_health", "decisions_stopped", "tool_failure_rate", "hook_latency"}


def catalogue() -> dict:
    return yaml.safe_load((OBS / "metrics.yaml").read_text())


class MetricCatalogueTest(unittest.TestCase):
    def test_catalogue_is_traced_and_complete(self):
        doc = catalogue()
        self.assertEqual(doc["meta"]["id"], "observability-metrics")
        self.assertTrue(doc["meta"]["guide"])
        self.assertEqual({m["id"] for m in doc["metrics"]}, GUIDE_METRICS)

    def test_every_metric_names_a_real_source(self):
        for metric in catalogue()["metrics"]:
            with self.subTest(metric=metric["id"]):
                for key in ("guide", "definition", "status", "source", "read_with", "action"):
                    self.assertIn(key, metric)
                self.assertIn(metric["status"], STATUS_KEY)
                self.assertTrue(metric.get(STATUS_KEY[metric["status"]]))
                if metric["status"] == "platform-panel":
                    self.assertRegex(metric["panel"], r"^(ai-usage-overview|agent-flow)/.+")

    def test_queries_use_only_attributes_the_collector_keeps(self):
        for metric in catalogue()["metrics"]:
            if metric["status"] != "query":
                continue
            with self.subTest(metric=metric["id"]):
                expr = metric["query"]
                self.assertIn('service_name="claude-code"', expr)
                for label in re.findall(r"\b([a-z_]+)\s*(?:=|!=|=~|!~)\s*\"", expr):
                    self.assertIn(label, KEPT)
                for label in re.findall(r"unwrap\s+([a-z_]+)", expr):
                    self.assertIn(label, KEPT)
                if "unwrap" in expr:
                    self.assertIn('__error__=""', expr)
```

Add to `tests/unit/test_trace.py`, inside its existing test class:

```python
    def test_observability_files_are_traced(self):
        from aidlc.trace import collect
        elements, problems = collect()
        self.assertIn("observability", {e.kind for e in elements})
        self.assertEqual([p for p in problems if "observability" in p], [])
```

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets tests.unit.test_trace -v`. Expected: FAIL with `FileNotFoundError` for `metrics.yaml`, and the trace test fails on the missing kind.
- [ ] **Step 3: Write the catalogue and the trace scan.**

```yaml
# core/observability/metrics.yaml
meta: {id: observability-metrics, owner: "@harness-owners", review_by: "2027-04-22", guide: ["3.4", "3.9", "12.11", "12.12", "12.16"]}
# The guide's agent metrics, each mapped to where its data really lives (ADR 0003):
#   - Claude Code's built-in telemetry (Loki, service_name="claude-code"), switched on centrally;
#   - the platform's generated dashboards (PC/grafana/dashboards), which we reuse, never copy;
#   - GitHub CI, the trusted record of check results (ADR 0002);
#   - the local hook record (~/.aidlc/logs/decisions.jsonl), matched to telemetry by tool_use_id.
# Usage is read, never targeted (guide 3.4).
metrics:
  - id: guard_denial_rate
    guide: ["3.4", "3.9"]
    definition: Tool calls a hook rejected, over all tool decisions.
    status: query
    source: claude-code tool_decision (source="hook")
    query: 'sum(count_over_time({service_name="claude-code"} | event_name="tool_decision" | decision="reject" | source="hook" [$__range])) / sum(count_over_time({service_name="claude-code"} | event_name="tool_decision" [$__range]))'
    read_with: [override_rate, fail_safe_blocks]
    action: A jump after a harness change - read the local records of a few rejected calls (runbook); a fall to zero - check that the hooks still run.
  - id: override_rate
    guide: ["3.4", "3.9"]
    definition: Calls a person approved, over calls a person was asked about (accepts and rejects from a user source).
    status: query
    source: claude-code tool_decision (source user_temporary, user_permanent, user_reject)
    query: 'sum(count_over_time({service_name="claude-code"} | event_name="tool_decision" | decision="accept" | source=~"user_(temporary|permanent)" [$__range])) / sum(count_over_time({service_name="claude-code"} | event_name="tool_decision" | source=~"user_(temporary|permanent|reject)" [$__range]))'
    read_with: [guard_denial_rate, approval_time]
    action: Close to 100% - people approve by reflex (guide 3.9); narrow the ask rules or move safe calls to allow.
  - id: approval_time
    guide: ["3.4"]
    definition: Time a tool call waited for a person's answer.
    status: langfuse
    source: claude_code.tool.blocked_on_user spans (enhanced telemetry beta traces)
    where: Langfuse traces, span claude_code.tool.blocked_on_user, duration; needs CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1 and OTEL_TRACES_EXPORTER=otlp, both on in the lab's managed settings.
    read_with: [override_rate]
    action: Long waits - unattended work stalls on asks; review which rules ask.
  - id: cost_per_session
    guide: ["12.16"]
    definition: Claude Code list-price cost per session.
    status: platform-panel
    source: claude-code api_request cost_usd
    panel: agent-flow/Costliest sessions (open one in Langfuse)
    read_with: [tool_failure_rate]
    action: An outlier - open the session in Langfuse; check retries, context size and model tier.
  - id: cost_per_task
    guide: ["12.16"]
    definition: Cost per ticket.
    status: not-available
    source: claude-code api_request plus a ticket key
    gap: Claude Code events carry no branch or ticket key, and the hook records stay local, so no central join exists. Plan 6 (aidlc metrics) joins GitHub PRs to sessions.
    read_with: [cost_per_session]
    action: Until then, read cost per session.
  - id: tool_failure_rate
    guide: ["3.4"]
    definition: Tool calls that ran and failed, over tool calls that ran.
    status: platform-panel
    source: claude-code tool_result (success="false")
    panel: agent-flow/Tool failure rate per day
    read_with: [guard_denial_rate]
    action: Rising - read the failing tools (agent-flow/Failed tool calls by tool (M7)).
  - id: guard_hook_health
    guide: ["3.9"]
    definition: PreToolUse hook runs that errored without blocking, or were cancelled (timeout).
    status: query
    source: claude-code hook_execution_complete (hook_event="PreToolUse")
    query: '(sum(sum_over_time({service_name="claude-code"} | event_name="hook_execution_complete" | hook_event="PreToolUse" | unwrap num_non_blocking_error | __error__="" [$__range])) or vector(0)) + (sum(sum_over_time({service_name="claude-code"} | event_name="hook_execution_complete" | hook_event="PreToolUse" | unwrap num_cancelled | __error__="" [$__range])) or vector(0))'
    read_with: [fail_safe_blocks, hook_latency]
    action: Any - the guard did not decide; run aidlc doctor in the repository and read the local record.
  - id: hook_latency
    guide: ["3.9"]
    definition: 95th percentile of hook run time, per hook.
    status: platform-panel
    source: claude-code hook_execution_complete total_duration_ms
    panel: agent-flow/Hook time p95 by hook
    read_with: [guard_hook_health]
    action: Near the hook timeout - profile the guard; a slow guard is cancelled and blocks the call.
  - id: fail_safe_blocks
    guide: ["3.9"]
    definition: Calls the harness blocked because a hook failed (rule fail-safe).
    status: local-log
    source: hook record rule="fail-safe"
    where: ~/.aidlc/logs/decisions.jsonl; centrally each one is a tool_decision reject with source="hook", traced by tool_use_id (docs/observability/runbooks.md).
    read_with: [guard_hook_health]
    action: Any - read the record's reason and fix the hook.
  - id: decisions_stopped
    guide: ["3.9"]
    definition: Sessions in an aidlc repository whose tool calls produced no hook decision.
    status: not-available
    source: claude-code tool_decision and hook_execution_complete
    gap: Claude Code events carry no repository, so a central query cannot tell aidlc repositories from others. aidlc doctor (D4) and the live attack preflight check that the hooks are wired.
    read_with: [guard_hook_health]
    action: Run aidlc doctor; start sessions at the repository root.
  - id: first_attempt_green_rate
    guide: ["3.4", "12.11"]
    definition: Pull requests whose first aidlc-verify run passed.
    status: github-ci
    source: GitHub Actions runs of the aidlc-verify workflow
    where: GitHub run history per pull request; computed by aidlc metrics in Plan 6.
    read_with: [retries_per_task]
    action: Falling - read the failing steps; fix the context or the harness, not the agent.
  - id: retries_per_task
    guide: ["3.4"]
    definition: Failing aidlc-verify runs before the first pass, per pull request.
    status: github-ci
    source: GitHub Actions runs of the aidlc-verify workflow
    where: GitHub run history per pull request; computed by aidlc metrics in Plan 6. Locally, check-attempts records in the decision log.
    read_with: [first_attempt_green_rate]
    action: Above three - read the step that keeps failing.
  - id: p95_time_to_green
    guide: ["3.4", "12.12"]
    definition: 95th percentile of the time from a pull request's first push to its first passing aidlc-verify run.
    status: github-ci
    source: GitHub Actions runs and pull request events
    where: Computed by aidlc metrics in Plan 6.
    read_with: [first_attempt_green_rate]
    action: Rising - look for slow steps or long retries.
  - id: retry_limit_hits
    guide: ["3.4"]
    definition: Times an agent reached the one-command check's retry limit.
    status: local-log
    source: hook record hook="check-attempts", rule="retry-limit"
    where: ~/.aidlc/logs/decisions.jsonl on the developer's machine.
    read_with: [retries_per_task]
    action: Any - a person reads why the agent kept failing before resetting the counter.
```

In `cli/aidlc/trace.py` `collect`, after the `core/ci/*/setup.yaml` block, add:

```python
    for path in sorted((core / "observability").glob("*.yaml")):
        rel = str(path.relative_to(root))
        try:
            meta = load_yaml(path).get("meta", {})
        except (PolicyError, AttributeError) as exc:
            problems.append(f"{rel}: {exc}")
            continue
        problems += _guide_problems(meta.get("guide"), rel)
        elements.append(Element(meta.get("id", path.stem), "observability", rel, list(meta.get("guide") or [])))
```

Run `bin/aidlc trace` to regenerate `docs/traceability.md`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(observability): metric catalogue mapping each guide metric to built-in telemetry, platform panels, GitHub CI or the local record`.

### Task 3: Proposed alert rules

**Files:**
- Create: `core/observability/alerting/aidlc.yaml` (Grafana alert provisioning, for the platform owner to copy)
- Modify: `tests/unit/test_observability_assets.py` (add one test class)

**Interfaces:**
- Produces two rule uids, `aidlc-guard-hook-health` and `aidlc-session-cost`.
- Each rule's `runbook_url` points to `https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#<uid>`.
- Task 4 writes the runbook headings `## aidlc-guard-hook-health` and `## aidlc-session-cost`.

- [ ] **Step 1: Write the failing test.** Append to `tests/unit/test_observability_assets.py`:

```python
RUNBOOK_URL = "https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#"


class AlertRulesTest(unittest.TestCase):
    def rules(self) -> list[dict]:
        doc = yaml.safe_load((OBS / "alerting" / "aidlc.yaml").read_text())
        self.assertEqual(doc["apiVersion"], 1)
        return [r for g in doc["groups"] for r in g["rules"]]

    def test_every_alert_is_complete_and_evaluable(self):
        rules = self.rules()
        self.assertEqual({r["uid"] for r in rules}, {"aidlc-guard-hook-health", "aidlc-session-cost"})
        for rule in rules:
            with self.subTest(rule=rule["uid"]):
                self.assertTrue(rule["title"])
                self.assertEqual(rule["condition"], "C")
                self.assertIn("for", rule)
                self.assertEqual(rule["labels"]["owner"], "harness-owners")
                self.assertEqual(rule["annotations"]["runbook_url"], RUNBOOK_URL + rule["uid"])
                by_ref = {d["refId"]: d for d in rule["data"]}
                self.assertEqual(set(by_ref), {"A", "B", "C"})
                self.assertEqual(by_ref["A"]["datasourceUid"], "loki")
                self.assertEqual(by_ref["A"]["model"]["queryType"], "instant")
                self.assertIn('service_name="claude-code"', by_ref["A"]["model"]["expr"])
                self.assertIn("relativeTimeRange", by_ref["A"])
                self.assertEqual(by_ref["B"]["model"]["type"], "reduce")
                self.assertEqual(by_ref["B"]["model"]["expression"], "A")
                self.assertEqual(by_ref["C"]["model"]["type"], "threshold")
                self.assertEqual(by_ref["C"]["model"]["expression"], "B")

    def test_alert_queries_use_only_attributes_the_collector_keeps(self):
        for rule in self.rules():
            expr = {d["refId"]: d for d in rule["data"]}["A"]["model"]["expr"]
            with self.subTest(rule=rule["uid"]):
                for label in re.findall(r"\b([a-z_]+)\s*(?:=|!=|=~|!~)\s*\"", expr):
                    self.assertIn(label, KEPT)
                for label in re.findall(r"unwrap\s+([a-z_]+)", expr):
                    self.assertIn(label, KEPT)
                self.assertIn('__error__=""', expr)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets -v`. Expected: FAIL with `FileNotFoundError` for `alerting/aidlc.yaml`.
- [ ] **Step 3: Write the rules exactly as follows.**

```yaml
# core/observability/alerting/aidlc.yaml
# Proposed Grafana alert rules for the platform owner (docs/observability/platform-patch.md). Built on
# Claude Code's built-in telemetry only (ADR 0003). Copy to PC/lab/grafana/provisioning/alerting/.
apiVersion: 1
groups:
  - orgId: 1
    name: aidlc
    folder: aidlc
    interval: 5m
    rules:
      - uid: aidlc-guard-hook-health
        title: aidlc guard hook errored or timed out
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: A PreToolUse hook run errored without blocking, or was cancelled, in the last 15 minutes.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-guard-hook-health
        noDataState: OK
        execErrState: Error
        data:
          - refId: A
            relativeTimeRange: {from: 900, to: 0}
            datasourceUid: loki
            model:
              refId: A
              queryType: instant
              expr: '(sum(sum_over_time({service_name="claude-code"} | event_name="hook_execution_complete" | hook_event="PreToolUse" | unwrap num_non_blocking_error | __error__="" [15m])) or vector(0)) + (sum(sum_over_time({service_name="claude-code"} | event_name="hook_execution_complete" | hook_event="PreToolUse" | unwrap num_cancelled | __error__="" [15m])) or vector(0))'
          - refId: B
            datasourceUid: __expr__
            model: {refId: B, type: reduce, reducer: last, expression: A}
          - refId: C
            datasourceUid: __expr__
            model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [0]}}]}
      - uid: aidlc-session-cost
        title: aidlc session over budget
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: A Claude Code session spent more than 5 USD (list price) in the last 24 hours.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-session-cost
        noDataState: OK
        execErrState: Error
        data:
          - refId: A
            relativeTimeRange: {from: 86400, to: 0}
            datasourceUid: loki
            model:
              refId: A
              queryType: instant
              expr: 'max(sum by (session_id) (sum_over_time({service_name="claude-code"} | event_name="api_request" | unwrap cost_usd | __error__="" [24h]))) or vector(0)'
          - refId: B
            datasourceUid: __expr__
            model: {refId: B, type: reduce, reducer: last, expression: A}
          - refId: C
            datasourceUid: __expr__
            model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [5]}}]}
```

- [ ] **Step 4: Run it and watch it pass.** Run the Step 2 command and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(observability): two proposed alert rules on built-in telemetry (guard hook health, session cost)`.

### Task 4: Docs, the runbook, the platform kit and ADR 0003

**Files:**
- Create:
  - `docs/adr/0003-observability-built-in-telemetry.md`;
  - `docs/observability/README.md`;
  - `docs/observability/runbooks.md`;
  - `docs/observability/platform-patch.md`.
- Modify:
  - `docs/design/2026-10-18-aidlc-framework-design.md` §10: add a dated note pointing to ADR 0003;
  - `docs/codebase-map.md`: add an area for `core/observability/` and a "Where common changes go" line ("a new metric: `core/observability/metrics.yaml`; never a new emitter, ADR 0003");
  - `docs/harness/hooks.md`: one paragraph and a link, saying hook records stay local and carry `session` and `call` (`tool_use_id`);
  - `README.md`: add the observability docs to the list.
- Modify: `tests/unit/test_observability_assets.py` (one test class)

- [ ] **Step 1: Write the failing test.** Append:

```python
DOCS = framework_root() / "docs" / "observability"


class ObservabilityDocsTest(unittest.TestCase):
    def test_runbooks_cover_every_alert_and_the_trace_procedure(self):
        text = (DOCS / "runbooks.md").read_text()
        anchors = set(re.findall(r"^## (aidlc-[a-z0-9-]+)$", text, re.M))
        self.assertEqual(anchors, {"aidlc-guard-hook-health", "aidlc-session-cost"})
        self.assertIn("## From a Grafana rejection to the local record", text)
        self.assertIn('"call": "toolu_', text)

    def test_platform_patch_covers_the_alerts_and_the_panel(self):
        text = (DOCS / "platform-patch.md").read_text()
        for needle in ("core/observability/alerting/aidlc.yaml", "provisioning/alerting/aidlc.yaml",
                       "tools/grafana_dashboards.py", "test_grafana_dashboards.py", "guard_denial_rate"):
            self.assertIn(needle, text)

    def test_readme_states_the_boundary(self):
        text = (DOCS / "README.md").read_text()
        for needle in ("CLAUDE_CODE_ENABLE_TELEMETRY", "tool_use_id", "never leave", "ADR 0003",
                       "claude-apps-gateway", "OTEL_LOG_TOOL_DETAILS"):
            self.assertIn(needle, text)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets -v`. Expected: FAIL, because the files are missing.
- [ ] **Step 3: Write the docs.** Use short sentences, British spelling, and "you"; link to sources rather than copying values.

**1. ADR 0003, "Observability uses Claude Code's built-in telemetry; hook records stay local".** Status: accepted, 2026-10-22.

- **Context:**
  - Design §10 planned harness emitters. Plans 4a v1 and v2 built a custom OTLP sender in hook phases.
  - The user ruled that out on 2026-10-22: no custom telemetry plumbing, and nothing extra on the developer's machine.
  - Anthropic's documented paths all ship Claude Code's own telemetry: managed settings straight to a collector, the Claude apps gateway, or Team/Enterprise analytics. None of them ships custom hook data. Anthropic documents that `tool_use_id` matches the id passed to hooks, so hook data can be correlated.
- **Decision:**
  1. Observability uses Claude Code's built-in telemetry, switched on centrally through managed settings or a gateway's `managed` block.
  2. The framework emits nothing itself.
  3. Hook records stay in the local decision log, and every record carries `session` and `call` (`tool_use_id`).
  4. Check results are read from GitHub CI (ADR 0002).
  5. Dashboards are the platform's; the framework proposes panels and alerts, and never copies a dashboard.
- **Consequences:**
  - The rule name, reason and target of a hook decision are visible only on the developer's machine. Centrally, you see that a hook blocked a call, which tool, and in which session.
  - Cost per task and "decisions stopped" have no central source (`metrics.yaml` records the gaps).
  - There is no network code in hooks, and no new failure modes.
- **Rejected alternatives:**
  - a custom OTLP sender in hook phases (v2), which reinvents a log shipper;
  - a collector or agent tailing the log on the developer's machine, which is not common practice for developer laptops;
  - HTTP hooks posting raw payloads to a central service, which needs a new service that strips content.

**2. `docs/observability/README.md`** covers:

- **What you see centrally, and where.** A table:

  | Question | Event or panel | Dashboard |
  |---|---|---|
  | Did a hook block a call? | `tool_decision`, `source=hook` | `agent-flow` "Rejected actions by tool", "Hook refusals by hook" |
  | Did a hook fail or time out? | `hook_execution_complete` | the `guard_hook_health` query and alert |
  | Cost | `api_request` | `ai-usage-overview`, `agent-flow` "Costliest sessions" |
  | Tool failures | `tool_result` | `agent-flow` "Tool failure rate per day" |
  | Approvals | `tool_decision` with a user source | the `override_rate` query |

- **What never leaves the machine:** the hook record's rule, reason and target. The decision log is the harness's audit trail. Say where it is, that the framework does not rotate it, and that you can delete it.
- **Check results:** their central record is GitHub CI.
- **The telemetry baseline an organisation switches on centrally,** with the meaning of each setting:
  - `CLAUDE_CODE_ENABLE_TELEMETRY=1`;
  - `OTEL_LOGS_EXPORTER=otlp` and `OTEL_METRICS_EXPORTER=otlp`;
  - `OTEL_EXPORTER_OTLP_PROTOCOL`;
  - the endpoint, plus `otelHeadersHelper`;
  - `OTEL_RESOURCE_ATTRIBUTES` (team, cost centre, environment, pseudonym);
  - optionally, traces plus `CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1`, for approval time.
- **The two delivery routes for that baseline,** linking to Anthropic's docs:
  - a managed-settings file pushed by MDM, which is this lab's route (`/etc/claude-code/managed-settings.json`);
  - the Claude apps gateway's `managed` block (https://code.claude.com/docs/en/claude-apps-gateway), where clients send telemetry to the gateway and it forwards it.

  `tool_use_id` is a standard event attribute; no extra setting is needed.
- **Content flags.** `OTEL_LOG_USER_PROMPTS`, `OTEL_LOG_ASSISTANT_RESPONSES`, `OTEL_LOG_TOOL_DETAILS` and `OTEL_LOG_TOOL_CONTENT` are off by default and send content. Switch them on only when the collector strips content, as this lab's does for non-cohort records.
- **What is not available centrally, and why:** link to `metrics.yaml`.
- **The metric catalogue:** how to read it.
- **The decision:** ADR 0003.

**3. `docs/observability/runbooks.md`** has three sections:

- **`## From a Grafana rejection to the local record`:**
  1. In Grafana Explore, run `{service_name="claude-code"} | event_name="tool_decision" | decision="reject" | source="hook"`.
  2. Copy the record's `tool_use_id`.
  3. On the machine that ran the session, run `grep '"call": "toolu_<id>"' ~/.aidlc/logs/decisions.jsonl`.
  4. Read the record: `rule` is the deciding control, `reason` is why. A `fail-safe` rule means the hook failed; read its reason.
  5. If nothing matches: the session ran on another machine, the log was deleted, or the hook could not parse its input. In that last case, the fail-safe record has no ids; look for `fail-safe` records at the same time.
- **`## aidlc-guard-hook-health`:** the threshold (any errored or cancelled PreToolUse run in 15 minutes); what it means (the guard did not decide); the first three checks (`aidlc doctor` in the repository; hook time p95 near the timeout; the local record); how to close it.
- **`## aidlc-session-cost`:** the threshold (more than 5 USD list price in 24 hours, per session); the first three checks (open the session in Langfuse from "Costliest sessions"; retries; model tier, guide 12.16); how to close it.

**4. `docs/observability/platform-patch.md`** is the platform owner's kit. The framework applies none of it.
1. **Alerts:**
   - Copy `core/observability/alerting/aidlc.yaml` to `PC/lab/grafana/provisioning/alerting/aidlc.yaml`. The provisioning folder is already mounted.
   - Add a contact point.
   - Restart Grafana (runbook `docs/runbooks/lab-deployment.md`).
2. **One proposed panel:**
   - Add "Guard denial rate" to `agent-flow` through `PC/tools/grafana_dashboards.py`, using the `guard_denial_rate` query from `core/observability/metrics.yaml`.
   - Update `PC/tests/grafana/test_grafana_dashboards.py` if it pins the panel set.
   - Regenerate with the platform's generator.

   This is the only panel the platform lacks. Every other metric uses an existing panel, a query or another source.
3. **Verify:** check that the alert rules load (Grafana, Alerting, folder `aidlc`), and that the new panel shows data.

Close with a platform notes section:
- Loki `/ready` alternated between 503 and `ready` on 2026-10-20 and 2026-10-22, and has no runbook entry.
- `hook_execution_complete` is observed in lab data but not in the parts of Anthropic's monitoring page read so far.

**5. The design §10 note** (2026-10-22): "Superseded in part by ADR 0003. The harness emits no telemetry. Correlation ids are Claude Code's `session.id` and `tool_use_id`. `aidlc.bundle` and `aidlc.tier` are not emitted. Check results come from GitHub CI."

**6. `docs/codebase-map.md`, `docs/harness/hooks.md` and `README.md`,** as listed under Files. Run `bin/aidlc check context-drift .`.
- [ ] **Step 4: Run the tests and the checks, and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check`, `bin/aidlc check context-drift .` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `docs(observability): built-in telemetry boundary, runbooks, platform kit, ADR 0003; design §10 note`.

### Task 5: Live proof of the match (controller, with the user's go-ahead)

**Files:**
- Create: `docs/verification/<date>-observability-live.md`

This task spends a few cents of Haiku through the user's subscription, and queries Loki read-only. Ask the user before Step 2.

- [ ] **Step 1: Check the stack, read-only.** Run `curl -s 127.0.0.1:3100/ready`. Expected: `ready`. If it returns 503, wait 30 s and retry twice; if it still fails, ask the user before any restart.
- [ ] **Step 2: Run one session that the guard blocks.**
  1. Build the `tests/harness_live/fixture.py` repository in a scratch directory, with its own `AIDLC_HOME_DIR` and `AIDLC_LOG_DIR`, and render it.
  2. From its root, run: `claude -p --model haiku --setting-sources project,local --strict-mcp-config "Run the shell command: git push origin HEAD"`. Managed settings still apply, so built-in telemetry is on.
  3. Read the last `pre-tool-guard` record in the scratch `decisions.jsonl`.

  Expected: `decision` is `deny`, `rule` is `shell-deny`, and `session` and `call` (`toolu_…`) are present.
- [ ] **Step 3: Find the same call in Loki.** Wait 15 s; the logs export every 5 s. Then run:

```bash
curl -s -G 127.0.0.1:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service_name="claude-code"} | event_name="tool_decision" | tool_use_id="<call>"' \
  --data-urlencode "start=$(date -d '30 minutes ago' +%s)000000000" | jq -c '.data.result[].stream | {decision, source, tool_name, tool_use_id, session_id}'
```

  Expected: one stream with `decision` `reject`, `source` `hook`, `tool_name` `Bash`, the same `tool_use_id`, and `session_id` equal to the record's `session`.

  Also query `{service_name="claude-code"} | event_name="hook_execution_complete" | session_id="<session>" | hook_event="PreToolUse"`. Expected: `num_blocking` is at least 1.
- [ ] **Step 4: Write the evidence.** Write `docs/verification/<date>-observability-live.md` with:
  - the commands;
  - the local record, with its rule and ids (the target is already redacted);
  - the two Loki results;
  - what was not verified: the alerts and the proposed panel stay unloaded until the platform owner applies the kit; approval time in Langfuse is not exercised by `-p`.

  Commit it in the plan's pull request.

---

## Self-review notes

- **The user's decisions of 2026-10-22:**
  - no custom sender: Global Constraints, and no task adds one;
  - nothing on the developer's machine: no task adds an agent;
  - built-in only: the Task 2 catalogue and the Task 3 alerts use only `service_name="claude-code"`;
  - hook records matched by `tool_use_id`: Task 1, the runbook in Task 4, and the live proof in Task 5.
- **Design §10 rows,** amended by ADR 0003:

  | Row | Where |
  |---|---|
  | Correlation ids | `session.id` and `tool_use_id` (Task 1, ADR) |
  | Session start, tool decisions, deciding control | Central: built-in events. Local: the rule. |
  | Check results | GitHub CI (catalogue) |
  | Cost | Platform panels |
  | Paired metrics | Task 2 |
  | Redaction | Hook records never leave the machine; the collector's allow-list |
  | Alerts | Task 3 |
  | Retention | Task 4 README |
  | Eval runs | Plan 4b |
  | Delivery measures | Plan 6 |

- **Review-finding carry-over from v2:**
  - test isolation (I7): Task 0;
  - evaluable alerts (I6): Task 3;
  - `__error__` after `unwrap`: Tasks 2 and 3 tests;
  - absolute runbook URLs: Task 3;
  - the platform's generator-owned dashboards (I13): a proposed panel through the generator.

  The other v2 findings concerned the dropped sender and no longer apply.
- **Placeholder scan:** none. `<date>`, `<call>` and `<session>` in Task 5 are runtime values.
- **Type consistency:**
  - Task 3 rule uids equal the Task 4 runbook anchors;
  - the `KEPT` set is shared by the Task 2 and Task 3 tests;
  - `metrics.yaml` ids equal `GUIDE_METRICS`.
