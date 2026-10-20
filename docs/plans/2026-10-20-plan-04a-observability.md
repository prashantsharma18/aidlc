# Plan 4a: Observability. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The harness's own record (hook decisions, check results, session starts) reaches the platform's telemetry pipeline as enumerated metadata. Dashboards, alerts and a metric catalogue answer the guide's questions, and nothing secret or personal ever leaves the machine.

**Architecture:**
- **The source.** The guard and post-check already write every decision, and every run of the one-command check, to `$AIDLC_LOG_DIR/decisions.jsonl`, outside the agent's sandbox. They never use the network.
- **The telemetry module.** A new stdlib module, `core/hooks/telemetry.py`, runs in two new non-blocking hook phases and in the person-run CLI `aidlc telemetry`:
  - `session-start` records the session's context and queues a start event. It sends nothing.
  - `session-end` converts new log lines into records and sends the outbox.

  The records carry only validated enums, ids and counts. They wait in a bounded outbox under `$AIDLC_HOME_DIR/telemetry/`, and go to the loopback collector oldest first, one Loki stream per session (`service.instance.id`), within one deadline that covers the whole phase.
- **Where the rest lives.** Dashboards, alert rules and the metric catalogue are in `core/observability/`. Platform changes (the collector allow-list, alert provisioning and a dashboard provider) are a documented kit for the platform owner. The framework never applies them.

**Tech Stack:** Python 3.12 standard library (`urllib.request`, `http.client`, `fcntl`, `tempfile`, `uuid`) for the hook-side code; PyYAML and jsonschema on the CLI side only. OTLP/HTTP JSON (`/v1/logs`), Grafana 13 file provisioning, LogQL (Loki 3.7).

**Spec:**
- design §10 and §8 (`docs/design/2026-10-18-aidlc-framework-design.md`);
- ADR 0002;
- the user's decisions of 2026-10-20 (Plan 4 split 4a then 4b, telemetry stack checked read-only, platform changes only as proposed patches);
- the research notes in the session scratchpad `p4-research/`: guide §4 and §5, the platform contract, the integration map and Claude Code;
- the independent plan review of 2026-10-20 (`p4a-review/`). Every finding is addressed in this revision.

## Facts this plan relies on (verified 2026-10-20)

- **Collector.**
  - OTLP/HTTP only, on `127.0.0.1:4318`, with bearer auth (401 without it). The request body limit is 8 MiB.
  - The header comes from `/usr/local/lib/ai-lab/otel-headers.sh`, which prints one line: `{"Authorization": "Bearer <token>"}`.
  - Logs go to Loki, and Langfuse receives only traces.
  - On every non-cohort record (all of ours), the collector empties the log body and keeps only allow-listed attribute keys. These are kept: `event.name`, `session.key`, `tool_use_id`, and the `vcs.ref.head.name` and `vcs.repository.url.full` patterns. From the last two the collector derives `branch`, `repo` and `ticket.key`.
  - No `aidlc.*` key is kept until the platform owner adds one.
  - Resource attributes are not filtered by the allow-list.
- **Loki 3.7.8.**
  - Only resource attributes such as `service.name` and `service.instance.id` become stream labels.
  - The out-of-order window is 1 hour behind the newest entry of the same stream: `max_chunk_age` is 2h, and `unordered_writes` is on.
  - `reject_old_samples_max_age` is 1 week.
  - Rejected entries are silent to the client, because the collector has already answered 200.
  - `/ready` answered `ready` during the review. It had answered 503 earlier the same day, so treat its state as variable.
- **Claude Code's own records** (`service_name="claude-code"`) carry `session_key` but **no** `branch`, `ticket_key` or `repo`. The reviewer checked 7 days of live data. So a task-level view of Claude Code cost or approvals needs a join on `session_key`, through aidlc's records, which do carry `ticket_key`.
  - `tool_decision` has `decision` ∈ {`accept`, `reject`} and `source` ∈ {`config`, `user_temporary`, `user_permanent`, `hook`, `user_reject`}. `decision_source` does not exist.
- **Grafana.**
  - Datasource uids are `loki` and `mimir`. There is no alert provisioning directory; `PC/lab/grafana/provisioning/alerting/` would already be mounted.
  - The platform's dashboard folder is generator-owned: its tests require every JSON there to come from `PC/tools/grafana_dashboards.py`.
  - In LogQL, dots become underscores: `aidlc.rule` is `aidlc_rule`.
  - Unified alerting needs reduced (numeric) data for a condition.
- **Claude Code 2.1.296.**
  - It has the hook events `SessionStart` (payload `session_id`, `cwd`, `source`) and `SessionEnd` (`session_id`, `cwd`, `reason`).
  - The SessionEnd budget defaults to 1.5 s, and the hook's `timeout` raises it.
  - Hooks run in `-p` unless `--bare` is set. Whether SessionEnd fires at a normal `-p` exit is unverified; Task 8 verifies it.
  - `onFailure` semantics are documented for tool events only.
- **This framework.**
  - `guard._log(event, result, version=None)` fills `version` from `load_harness()` when it is `None`, so post records already carry the harness version.
  - `post_check.check_run_id` reads `.check/result.json` safely (no symlink, `O_NOFOLLOW|O_NONBLOCK`, size cap).
  - `settings.rego` and doctor D4 cover only the three tool events.
  - Existing unit tests write fail-safe records into the real `~/.aidlc/logs/decisions.jsonl` today; Task 0 stops that.

## Global Constraints

- **Dependencies.** Hooks use the standard library only. The CLI uses the standard library plus PyYAML and jsonschema. Add no new dependency.
- **Network.** The guard and post-check never use the network. Only `core/hooks/telemetry.py` may, and only:
  - in the `session-end` phase or under `aidlc telemetry flush`;
  - to `http://127.0.0.1:<port>` or `http://[::1]:<port>`, with port 1–65535 (no `localhost`: name resolution is not trusted);
  - with no redirects followed and no proxy;
  - within one monotonic deadline per call, `timeout_s` (policy default 3 s), covering lock waits, git calls, the helper and the sends.
- **What leaves the machine.** Only the keys listed in `core/policy/telemetry.yaml` (`events`, `context`, `resource`), each with a validated value: an enum, an id, a count, a known step name, or a version. These never leave, under any setting:
  - a decision reason, target, command, path, prompt, tool output or file content;
  - a header value, a token, or a remote URL's credentials or local path.
- **Session phases never block and never fail a session.**
  - Both phases always exit 0, with no stdout.
  - Their settings entries carry no `onFailure` key and have `"timeout": 5`.
  - `session-start` never touches the network.
- **State.**
  - State lives under `$AIDLC_HOME_DIR/telemetry/` (default `~/.aidlc/telemetry/`), which the agent's sandbox cannot write. A symlinked state directory, lock, outbox, cursor or sessions directory is refused.
  - Every update is taken under an `fcntl` lock that is waited for no longer than the deadline. Files are written with `tempfile.mkstemp` and `os.replace`.
  - The outbox is bounded (`outbox_max_bytes`, default 5,000,000). The oldest entries are dropped first, in one slice, and counted.
- **Delivery.**
  - Delivery is at least once. A duplicate is possible after a crash between writes, or after a timeout on a request the collector accepted. Loss is possible only through the outbox cap or the age limit, both counted.
  - Entries older than 7 days are not sent, and are counted (`expired`).
  - The first run starts at the current end of the decision log. History written before telemetry existed is never shipped.
- **The platform.** The framework edits no platform file. Platform changes are a kit in `docs/observability/platform-patch.md`, plus files under `core/observability/`.
- **Tests.**
  - The suite runs with `AIDLC_TELEMETRY=off` and its own `AIDLC_LOG_DIR` unless a test opts in (Task 0). Unit tests never touch the real `~/.aidlc`, `~/.claude`, the real header helper, or the network; only a loopback server or closed port the test itself chose is allowed.
  - `make test` stays model-free.
  - Never change an assertion in a test older than this plan, except these, which are named design changes:
    - `tests/unit/test_claude_settings.py`'s hook-file set gains `telemetry.py`;
    - the golden `tests/fixtures/render/claude-code/settings.node.json` is regenerated with the renderer.
- **Commits** use the repo-local identity (`prashantsharma18`, noreply) and stage explicit paths. `main` is protected: the work lands through a pull request whose `unit`, `sandbox` and `policy` checks are green.
- **Every policy and observability file** declares `guide:`. Run `bin/aidlc trace` after adding or changing one.
- **Run before every commit:**
  - `make test`;
  - `bin/aidlc trace --check`;
  - `bin/aidlc check context-drift .`;
  - `bin/aidlc policy validate`;
  - `bin/aidlc render --tool claude-code --check .`

## Review Focus

1. **A long session, or a replay after an outage.** Loki accepts every record: one stream per session, sent oldest first. Pinned by Task 3 `test_records_are_grouped_per_session_and_oldest_first`, and by Task 8 Step 4, which checks that a record more than 1 h old arrives.
2. **The collector is slow, the lock is held, or the outbox is full.** The phase returns within its deadline, and trimming is linear. Pinned by Task 3 `test_run_phase_returns_within_deadline_when_the_lock_is_held` and Task 2 `test_trimming_a_full_outbox_is_fast`.
3. **One poisoned record:** a bad remote URL, a huge line, or an unknown value. It is skipped and counted, and the cursor keeps moving. Pinned by Task 2 `test_a_bad_record_is_skipped_and_the_cursor_moves` and `test_a_line_longer_than_the_window_is_skipped`.
4. **A secret in a target, reason or remote URL.** It never reaches the outbox, the session file, the collector or stdout. Pinned by Task 2 `test_a_decision_becomes_enumerated_metadata_only` and `test_repo_url_never_keeps_credentials_or_paths`.
5. **Rotating or replacing the decision log.** The next run restarts on the new file from the beginning, and nothing is shipped twice from the old one. Pinned by Task 2 `test_a_rotated_log_restarts_on_the_new_file`.

---

### Task 0: Isolate the test suite from real telemetry

**Files:**
- Modify: `tests/__init__.py` (currently empty), `tests/harness_live/run_attacks.py` (the session environment)
- Test: `tests/unit/test_suite_isolation.py`

**Interfaces:** Produces the suite-wide defaults `AIDLC_TELEMETRY=off` and a temporary `AIDLC_LOG_DIR`, unless the caller has already set them. Tests that need telemetry opt in by patching `os.environ`.

- [ ] **Step 1: Write the failing test.**

```python
# tests/unit/test_suite_isolation.py
import os
import unittest
from pathlib import Path


class SuiteIsolationTest(unittest.TestCase):
    def test_the_suite_runs_with_telemetry_off_and_its_own_log(self):
        self.assertEqual(os.environ.get("AIDLC_TELEMETRY"), "off")
        log_dir = Path(os.environ["AIDLC_LOG_DIR"])
        self.assertNotEqual(log_dir.resolve(), (Path.home() / ".aidlc" / "logs").resolve())
        self.assertTrue(log_dir.name.startswith("aidlc-test-logs-"))
```

- [ ] **Step 2: Run the test and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_suite_isolation -v`. Expected: FAIL, because `AIDLC_TELEMETRY` is `None`.
- [ ] **Step 3: Implement.** Write `tests/__init__.py`:

```python
"""Suite-wide defaults: no test ships telemetry or writes the real decision log (Plan 4a Task 0).
A test that needs telemetry opts in by patching os.environ."""
import atexit
import os
import shutil
import tempfile

os.environ.setdefault("AIDLC_TELEMETRY", "off")
if "AIDLC_LOG_DIR" not in os.environ:
    _logs = tempfile.mkdtemp(prefix="aidlc-test-logs-")
    os.environ["AIDLC_LOG_DIR"] = _logs
    atexit.register(shutil.rmtree, _logs, True)
```

In `tests/harness_live/run_attacks.py`, in the session environment's `env.update({...})`, add `"AIDLC_TELEMETRY": "off"` before `**attempt.env`. Attack sessions are tests, not work.
- [ ] **Step 4: Run the test and watch it pass.** Run the Step 2 command, then `make test`. Then check that `~/.aidlc/logs/decisions.jsonl` is unchanged: compare its size before and after `make test`. Expected: both runs pass and the size is unchanged.
- [ ] **Step 5: Commit.** Commit with `test: suite-wide AIDLC_TELEMETRY=off and a private decision log; live attack sessions ship nothing`.

### Task 1: The telemetry policy, and the harness's telemetry block

**Files:**
- Create: `core/policy/telemetry.yaml`, `core/schemas/telemetry.schema.json`
- Modify: `cli/aidlc/harness.py` (`harness_data` gains `telemetry` and `check_steps`)
- Test: `tests/unit/test_telemetry_policy.py`

**Interfaces:**
- `load_policy("telemetry")` returns these keys:
  - `enabled: bool`;
  - `endpoint: str`;
  - `headers_helper: str | None`;
  - `timeout_s: float`;
  - `outbox_max_bytes: int`;
  - `budget_usd_per_session: float`;
  - `events: dict[str, list[str]]`;
  - `context: list[str]`;
  - `resource: list[str]`;
  - `allowlist_pattern: str`.
- `harness_data(repo)` adds:
  - `"telemetry": {"enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes"}`;
  - `"check_steps": list[str]`: the repository's `check_steps` plus the built-in step names, sorted.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry_policy.py
import copy
import re
import unittest
from datetime import date

import aidlc.policy as policy
from aidlc.harness import harness_data
from aidlc.policy import load_policy
from aidlc.repo import init_repo
from tests.helpers import TempRepo
from tests.hook_loader import load_hook

EXPECTED_EVENTS = {
    "aidlc.hook.decision": ["session.key", "tool_use_id", "aidlc.hook", "aidlc.decision", "aidlc.rule",
                            "aidlc.tool", "aidlc.unattended", "aidlc.harness.version"],
    "aidlc.check.result": ["session.key", "aidlc.check.result", "aidlc.check.failing_in_a_row",
                           "aidlc.check.failed_steps", "aidlc.check.retry_limit", "aidlc.harness.version"],
    "aidlc.session.start": ["session.key", "aidlc.session.source", "aidlc.harness.version"],
}


class TelemetryPolicyTest(unittest.TestCase):
    def test_policy_lists_events_context_and_resource(self):
        data = load_policy("telemetry")
        self.assertEqual(data["events"], EXPECTED_EVENTS)
        self.assertEqual(data["context"], ["vcs.ref.head.name", "vcs.repository.url.full"])
        self.assertEqual(data["resource"], ["team", "cost_center", "env", "ai.cohort", "enduser.pseudonym"])
        self.assertEqual(data["endpoint"], "http://127.0.0.1:4318")
        self.assertEqual(data["headers_helper"], "/usr/local/lib/ai-lab/otel-headers.sh")

    def test_hook_module_events_match_the_policy(self):
        telemetry = load_hook("telemetry")
        data = load_policy("telemetry")
        self.assertEqual({k: list(v) for k, v in telemetry.EVENTS.items()}, data["events"])
        self.assertEqual(list(telemetry.CONTEXT), data["context"])
        self.assertEqual(list(telemetry.RESOURCE_KEYS), data["resource"])

    def test_allowlist_pattern_covers_every_aidlc_key_and_nothing_broad(self):
        data = load_policy("telemetry")
        pattern = re.compile(data["allowlist_pattern"])
        keys = {k for keys in data["events"].values() for k in keys if k.startswith("aidlc.")}
        for key in keys:
            with self.subTest(key=key):
                self.assertTrue(pattern.fullmatch(key))
        for leak in ("aidlc.reason", "aidlc.target", "aidlc.hook.content", "aidlc.prompt", "aidlc.x"):
            with self.subTest(leak=leak):
                self.assertIsNone(pattern.fullmatch(leak))

    def test_policy_refuses_a_non_loopback_or_bad_port_endpoint(self):
        data = load_policy("telemetry")
        schema = policy._schema(policy.framework_root(), "telemetry")
        for endpoint in ("http://example.com:4318", "https://127.0.0.1:4318", "http://10.0.0.5:4318",
                         "http://127.0.0.1:4318/v1/logs", "http://localhost:4318", "http://127.0.0.1:0",
                         "http://127.0.0.1:099"):
            with self.subTest(endpoint=endpoint):
                bad = copy.deepcopy(data)
                bad["endpoint"] = endpoint
                self.assertTrue(policy._errors(schema, bad, "telemetry"))
        broad = copy.deepcopy(data)
        broad["allowlist_pattern"] = "^aidlc\\..*$"
        self.assertTrue(policy._errors(schema, broad, "telemetry"))

    def test_harness_data_carries_telemetry_and_check_steps(self):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 20))
            data = harness_data(root)
        self.assertEqual(set(data["telemetry"]), {"enabled", "endpoint", "headers_helper", "timeout_s",
                                                  "outbox_max_bytes"})
        self.assertTrue({"scope", "protected-tests", "skips", "context-drift", "secrets"} <= set(data["check_steps"]))
        self.assertEqual(data["check_steps"], sorted(data["check_steps"]))
```

`test_hook_module_events_match_the_policy` fails until Task 2 creates `core/hooks/telemetry.py`. Mark it `@unittest.skip("enabled in Task 2")` in this task, and remove the decorator in Task 2 Step 1.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_policy -v`. Expected: FAIL, with "no schema telemetry.schema.json".
- [ ] **Step 3: Write the policy, the schema and the harness block.**

```yaml
# core/policy/telemetry.yaml
meta: {id: policy-telemetry, owner: "@harness-owners", review_by: "2027-04-20", guide: ["3.4", "3 step 7", "13.5"]}
# The harness's own telemetry (design §10). Only these keys leave the machine, each with a validated
# enum, id, count, known step name or version. A reason, target, command, path, prompt, output,
# header value or token never does.
enabled: true
endpoint: "http://127.0.0.1:4318"            # loopback only (127.0.0.1 or [::1]): the platform collector
headers_helper: "/usr/local/lib/ai-lab/otel-headers.sh"   # prints {"Authorization": "Bearer <token>"}
timeout_s: 3                                  # one deadline per hook phase: locks, git, helper and sends
outbox_max_bytes: 5000000                     # oldest entries dropped first, and counted
budget_usd_per_session: 5                     # the session-cost alert: spend per session over 24 hours
events:
  aidlc.hook.decision: [session.key, tool_use_id, aidlc.hook, aidlc.decision, aidlc.rule, aidlc.tool,
                        aidlc.unattended, aidlc.harness.version]
  aidlc.check.result: [session.key, aidlc.check.result, aidlc.check.failing_in_a_row, aidlc.check.failed_steps,
                       aidlc.check.retry_limit, aidlc.harness.version]
  aidlc.session.start: [session.key, aidlc.session.source, aidlc.harness.version]
context: [vcs.ref.head.name, vcs.repository.url.full]   # per session; the collector derives branch, repo, ticket.key
resource: [team, cost_center, env, ai.cohort, enduser.pseudonym]   # copied from OTEL_RESOURCE_ATTRIBUTES at session start
# The one line the platform owner adds to metadata-allowlist.yaml `patterns:` (docs/observability/platform-patch.md).
allowlist_pattern: '^aidlc\.(hook|decision|rule|tool|unattended|harness\.version|session\.source|check\.(result|failing_in_a_row|failed_steps|retry_limit))$'
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "telemetry",
  "type": "object",
  "additionalProperties": false,
  "required": ["meta", "enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes",
               "budget_usd_per_session", "events", "context", "resource", "allowlist_pattern"],
  "properties": {
    "meta": {"type": "object"},
    "enabled": {"type": "boolean"},
    "endpoint": {"type": "string", "pattern": "^http://(127\\.0\\.0\\.1|\\[::1\\]):[1-9][0-9]{0,4}$"},
    "headers_helper": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^/[A-Za-z0-9._/-]+$"}]},
    "timeout_s": {"type": "number", "minimum": 0.5, "maximum": 4},
    "outbox_max_bytes": {"type": "integer", "minimum": 10000, "maximum": 50000000},
    "budget_usd_per_session": {"type": "number", "exclusiveMinimum": 0},
    "events": {
      "type": "object", "minProperties": 1,
      "propertyNames": {"pattern": "^aidlc\\.[a-z]+(\\.[a-z_]+)*$"},
      "additionalProperties": {"type": "array", "minItems": 1, "uniqueItems": true,
                               "items": {"type": "string", "pattern": "^(session\\.key|tool_use_id|aidlc\\.[a-z_.]+)$"}}
    },
    "context": {"type": "array", "items": {"enum": ["vcs.ref.head.name", "vcs.repository.url.full"]}, "uniqueItems": true},
    "resource": {"type": "array", "items": {"enum": ["team", "cost_center", "env", "ai.cohort", "enduser.pseudonym"]}, "uniqueItems": true},
    "allowlist_pattern": {"type": "string", "pattern": "^\\^aidlc\\\\\\.\\(.*\\)\\$$"}
  }
}
```

The `meta` style matches `core/schemas/routing.schema.json`, which uses `{"type": "object"}`. `policy.py` validates `meta` separately.

`timeout_s` is at most 4, so that one phase (its deadline plus a final lock wait of at most 1 s) fits inside the hook `timeout` of 5.

In `cli/aidlc/harness.py` `harness_data`, add:

```python
    from .checks.onecheck import BUILTINS                      # local import: onecheck imports hookbridge
    tel = load_policy("telemetry")
    data["telemetry"] = {"enabled": bool(tel["enabled"]), "endpoint": tel["endpoint"],
                         "headers_helper": tel["headers_helper"], "timeout_s": tel["timeout_s"],
                         "outbox_max_bytes": tel["outbox_max_bytes"]}
    data["check_steps"] = sorted(set(load_config(repo).check_steps) | {name for name, _ in BUILTINS})
```

This changes `version` in every repository, so repositories must re-render. Task 7 documents the upgrade.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `bin/aidlc policy validate`, `bin/aidlc trace` and `make test`. Expected: everything passes, with one skip (the Task 2 test).
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): policy for the harness's own telemetry; harness.json telemetry and check-step names (guide 3.4, 13.5)`.

### Task 2: The telemetry module: the log, the session context and the outbox (no network)

**Files:**
- Create: `core/hooks/telemetry.py`
- Modify:
  - `core/hooks/guard.py`: `_log` adds `"unattended": _unattended()` to every record.
  - `tests/unit/test_telemetry_policy.py`: remove the Task 1 skip.
- Test: `tests/unit/test_telemetry.py`

**Interfaces:**
- Consumes the decision-log line shape: `ts, hook, session, call, harness, tool, target, decision, rule, reason, unattended`. Task 4 adds `passed`, `failing_in_a_row` and `failed_steps` for `check-attempts`.
- Produces, in `core/hooks/telemetry.py`:
  - `EVENTS`, `CONTEXT` and `RESOURCE_KEYS`, which equal the policy;
  - `Deadline(seconds)`, with `.left() -> float`;
  - `home_dir()`, `log_dir()`, `state_dir()`;
  - `load_config() -> dict`, with keys `enabled`, `endpoint`, `headers_helper`, `timeout_s`, `outbox_max_bytes`, `version`, `check_steps`;
  - `record_from_decision(rec, context, check_steps) -> dict | None`, returning an entry `{"id", "event", "time", "attrs", "resource"}`;
  - `collect(deadline: Deadline, commit: bool = True) -> list[dict]`;
  - `remember_session(payload, deadline) -> dict | None`;
  - `start_entry(payload, version, context) -> dict | None`;
  - `enqueue(entries, deadline) -> None`;
  - `read_outbox(deadline) -> list[dict]`;
  - `counters() -> dict[str, int]`, with keys `dropped`, `expired` and `skipped`;
  - `prune_sessions(deadline) -> None`;
  - `repo_url(raw) -> str | None`;
  - `resource_attributes() -> dict[str, str]`.

- [ ] **Step 1: Write the failing tests.** Remove the skip decorator from `test_hook_module_events_match_the_policy`, then add:

```python
# tests/unit/test_telemetry.py
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import TempRepo, git
from tests.hook_loader import load_hook

telemetry = load_hook("telemetry")
SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"
STEPS = frozenset({"lint", "test", "scope", "secrets"})


def decision(**kw):
    rec = {"ts": "2026-10-20T09:12:31+00:00", "hook": "pre-tool-guard", "session": "s-1", "call": "toolu_01AbC",
           "harness": "0.1.0+3fa9c1d2e4b5", "tool": "shell", "unattended": False,
           "target": f"curl -H 'x: {SECRET}' /home/someone/x", "decision": "deny", "rule": "shell-deny",
           "reason": f"blocked {SECRET} in /home/someone/x"}
    rec.update(kw)
    return rec


class TelemetryBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "logs").mkdir()
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        os.environ.pop("OTEL_RESOURCE_ATTRIBUTES", None)
        self.cfg = mock.patch.object(telemetry, "load_config", return_value={
            "enabled": True, "endpoint": "http://127.0.0.1:9", "headers_helper": None, "timeout_s": 3.0,
            "outbox_max_bytes": 5_000_000, "version": "0.1.0+abc", "check_steps": STEPS})
        self.cfg.start()
        self.log()                                    # create the log, then start the cursor at its end
        telemetry.collect(telemetry.Deadline(3))

    def tearDown(self):
        self.cfg.stop()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def log(self, *records, partial=""):
        with (self.tmp / "logs" / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
            fh.write(partial)

    def collect(self):
        return telemetry.collect(telemetry.Deadline(3))

    def outbox(self):
        return telemetry.read_outbox(telemetry.Deadline(3))


class ConvertTest(TelemetryBase):
    def test_the_first_run_ships_nothing_written_before_it(self):
        fresh = self.tmp / "logs2"
        fresh.mkdir()
        (fresh / "decisions.jsonl").write_text(json.dumps(decision()) + "\n")
        with mock.patch.dict(os.environ, {"AIDLC_LOG_DIR": str(fresh), "AIDLC_HOME_DIR": str(self.tmp / "home2")}):
            self.assertEqual(telemetry.collect(telemetry.Deadline(3)), [])
            with (fresh / "decisions.jsonl").open("a") as fh:
                fh.write(json.dumps(decision(call="toolu_02")) + "\n")
            self.assertEqual(len(telemetry.collect(telemetry.Deadline(3))), 1)

    def test_a_decision_becomes_enumerated_metadata_only(self):
        self.log(decision())
        self.assertEqual(len(self.collect()), 1)
        [entry] = self.outbox()
        self.assertEqual(entry["event"], "aidlc.hook.decision")
        self.assertEqual(entry["attrs"], {"session.key": "s-1", "tool_use_id": "toolu_01AbC",
                                          "aidlc.hook": "pre-tool-guard", "aidlc.decision": "deny",
                                          "aidlc.rule": "shell-deny", "aidlc.tool": "shell",
                                          "aidlc.unattended": "false", "aidlc.harness.version": "0.1.0+3fa9c1d2e4b5"})
        self.assertEqual(entry["resource"], {"service.name": "aidlc", "service.instance.id": "s-1"})
        raw = (self.tmp / "home" / "telemetry" / "outbox.jsonl").read_text()
        for leak in (SECRET, "/home/someone", "curl", "blocked"):
            self.assertNotIn(leak, raw)

    def test_every_attribute_key_is_one_the_policy_lists(self):
        self.remember("s-1")
        self.log(decision(), decision(hook="check-attempts", decision="pass", rule="check-recorded",
                                      passed=False, failing_in_a_row=2, failed_steps=["lint", "test"]))
        self.collect()
        for entry in self.outbox():
            allowed = set(telemetry.EVENTS[entry["event"]]) | set(telemetry.CONTEXT)
            self.assertLessEqual(set(entry["attrs"]), allowed)
            self.assertIn("vcs.ref.head.name", entry["attrs"])

    def test_unknown_values_are_dropped_not_shipped(self):
        self.log(decision(hook="evil-hook"), decision(tool="rm -rf /", rule="Bad Rule!", decision="maybe",
                                                      call="not-a-tool-use-id"))
        self.collect()
        [entry] = self.outbox()
        for key in ("aidlc.tool", "aidlc.rule", "aidlc.decision", "tool_use_id"):
            self.assertNotIn(key, entry["attrs"])

    def test_check_attempts_becomes_a_check_result_with_known_step_names_only(self):
        self.log(decision(hook="check-attempts", decision="flag", rule="retry-limit", passed=False,
                          failing_in_a_row=3, failed_steps=["lint", "test", "made-up-step", "../etc"]))
        self.collect()
        [entry] = self.outbox()
        self.assertEqual(entry["event"], "aidlc.check.result")
        self.assertEqual(entry["attrs"]["aidlc.check.result"], "FAIL")
        self.assertEqual(entry["attrs"]["aidlc.check.failing_in_a_row"], 3)
        self.assertEqual(entry["attrs"]["aidlc.check.failed_steps"], "lint,test")
        self.assertEqual(entry["attrs"]["aidlc.check.retry_limit"], "true")

    def test_records_without_a_session_go_to_the_shared_stream(self):
        self.log(decision(session=None, rule="fail-safe"))
        self.collect()
        self.assertEqual(self.outbox()[0]["resource"]["service.instance.id"], "aidlc-nosession")

    def test_cursor_skips_shipped_and_partial_lines(self):
        self.log(decision(), decision(call="toolu_2"), partial='{"hook": "pre-tool-guard", "sess')
        self.assertEqual(len(self.collect()), 2)
        self.assertEqual(self.collect(), [])
        with (self.tmp / "logs" / "decisions.jsonl").open("a") as fh:
            fh.write('ion": "s-2", "ts": "2026-10-20T09:13:00+00:00", "decision": "allow", "rule": "read", "tool": "read"}\n')
        self.assertEqual(len(self.collect()), 1)
        self.assertEqual(len(self.outbox()), 3)

    def test_a_rotated_log_restarts_on_the_new_file(self):
        self.log(decision(), decision(call="toolu_2"))
        self.collect()
        log = self.tmp / "logs" / "decisions.jsonl"
        log.rename(self.tmp / "logs" / "decisions.jsonl.1")
        self.log(*[decision(call=f"toolu_{n}") for n in range(10, 20)])   # bigger than the old offset
        self.assertEqual(len(self.collect()), 10)

    def test_a_truncated_log_restarts_from_the_beginning(self):
        self.log(decision(), decision())
        self.collect()
        (self.tmp / "logs" / "decisions.jsonl").write_text(json.dumps(decision()) + "\n")
        self.assertEqual(len(self.collect()), 1)

    def test_a_bad_record_is_skipped_and_the_cursor_moves(self):
        (self.tmp / "home/telemetry/sessions").mkdir(parents=True, exist_ok=True)
        (self.tmp / "home/telemetry/sessions/s-9.json").write_text(json.dumps({"branch": "x", "remote": "https://h:99999/x"}))
        self.log(decision(session="s-9"), partial="not json\n[1,2]\n")
        self.log(decision(call="toolu_3"))
        self.assertEqual(len(self.collect()), 2)
        self.assertEqual(self.collect(), [])

    def test_a_line_longer_than_the_window_is_skipped(self):
        with mock.patch.object(telemetry, "READ_MAX_BYTES", 1_000):
            self.log(partial="x" * 5_000 + "\n")
            self.log(decision())
            self.collect()                            # skips the long line
            self.assertEqual(len(self.collect()), 1)
        self.assertGreaterEqual(telemetry.counters()["skipped"], 1)

    def test_concurrent_collect_queues_each_line_once(self):
        self.log(*[decision(call=f"toolu_{n}") for n in range(200)])
        threads = [threading.Thread(target=self.collect) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(self.outbox()), 200)

    def test_trimming_a_full_outbox_is_fast(self):
        entry = telemetry.record_from_decision(decision(), None, STEPS)
        telemetry.enqueue([dict(entry, id=f"{n:032x}") for n in range(8_000)], telemetry.Deadline(10))
        start = time.monotonic()
        telemetry.enqueue([dict(entry, id=f"{n:032x}") for n in range(8_000, 15_000)], telemetry.Deadline(10))
        self.assertLess(time.monotonic() - start, 1.5)
        self.assertLessEqual((self.tmp / "home/telemetry/outbox.jsonl").stat().st_size, 5_000_000)
        self.assertGreater(telemetry.counters()["dropped"], 0)

    def test_a_symlinked_state_directory_is_refused(self):
        other = self.tmp / "elsewhere"
        other.mkdir()
        shutil.rmtree(self.tmp / "home" / "telemetry")
        (self.tmp / "home" / "telemetry").symlink_to(other)
        self.log(decision())
        with self.assertRaises(OSError):
            self.collect()
        self.assertEqual(list(other.iterdir()), [])

    def test_repo_url_never_keeps_credentials_or_paths(self):
        cases = {
            "https://user:tok123@github.com/o/r.git": "https://github.com/o/r.git",
            "git@github.com:o/r.git": "git@github.com:o/r.git",
            "ssh://git@github.com:22/o/r.git": "ssh://github.com:22/o/r.git",
            "oauth2:glpat-abcdef@gitlab.com:g/r.git": None,
            "/home/someone/secret-proj": None,
            "file:///home/someone/x": None,
            "https://h:99999/x": None,
            "https://h:abc/x": None,
            "https://github.com/o/r\nInjected: x": None,
            "": None,
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(telemetry.repo_url(raw), expected)

    def test_resource_attributes_are_the_allow_listed_keys_only(self):
        with mock.patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES":
                                          "team=lab,cost_center=lab,service.name=evil,user.email=a@b.com,ai.cohort=improvement,bad key=x"}):
            attrs = telemetry.resource_attributes()
        self.assertEqual(attrs, {"team": "lab", "cost_center": "lab", "ai.cohort": "improvement"})

    def remember(self, session):
        with TempRepo({"a.txt": "a\n"}) as root:
            git(root, "checkout", "-q", "-b", "feat/SHIP-7-x")
            git(root, "remote", "add", "origin", "https://u:secret@github.com/o/r.git")
            with mock.patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES": "team=lab"}):
                return telemetry.remember_session({"session_id": session, "cwd": str(root)}, telemetry.Deadline(3))

    def test_session_context_adds_branch_origin_and_resource_without_secrets(self):
        context = self.remember("s-1")
        self.assertEqual(context["branch"], "feat/SHIP-7-x")
        self.log(decision())
        self.collect()
        [entry] = self.outbox()
        self.assertEqual(entry["attrs"]["vcs.ref.head.name"], "feat/SHIP-7-x")
        self.assertEqual(entry["attrs"]["vcs.repository.url.full"], "https://github.com/o/r.git")
        self.assertEqual(entry["resource"]["team"], "lab")
        for path in (self.tmp / "home").rglob("*"):
            if path.is_file():
                self.assertNotIn("secret", path.read_text(errors="replace"))

    def test_start_entry_carries_the_source_version_and_stream(self):
        context = self.remember("s-9")
        entry = telemetry.start_entry({"session_id": "s-9", "source": "startup"}, "0.1.0+abc", context)
        self.assertEqual(entry["event"], "aidlc.session.start")
        self.assertEqual(entry["attrs"]["aidlc.session.source"], "startup")
        self.assertEqual(entry["resource"]["service.instance.id"], "s-9")
        self.assertIsNone(telemetry.start_entry({"session_id": "bad id!"}, "0.1.0", None))

    def test_old_session_files_are_pruned(self):
        sessions = self.tmp / "home/telemetry/sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        old = sessions / "old.json"
        old.write_text("{}")
        os.utime(old, (time.time() - 40 * 86400, time.time() - 40 * 86400))
        telemetry.prune_sessions(telemetry.Deadline(3))
        self.assertFalse(old.exists())

    def test_git_for_the_session_context_ignores_the_callers_git_environment(self):
        with TempRepo({"a.txt": "a\n"}) as root, mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent"}):
            git(root, "checkout", "-q", "-b", "feat/x")
            context = telemetry.remember_session({"session_id": "s-3", "cwd": str(root)}, telemetry.Deadline(3))
        self.assertEqual(context["branch"], "feat/x")
```

If `tests.helpers.git` itself honours `GIT_DIR`, run the `checkout` before entering the `mock.patch.dict` (record that as a ruling); the assertion stays.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry tests.unit.test_telemetry_policy -v`. Expected: FAIL, because `core/hooks/telemetry.py` does not exist.
- [ ] **Step 3: Write `core/hooks/telemetry.py`.** It covers conversion, state, the cursor, the outbox and the session context; Task 3 adds sending.

```python
#!/usr/bin/env python3
"""The harness's own telemetry (guide 3.4, 3 step 7, 13.5; design §10; ADR 0003).

The guard and the post-check write every decision to $AIDLC_LOG_DIR/decisions.jsonl and never use
the network. This module runs in the session-start and session-end hook phases and under the
person-run `aidlc telemetry`. It turns new log lines into OTLP log records that carry enumerated
metadata only (core/policy/telemetry.yaml), queues them in a bounded outbox under
$AIDLC_HOME_DIR/telemetry/, and (session-end, `aidlc telemetry flush`) sends the outbox to the
loopback collector: one Loki stream per session, oldest first, within one deadline. A reason,
target, command, path, prompt, output, header value or token never leaves the machine."""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
SERVICE_NAME = "aidlc"
SCOPE_NAME = "aidlc.harness"
NO_SESSION = "aidlc-nosession"
DEFAULT_OUTBOX_MAX_BYTES = 5_000_000
READ_MAX_BYTES = 2_000_000           # decision-log bytes converted per call; the rest waits for the next
SESSION_KEEP_S = 30 * 86_400
MAX_STEPS = 20
EVENTS = {
    "aidlc.hook.decision": ("session.key", "tool_use_id", "aidlc.hook", "aidlc.decision", "aidlc.rule",
                            "aidlc.tool", "aidlc.unattended", "aidlc.harness.version"),
    "aidlc.check.result": ("session.key", "aidlc.check.result", "aidlc.check.failing_in_a_row",
                           "aidlc.check.failed_steps", "aidlc.check.retry_limit", "aidlc.harness.version"),
    "aidlc.session.start": ("session.key", "aidlc.session.source", "aidlc.harness.version"),
}
CONTEXT = ("vcs.ref.head.name", "vcs.repository.url.full")
RESOURCE_KEYS = ("team", "cost_center", "env", "ai.cohort", "enduser.pseudonym")
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
SESSION = re.compile(r"[A-Za-z0-9_-]{1,128}")
TOOL_USE = re.compile(r"toolu_[A-Za-z0-9]{1,64}")
VERSION = re.compile(r"[0-9A-Za-z.+-]{1,64}")
BRANCH = re.compile(r"(?!-)[A-Za-z0-9._/-]{1,200}")
SCP = re.compile(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+:[A-Za-z0-9._/~-]{1,250}")
HOST = re.compile(r"[A-Za-z0-9.-]{1,253}")
URL_PATH = re.compile(r"[A-Za-z0-9._/~-]{0,250}")
RESOURCE_VALUE = re.compile(r"[A-Za-z0-9_.@-]{1,64}")
LOOPBACK = re.compile(r"http://(127\.0\.0\.1|\[::1\]):([1-9][0-9]{0,4})")
HOOKS = frozenset({"pre-tool-guard", "post-tool-check", "check-attempts"})
DECISIONS = frozenset({"allow", "ask", "deny", "flag", "pass"})
TOOLS = frozenset({"read", "edit", "shell", "external", "mcp", "unknown"})
SOURCES = frozenset({"startup", "resume", "clear", "compact", "fork"})


class Deadline:
    """One monotonic deadline for a whole phase: lock waits, git, the helper and the sends."""

    def __init__(self, seconds: float):
        self.end = time.monotonic() + float(seconds)

    def left(self) -> float:
        return max(0.0, self.end - time.monotonic())


def home_dir() -> Path:
    return Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()


def log_dir() -> Path:
    return Path(os.environ.get("AIDLC_LOG_DIR") or "~/.aidlc/logs").expanduser()


def state_dir() -> Path:
    return home_dir() / "telemetry"


def loopback(endpoint) -> bool:
    match = LOOPBACK.fullmatch(endpoint) if isinstance(endpoint, str) else None
    return bool(match) and 1 <= int(match.group(2)) <= 65535


def load_config() -> dict:
    """The rendered harness.json (AIDLC_HARNESS_FILE, else next to this file). Missing, unreadable or
    malformed, or AIDLC_TELEMETRY=off: disabled. Values are clamped; a bad endpoint or helper disables it."""
    off = {"enabled": False, "endpoint": "", "headers_helper": None, "timeout_s": 3.0,
           "outbox_max_bytes": DEFAULT_OUTBOX_MAX_BYTES, "version": None, "check_steps": frozenset()}
    if os.environ.get("AIDLC_TELEMETRY", "").strip().lower() == "off":
        return off
    try:
        path = Path(os.environ.get("AIDLC_HARNESS_FILE") or HERE / "harness.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        block = data["telemetry"]
        helper = block["headers_helper"]
        config = {"enabled": block["enabled"] is True, "endpoint": block["endpoint"], "headers_helper": helper,
                  "timeout_s": min(max(float(block["timeout_s"]), 0.5), 4.0),
                  "outbox_max_bytes": min(max(int(block["outbox_max_bytes"]), 10_000), 50_000_000),
                  "version": _match(VERSION, data.get("version")),
                  "check_steps": frozenset(s for s in data.get("check_steps") or [] if isinstance(s, str) and SLUG.fullmatch(s))}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return off
    if not loopback(config["endpoint"]) or not (helper is None or (isinstance(helper, str) and helper.startswith("/"))):
        return off
    return config


def _match(pattern: re.Pattern, value) -> str | None:
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _member(allowed: frozenset, value) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def _nanos(ts) -> str | None:
    try:
        return str(int(datetime.fromisoformat(str(ts)).timestamp() * 1_000_000_000))
    except (TypeError, ValueError, OverflowError):
        return None


def _now() -> str:
    return str(time.time_ns())


def _clean(attrs: dict) -> dict:
    return {k: v for k, v in attrs.items() if v is not None}


def resource_attributes() -> dict[str, str]:
    """The allow-listed resource keys (RESOURCE_KEYS) from OTEL_RESOURCE_ATTRIBUTES, values in the safe set."""
    out = {}
    for pair in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(","):
        key, sep, value = pair.partition("=")
        key, value = key.strip(), value.strip()
        if sep and key in RESOURCE_KEYS and RESOURCE_VALUE.fullmatch(value):
            out[key] = value
    return out


def repo_url(raw) -> str | None:
    """The origin URL without credentials. Only https, http, ssh, git URLs (rebuilt from scheme, host,
    port, path) or a plain scp form `user@host:path`. Local paths, files, odd forms: None."""
    if not isinstance(raw, str) or not raw or len(raw) > 300:
        return None
    if SCP.fullmatch(raw):
        return raw
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        return None
    host = parts.hostname
    if parts.scheme not in ("https", "http", "ssh", "git") or not host or not HOST.fullmatch(host):
        return None
    if not URL_PATH.fullmatch(parts.path or ""):
        return None
    return urlunsplit((parts.scheme, host + (f":{port}" if port else ""), parts.path, "", ""))


def _stream(session) -> dict:
    return {"service.name": SERVICE_NAME, "service.instance.id": _match(SESSION, session) or NO_SESSION}


def record_from_decision(rec: dict, context: dict | None, check_steps: frozenset) -> dict | None:
    """One decision-log line as an outbox entry. Only enumerated keys are built: the line's reason
    and target are never read. None when the line is not a harness decision or carries no time."""
    hook = _member(HOOKS, rec.get("hook"))
    when = _nanos(rec.get("ts"))
    if hook is None or when is None:
        return None
    common = {"session.key": _match(SESSION, rec.get("session")),
              "aidlc.harness.version": _match(VERSION, rec.get("harness"))}
    if hook == "check-attempts":
        failing = rec.get("failing_in_a_row")
        steps = rec.get("failed_steps") if isinstance(rec.get("failed_steps"), list) else []
        names = [s for s in steps if isinstance(s, str) and s in check_steps][:MAX_STEPS]
        attrs = {**common,
                 "aidlc.check.result": "PASS" if rec.get("passed") is True else "FAIL",
                 "aidlc.check.failing_in_a_row": failing if type(failing) is int and 0 <= failing < 10_000 else None,
                 "aidlc.check.failed_steps": ",".join(names) or None,
                 "aidlc.check.retry_limit": "true" if rec.get("rule") == "retry-limit" else "false"}
        event = "aidlc.check.result"
    else:
        unattended = rec.get("unattended")
        attrs = {**common, "tool_use_id": _match(TOOL_USE, rec.get("call")), "aidlc.hook": hook,
                 "aidlc.decision": _member(DECISIONS, rec.get("decision")),
                 "aidlc.rule": _match(SLUG, rec.get("rule")), "aidlc.tool": _member(TOOLS, rec.get("tool")),
                 "aidlc.unattended": "true" if unattended is True else ("false" if unattended is False else None)}
        event = "aidlc.hook.decision"
    attrs = _clean(attrs)
    resource = _stream(rec.get("session"))
    if isinstance(context, dict):
        attrs.update(_clean({"vcs.ref.head.name": _match(BRANCH, context.get("branch")),
                             "vcs.repository.url.full": repo_url(context.get("remote"))}))
        resource.update({k: v for k, v in (context.get("resource") or {}).items()
                         if k in RESOURCE_KEYS and isinstance(v, str) and RESOURCE_VALUE.fullmatch(v)})
    return {"id": uuid.uuid4().hex, "event": event, "time": when, "attrs": attrs, "resource": resource}


@contextmanager
def _locked(deadline: Deadline | float):
    """The state directory, locked exclusively. Waits no longer than the deadline (TimeoutError,
    an OSError); refuses a symlinked state directory or lock."""
    seconds = deadline.left() if isinstance(deadline, Deadline) else float(deadline)
    state = state_dir()
    if state.is_symlink():
        raise OSError(f"{state} is a symlink; telemetry does not follow it")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        stop = time.monotonic() + seconds
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= stop:
                    raise TimeoutError("telemetry state is busy") from None
                time.sleep(0.02)
        yield state
    finally:
        os.close(fd)


def _guard_path(path: Path) -> Path:
    if path.is_symlink():
        raise OSError(f"{path} is a symlink; telemetry does not follow it")
    return path


def _write_atomic(path: Path, text: str) -> None:
    _guard_path(path)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def _read_json(path: Path):
    try:
        return json.loads(_guard_path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except ValueError:
        return None


def _bump(state: Path, name: str, by: int = 1) -> None:
    data = _read_json(state / "counters.json")
    data = data if isinstance(data, dict) else {}
    data[name] = int(data.get(name, 0) or 0) + by
    _write_atomic(state / "counters.json", json.dumps(data))


def counters() -> dict[str, int]:
    data = _read_json(state_dir() / "counters.json")
    data = data if isinstance(data, dict) else {}
    return {k: int(data.get(k, 0) or 0) for k in ("dropped", "expired", "skipped")}


def _identity(log: Path, st: os.stat_result) -> dict:
    return {"path": str(log), "dev": st.st_dev, "ino": st.st_ino}


def _start_offset(state: Path, log: Path, st: os.stat_result) -> int | None:
    """Where to read from. None: no cursor yet (first run starts at the end, so history logged before
    telemetry existed is never shipped). A cursor for another file (rotated or replaced): 0."""
    data = _read_json(state / "cursor.json")
    if not isinstance(data, dict):
        return None
    if any(data.get(k) != v for k, v in _identity(log, st).items()):
        return 0
    offset = data.get("offset")
    return offset if type(offset) is int and 0 <= offset <= st.st_size else 0


def _save_cursor(state: Path, log: Path, st: os.stat_result, offset: int) -> None:
    _write_atomic(state / "cursor.json", json.dumps({**_identity(log, st), "offset": offset}))


def _next_newline(log: Path, start: int) -> int | None:
    with log.open("rb") as fh:
        fh.seek(start)
        position = start
        while True:
            block = fh.read(65_536)
            if not block:
                return None                          # the long line is still being written
            index = block.find(b"\n")
            if index >= 0:
                return position + index + 1
            position += len(block)


def _session_context(state: Path, session) -> dict | None:
    name = _match(SESSION, session)
    if name is None:
        return None
    data = _read_json(_guard_path(state / "sessions") / f"{name}.json")
    return data if isinstance(data, dict) else None


def collect(deadline: Deadline, commit: bool = True) -> list[dict]:
    """Convert complete new decision-log lines. commit=True queues them and moves the cursor;
    commit=False is a dry run (`aidlc telemetry show`)."""
    log = log_dir() / "decisions.jsonl"
    config = load_config()
    with _locked(deadline) as state:
        if log.is_symlink() or not log.is_file():
            return []
        st = log.stat()
        offset = _start_offset(state, log, st)
        if offset is None:
            if commit:
                _save_cursor(state, log, st, st.st_size)
            return []
        with log.open("rb") as fh:
            fh.seek(offset)
            chunk = fh.read(READ_MAX_BYTES)
        end = chunk.rfind(b"\n")
        if end < 0:
            if len(chunk) == READ_MAX_BYTES:         # one line longer than the window: skip past it
                after = _next_newline(log, offset + len(chunk))
                if commit and after is not None:
                    _save_cursor(state, log, st, after)
                    _bump(state, "skipped")
            return []
        entries, contexts, skipped = [], {}, 0
        for raw in chunk[:end + 1].split(b"\n"):
            if not raw:
                continue
            try:
                rec = json.loads(raw.decode("utf-8"))
                if not isinstance(rec, dict):
                    raise ValueError("not an object")
                session = rec.get("session")
                if session not in contexts:
                    contexts[session] = _session_context(state, session)
                entry = record_from_decision(rec, contexts[session], config["check_steps"])
            except Exception:  # noqa: BLE001 - one bad line never stops the cursor
                skipped += 1
                continue
            if entry is not None:
                entries.append(entry)
        if commit:
            _append(state, entries, config["outbox_max_bytes"])
            _save_cursor(state, log, st, offset + end + 1)
            if skipped:
                _bump(state, "skipped", skipped)
        return entries


def enqueue(entries: list[dict], deadline: Deadline) -> None:
    with _locked(deadline) as state:
        _append(state, [e for e in entries if e], load_config()["outbox_max_bytes"])


def _append(state: Path, entries: list[dict], limit: int) -> None:
    """Add entries; when over the cap, drop the oldest in one slice (linear, whatever the size)."""
    if not entries:
        return
    lines = _outbox_lines(state) + [json.dumps(e, sort_keys=True) + "\n" for e in entries]
    sizes = [len(line.encode("utf-8")) for line in lines]
    total, drop = sum(sizes), 0
    while drop < len(lines) and total > limit:
        total -= sizes[drop]
        drop += 1
    _write_atomic(state / "outbox.jsonl", "".join(lines[drop:]))
    if drop:
        _bump(state, "dropped", drop)


def _outbox_lines(state: Path) -> list[str]:
    try:
        text = _guard_path(state / "outbox.jsonl").read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    return [line + "\n" for line in text.splitlines() if line.strip()]


def _parse(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("event") in EVENTS and isinstance(entry.get("id"), str):
            out.append(entry)
    return out


def read_outbox(deadline: Deadline) -> list[dict]:
    with _locked(deadline) as state:
        return _parse(_outbox_lines(state))


def _git(cwd: str, deadline: Deadline, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "-C", cwd, *args],
                             capture_output=True, text=True, timeout=min(1.0, max(deadline.left(), 0.05)),
                             check=False, env=env, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def remember_session(payload: dict, deadline: Deadline) -> dict | None:
    """At session start: the sanitised branch, origin and resource attributes, kept for the session's
    records. Never stores credentials or a local path."""
    session = _match(SESSION, payload.get("session_id"))
    cwd = payload.get("cwd")
    if session is None or not isinstance(cwd, str) or not os.path.isdir(cwd):
        return None
    context = {"branch": _match(BRANCH, _git(cwd, deadline, "symbolic-ref", "--quiet", "--short", "HEAD")),
               "remote": repo_url(_git(cwd, deadline, "config", "--get", "remote.origin.url")),
               "resource": resource_attributes()}
    with _locked(deadline) as state:
        sessions = _guard_path(state / "sessions")
        sessions.mkdir(exist_ok=True, mode=0o700)
        _write_atomic(sessions / f"{session}.json", json.dumps(context))
    return context


def start_entry(payload: dict, version: str | None, context: dict | None) -> dict | None:
    session = _match(SESSION, payload.get("session_id"))
    if session is None:
        return None
    entry = record_from_decision({"hook": "pre-tool-guard", "ts": datetime.now(timezone.utc).isoformat(),
                                  "session": session}, context, frozenset())
    entry["event"] = "aidlc.session.start"
    entry["attrs"] = _clean({"session.key": session, "aidlc.session.source": _member(SOURCES, payload.get("source")),
                             "aidlc.harness.version": _match(VERSION, version),
                             **{k: v for k, v in entry["attrs"].items() if k in CONTEXT}})
    return entry


def prune_sessions(deadline: Deadline) -> None:
    sessions = state_dir() / "sessions"
    if sessions.is_symlink() or not sessions.is_dir():
        return
    cutoff = time.time() - SESSION_KEEP_S
    for path in sessions.glob("*.json"):
        if deadline.left() <= 0:
            return
        try:
            if not path.is_symlink() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue
```

The changes for this task, beyond the module itself:
- **`guard._log`:** add `"unattended": _unattended()` to `record`, next to `"tool"`. `_unattended` is defined at `guard.py:70`. The live harness and every existing reader ignore unknown keys.
- **The setUp cursor:** the setUp's first `collect` starts the cursor at the end of the empty log. That is the first-run rule, and every test then logs after it.
- **`test_trimming_a_full_outbox_is_fast`:** each entry is about 400 bytes. 8,000 entries is about 3.2 MB, and 15,000 is about 6 MB, so the second call trims.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): decision log to an enumerated, bounded outbox; per-session context; cursor by file identity`.

### Task 3: Sending: OTLP/JSON per session, the header helper and the deadline

**Files:**
- Modify: `core/hooks/telemetry.py`
- Test: `tests/unit/test_telemetry_send.py`

**Interfaces:** Produces, in `core/hooks/telemetry.py`:
- `otlp_payload(entries) -> bytes`;
- `headers_from_helper(helper, timeout) -> dict | None`. `None` means do not send; `{}` means no helper.
- `send(body, endpoint, headers, timeout) -> str`, one of `"ok"`, `"collector rejected"` or `"collector unreachable"`;
- `flush(config, deadline) -> tuple[int, str]`. The outcome is one of `"disabled"`, `"empty"`, `"sent"`, `"headers helper failed"`, `"collector unreachable"`, `"collector rejected"`, `"deadline"` or `"endpoint refused"`.
- `last_result() -> dict`;
- `run_phase(phase, payload) -> int`, which is always 0.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry_send.py
import http.server
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from tests.hook_loader import load_hook

telemetry = load_hook("telemetry")


class Collector(http.server.BaseHTTPRequestHandler):
    received: list = []
    delay = 0.0
    status = 200
    redirect_to = None

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        Collector.received.append((self.path, dict(self.headers), body))
        time.sleep(Collector.delay)
        if Collector.redirect_to:
            self.send_response(307)
            self.send_header("Location", Collector.redirect_to)
            self.end_headers()
            return
        self.send_response(Collector.status)
        self.end_headers()

    def log_message(self, *args):
        pass


def serve():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Collector)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SendBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        Collector.received, Collector.delay, Collector.status, Collector.redirect_to = [], 0.0, 200, None
        self.server = serve()
        self.helper = self.helper_script('print(\'{"Authorization": "Bearer t0ken"}\')')
        self.config_patch = mock.patch.object(telemetry, "load_config", side_effect=lambda: self.config())
        self.config_patch.start()
        telemetry.enqueue([self.entry("s-1")], telemetry.Deadline(3))

    def tearDown(self):
        self.config_patch.stop()
        self.server.shutdown()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def entry(self, session, age_s=0.0):
        e = telemetry.start_entry({"session_id": session, "source": "startup"}, "0.1.0+abc", None)
        e["time"] = str(time.time_ns() - int(age_s * 1e9))
        return e

    def helper_script(self, body: str, code: int = 0) -> str:
        path = self.tmp / f"helper-{len(list(self.tmp.glob('helper-*')))}.py"
        path.write_text(f"#!{sys.executable}\nimport sys\n{body}\nsys.exit({code})\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def config(self, **kw):
        base = {"enabled": True, "endpoint": f"http://127.0.0.1:{self.server.server_address[1]}",
                "headers_helper": self.helper, "timeout_s": 3.0, "outbox_max_bytes": 5_000_000,
                "version": "0.1.0+abc", "check_steps": frozenset()}
        base.update(getattr(self, "overrides", {}))
        base.update(kw)
        return base

    def flush(self, **kw):
        return telemetry.flush(self.config(**kw), telemetry.Deadline(kw.get("timeout_s", 3.0)))

    def outbox(self):
        return telemetry.read_outbox(telemetry.Deadline(3))


class SendTest(SendBase):
    def test_flush_posts_otlp_json_to_v1_logs_with_the_helper_header(self):
        self.assertEqual(self.flush(), (1, "sent"))
        [(path, headers, body)] = Collector.received
        self.assertEqual(path, "/v1/logs")
        self.assertEqual(headers["Authorization"], "Bearer t0ken")
        self.assertEqual(headers["Content-Type"], "application/json")
        doc = json.loads(body)
        resource = {a["key"]: a["value"]["stringValue"] for a in doc["resourceLogs"][0]["resource"]["attributes"]}
        self.assertEqual(resource, {"service.name": "aidlc", "service.instance.id": "s-1"})
        [record] = doc["resourceLogs"][0]["scopeLogs"][0]["logRecords"]
        self.assertEqual(record["eventName"], "aidlc.session.start")
        self.assertIn("observedTimeUnixNano", record)
        self.assertIn({"key": "event.name", "value": {"stringValue": "aidlc.session.start"}}, record["attributes"])
        self.assertEqual(self.outbox(), [])

    def test_records_are_grouped_per_session_and_oldest_first(self):
        telemetry.enqueue([self.entry("s-2", age_s=10), self.entry("s-1", age_s=7200), self.entry("s-2", age_s=3600)],
                          telemetry.Deadline(3))
        self.flush()
        doc = json.loads(Collector.received[0][2])
        for resource_logs in doc["resourceLogs"]:
            times = [int(r["timeUnixNano"]) for r in resource_logs["scopeLogs"][0]["logRecords"]]
            self.assertEqual(times, sorted(times))
        streams = [{a["key"]: a["value"]["stringValue"] for a in rl["resource"]["attributes"]}["service.instance.id"]
                   for rl in doc["resourceLogs"]]
        self.assertEqual(sorted(streams), ["s-1", "s-2"])

    def test_entries_older_than_a_week_are_expired_not_sent(self):
        telemetry.enqueue([self.entry("s-3", age_s=8 * 86_400)], telemetry.Deadline(3))
        sent, outcome = self.flush()
        self.assertEqual((sent, outcome), (1, "sent"))
        self.assertEqual(telemetry.counters()["expired"], 1)
        self.assertEqual(self.outbox(), [])

    def test_unreachable_collector_keeps_the_outbox(self):
        self.assertEqual(self.flush(endpoint=f"http://127.0.0.1:{closed_port()}"), (0, "collector unreachable"))
        self.assertEqual(len(self.outbox()), 1)

    def test_a_rejected_request_keeps_the_outbox(self):
        Collector.status = 401
        self.assertEqual(self.flush()[1], "collector rejected")
        self.assertEqual(len(self.outbox()), 1)

    def test_helper_failure_keeps_outbox_and_never_writes_the_header(self):
        for helper in (self.helper_script("print('Bearer leaked-value')"),
                       self.helper_script('print(\'{"Bad Header": "leaked-value"}\')'),
                       self.helper_script('print(\'{"Authorization": "leaked-value"}\')', code=1),
                       self.helper_script("import time; time.sleep(5)"),
                       str(self.tmp / "missing-helper")):
            with self.subTest(helper=helper):
                self.assertEqual(self.flush(headers_helper=helper), (0, "headers helper failed"))
        self.assertEqual(Collector.received, [])
        for path in (self.tmp / "home").rglob("*"):
            if path.is_file():
                self.assertNotIn("leaked-value", path.read_text(errors="replace"))

    def test_redirect_is_not_followed(self):
        other = serve()
        try:
            Collector.redirect_to = f"http://127.0.0.1:{other.server_address[1]}/v1/logs"
            self.assertEqual(self.flush()[1], "collector unreachable")
            self.assertEqual(len(Collector.received), 1)
        finally:
            other.shutdown()

    def test_proxy_env_is_ignored(self):
        with mock.patch.dict(os.environ, {"http_proxy": f"http://127.0.0.1:{closed_port()}",
                                          "HTTP_PROXY": f"http://127.0.0.1:{closed_port()}"}):
            self.assertEqual(self.flush()[1], "sent")

    def test_flush_respects_deadline(self):
        Collector.delay = 5
        start = time.monotonic()
        sent, outcome = self.flush(timeout_s=1.0)
        self.assertLess(time.monotonic() - start, 3.0)
        self.assertEqual(sent, 0)
        self.assertIn(outcome, ("collector unreachable", "deadline"))
        self.assertEqual(len(self.outbox()), 1)

    def test_entries_added_during_a_send_survive(self):
        Collector.delay = 0.5
        thread = threading.Thread(target=self.flush)
        thread.start()
        time.sleep(0.2)
        telemetry.enqueue([self.entry("s-late")], telemetry.Deadline(3))
        thread.join()
        self.assertEqual([e["attrs"]["session.key"] for e in self.outbox()], ["s-late"])

    def test_a_non_loopback_endpoint_is_refused_without_a_request(self):
        for endpoint in ("http://example.com:4318", "http://localhost:4318", "http://127.0.0.1:99999"):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.flush(endpoint=endpoint), (0, "endpoint refused"))
        self.assertEqual(Collector.received, [])

    def test_disabled_sends_nothing(self):
        self.assertEqual(self.flush(enabled=False), (0, "disabled"))

    def test_large_outboxes_go_in_batches(self):
        telemetry.enqueue([self.entry(f"s-{n}") for n in range(1200)], telemetry.Deadline(5))
        self.assertEqual(self.flush(), (1201, "sent"))
        self.assertGreaterEqual(len(Collector.received), 3)

    def test_last_result_records_the_outcome_without_headers(self):
        self.flush()
        result = telemetry.last_result()
        self.assertEqual(result["outcome"], "sent")
        self.assertNotIn("t0ken", json.dumps(result))


class RunPhaseTest(SendBase):
    def test_run_phase_never_raises_never_prints_and_returns_zero(self):
        for payload in ({}, {"session_id": None}, {"session_id": "s", "cwd": "/nonexistent"}, {"x": object()}):
            for phase in ("session-start", "session-end", "unknown"):
                with mock.patch("sys.stdout") as stdout:
                    self.assertEqual(telemetry.run_phase(phase, payload), 0)
                stdout.write.assert_not_called()

    def test_session_start_never_touches_the_network(self):
        telemetry.run_phase("session-start", {"session_id": "s-5", "source": "startup", "cwd": str(self.tmp)})
        self.assertEqual(Collector.received, [])
        self.assertIn("s-5", [e["attrs"]["session.key"] for e in self.outbox()])

    def test_session_end_collects_and_sends(self):
        telemetry.run_phase("session-end", {"session_id": "s-1"})
        self.assertEqual(len(Collector.received), 1)

    def test_run_phase_returns_within_deadline_when_the_lock_is_held(self):
        lock = self.tmp / "home" / "telemetry" / ".lock"
        holder = subprocess.Popen([sys.executable, "-c",
                                   "import fcntl,os,sys,time; fd=os.open(sys.argv[1], os.O_RDWR); "
                                   "fcntl.flock(fd, fcntl.LOCK_EX); print('held', flush=True); time.sleep(30)", str(lock)],
                                  stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(holder.stdout.readline().strip(), "held")
            self.overrides = {"timeout_s": 1.0}
            start = time.monotonic()
            self.assertEqual(telemetry.run_phase("session-end", {"session_id": "s-1"}), 0)
            self.assertLess(time.monotonic() - start, 5.0)
        finally:
            holder.kill()
            holder.wait()

    def test_disabled_writes_no_state(self):
        self.config_patch.stop()
        try:
            with mock.patch.dict(os.environ, {"AIDLC_TELEMETRY": "off"}):
                shutil.rmtree(self.tmp / "home", ignore_errors=True)
                telemetry.run_phase("session-start", {"session_id": "s-1", "source": "startup"})
            self.assertFalse((self.tmp / "home" / "telemetry").exists())
        finally:
            self.config_patch.start()
```

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_send -v`. Expected: FAIL, because `flush` does not exist.
- [ ] **Step 3: Implement sending.** Add `import http.client`, `import urllib.error` and `import urllib.request` at the top, then:

```python
BATCH = 500                                      # records per request: well under the collector's 8 MiB
MAX_AGE_NS = 7 * 86_400 * 1_000_000_000          # Loki rejects older entries (reject_old_samples_max_age 1w)
PHASES = ("session-start", "session-end")
HEADER_NAME = re.compile(r"[A-Za-z0-9-]{1,64}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # never follow: a redirect could carry the header elsewhere
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def _value(v) -> dict:
    return {"intValue": str(v)} if type(v) is int else {"stringValue": str(v)}


def otlp_payload(entries: list[dict]) -> bytes:
    """One resourceLogs per stream (session), its records oldest first."""
    observed = _now()
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        groups.setdefault(json.dumps(entry.get("resource") or {}, sort_keys=True), []).append(entry)
    resource_logs = []
    for key in sorted(groups):
        items = sorted(groups[key], key=lambda e: int(e["time"]))
        records = [{"timeUnixNano": e["time"], "observedTimeUnixNano": observed, "eventName": e["event"],
                    "attributes": [{"key": "event.name", "value": {"stringValue": e["event"]}}]
                                  + [{"key": k, "value": _value(v)} for k, v in sorted(e["attrs"].items())]}
                   for e in items]
        resource_logs.append({"resource": {"attributes": [{"key": k, "value": {"stringValue": v}}
                                                          for k, v in sorted(json.loads(key).items())]},
                              "scopeLogs": [{"scope": {"name": SCOPE_NAME}, "logRecords": records}]})
    return json.dumps({"resourceLogs": resource_logs}).encode("utf-8")


def headers_from_helper(helper, timeout: float) -> dict | None:
    """The helper's one-line JSON object of headers. None (do not send) on any failure. The value is
    never logged or stored."""
    if helper is None:
        return {}
    try:
        out = subprocess.run([helper], capture_output=True, timeout=max(timeout, 0.05), check=False,
                             stdin=subprocess.DEVNULL)
        if out.returncode != 0:
            return None
        data = json.loads(out.stdout.decode("utf-8"))
    except (OSError, subprocess.SubprocessError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    for key, value in data.items():
        if not (isinstance(key, str) and HEADER_NAME.fullmatch(key) and isinstance(value, str)
                and value and not any(c in value for c in "\r\n\0")):
            return None
    return data


def send(body: bytes, endpoint: str, headers: dict, timeout: float) -> str:
    request = urllib.request.Request(endpoint + "/v1/logs", data=body, method="POST",
                                     headers={**headers, "Content-Type": "application/json"})
    try:
        with _OPENER.open(request, timeout=max(timeout, 0.05)) as response:
            return "ok" if 200 <= response.status < 300 else "collector unreachable"
    except urllib.error.HTTPError as exc:
        return "collector rejected" if exc.code in (400, 401, 403, 413) else "collector unreachable"
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return "collector unreachable"


def _record(state: Path, sent: int, outcome: str) -> None:
    _write_atomic(state / "last.json", json.dumps({"time": int(time.time()), "sent": sent, "outcome": outcome}))


def last_result() -> dict:
    data = _read_json(state_dir() / "last.json")
    return data if isinstance(data, dict) else {}


def flush(config: dict, deadline: Deadline) -> tuple[int, str]:
    """Send the outbox oldest first per session. The lock is held only to snapshot and to remove what
    was sent (by id), never during the helper or the network."""
    if not config.get("enabled"):
        return 0, "disabled"
    if not loopback(config.get("endpoint")):
        return 0, "endpoint refused"
    with _locked(deadline) as state:
        snapshot = _parse(_outbox_lines(state))
    if not snapshot:
        return 0, "empty"
    now = time.time_ns()
    expired = {e["id"] for e in snapshot if now - int(e.get("time") or 0) > MAX_AGE_NS}
    fresh = sorted((e for e in snapshot if e["id"] not in expired),
                   key=lambda e: (e["resource"].get("service.instance.id", ""), int(e["time"])))
    sent_ids, outcome = set(), "sent"
    headers = headers_from_helper(config.get("headers_helper"), timeout=min(2.0, deadline.left())) if fresh else {}
    if headers is None:
        outcome = "headers helper failed"
    else:
        for start in range(0, len(fresh), BATCH):
            if deadline.left() <= 0.05:
                outcome = "deadline"
                break
            batch = fresh[start:start + BATCH]
            status = send(otlp_payload(batch), config["endpoint"], headers, timeout=deadline.left())
            if status != "ok":
                outcome = status
                break
            sent_ids.update(e["id"] for e in batch)
    done = sent_ids | expired
    with _locked(max(deadline.left(), 1.0)) as state:      # removal is worth a short wait past the deadline
        keep = [line for line in _outbox_lines(state) if _line_id(line) not in done]
        _write_atomic(state / "outbox.jsonl", "".join(keep))
        if expired:
            _bump(state, "expired", len(expired))
        _record(state, len(sent_ids), outcome)
    return len(sent_ids), outcome


def _line_id(line: str) -> str | None:
    try:
        value = json.loads(line).get("id")
    except (ValueError, AttributeError):
        return None
    return value if isinstance(value, str) else None


def run_phase(phase: str, payload: dict) -> int:
    """The session-start and session-end hook phases. Always 0, never prints. session-start only
    records and queues; session-end collects and sends, within one deadline."""
    try:
        config = load_config()
        if not config["enabled"] or phase not in PHASES:
            return 0
        deadline = Deadline(config["timeout_s"])
        if phase == "session-start":
            context = remember_session(payload, deadline)
            entry = start_entry(payload, config["version"], context)
            if entry is not None:
                enqueue([entry], deadline)
            return 0
        collect(deadline)
        prune_sessions(deadline)
        flush(config, deadline)
    except Exception:  # noqa: BLE001 - telemetry never blocks or fails a session
        pass
    return 0
```

**How `flush` meets the plan's guarantees:**
- **"Sent" counts expired entries.** An entry older than a week counts as handled: it is removed and counted in `expired`, and `test_entries_older_than_a_week_are_expired_not_sent` expects `(1, "sent")`, where the 1 is the fresh setUp entry.
- **Duplicates are possible.** A request that times out after the collector accepted it is re-sent later. That is the documented at-least-once behaviour.
- **A held lock.** In `test_run_phase_returns_within_deadline_when_the_lock_is_held`, the lock file must exist before the holder starts. `SendBase.setUp`'s `enqueue` creates it.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, the Task 2 command, and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): OTLP/JSON per session, oldest first; helper headers; no redirects or proxies; one deadline`.

### Task 4: Hook wiring: the session phases, check details, rendering and doctor

**Files:**
- Modify:
  - `core/hooks/claude_shim.py` (the session phases; `check-attempts` details);
  - `core/hooks/post_check.py` (`_read_check_record`, `record_check_details`; `check_run_id` and `record_check` keep their contracts);
  - `cli/aidlc/adapters/claude_code.py` (`HOOK_FILES`; the SessionStart and SessionEnd entries, with no `onFailure` and `timeout: 5`);
  - `cli/aidlc/checks/doctor.py` (D4 covers the session hooks, and requires that they carry no `onFailure: block`);
  - `cli/aidlc/hookbridge.py` (also loads `telemetry`);
  - `core/policy-as-code/rego/settings_test.rego` (one new test);
  - `core/hooks/README.md`, `docs/harness/hooks.md`;
  - `tests/unit/test_claude_settings.py` (the hook-file set gains `telemetry.py`; a named design change);
  - `tests/fixtures/render/claude-code/settings.node.json` (regenerated).
- Test: `tests/unit/test_session_hooks.py`

**Interfaces:** Consumes `telemetry.run_phase`. Produces:
- rendered `"SessionStart": [{"hooks": [_session_hook("session-start")]}]` and `"SessionEnd": [{"hooks": [_session_hook("session-end")]}]`;
- `check-attempts` records with `passed`, `failing_in_a_row` and `failed_steps`;
- `hooks().telemetry`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_session_hooks.py
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from aidlc.checks.doctor import check_d4
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git, run_cli


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SessionHooksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs"),
                                                "AIDLC_TELEMETRY": "on"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def repo(self):
        repo = TempRepo({"a.txt": "a\n"})
        root = repo.__enter__()
        self.addCleanup(repo.__exit__, None, None, None)
        init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 20))
        code, out, err = run_cli("render", "--tool", "claude-code", str(root))
        assert code == 0, out + err
        # Never the real collector or helper: a closed loopback port and no helper.
        harness = json.loads((root / ".aidlc/hooks/harness.json").read_text())
        harness["telemetry"].update({"endpoint": f"http://127.0.0.1:{closed_port()}", "headers_helper": None})
        (root / ".aidlc/hooks/harness.json").write_text(json.dumps(harness))
        return root

    def shim(self, root, phase, stdin):
        return subprocess.run([sys.executable, str(root / ".aidlc/hooks/claude_shim.py"), phase],
                              input=stdin, capture_output=True, text=True, timeout=30, cwd=root)

    def test_settings_carry_both_non_blocking_session_hooks(self):
        root = self.repo()
        settings = json.loads((root / ".claude/settings.json").read_text())
        for event, phase in (("SessionStart", "session-start"), ("SessionEnd", "session-end")):
            with self.subTest(event=event):
                [entry] = settings["hooks"][event]
                [hook] = entry["hooks"]
                self.assertTrue(hook["command"].endswith(f'claude_shim.py" {phase}'))
                self.assertNotIn("onFailure", hook)
                self.assertEqual(hook["timeout"], 5)
                self.assertNotIn("matcher", entry)
        self.assertTrue((root / ".aidlc/hooks/telemetry.py").is_file())

    def test_session_phases_always_exit_zero_and_print_nothing(self):
        root = self.repo()
        for phase in ("session-start", "session-end"):
            for stdin in ("", "not json", "[1]", json.dumps({"session_id": "s-1", "cwd": str(root)})):
                with self.subTest(phase=phase, stdin=stdin[:10]):
                    done = self.shim(root, phase, stdin)
                    self.assertEqual(done.returncode, 0)
                    self.assertEqual(done.stdout, "")

    def test_session_start_queues_the_start_event(self):
        root = self.repo()
        self.shim(root, "session-start", json.dumps({"session_id": "s-1", "cwd": str(root), "source": "startup"}))
        outbox = (self.tmp / "home/telemetry/outbox.jsonl").read_text()
        self.assertIn("aidlc.session.start", outbox)

    def test_a_check_run_logs_its_details(self):
        root = self.repo()
        git(root, "add", "-A")
        git(root, "commit", "-qm", "render")
        (root / ".check").mkdir(exist_ok=True)
        (root / ".check/result.json").write_text(json.dumps({"run": "r1", "steps": [
            {"name": "scope", "status": "ok"}, {"name": "secrets", "status": "FAIL"}]}))
        payload = {"session_id": "s-1", "tool_use_id": "toolu_1", "cwd": str(root), "tool_name": "Bash",
                   "tool_input": {"command": "aidlc check"}, "tool_response": {"stdout": "check  result FAIL  (1 of 5 steps failed)\n", "stderr": ""}}
        self.shim(root, "post", json.dumps(payload))
        records = [json.loads(l) for l in (self.tmp / "logs/decisions.jsonl").read_text().splitlines()]
        [attempt] = [r for r in records if r.get("hook") == "check-attempts"]
        self.assertIs(attempt["passed"], False)
        self.assertIsInstance(attempt["failing_in_a_row"], int)
        self.assertEqual(attempt["failed_steps"], ["secrets"])
        self.assertTrue(attempt["harness"])

    def test_a_fifo_check_record_never_hangs_the_post_hook(self):
        root = self.repo()
        (root / ".check").mkdir(exist_ok=True)
        os.mkfifo(root / ".check/result.json")
        payload = {"session_id": "s-1", "tool_use_id": "toolu_1", "cwd": str(root), "tool_name": "Bash",
                   "tool_input": {"command": "aidlc check"}, "tool_response": {"stdout": "", "stderr": ""}}
        done = self.shim(root, "post", json.dumps(payload))            # timeout=30 in shim(): a hang fails the test
        self.assertEqual(done.returncode, 0)

    def test_doctor_d4_requires_the_session_hooks_without_block(self):
        root = self.repo()
        settings = json.loads((root / ".claude/settings.json").read_text())
        self.assertEqual([f for f in check_d4(root, settings) if "Session" in f.message], [])
        broken = json.loads(json.dumps(settings))
        del broken["hooks"]["SessionEnd"]
        self.assertTrue(any("D4 SessionEnd" in f.message for f in check_d4(root, broken)))
        blocking = json.loads(json.dumps(settings))
        blocking["hooks"]["SessionStart"][0]["hooks"][0]["onFailure"] = "block"
        self.assertTrue(any("D4 SessionStart" in f.message and "onFailure" in f.message
                            for f in check_d4(root, blocking)))
```

`test_a_check_run_logs_its_details` and the FIFO test drive the post phase with a payload shaped like the existing post-check tests. If the existing tests reach a check record through a different command text or stdout format (read `tests/unit/test_post_check.py` first), use theirs; the assertions on `passed`, `failing_in_a_row`, `failed_steps` and `harness` stay as written. Check `check_d4`'s real signature in `doctor.py` and call it the way its existing tests do.

Add this test to `core/policy-as-code/rego/settings_test.rego`, in the file's existing style; check how its other tests build their input:

```rego
test_session_hooks_without_onfailure_are_accepted if {
	count(deny) == 0 with input as object.union(good_settings, {"hooks": object.union(good_settings.hooks, {
		"SessionStart": [{"hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.aidlc/hooks/claude_shim.py\" session-start", "timeout": 5}]}],
		"SessionEnd": [{"hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.aidlc/hooks/claude_shim.py\" session-end", "timeout": 5}]}]})})
		with data.aidlc as test_data
}
```

Use the names the file already defines for the good input and the data (`good_settings`, `test_data` or similar); the assertion stays as written.
- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_session_hooks -v`. Expected: FAIL, with `KeyError: 'SessionStart'`.
- [ ] **Step 3: Implement the changes.**

**1. Session phases in `claude_shim.py`.** At the very top of `main`, before the existing `try:`, add:

```python
    if len(argv) > 1 and argv[1] in ("session-start", "session-end"):
        try:                                   # telemetry (Plan 4a, ADR 0003): never blocks, never prints
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import telemetry  # noqa: E402
            try:
                payload = json.loads(sys.stdin.read())
            except ValueError:
                payload = {}
            return telemetry.run_phase(argv[1], payload if isinstance(payload, dict) else {})
        except Exception:  # noqa: BLE001
            return 0
```

Then:
- Update the usage line in the docstring to `pre|post|post-failure|session-start|session-end`.
- In the post branch, replace `attempt = post_check.record_check(event)` with `attempt, details = post_check.record_check_details(event)`.
- Log `guard._log({**event, "hook": "check-attempts"}, {**attempt, **details})`.
- `guard._log` already fills the harness version.

**2. In `post_check.py`,** add one safe reader, and make `check_run_id` use it, keeping its contract exactly:

```python
def _read_check_record(root: Path) -> dict | None:
    """<root>/.check/result.json, read without following links or blocking on a FIFO. None: absent,
    a symlink, not a regular file, too big or malformed."""
    try:
        if (root / ".check").is_symlink():
            return None
        fd = os.open(root / ".check" / "result.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as fh:
            if not stat.S_ISREG(os.fstat(fh.fileno()).st_mode):
                return None
            raw = fh.read(MAX_ARTEFACT_BYTES + 1)
        if len(raw) > MAX_ARTEFACT_BYTES:
            return None
        data = json.loads(raw.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    return data if isinstance(data, dict) else None


def check_run_id(root: Path) -> str | None:
    run = (_read_check_record(root) or {}).get("run")
    return run if isinstance(run, str) and run else None


def _failed_steps(record: dict | None) -> list[str]:
    steps = (record or {}).get("steps")
    return [s["name"] for s in steps if isinstance(s, dict) and s.get("status") == "FAIL"
            and isinstance(s.get("name"), str)][:20] if isinstance(steps, list) else []
```

Add `import stat` if it is missing. Then:
- Rename the body of `record_check` to `record_check_details(event) -> tuple[dict | None, dict]`. It returns `(result, details)`, with `details = {"passed": passed, "failing_in_a_row": failures, "failed_steps": _failed_steps(_read_check_record(root))}` whenever `result` is not None, and `{}` otherwise.
- Add `def record_check(event): return record_check_details(event)[0]`.
- Names are filtered against the known step list on the telemetry side (Task 2).
- `.check/result.json` step entries are `StepResult` records (`name`, `status`, with `status` `"FAIL"` for a failed step; `onecheck.py:33,41`).

**3. In `claude_code.py`:**
- Set `HOOK_FILES = ("guard.py", "post_check.py", "claude_shim.py", "telemetry.py")`.
- Add:

```python
def _session_hook(phase: str) -> dict:
    """Telemetry phases (ADR 0003): no onFailure, so a failure or timeout never blocks a session."""
    return {"type": "command",
            "command": f'python3 "${{CLAUDE_PROJECT_DIR}}/.aidlc/hooks/claude_shim.py" {phase}', "timeout": 5}
```

- In `render_permissions`' `"hooks"`, add `"SessionStart": [{"hooks": [_session_hook("session-start")]}]` and `"SessionEnd": [{"hooks": [_session_hook("session-end")]}]`.

**4. In `doctor.check_d4`,** after the existing loop, add:

```python
    for event, phase in (("SessionStart", "session-start"), ("SessionEnd", "session-end")):
        entries = _get(settings, "hooks", event, default=[])
        hooks = [h for e in (entries if isinstance(entries, list) else []) if isinstance(e, dict)
                 for h in e.get("hooks", []) if isinstance(h, dict)
                 and "claude_shim.py" in str(h.get("command", ""))
                 and str(h.get("command", "")).rsplit(" ", 1)[-1] == phase]
        if not hooks:
            out.append(_fail(SETTINGS, f"D4 {event} has no claude_shim.py {phase} hook (telemetry)"))
        elif any(h.get("onFailure") == "block" for h in hooks):
            out.append(_fail(SETTINGS, f"D4 {event} telemetry hook must not set onFailure: block; "
                                       "a failure would block the session"))
```

Use the helper names `doctor.py` already has for reading nested settings and making a failing finding; `_get`, `_fail` and `SETTINGS` stand for them.

**5. In `hookbridge.hooks()`,** also load `telemetry = _load("telemetry", "aidlc_telemetry")`, and return `SimpleNamespace(guard=guard, post_check=post_check, telemetry=telemetry)`.

**6. The named design-change test edits.** In `tests/unit/test_claude_settings.py`, the expected hook-file set gains `".aidlc/hooks/telemetry.py"`. Regenerate the golden `settings.node.json` with the renderer, using the module's own `scaffolded()` and `render_permissions`. Its diff must be exactly the two session-hook entries.

**7. Docs.** In `core/hooks/README.md`, amend line 5's rule to say: "guard and post-check: no network; the telemetry phases are the one exception (ADR 0003)". Document the two phases, `telemetry.py`, and `AIDLC_TELEMETRY=off`. In `docs/harness/hooks.md`, add a "Telemetry" section linking to `docs/observability/README.md`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command and `make test`, then `make policy-test` with `AIDLC_TOOLS_DIR` set. Then run `git diff $(git merge-base main HEAD) -- tests/ | grep '^-.*assert'`, which must show only the named change. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(hooks): non-blocking session-start and session-end telemetry phases; check details read safely`.

### Task 5: `aidlc telemetry status | flush | show` and doctor D15

**Files:**
- Create: `cli/aidlc/commands/telemetry_cmd.py` (register it in `cli/aidlc/commands/__init__.py`)
- Modify: `cli/aidlc/checks/doctor.py` (`check_d15`, called from `run_doctor`), `docs/harness/doctor.md`
- Test: `tests/unit/test_telemetry_cmd.py`

**Interfaces:**
- `aidlc telemetry status`: read-only. Exits 0, or 1 when records were dropped or expired, or when the helper is missing or not executable while telemetry is enabled.
- `aidlc telemetry show [--limit N]`: read-only. It prints the outbox, then a dry run of new log lines, as JSON lines, and exits 0. A limit below 1 is a usage error (exit 2).
- `aidlc telemetry flush`: collects, then sends. Exits 0 on sent, empty or disabled, and 1 when records are kept.
- D15 warns, and never fails.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry_cmd.py
import json
import os
import shutil
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc.checks.doctor import check_d15
from aidlc.hookbridge import hooks
from tests.helpers import run_cli

SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"


def closed_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TelemetryCmdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "logs").mkdir()
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        self.log = self.tmp / "logs/decisions.jsonl"
        self.log.write_text("")
        tel = hooks().telemetry
        tel.collect(tel.Deadline(3))                           # cursor at the end of the empty log
        self.log.write_text(json.dumps({"ts": "2026-10-20T09:00:00+00:00", "hook": "pre-tool-guard",
                                        "session": "s-1", "tool": "shell", "decision": "deny", "rule": "shell-deny",
                                        "target": SECRET, "reason": SECRET, "harness": "0.1.0+abc"}) + "\n")
        self.config = {"enabled": True, "endpoint": f"http://127.0.0.1:{closed_port()}", "headers_helper": None,
                       "timeout_s": 1.0, "outbox_max_bytes": 5_000_000}

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_show_is_read_only_and_prints_nothing_secret(self):
        code, out, _ = run_cli("telemetry", "show")
        self.assertEqual(code, 0)
        [line] = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(json.loads(line)["event"], "aidlc.hook.decision")
        self.assertNotIn(SECRET, out)
        self.assertFalse((self.tmp / "home/telemetry/outbox.jsonl").exists())

    def test_flush_with_the_collector_down_keeps_records_and_exits_1(self):
        with mock.patch("aidlc.commands.telemetry_cmd._config", return_value=self.config):
            code, out, err = run_cli("telemetry", "flush")
        self.assertEqual(code, 1)
        self.assertIn("1 kept", out)

    def test_status_reports_the_outbox_and_last_result(self):
        with mock.patch("aidlc.commands.telemetry_cmd._config", return_value=self.config):
            run_cli("telemetry", "flush")
            code, out, _ = run_cli("telemetry", "status")
        self.assertIn("outbox: 1 record(s)", out)
        self.assertIn("last send: collector unreachable", out)

    def test_status_exits_1_when_the_helper_is_missing(self):
        with mock.patch("aidlc.commands.telemetry_cmd._config",
                        return_value=dict(self.config, headers_helper=str(self.tmp / "missing"))):
            code, _, _ = run_cli("telemetry", "status")
        self.assertEqual(code, 1)

    def test_limit_below_one_is_a_usage_error(self):
        code, _, _ = run_cli("telemetry", "show", "--limit", "0")
        self.assertEqual(code, 2)

    def test_d15_warns_about_counters_and_a_missing_helper(self):
        (self.tmp / "home/telemetry").mkdir(parents=True, exist_ok=True)
        (self.tmp / "home/telemetry/counters.json").write_text(json.dumps({"dropped": 7, "expired": 2}))
        with mock.patch("aidlc.checks.doctor._telemetry_policy",
                        return_value={"enabled": True, "headers_helper": str(self.tmp / "missing")}):
            findings = check_d15()
        self.assertEqual({f.level for f in findings}, {"WARN"})
        text = " ".join(f.message for f in findings)
        self.assertIn("7 dropped", text)
        self.assertIn("2 expired", text)
        self.assertIn("header helper", text)
```

`show` and `flush` read the decision log with the hook module's own `load_config` for `check_steps`; in this test the suite's `AIDLC_TELEMETRY=off` makes it return an empty step set, which does not affect a `pre-tool-guard` record. `run_cli` runs `aidlc.cli.main` in-process, so `mock.patch` reaches `_config`.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_cmd -v`. Expected: FAIL, because the command does not exist.
- [ ] **Step 3: Write the command and D15.**

```python
"""aidlc telemetry: inspect and send the harness's own telemetry (guide 3.4; design §10). A person's
command: run it outside an agent session (the agent's sandbox cannot write ~/.aidlc). status and
show never change state; flush collects new decisions and sends."""
from __future__ import annotations

import argparse
import json
import os
import sys

from ..cli import command
from ..hookbridge import hooks
from ..policy import PolicyError, load_policy

KEYS = ("enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes")


def _config() -> dict:
    data = load_policy("telemetry")
    config = {k: data[k] for k in KEYS}
    if os.environ.get("AIDLC_TELEMETRY", "").strip().lower() == "off":
        config["enabled"] = False
    return config


def _helper_ok(config: dict) -> bool:
    helper = config.get("headers_helper")
    return helper is None or os.access(helper, os.X_OK)


def _run(args: argparse.Namespace) -> int:
    tel = hooks().telemetry
    try:
        config = _config()
        deadline = tel.Deadline(max(float(config["timeout_s"]), 3.0))
        if args.action == "show":
            if args.limit < 1:
                print("aidlc telemetry: --limit must be at least 1", file=sys.stderr)
                return 2
            entries = tel.read_outbox(deadline) + tel.collect(deadline, commit=False)
            for entry in entries[: args.limit]:
                print(json.dumps(entry, sort_keys=True))
            return 0
        if args.action == "flush":
            tel.collect(deadline)
            sent, outcome = tel.flush({**config, "version": None, "check_steps": frozenset()}, deadline)
            kept = len(tel.read_outbox(tel.Deadline(3)))
            print(f"telemetry: {outcome}; {sent} sent, {kept} kept")
            return 0 if outcome in ("sent", "empty", "disabled") else 1
        counts = tel.counters()
        print(f"telemetry: {'enabled' if config['enabled'] else 'disabled'}")
        print(f"endpoint: {config['endpoint']}")
        print(f"header helper: {config['headers_helper'] or 'none'}{'' if _helper_ok(config) else ' (missing)'}")
        print(f"outbox: {len(tel.read_outbox(deadline))} record(s); dropped: {counts['dropped']}; "
              f"expired: {counts['expired']}; skipped: {counts['skipped']}")
        print(f"last send: {tel.last_result().get('outcome', 'never')}")
        bad = counts["dropped"] or counts["expired"] or (config["enabled"] and not _helper_ok(config))
        return 1 if bad else 0
    except (PolicyError, OSError, ValueError) as exc:
        print(f"aidlc telemetry: {exc}", file=sys.stderr)
        return 2


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("telemetry", help="inspect and send the harness's own telemetry", allow_abbrev=False)
    parser.add_argument("action", choices=("status", "flush", "show"))
    parser.add_argument("--limit", type=int, default=50)
    parser.set_defaults(func=_run)
```

Follow the registration pattern the other command modules in `cli/aidlc/commands/` use; `@command` and `register` stand for it.

Register the command in `cli/aidlc/commands/__init__.py`. Then add `check_d15` to `doctor.py`. The module imports hooks as `load_hooks`, at `doctor.py:20`.

```python
def _telemetry_policy() -> dict:
    return load_policy("telemetry")


def check_d15() -> list[Finding]:
    """D15 telemetry: warnings only (telemetry never fails a check)."""
    try:
        data = _telemetry_policy()
    except PolicyError as exc:
        return [_warn("core/policy/telemetry.yaml", f"D15 telemetry policy unreadable: {exc}")]
    if not data.get("enabled"):
        return []
    out = []
    helper = data.get("headers_helper")
    if helper and not os.access(helper, os.X_OK):
        out.append(_warn(helper, "D15 the telemetry header helper is missing or not executable; records wait in the outbox"))
    counts = load_hooks().telemetry.counters()
    if counts["dropped"] or counts["expired"]:
        out.append(_warn("~/.aidlc/telemetry", f"D15 telemetry lost records: {counts['dropped']} dropped "
                                               f"(full outbox), {counts['expired']} expired (older than 7 days)"))
    return out
```

Call it from `run_doctor` after D14, in the same way the other checks are appended. Add a D15 row to `docs/harness/doctor.md`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): aidlc telemetry status|flush|show (status and show read-only); doctor D15`.

### Task 6: The metric catalogue, the dashboard and the alert rules

**Files:**
- Create:
  - `core/observability/metrics.yaml`;
  - `core/observability/grafana/aidlc-harness.json`;
  - `core/observability/grafana/alerting/aidlc.yaml`;
  - `docs/observability/runbooks.md`.
- Modify: `cli/aidlc/trace.py` (`collect` scans `core/observability/*.yaml` `meta.guide` with kind `observability`); `tests/unit/test_trace.py` (one new test); `docs/traceability.md` (regenerated).
- Test: `tests/unit/test_observability_assets.py`

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_observability_assets.py
import json
import re
import unittest

import yaml

from aidlc.paths import framework_root
from aidlc.policy import load_policy

OBS = framework_root() / "core" / "observability"
RUNBOOKS = framework_root() / "docs" / "observability" / "runbooks.md"
RUNBOOK_URL = "https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#"


def known_labels() -> set[str]:
    data = load_policy("telemetry")
    keys = {k for keys in data["events"].values() for k in keys} | set(data["context"])
    return {k.replace(".", "_") for k in keys} | {"event_name", "service_name", "service_instance_id", "session_key",
                                                   "ticket_key", "branch", "repo", "team", "cost_usd", "decision",
                                                   "source", "tool_name", "__error__"}


def panel_targets(dashboard: dict) -> list[dict]:
    return [t for p in dashboard["panels"] for t in p.get("targets", [])]


class ObservabilityAssetsTest(unittest.TestCase):
    def test_dashboard_uses_lab_datasources_and_known_labels_only(self):
        dash = json.loads((OBS / "grafana/aidlc-harness.json").read_text())
        self.assertEqual(dash["uid"], "aidlc-harness")
        for target in panel_targets(dash):
            with self.subTest(expr=target["expr"][:60]):
                self.assertEqual(target["datasource"]["uid"], "loki")
                self.assertRegex(target["expr"], r'service_name="(aidlc|claude-code)"')
                for label in re.findall(r"\b([a-z_]+)\s*(?:=|!=|=~|!~)\s*\"", target["expr"]):
                    self.assertIn(label, known_labels())
                if "unwrap" in target["expr"]:
                    self.assertIn('__error__=""', target["expr"])

    def test_per_task_panels_drop_empty_ticket_keys(self):
        dash = json.loads((OBS / "grafana/aidlc-harness.json").read_text())
        for target in panel_targets(dash):
            if "by (ticket_key" in target["expr"]:
                self.assertIn('ticket_key!=""', target["expr"])

    def test_cost_per_task_joins_on_session_key(self):
        dash = json.loads((OBS / "grafana/aidlc-harness.json").read_text())
        [panel] = [p for p in dash["panels"] if p["title"] == "Cost per task"]
        self.assertEqual({t["refId"] for t in panel["targets"]}, {"cost", "tasks"})
        joins = [t for t in panel["transformations"] if t["id"] == "joinByField"]
        self.assertEqual(joins[0]["options"]["byField"], "session_key")

    def test_every_alert_is_complete_and_evaluable(self):
        doc = yaml.safe_load((OBS / "grafana/alerting/aidlc.yaml").read_text())
        rules = [r for g in doc["groups"] for r in g["rules"]]
        self.assertEqual({r["uid"] for r in rules},
                         {"aidlc-fail-safe", "aidlc-retry-limit", "aidlc-session-cost", "aidlc-unattended-denials"})
        anchors = set(re.findall(r"^## (aidlc-[a-z0-9-]+)$", RUNBOOKS.read_text(), re.M))
        for rule in rules:
            with self.subTest(rule=rule["uid"]):
                self.assertTrue(rule["title"])
                self.assertEqual(rule["condition"], "C")
                self.assertIn("for", rule)
                self.assertIn("owner", rule["labels"])
                url = rule["annotations"]["runbook_url"]
                self.assertTrue(url.startswith(RUNBOOK_URL))
                self.assertIn(url[len(RUNBOOK_URL):], anchors)
                by_ref = {d["refId"]: d for d in rule["data"]}
                self.assertEqual(by_ref["A"]["model"]["queryType"], "instant")
                self.assertEqual(by_ref["B"]["model"]["type"], "reduce")
                self.assertEqual(by_ref["C"]["model"]["type"], "threshold")
                self.assertEqual(by_ref["C"]["model"]["expression"], "B")

    def test_cost_alert_threshold_is_the_policy_budget(self):
        doc = yaml.safe_load((OBS / "grafana/alerting/aidlc.yaml").read_text())
        [rule] = [r for g in doc["groups"] for r in g["rules"] if r["uid"] == "aidlc-session-cost"]
        threshold = {d["refId"]: d for d in rule["data"]}["C"]["model"]["conditions"][0]["evaluator"]["params"][0]
        self.assertEqual(threshold, load_policy("telemetry")["budget_usd_per_session"])

    def test_metric_catalogue_is_complete(self):
        doc = yaml.safe_load((OBS / "metrics.yaml").read_text())
        self.assertEqual(doc["meta"]["id"], "observability-metrics")
        names = {m["id"] for m in doc["metrics"]}
        self.assertTrue({"first_attempt_green_rate", "retries_per_task", "p95_time_to_green", "denial_rate",
                         "override_rate", "asks_per_task", "approval_time", "cost_per_successful_task",
                         "retry_limit_hits", "fail_safe_blocks", "decisions_stopped"} <= names)
        for metric in doc["metrics"]:
            with self.subTest(metric=metric["id"]):
                for key in ("definition", "source", "owner", "read_with", "action", "status"):
                    self.assertIn(key, metric)
                self.assertIn(metric["status"], {"dashboard", "query", "not-available"})
                if metric["status"] in ("dashboard", "query"):
                    self.assertTrue(metric.get("query"))
                else:
                    self.assertTrue(metric.get("gap"))
```

`framework_root` lives where `aidlc.policy` imports it from; import it from that module if `aidlc.paths` does not exist.

Add to `tests/unit/test_trace.py`:

```python
    def test_observability_files_are_traced(self):
        from aidlc.trace import collect
        elements, problems = collect()
        self.assertIn("observability", {e.kind for e in elements})
```

`collect(root=None) -> (elements, problems)` is the real signature; check the element type's attribute name for the kind and use it.
- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets tests.unit.test_trace -v`. Expected: FAIL, because the files are missing.
- [ ] **Step 3: Write the files exactly as follows.**

```yaml
# core/observability/metrics.yaml
meta: {id: observability-metrics, owner: "@harness-owners", review_by: "2027-04-20", guide: ["3.4", "12.11", "12.12"]}
# The guide's paired agent metrics (3.4) in this platform's terms. Tasks are ticket.key (from the branch,
# on aidlc records only); Claude Code records join to tasks through session_key. "Usage is read, never targeted".
metrics:
  - id: first_attempt_green_rate
    definition: Tasks whose first aidlc.check.result is PASS, over tasks with any check result.
    source: aidlc.check.result
    owner: "@harness-owners"
    read_with: [retries_per_task]
    action: Falling two weeks running - read the failing steps by harness version and fix the context or the harness.
    status: query
    query: 'sum by (ticket_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | ticket_key!="" | aidlc_check_result="PASS" | aidlc_check_failing_in_a_row="0" [$__range]))'
    note: A PASS with zero failures before it marks a first-attempt green task; divide by the count of tasks with any check result.
  - id: retries_per_task
    definition: FAIL check results per task.
    source: aidlc.check.result
    owner: "@harness-owners"
    read_with: [first_attempt_green_rate]
    action: A task above three - read its session and the step that keeps failing.
    status: dashboard
    query: 'sum by (ticket_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | ticket_key!="" | aidlc_check_result="FAIL" [$__range]))'
  - id: p95_time_to_green
    definition: 95th percentile of the time from a task's first session start to its first PASS.
    source: aidlc.session.start and aidlc.check.result
    owner: "@harness-owners"
    read_with: [first_attempt_green_rate]
    action: Rising - look for slow steps or long retries.
    status: not-available
    gap: LogQL cannot pair two event times per task; computed by aidlc metrics in Plan 6 from the same records.
  - id: denial_rate
    definition: Pre-tool-guard deny decisions over all pre-tool-guard decisions.
    source: aidlc.hook.decision
    owner: "@harness-owners"
    read_with: [override_rate]
    action: A jump after a harness change - read the rules behind it; a fall to zero - check that the hooks still run.
    status: dashboard
    query: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_decision="deny" [$__range])) / sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_hook="pre-tool-guard" [$__range]))'
  - id: override_rate
    definition: Asks a person approved over aidlc ask decisions, per session (approvals are Claude Code tool_decision accept events from a user source).
    source: aidlc.hook.decision and claude-code tool_decision
    owner: "@harness-owners"
    read_with: [denial_rate, asks_per_task]
    action: High - the ask rule may be too broad; read which asks are always approved.
    status: query
    query: 'sum by (session_key) (count_over_time({service_name="claude-code"} | event_name="tool_decision" | decision="accept" | source=~"user_(temporary|permanent)" [$__range])) / sum by (session_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_decision="ask" [$__range]))'
    note: Also counts approvals of settings-level ask rules; an exact match per call joins tool_use_id.
  - id: asks_per_task
    definition: aidlc ask decisions per task.
    source: aidlc.hook.decision
    owner: "@harness-owners"
    read_with: [approval_time]
    action: Many asks per task - reflexive approval risk (guide 3.9); narrow or widen the rule.
    status: dashboard
    query: 'sum by (ticket_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | ticket_key!="" | aidlc_decision="ask" [$__range]))'
  - id: approval_time
    definition: Time from an ask to the person's answer.
    source: claude_code.tool.blocked_on_user spans (enhanced telemetry beta, Langfuse)
    owner: "@harness-owners"
    read_with: [asks_per_task]
    action: Long waits - unattended work is stalling on asks.
    status: not-available
    gap: Needs Claude Code's beta traces (CLAUDE_CODE_ENHANCED_TELEMETRY_BETA) in Langfuse; not in the log events.
  - id: cost_per_successful_task
    definition: Claude Code cost (api_request cost_usd) per task, joined to tasks through session_key, for tasks with a PASS.
    source: claude-code api_request and aidlc.session.start
    owner: "@harness-owners"
    read_with: [retries_per_task]
    action: High for a kind of change - check retries, context size and the model tier (guide 12.16).
    status: dashboard
    query: 'sum by (session_key) (sum_over_time({service_name="claude-code"} | event_name="api_request" | unwrap cost_usd | __error__="" [$__range]))'
  - id: retry_limit_hits
    definition: Check results at the retry limit.
    source: aidlc.check.result
    owner: "@harness-owners"
    read_with: [retries_per_task]
    action: Any - a person reads why the agent kept failing before resetting the counter.
    status: dashboard
    query: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | aidlc_check_retry_limit="true" [$__range]))'
  - id: fail_safe_blocks
    definition: Decisions with rule fail-safe.
    source: aidlc.hook.decision
    owner: "@harness-owners"
    read_with: [denial_rate]
    action: Any - a hook failed; read the local decision log for the reason.
    status: dashboard
    query: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_rule="fail-safe" [$__range]))'
  - id: decisions_stopped
    definition: Sessions that called tools but produced no aidlc decision (hooks not running).
    source: aidlc.session.start, aidlc.hook.decision, claude-code tool_decision
    owner: "@harness-owners"
    read_with: [denial_rate]
    action: Any - doctor D4; the session may have started outside the repository root.
    status: not-available
    gap: Claude Code records carry no repository, so a machine-wide count cannot tell aidlc repositories apart; doctor D4 and the live attack preflight cover it locally (guide 3.9 "alert when decisions stop").
```

For the dashboard, write `core/observability/grafana/aidlc-harness.json` as one JSON object with:
- `"uid": "aidlc-harness"`, `"title": "aidlc harness"`, `"tags": ["aidlc"]`, `"schemaVersion": 39`, `"time": {"from": "now-7d", "to": "now"}`;
- `"templating": {"list": []}`, so there is no team variable: aidlc records carry `team` only when the session set it;
- a `"panels"` array of the nine panels below.

Each target is `{"refId": ..., "datasource": {"type": "loki", "uid": "loki"}, "expr": ..., "queryType": "range" | "instant"}`. Each panel has `"title"` and `"type"`, plus `"targets"` and, where shown, `"transformations"`.

| title | type | targets (refId: expr, queryType) | transformations |
|---|---|---|---|
| Decisions by rule and outcome | `table` | `A`: `sum by (aidlc_rule, aidlc_decision) (count_over_time({service_name="aidlc"} \| event_name="aidlc.hook.decision" [$__range]))`, instant | — |
| Denial rate | `stat` | `A`: the `denial_rate` query from `metrics.yaml`, instant | — |
| Asks per task | `table` | `A`: the `asks_per_task` query, instant | — |
| Check results | `timeseries` | `A`: `sum by (aidlc_check_result) (count_over_time({service_name="aidlc"} \| event_name="aidlc.check.result" [1h]))`, range | — |
| Retries per task | `table` | `A`: the `retries_per_task` query, instant | — |
| Retry-limit hits and fail-safe blocks | `stat` | `A`: the `retry_limit_hits` query. `B`: the `fail_safe_blocks` query. Both instant. | — |
| Cost per session | `table` | `A`: the `cost_per_successful_task` query, instant | — |
| Cost per task | `table` | `cost`: the `cost_per_successful_task` query, instant. `tasks`: `sum by (session_key, ticket_key) (count_over_time({service_name="aidlc"} \| event_name="aidlc.session.start" \| ticket_key!="" [$__range]))`, instant. | `[{"id": "labelsToFields", "options": {}}, {"id": "joinByField", "options": {"byField": "session_key", "mode": "inner"}}, {"id": "groupBy", "options": {"fields": {"ticket_key": {"aggregations": [], "operation": "groupby"}, "Value #cost": {"aggregations": ["sum"], "operation": "aggregate"}}}}]` |
| Sessions by harness version | `table` | `A`: `count by (aidlc_harness_version) (sum by (aidlc_harness_version, session_key) (count_over_time({service_name="aidlc"} \| event_name="aidlc.session.start" \| aidlc_session_source="startup" [$__range])))`, instant | — |

Give each panel a `gridPos`, laid out two per row, 12 wide and 8 high.

```yaml
# core/observability/grafana/alerting/aidlc.yaml  (Grafana file provisioning; copied by the platform owner)
apiVersion: 1
groups:
  - orgId: 1
    name: aidlc
    folder: aidlc
    interval: 5m
    rules:
      - uid: aidlc-fail-safe
        title: aidlc fail-safe block
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: An aidlc hook failed and blocked to be safe.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-fail-safe
        noDataState: OK
        execErrState: Error
        data:
          - {refId: A, relativeTimeRange: {from: 900, to: 0}, datasourceUid: loki,
             model: {refId: A, queryType: instant, expr: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_rule="fail-safe" [15m])) or vector(0)'}}
          - {refId: B, datasourceUid: __expr__, model: {refId: B, type: reduce, reducer: last, expression: A}}
          - {refId: C, datasourceUid: __expr__, model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [0]}}]}}
      - uid: aidlc-retry-limit
        title: aidlc retry limit reached
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: An agent failed the one-command check at the retry limit; a person must look.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-retry-limit
        noDataState: OK
        execErrState: Error
        data:
          - {refId: A, relativeTimeRange: {from: 900, to: 0}, datasourceUid: loki,
             model: {refId: A, queryType: instant, expr: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | aidlc_check_retry_limit="true" [15m])) or vector(0)'}}
          - {refId: B, datasourceUid: __expr__, model: {refId: B, type: reduce, reducer: last, expression: A}}
          - {refId: C, datasourceUid: __expr__, model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [0]}}]}}
      - uid: aidlc-session-cost
        title: aidlc session over budget
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: A Claude Code session spent more than the per-session budget in the last 24 hours.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-session-cost
        noDataState: OK
        execErrState: Error
        data:
          - {refId: A, relativeTimeRange: {from: 86400, to: 0}, datasourceUid: loki,
             model: {refId: A, queryType: instant, expr: 'max(sum by (session_key) (sum_over_time({service_name="claude-code"} | event_name="api_request" | unwrap cost_usd | __error__="" [24h]))) or vector(0)'}}
          - {refId: B, datasourceUid: __expr__, model: {refId: B, type: reduce, reducer: last, expression: A}}
          - {refId: C, datasourceUid: __expr__, model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [5]}}]}}
      - uid: aidlc-unattended-denials
        title: aidlc denials in an unattended run
        condition: C
        for: 0m
        labels: {owner: harness-owners, severity: warning}
        annotations:
          summary: The guard denied calls in an unattended run (guide 13.4); read what the run tried.
          runbook_url: https://github.com/prashantsharma18/aidlc/blob/main/docs/observability/runbooks.md#aidlc-unattended-denials
        noDataState: OK
        execErrState: Error
        data:
          - {refId: A, relativeTimeRange: {from: 900, to: 0}, datasourceUid: loki,
             model: {refId: A, queryType: instant, expr: 'sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_unattended="true" | aidlc_decision="deny" [15m])) or vector(0)'}}
          - {refId: B, datasourceUid: __expr__, model: {refId: B, type: reduce, reducer: last, expression: A}}
          - {refId: C, datasourceUid: __expr__, model: {refId: C, type: threshold, expression: B, conditions: [{evaluator: {type: gt, params: [0]}}]}}
```

**`docs/observability/runbooks.md`.** Write one section per alert. Each heading is exactly the rule uid: `## aidlc-fail-safe`, `## aidlc-retry-limit`, `## aidlc-session-cost` and `## aidlc-unattended-denials`. Each section gives:
- the threshold and window, and the owner;
- what the alert means;
- the first three things to check, starting with `aidlc telemetry show` and the local decision log;
- how to close it.

Add a closing section, `## Gaps`, covering two items:
- "decisions stopped" is not an alert: Claude Code records carry no repository. Doctor D4 and the live attack preflight cover it locally.
- approval time and p95 time to green are not available, for the reasons in `metrics.yaml`.

**`cli/aidlc/trace.py`.** In `collect`, add `core/observability/*.yaml` with `meta.guide` and kind `observability`, mirroring the `core/ci/*/setup.yaml` block. Run `bin/aidlc trace`, then commit the regenerated `docs/traceability.md`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(observability): metric catalogue, dashboard (cost per task joined on session_key) and four evaluable alerts with runbooks`.

### Task 7: The platform kit, docs and ADR 0003

**Files:**
- Create:
  - `docs/observability/README.md`;
  - `docs/observability/platform-patch.md`;
  - `docs/adr/0003-telemetry-hook-network.md`.
- Modify:
  - `docs/codebase-map.md`: add areas for `core/hooks/telemetry.py`, `core/observability/` and `cli/aidlc/commands/telemetry_cmd.py`; under "Where common changes go", add a new telemetry key, which needs the policy, the hook's `EVENTS`, the allow-list pattern and the platform kit. Amend line 57's hook rule.
  - `docs/design/2026-10-18-aidlc-framework-design.md` §10: add a dated note (see Step 3).
  - `README.md`: add the docs to the list.
- Test: `tests/unit/test_observability_assets.py` (one added test).

- [ ] **Step 1: Write the failing test.**

```python
    def test_platform_patch_quotes_the_policy_and_covers_the_platforms_rules(self):
        text = (framework_root() / "docs/observability/platform-patch.md").read_text()
        self.assertIn(load_policy("telemetry")["allowlist_pattern"], text)
        for needle in ("alerting/aidlc.yaml", "provisioning/dashboards/aidlc.yaml", "render_lookups",
                       "force-recreate otel-collector", "test_grafana_dashboards.py"):
            self.assertIn(needle, text)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets -v`. Expected: FAIL, because the file is missing.
- [ ] **Step 3: Write the docs.** Use short sentences, British spelling, and "you"; link to sources rather than copying values.

**1. `docs/observability/README.md`** covers:
- **What is sent:** the three events, the context and the resource keys, linked to the policy.
- **What is never sent:** the list from Global Constraints.
- **When it is sent:** at session end and on `aidlc telemetry flush`. Session start sends nothing.
- **Delivery:** one Loki stream per session; at least once; the outbox cap and the dropped, expired and skipped counters.
- **First run:** it starts at the end of the existing log.
- **Retention and access:**
  - local: the outbox and `sessions/` (pruned after 30 days), and the decision log, which is not rotated by the framework;
  - platform: Loki 720h and Langfuse 30 days, by policy.
- **Inspecting and switching off:** `aidlc telemetry show` and `status`, and `AIDLC_TELEMETRY=off`. The test suite and the live attack harness run with it off.
- **Not emitted:** events for checks a person runs outside a session, for `aidlc ci` and for GitHub runs. Their records are `.check/result.json` and CI artifacts; this is a known gap against design §8 and §10.
- **What `aidlc.check.result` means:** the retry counter's verdict. It is PASS only for the exact recorded entry point's `aidlc check`.
- **Joins:** `ticket.key` exists on aidlc records only, so Claude Code cost and approvals join through `session_key`.
- **Until the platform patch is applied,** records arrive with `event.name` and the contract keys only.
- **The upgrade note:** every installed repository must re-render (`aidlc render --tool claude-code`), or doctor D4 and the GitHub `config-policy` step report stale files.

**2. `docs/observability/platform-patch.md`** is the platform owner's kit. The framework applies none of it. Each numbered step gives the exact file and command:
1. Add the quoted `allowlist_pattern` under `patterns:` in `PC/policy/telemetry/metadata-allowlist.yaml`. Then run `cd PC && uv run python -m tools.render_lookups`.
2. Copy `core/observability/grafana/alerting/aidlc.yaml` to `PC/lab/grafana/provisioning/alerting/aidlc.yaml`, and choose a contact point.
3. For the dashboard, use a second provider; don't touch the generator folder. The platform's `PC/tests/grafana/test_grafana_dashboards.py` requires every JSON in `grafana/dashboards/` to be generator-written, and pins the set to two files.
   - Add `PC/lab/grafana/provisioning/dashboards/aidlc.yaml`, with provider `aidlc`, folder `aidlc`, and path `/var/lib/grafana/dashboards-aidlc`.
   - Add a compose volume that mounts a folder holding `aidlc-harness.json` at that path, read-only.
   - Alternatively, add the dashboard to the generator, and amend those two tests.
4. From `PC/lab`, run `docker compose up -d --force-recreate otel-collector` and restart Grafana (runbook `docs/runbooks/lab-deployment.md`).
5. Verify: run `aidlc telemetry flush`, then in Grafana Explore query `{service_name="aidlc"} | event_name="aidlc.hook.decision"`, and check that `aidlc_rule` is present.

Close with a platform notes section:
- Loki and Mimir `/ready` returned 503 earlier on 2026-10-20 and `ready` later, with no runbook entry.
- `lab-deployment.md:16-17,116` are stale.

**3. `docs/adr/0003-telemetry-hook-network.md`,** with Status, Context, Decision and Consequences.

The decision:
- The guard and post-check stay network-free and fail closed.
- One telemetry module may use the network, only at session end and under the person-run CLI, only to a loopback collector, with no redirects or proxies and one deadline.
- Its hooks carry no `onFailure`, and always exit 0: an explicit exception to AGENTS.md's "fail closed", because telemetry is not a control.
- It never ships content.

The precedent is the platform's own session-manifest hook. The rejected alternatives:
- shipping from the agent's sandboxed CLI, which cannot write `~/.aidlc` and may not reach loopback;
- a background daemon, which adds moving parts;
- `onFailure: block`, which could stop a session from starting.

**4. The design §10 note,** dated 2026-10-20, Plan 4a. It records:
- `aidlc.bundle` and `aidlc.tier` are deferred to Plan 5, when skills produce bundles; the PR id is deferred to Plan 4b or 6.
- No second `session_manifest` is emitted; aidlc's start event joins with it on `session.key`.
- `aidlc check` and `aidlc ci` emit no OTel events, and there are no Mimir counters. Check results reach telemetry from the hook side only.
- Claude Code records carry no `ticket.key`, so joins use `session_key`.

**5. The codebase map and README** as listed under Files. Run `bin/aidlc check context-drift .`.
- [ ] **Step 4: Run the test and the checks, and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check`, `bin/aidlc check context-drift .` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `docs(observability): what is sent and never sent, the platform kit, runbooks, ADR 0003; design §10 note`.

### Task 8: Live evidence (controller, with the user's go-ahead at each step)

**Files:**
- Create: `docs/verification/<date>-telemetry-live.md`

- [ ] **Step 1: Check the stack, read-only.** Check that `curl -s 127.0.0.1:3100/ready` and `curl -s 127.0.0.1:9009/ready` return `ready`. If either returns 503, ask the user before running `docker compose restart loki mimir` from `PC/lab`.
- [ ] **Step 2: Run 1, with telemetry pointing at a closed port.**
  1. Build the `tests/harness_live/fixture.py` repository in a temporary directory, with a temporary `AIDLC_HOME_DIR` and `AIDLC_LOG_DIR`, and `AIDLC_TELEMETRY=on`.
  2. Render it, then set `harness.json` `telemetry.endpoint` to a closed loopback port.
  3. Run one short `claude -p --model haiku --setting-sources project,local --strict-mcp-config` session that makes one denied call (`git push`) and one allowed read.

  Expected:
  - the outbox holds an `aidlc.session.start`, at least one `aidlc.hook.decision` with `aidlc.rule=shell-deny`, and the allowed read;
  - `last.json` shows `collector unreachable`. Its `time` must be later than the session's last decision `ts`. That proves SessionEnd fired at a normal `-p` exit; record it either way.
- [ ] **Step 3: Run 2, live.** Re-render to the real endpoint and helper, then run the same session again. Expected: `last.json` shows `sent`, with a time later than the last decision and `sent` at least equal to the number of decisions. `aidlc telemetry status`, run with the same `AIDLC_HOME_DIR` and `AIDLC_LOG_DIR`, shows `last send: sent`.
- [ ] **Step 4: Confirm in Loki.**
  - Query `{service_name="aidlc"} | event_name="aidlc.hook.decision"` through Grafana's API (`/api/ds/query`, datasource uid `loki`; credentials only if the user provides a way) or `logcli`.
  - Expected: the records are present, with `session_key`, `event_name`, `tool_use_id` and `service_instance_id`.
  - `aidlc_rule` stays absent until the platform patch is applied; record that state.
  - Also replay one record whose timestamp is more than 1 hour old, through `aidlc telemetry flush`, into a fresh session stream, and confirm it arrives.
- [ ] **Step 5: Apply the kit, only if the user chooses to.** Re-run Step 4 and expect `aidlc_rule="shell-deny"`. Load the dashboard and the alerts, and record each panel's query result.
- [ ] **Step 6: Write the evidence.** Write `docs/verification/<date>-telemetry-live.md` with:
  - the commands;
  - the outbox entries (enumerated metadata only);
  - `last.json`;
  - the Loki results;
  - the patch state;
  - the SessionEnd-in-`-p` result;
  - what was not verified.

  Commit it in the plan's pull request.

---

## Self-review notes

- **Design §10 coverage:**

  | Design §10 row | Where |
  |---|---|
  | Correlation ids | `session.key` and `tool_use_id` on every decision; `ticket.key` via `vcs.ref.head.name` on aidlc records. `aidlc.bundle`, `aidlc.tier` and the PR id are deferred (Task 7 design note). |
  | Session start | Tasks 2–4 (`aidlc.session.start`, joined with the platform's `session_manifest` on `session.key`) |
  | Tool call, decision, deciding control | Tasks 2–4 (`aidlc.hook.decision`, with `aidlc.rule` as the deciding control; unattended flag) |
  | Check results and attempts | Task 4 (safe-read details) and Task 2 (`aidlc.check.result`). Not emitted by `aidlc check` or `aidlc ci` directly, and no Mimir counters: recorded as a gap. |
  | Tokens and cost | Claude Code native `api_request`, joined on `session_key` (Task 6) |
  | Paired metrics | Task 6 `metrics.yaml`. p95 time to green and approval time are recorded as not available, with reasons. |
  | Redaction | Global Constraints; Task 2 tests; `repo_url`; the resource allow-list; the platform strip |
  | Alerts | Task 6: fail-safe, retry limit, session cost, unattended denials. "Decisions stopped" is a recorded gap, covered locally by D4. |
  | Eval runs | Plan 4b |
  | Delivery measures | Plan 6 |
  | Retention and access | Task 7 README |
- **Review findings addressed:**
  - C1: Task 0, and closed ports in every test.
  - C2: per-session streams, oldest first, the age limit, and the Task 8 replay check.
  - C3: linear trimming, plus a timing test.
  - C4: per-record isolation, the `repo_url` `ValueError`, and long-line skipping.
  - I1: joins on `session_key`.
  - I2: no `onFailure`, and `timeout` 5.
  - I3: one deadline; the lock with a timeout; no I/O under the lock; no network at session start.
  - I4: the `override_rate` definition and names.
  - I5: "decisions stopped" is a recorded gap.
  - I6: instant, reduce, threshold; titles; conditions; ranges per rule.
  - I7: Task 0, and the cursor starting at the end of the log.
  - I8: known step names, and the safe reader with a FIFO test.
  - I9: resource allow-list, captured per session; `status` and `show` read-only.
  - I10: `repo_url` tightened; nothing raw persisted.
  - I11: the cursor tracks file identity.
  - I12: first run at the end of the log; 7-day expiry.
  - I13: a second dashboard provider.
  - I14: the unattended alert, `tool_use_id`, the p95 and approval gaps, retention, and the design note.
  - I15: tests made non-vacuous.
  - I16: `load_hooks`.
  - I17: files written out in full.
  - I18: the Task 8 two-run design.
  - Minors: the meta style, the port and pattern schema, `mkstemp`, `HTTPException`, rejected outcomes, git env stripping and `fsmonitor`, config clamping, doc amendments, exit codes, `__error__`, `ticket_key!=""`, absolute runbook URLs, session counting, pruning, `observedTimeUnixNano`, at-least-once wording, the check-result meaning, the live harness off by default, and the upgrade note.
- **Out of scope:**
  - traces and spans (Plan 4b nests headless runs with `TRACEPARENT`);
  - Mimir counters;
  - editing the platform;
  - emitting from `aidlc check` and `aidlc ci`.
