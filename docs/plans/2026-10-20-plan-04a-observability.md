# Plan 4a: Observability. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The harness's own record (hook decisions, check results, session starts) reaches the platform's telemetry pipeline as enumerated metadata. Dashboards, alerts and a metric catalogue answer the guide's questions, and nothing secret or personal ever leaves the machine.

**Architecture:** The guard and post-check already write every decision, and every run of the one-command check, to `$AIDLC_LOG_DIR/decisions.jsonl`, outside the agent's sandbox. A new stdlib module, `core/hooks/telemetry.py`, runs only in two new hook phases, `session-start` and `session-end`, and in the person-run CLI `aidlc telemetry`. It turns new log lines into OTLP log records that carry only allow-listed enums, ids and counts. It queues them in a bounded outbox under `$AIDLC_HOME_DIR/telemetry/`, then sends that outbox to the loopback collector with a short deadline, using the platform's bearer-header helper.

Telemetry never blocks or fails a session. The guard's and post-check's decision paths stay network-free. Dashboards, alert rules and the metric catalogue live in `core/observability/`. Changes to the platform (the collector allow-list, alert provisioning and the dashboard file) are delivered as a documented kit for the platform owner, never applied by the framework.

**Tech Stack:** Python 3.12 standard library (`urllib.request`, `fcntl`, `json`), PyYAML and jsonschema on the CLI side only. OTLP/HTTP JSON (`/v1/logs`). Grafana 13 file provisioning. LogQL.

**Spec:**
- design §10 and §8, in `docs/design/2026-10-18-aidlc-framework-design.md`;
- ADR 0002 (`docs/adr/0002-github-trusted-ci.md`);
- user decisions of 2026-10-20 (Plan 4 split into 4a then 4b; telemetry stack checked read-only; platform changes only as proposed patches);
- the research notes in the session scratchpad `p4-research/` (guide §4, the platform contract and the integration map). The facts this plan relies on are restated below.

## Facts this plan relies on (verified 2026-10-20)

- **Collector.** OTLP/HTTP only, on `127.0.0.1:4318`, with bearer auth (401 without the header). The header comes from the helper at `/usr/local/lib/ai-lab/otel-headers.sh`, which prints one line: `{"Authorization": "Bearer <token>"}`. The request body limit is 8 MiB. Logs go to Loki and traces to Langfuse.
- **Allow-list.** On every non-cohort record (all of ours), the collector empties the log body and keeps only allow-listed attribute keys. `event.name` is kept. No `aidlc.*` key is kept until the platform owner adds one. The `vcs.ref.head.name` and `vcs.repository.url.full` keys are allow-listed, and the collector derives `branch`, `repo` and `ticket.key` from them.
- **Grafana.** Datasource uids are `loki` and `mimir`. There is no alert provisioning directory, but one under `PC/lab/grafana/provisioning/alerting/` would be mounted already. In LogQL, dots in attribute names become underscores, so `aidlc.rule` is queried as `aidlc_rule`. Claude Code's own records use `service_name="claude-code"`.
- **Claude Code 2.1.296.** It has the hook events `SessionStart` (payload `session_id`, `cwd`, `source`) and `SessionEnd` (`session_id`, `cwd`, `reason`). The SessionEnd budget defaults to 1.5 s and is raised by the hook's `timeout`. Hooks run in `-p` unless `--bare` is set.
- **Status.** The lab containers are up. Loki and Mimir answer `/ready` with 503 ("Ingester not ready"). A restart needs the user's OK (Task 8).

## Global Constraints

- **Dependencies.** Hooks use the standard library only. The CLI uses the standard library plus PyYAML and jsonschema. Add no new dependency.
- **The guard and post-check never use the network.** Only `core/hooks/telemetry.py` may, and only in the `session-start` and `session-end` phases or under `aidlc telemetry`.
- **Allowed destinations.** Telemetry goes only to a loopback endpoint (`127.0.0.1`, `localhost` or `[::1]`), over plain HTTP, with no redirects followed, no proxy, and a total deadline per call of `timeout_s` (policy default 3 s).
- **What leaves the machine.** Only the keys listed in `core/policy/telemetry.yaml` `events`, each with a validated value: an enum, an id, a count, a step-name list, or a version. These never leave, under any setting: a decision reason, a target, a command, a path, a prompt, tool output, a file content, a header value, a token.
- **Telemetry never blocks or fails a session.** The two telemetry phases always exit 0 with no stdout, whatever happens, while still declaring `onFailure: block` as `settings.rego` requires of every hook.
- **State lives under `$AIDLC_HOME_DIR/telemetry/`,** default `~/.aidlc/telemetry/`, which the agent sandbox cannot write. Refuse a symlinked state directory. Updates are taken under an `fcntl` lock. The outbox is bounded (`outbox_max_bytes`, default 5,000,000): the oldest records are dropped first and counted.
- **No platform file is edited by the framework.** Platform changes are a kit in `docs/observability/platform-patch.md` plus files under `core/observability/`.
- **Tests.**
  - Unit tests never touch the real `~/.aidlc`, `~/.claude` or the network. Only a loopback test server started by the test itself is allowed.
  - `make test` stays model-free.
  - Never change an assertion in a test older than this plan, except the two that this plan names as design changes:
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

1. **The collector is down, or slow.** The session ends within the hook timeout, the records stay in the outbox, and the outbox never grows beyond its cap. Pinned by Task 3 `test_flush_respects_deadline` and Task 2 `test_outbox_is_bounded`.
2. **A secret appears in a decision's target or reason.** Nothing of it is queued or sent, because only enumerated keys are built and the reason and target are never read. Pinned by Task 2 `test_a_decision_becomes_enumerated_metadata_only`.
3. **Two sessions end at the same time, or one crashes mid-append.** No record is shipped twice, none is lost, and a partial last line waits for its newline. Pinned by Task 2 `test_cursor_skips_shipped_and_partial_lines` and `test_concurrent_collect_queues_each_line_once`.
4. **The header helper is missing, slow, or prints junk.** Nothing is sent, nothing crashes, and the header value never reaches a file or stdout. Pinned by Task 3 `test_helper_failure_keeps_outbox_and_never_writes_the_header`.
5. **A redirect, a proxy, or a non-loopback endpoint.** The bearer header never reaches another host. Pinned by Task 3 `test_redirect_is_not_followed`, `test_proxy_env_is_ignored` and Task 1 `test_policy_refuses_a_non_loopback_endpoint`.

---

### Task 1: Telemetry policy and the harness's telemetry block

**Files:**
- Create: `core/policy/telemetry.yaml`, `core/schemas/telemetry.schema.json`
- Modify: `cli/aidlc/harness.py` (`harness_data` gains a `telemetry` block)
- Test: `tests/unit/test_telemetry_policy.py`

**Interfaces:**
- Produces:
  - `load_policy("telemetry")` returns a dict with these keys:
    - `enabled: bool`;
    - `endpoint: str`, loopback only;
    - `headers_helper: str | None`, an absolute path;
    - `timeout_s: float`;
    - `outbox_max_bytes: int`;
    - `budget_usd_per_session: float`;
    - `events: dict[str, list[str]]`;
    - `allowlist_pattern: str`.
  - `harness_data(repo)["telemetry"]` is `{"enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes"}`.

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

EXPECTED_EVENTS = {
    "aidlc.hook.decision": ["session.key", "aidlc.hook", "aidlc.decision", "aidlc.rule", "aidlc.tool",
                            "aidlc.harness.version"],
    "aidlc.check.result": ["session.key", "aidlc.check.result", "aidlc.check.failing_in_a_row",
                           "aidlc.check.failed_steps", "aidlc.check.retry_limit", "aidlc.harness.version"],
    "aidlc.session.start": ["session.key", "aidlc.session.source", "aidlc.harness.version"],
}


class TelemetryPolicyTest(unittest.TestCase):
    def test_policy_lists_the_events_and_their_keys(self):
        data = load_policy("telemetry")
        self.assertEqual(data["events"], EXPECTED_EVENTS)
        self.assertTrue(data["enabled"])
        self.assertEqual(data["endpoint"], "http://127.0.0.1:4318")
        self.assertEqual(data["headers_helper"], "/usr/local/lib/ai-lab/otel-headers.sh")

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

    def test_policy_refuses_a_non_loopback_endpoint(self):
        data = load_policy("telemetry")
        schema = policy._schema(policy.framework_root(), "telemetry")
        for endpoint in ("http://example.com:4318", "https://127.0.0.1:4318", "http://10.0.0.5:4318",
                         "http://127.0.0.1:4318/v1/logs", "http://localhost.evil.com:4318"):
            with self.subTest(endpoint=endpoint):
                bad = copy.deepcopy(data)
                bad["endpoint"] = endpoint
                self.assertTrue(policy._errors(schema, bad, "telemetry"))

    def test_harness_data_carries_the_telemetry_block(self):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 20))
            block = harness_data(root)["telemetry"]
        self.assertEqual(set(block), {"enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes"})
        self.assertEqual(block["endpoint"], "http://127.0.0.1:4318")
```

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_policy -v`. Expected: FAIL with `PolicyError: no schema telemetry.schema.json` or "not found".
- [ ] **Step 3: Write the policy and the schema.**

```yaml
# core/policy/telemetry.yaml
meta: {id: policy-telemetry, owner: "@harness-owners", review_by: "2027-04-20", guide: ["3.4", "3 step 7", "13.5"]}
# The harness's own telemetry (design §10). Only these keys leave the machine, each with a validated
# enum, id, count, step-name list or version. A reason, target, command, path, prompt, output or token never does.
enabled: true
endpoint: "http://127.0.0.1:4318"            # loopback only: the platform collector (OTLP/HTTP)
headers_helper: "/usr/local/lib/ai-lab/otel-headers.sh"   # prints {"Authorization": "Bearer <token>"}
timeout_s: 3                                  # total send deadline per hook call
outbox_max_bytes: 5000000                     # oldest records dropped first, and counted
budget_usd_per_session: 5                     # the cost alert's threshold (guide 3 step 7)
events:
  aidlc.hook.decision: [session.key, aidlc.hook, aidlc.decision, aidlc.rule, aidlc.tool, aidlc.harness.version]
  aidlc.check.result: [session.key, aidlc.check.result, aidlc.check.failing_in_a_row, aidlc.check.failed_steps,
                       aidlc.check.retry_limit, aidlc.harness.version]
  aidlc.session.start: [session.key, aidlc.session.source, aidlc.harness.version]
# The one line the platform owner adds to metadata-allowlist.yaml `patterns:` (docs/observability/platform-patch.md).
allowlist_pattern: '^aidlc\.(hook|decision|rule|tool|harness\.version|session\.source|check\.(result|failing_in_a_row|failed_steps|retry_limit))$'
```

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "telemetry",
  "type": "object",
  "additionalProperties": false,
  "required": ["meta", "enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes",
               "budget_usd_per_session", "events", "allowlist_pattern"],
  "properties": {
    "meta": {"$ref": "meta.schema.json"},
    "enabled": {"type": "boolean"},
    "endpoint": {"type": "string", "pattern": "^http://(127\\.0\\.0\\.1|localhost|\\[::1\\]):[0-9]{1,5}$"},
    "headers_helper": {"oneOf": [{"type": "null"}, {"type": "string", "pattern": "^/[A-Za-z0-9._/-]+$"}]},
    "timeout_s": {"type": "number", "minimum": 0.5, "maximum": 10},
    "outbox_max_bytes": {"type": "integer", "minimum": 10000, "maximum": 50000000},
    "budget_usd_per_session": {"type": "number", "exclusiveMinimum": 0},
    "events": {
      "type": "object",
      "minProperties": 1,
      "propertyNames": {"pattern": "^aidlc\\.[a-z]+(\\.[a-z_]+)*$"},
      "additionalProperties": {"type": "array", "minItems": 1, "uniqueItems": true,
                               "items": {"type": "string", "pattern": "^(session\\.key|aidlc\\.[a-z_.]+)$"}}
    },
    "allowlist_pattern": {"type": "string", "pattern": "^\\^aidlc\\\\\\..*\\$$"}
  }
}
```

Before relying on `{"$ref": "meta.schema.json"}`, read how the other schemas reference `meta`, for example `core/schemas/routing.schema.json`. Copy that exact form; if they inline the meta schema, inline it too.

- [ ] **Step 4: Add the telemetry block to `harness_data`.** In `cli/aidlc/harness.py`, inside `harness_data`, add to `data`:

```python
    tel = load_policy("telemetry")
    data["telemetry"] = {"enabled": bool(tel["enabled"]), "endpoint": tel["endpoint"],
                         "headers_helper": tel["headers_helper"], "timeout_s": tel["timeout_s"],
                         "outbox_max_bytes": tel["outbox_max_bytes"]}
```

The digest in `version` now covers the telemetry block, so every installed repository must re-render. That is expected: `judge_generated` and doctor report the stale files until it does.

- [ ] **Step 5: Run the tests and watch them pass.** Run the Step 2 command, then `bin/aidlc policy validate`, `bin/aidlc trace`, and `make test`. Expected: all pass. The golden settings fixture is unchanged by this task, because `harness.json` is not part of `settings.json`.
- [ ] **Step 6: Commit.** Stage explicit paths and commit with `feat(telemetry): policy for the harness's own telemetry; harness.json telemetry block (guide 3.4, 13.5)`.

### Task 2: The telemetry module: converting the log and the outbox (no network)

**Files:**
- Create: `core/hooks/telemetry.py`
- Test: `tests/unit/test_telemetry.py`

**Interfaces:**
- Consumes: the decision-log line shape written by `guard._log`, which has `ts`, `hook`, `session`, `call`, `harness`, `tool`, `target`, `decision`, `rule`, `reason`. Task 4's `check-attempts` records add `passed`, `failing_in_a_row` and `failed_steps`.
- Produces, in `core/hooks/telemetry.py`:
  - `EVENTS: dict[str, tuple[str, ...]]`, identical to the policy's `events`;
  - `home_dir()`, `log_dir()`, `state_dir()`, each returning `Path`;
  - `load_config(harness_file: Path | None = None) -> dict`, with keys `enabled`, `endpoint`, `headers_helper`, `timeout_s`, `outbox_max_bytes`;
  - `record_from_decision(rec: dict, context: dict | None = None) -> dict | None`, returning an outbox entry `{"event", "time", "attrs", "resource"}`;
  - `collect(max_bytes: int | None = None) -> int`;
  - `remember_session(payload: dict) -> None`;
  - `start_entry(payload: dict, version: str | None) -> dict | None`;
  - `enqueue(entries: list[dict]) -> None`;
  - `read_outbox() -> list[dict]`;
  - `dropped_count() -> int`;
  - `repo_url(raw: str) -> str | None`;
  - `resource_attributes() -> dict[str, str]`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry.py
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from tests.hook_loader import load_hook

telemetry = load_hook("telemetry")
SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"


def decision(**kw):
    rec = {"ts": "2026-10-20T09:12:31+00:00", "hook": "pre-tool-guard", "session": "s-1", "call": "toolu_1",
           "harness": "0.1.0+3fa9c1d2e4b5", "tool": "shell", "target": f"curl -H 'x: {SECRET}' /home/someone/x",
           "decision": "deny", "rule": "shell-deny", "reason": f"blocked {SECRET} in /home/someone/x"}
    rec.update(kw)
    return rec


class TelemetryBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "logs").mkdir()
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        os.environ.pop("AIDLC_TELEMETRY", None)
        os.environ.pop("OTEL_RESOURCE_ATTRIBUTES", None)

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def log(self, *records, partial=""):
        with (self.tmp / "logs" / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")
            fh.write(partial)


class ConvertTest(TelemetryBase):
    def test_a_decision_becomes_enumerated_metadata_only(self):
        self.log(decision())
        self.assertEqual(telemetry.collect(), 1)
        [entry] = telemetry.read_outbox()
        self.assertEqual(entry["event"], "aidlc.hook.decision")
        self.assertEqual(entry["attrs"], {"session.key": "s-1", "aidlc.hook": "pre-tool-guard",
                                          "aidlc.decision": "deny", "aidlc.rule": "shell-deny",
                                          "aidlc.tool": "shell", "aidlc.harness.version": "0.1.0+3fa9c1d2e4b5"})
        raw = (self.tmp / "home" / "telemetry" / "outbox.jsonl").read_text()
        for leak in (SECRET, "/home/someone", "curl", "blocked"):
            self.assertNotIn(leak, raw)

    def test_every_attribute_key_is_one_the_policy_lists(self):
        self.log(decision(), decision(hook="check-attempts", decision="pass", rule="check-recorded",
                                      passed=False, failing_in_a_row=2, failed_steps=["lint", "test"]))
        telemetry.collect()
        for entry in telemetry.read_outbox():
            self.assertLessEqual(set(entry["attrs"]), set(telemetry.EVENTS[entry["event"]]))

    def test_unknown_values_are_dropped_not_shipped(self):
        self.log(decision(hook="evil-hook"), decision(tool="rm -rf /", rule="Bad Rule!", decision="maybe"))
        telemetry.collect()
        entries = telemetry.read_outbox()
        self.assertEqual(len(entries), 1)                   # the unknown hook is not an event at all
        self.assertEqual(entries[0]["attrs"].get("aidlc.tool"), None)
        self.assertEqual(entries[0]["attrs"].get("aidlc.rule"), None)
        self.assertEqual(entries[0]["attrs"].get("aidlc.decision"), None)

    def test_check_attempts_becomes_a_check_result(self):
        self.log(decision(hook="check-attempts", decision="flag", rule="retry-limit", passed=False,
                          failing_in_a_row=3, failed_steps=["lint", "test", "../etc"]))
        telemetry.collect()
        [entry] = telemetry.read_outbox()
        self.assertEqual(entry["event"], "aidlc.check.result")
        self.assertEqual(entry["attrs"]["aidlc.check.result"], "FAIL")
        self.assertEqual(entry["attrs"]["aidlc.check.failing_in_a_row"], 3)
        self.assertEqual(entry["attrs"]["aidlc.check.failed_steps"], "lint,test")
        self.assertEqual(entry["attrs"]["aidlc.check.retry_limit"], "true")

    def test_cursor_skips_shipped_and_partial_lines(self):
        self.log(decision(), decision(call="toolu_2"), partial='{"hook": "pre-tool-guard", "sess')
        self.assertEqual(telemetry.collect(), 2)
        self.assertEqual(telemetry.collect(), 0)
        with (self.tmp / "logs" / "decisions.jsonl").open("a") as fh:
            fh.write('ion": "s-2", "decision": "allow", "rule": "read", "tool": "read"}\n')
        self.assertEqual(telemetry.collect(), 1)
        self.assertEqual(len(telemetry.read_outbox()), 3)

    def test_a_replaced_log_restarts_from_the_beginning(self):
        self.log(decision(), decision())
        telemetry.collect()
        (self.tmp / "logs" / "decisions.jsonl").write_text(json.dumps(decision()) + "\n")
        self.assertEqual(telemetry.collect(), 1)

    def test_malformed_and_huge_lines_are_skipped(self):
        self.log(decision(), partial="not json\n[1,2]\n" + "x" * 70_000 + "\n")
        self.assertEqual(telemetry.collect(), 1)

    def test_concurrent_collect_queues_each_line_once(self):
        self.log(*[decision(call=f"toolu_{n}") for n in range(200)])
        threads = [threading.Thread(target=telemetry.collect) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(telemetry.read_outbox()), 200)

    def test_outbox_is_bounded(self):
        with mock.patch.object(telemetry, "DEFAULT_OUTBOX_MAX_BYTES", 2_000):
            telemetry.enqueue([telemetry.record_from_decision(decision(call=f"toolu_{n}")) for n in range(100)])
        size = (self.tmp / "home" / "telemetry" / "outbox.jsonl").stat().st_size
        self.assertLessEqual(size, 2_000)
        self.assertGreater(telemetry.dropped_count(), 0)

    def test_a_symlinked_state_directory_is_refused(self):
        target = self.tmp / "elsewhere"
        target.mkdir()
        (self.tmp / "home").mkdir()
        (self.tmp / "home" / "telemetry").symlink_to(target)
        self.log(decision())
        with self.assertRaises(OSError):
            telemetry.collect()
        self.assertEqual(list(target.iterdir()), [])

    def test_repo_url_never_keeps_credentials(self):
        self.assertEqual(telemetry.repo_url("https://user:tok123@github.com/o/r.git"), "https://github.com/o/r.git")
        self.assertEqual(telemetry.repo_url("git@github.com:o/r.git"), "git@github.com:o/r.git")
        self.assertIsNone(telemetry.repo_url("https://github.com/o/r\nInjected: x"))
        self.assertIsNone(telemetry.repo_url(""))

    def test_resource_attributes_come_from_the_environment_and_never_override_the_service(self):
        with mock.patch.dict(os.environ, {"OTEL_RESOURCE_ATTRIBUTES":
                                          "team=lab,cost_center=lab,service.name=evil,bad key=x,note=a%20b"}):
            attrs = telemetry.resource_attributes()
        self.assertEqual(attrs["service.name"], "aidlc")
        self.assertEqual(attrs["team"], "lab")
        self.assertNotIn("bad key", attrs)
        self.assertNotIn("note", attrs)                     # values outside the safe set are dropped
```

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry -v`. Expected: FAIL, because `core/hooks/telemetry.py` does not exist.
- [ ] **Step 3: Write `core/hooks/telemetry.py`.** Write the conversion and the outbox now; Task 3 adds sending.

```python
#!/usr/bin/env python3
"""The harness's own telemetry (guide 3.4, 3 step 7, 13.5; design §10).

The guard and the post-check write every decision to $AIDLC_LOG_DIR/decisions.jsonl and never use
the network. This module runs only in the session-start and session-end hook phases and under the
person-run `aidlc telemetry`. It turns new log lines into OTLP log records that carry enumerated
metadata only (core/policy/telemetry.yaml `events`), queues them in a bounded outbox under
$AIDLC_HOME_DIR/telemetry/, and sends the outbox to the loopback collector with a short deadline.
A reason, target, command, path, prompt, output or token never leaves the machine."""
from __future__ import annotations

import fcntl
import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
SERVICE_NAME = "aidlc"
SCOPE_NAME = "aidlc.harness"
DEFAULT_OUTBOX_MAX_BYTES = 5_000_000
READ_MAX_BYTES = 2_000_000          # decision-log bytes converted per call; the rest waits for the next
LINE_MAX = 65_536
MAX_STEPS = 20
EVENTS = {
    "aidlc.hook.decision": ("session.key", "aidlc.hook", "aidlc.decision", "aidlc.rule", "aidlc.tool",
                            "aidlc.harness.version"),
    "aidlc.check.result": ("session.key", "aidlc.check.result", "aidlc.check.failing_in_a_row",
                           "aidlc.check.failed_steps", "aidlc.check.retry_limit", "aidlc.harness.version"),
    "aidlc.session.start": ("session.key", "aidlc.session.source", "aidlc.harness.version"),
}
CONTEXT_KEYS = ("vcs.ref.head.name", "vcs.repository.url.full")   # the collector derives branch, repo, ticket.key
SLUG = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
SESSION = re.compile(r"[A-Za-z0-9_-]{1,128}")
VERSION = re.compile(r"[0-9A-Za-z.+-]{1,64}")
BRANCH = re.compile(r"(?!-)[A-Za-z0-9._/-]{1,200}")
SAFE_URL = re.compile(r"[A-Za-z0-9@:._/~+-]{1,300}")
RESOURCE_KEY = re.compile(r"[a-z][a-z0-9_.]{0,63}")
RESOURCE_VALUE = re.compile(r"[A-Za-z0-9_.@-]{1,64}")
HOOKS = frozenset({"pre-tool-guard", "post-tool-check", "check-attempts"})
DECISIONS = frozenset({"allow", "ask", "deny", "flag", "pass"})
TOOLS = frozenset({"read", "edit", "shell", "external", "mcp", "unknown"})
SOURCES = frozenset({"startup", "resume", "clear", "compact", "fork"})


def home_dir() -> Path:
    return Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()


def log_dir() -> Path:
    return Path(os.environ.get("AIDLC_LOG_DIR") or "~/.aidlc/logs").expanduser()


def state_dir() -> Path:
    return home_dir() / "telemetry"


def load_config(harness_file: Path | None = None) -> dict:
    """The rendered harness.json `telemetry` block. Missing, unreadable or malformed: disabled.
    AIDLC_TELEMETRY=off disables it whatever the file says."""
    off = {"enabled": False, "endpoint": "", "headers_helper": None, "timeout_s": 3.0,
           "outbox_max_bytes": DEFAULT_OUTBOX_MAX_BYTES}
    if os.environ.get("AIDLC_TELEMETRY", "").lower() == "off":
        return off
    try:
        data = json.loads((harness_file or HERE / "harness.json").read_text(encoding="utf-8"))
        block = data["telemetry"]
        config = {"enabled": block["enabled"] is True, "endpoint": str(block["endpoint"]),
                  "headers_helper": block["headers_helper"], "timeout_s": float(block["timeout_s"]),
                  "outbox_max_bytes": int(block["outbox_max_bytes"])}
    except (OSError, ValueError, KeyError, TypeError):
        return off
    if config["headers_helper"] is not None and not isinstance(config["headers_helper"], str):
        return off
    return config


def _match(pattern: re.Pattern, value) -> str | None:
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _member(allowed: frozenset, value) -> str | None:
    return value if isinstance(value, str) and value in allowed else None


def _nanos(ts) -> str:
    try:
        return str(int(datetime.fromisoformat(str(ts)).timestamp() * 1_000_000_000))
    except (TypeError, ValueError):
        return "0"


def _clean(attrs: dict) -> dict:
    return {k: v for k, v in attrs.items() if v is not None}


def resource_attributes() -> dict[str, str]:
    """service.name=aidlc plus the session's OTEL_RESOURCE_ATTRIBUTES (team, cost_center, ai.cohort,
    env), when key and value are both in the safe set. service.name is never overridden."""
    out = {}
    for pair in os.environ.get("OTEL_RESOURCE_ATTRIBUTES", "").split(","):
        key, sep, value = pair.partition("=")
        key, value = key.strip(), value.strip()
        if sep and RESOURCE_KEY.fullmatch(key) and RESOURCE_VALUE.fullmatch(value):
            out[key] = value
    out["service.name"] = SERVICE_NAME
    return out


def repo_url(raw: str) -> str | None:
    """The origin URL without credentials, or None when it is not a plain URL."""
    if not raw or not SAFE_URL.fullmatch(raw):
        return None
    if "://" in raw:
        parts = urlsplit(raw)
        if not parts.hostname:
            return None
        host = parts.hostname + (f":{parts.port}" if parts.port else "")
        return urlunsplit((parts.scheme, host, parts.path, "", ""))
    return raw                                         # scp form: user@host:path carries no secret


def record_from_decision(rec: dict, context: dict | None = None) -> dict | None:
    """One decision-log line as an outbox entry. Only enumerated keys are built; the line's reason
    and target are never read. None when the line is not a harness decision."""
    hook = _member(HOOKS, rec.get("hook"))
    if hook is None:
        return None
    common = {"session.key": _match(SESSION, rec.get("session")),
              "aidlc.harness.version": _match(VERSION, rec.get("harness"))}
    if hook == "check-attempts":
        failing = rec.get("failing_in_a_row")
        steps = rec.get("failed_steps") if isinstance(rec.get("failed_steps"), list) else []
        names = [s for s in steps if isinstance(s, str) and SLUG.fullmatch(s)][:MAX_STEPS]
        attrs = {**common,
                 "aidlc.check.result": "PASS" if rec.get("passed") is True else "FAIL",
                 "aidlc.check.failing_in_a_row": failing if isinstance(failing, int) and 0 <= failing < 10_000 else None,
                 "aidlc.check.failed_steps": ",".join(names) or None,
                 "aidlc.check.retry_limit": "true" if rec.get("rule") == "retry-limit" else "false"}
        event = "aidlc.check.result"
    else:
        attrs = {**common, "aidlc.hook": hook, "aidlc.decision": _member(DECISIONS, rec.get("decision")),
                 "aidlc.rule": _match(SLUG, rec.get("rule")), "aidlc.tool": _member(TOOLS, rec.get("tool"))}
        event = "aidlc.hook.decision"
    attrs = _clean(attrs)
    attrs.update(_context_attrs(context))
    return {"event": event, "time": _nanos(rec.get("ts")), "attrs": attrs, "resource": resource_attributes()}


def _context_attrs(context: dict | None) -> dict:
    if not isinstance(context, dict):
        return {}
    out = {"vcs.ref.head.name": _match(BRANCH, context.get("branch")),
           "vcs.repository.url.full": repo_url(str(context.get("remote") or ""))}
    return _clean(out)


@contextmanager
def _locked():
    """Exclusive lock on the state directory; refuses a symlinked state directory or lock."""
    state = state_dir()
    if state.is_symlink():
        raise OSError(f"{state} is a symlink; telemetry does not follow it")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield state
    finally:
        os.close(fd)


def _read_int(path: Path) -> int:
    try:
        value = int(path.read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0
    return value if value >= 0 else 0


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def _session_context(state: Path, session) -> dict | None:
    name = _match(SESSION, session)
    if name is None:
        return None
    try:
        data = json.loads((state / "sessions" / f"{name}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def collect(max_bytes: int | None = None) -> int:
    """Move complete new decision-log lines into the outbox. Returns the number of entries queued."""
    log = log_dir() / "decisions.jsonl"
    with _locked() as state:
        if log.is_symlink():
            return 0
        cursor = _read_int(state / "cursor")
        try:
            size = log.stat().st_size
        except FileNotFoundError:
            return 0
        if cursor > size:
            cursor = 0                               # the log was replaced or truncated
        with log.open("rb") as fh:
            fh.seek(cursor)
            chunk = fh.read(max_bytes or READ_MAX_BYTES)
        end = chunk.rfind(b"\n")
        if end < 0:
            return 0
        entries, contexts = [], {}
        for raw in chunk[:end + 1].split(b"\n"):
            if not raw or len(raw) > LINE_MAX:
                continue
            try:
                rec = json.loads(raw.decode("utf-8"))
            except ValueError:
                continue
            if not isinstance(rec, dict):
                continue
            session = rec.get("session")
            if session not in contexts:
                contexts[session] = _session_context(state, session)
            entry = record_from_decision(rec, contexts[session])
            if entry is not None:
                entries.append(entry)
        _append(state, entries)
        _write_atomic(state / "cursor", str(cursor + end + 1))
        return len(entries)


def enqueue(entries: list[dict]) -> None:
    with _locked() as state:
        _append(state, [e for e in entries if e])


def _append(state: Path, entries: list[dict]) -> None:
    if not entries:
        return
    limit = _outbox_limit()
    path = state / "outbox.jsonl"
    lines = _outbox_lines(state) + [json.dumps(e, sort_keys=True) + "\n" for e in entries]
    dropped = 0
    while lines and sum(len(l.encode()) for l in lines) > limit:
        lines.pop(0)                                 # oldest first
        dropped += 1
    _write_atomic(path, "".join(lines))
    if dropped:
        _write_atomic(state / "dropped", str(_read_int(state / "dropped") + dropped))


def _outbox_limit() -> int:
    try:
        return int(load_config().get("outbox_max_bytes") or DEFAULT_OUTBOX_MAX_BYTES)
    except (TypeError, ValueError):
        return DEFAULT_OUTBOX_MAX_BYTES


def _outbox_lines(state: Path) -> list[str]:
    path = state / "outbox.jsonl"
    if path.is_symlink():
        raise OSError(f"{path} is a symlink; telemetry does not follow it")
    try:
        return [l if l.endswith("\n") else l + "\n" for l in path.read_text(encoding="utf-8").splitlines()]
    except FileNotFoundError:
        return []


def read_outbox() -> list[dict]:
    with _locked() as state:
        out = []
        for line in _outbox_lines(state):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if isinstance(entry, dict) and entry.get("event") in EVENTS:
                out.append(entry)
        return out


def dropped_count() -> int:
    return _read_int(state_dir() / "dropped")
```

`_outbox_limit` reads `load_config()`, which reads `harness.json` next to the module. In tests, no `harness.json` exists, so the limit is `DEFAULT_OUTBOX_MAX_BYTES`, the value `test_outbox_is_bounded` patches. Read the final section of this task for `remember_session` and `start_entry`.

- [ ] **Step 4: Add the session context.** Add these functions to the same file:

```python
import subprocess  # noqa: E402  (keep with the other imports at the top of the file)


def _git(cwd: str, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-C", cwd, *args],
                             capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def remember_session(payload: dict) -> None:
    """At session start: the branch and origin, kept for the session's records."""
    session = _match(SESSION, payload.get("session_id"))
    cwd = payload.get("cwd")
    if session is None or not isinstance(cwd, str) or not os.path.isdir(cwd):
        return
    context = {"branch": _git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD"),
               "remote": _git(cwd, "config", "--get", "remote.origin.url")}
    with _locked() as state:
        sessions = state / "sessions"
        if sessions.is_symlink():
            raise OSError(f"{sessions} is a symlink; telemetry does not follow it")
        sessions.mkdir(exist_ok=True, mode=0o700)
        _write_atomic(sessions / f"{session}.json", json.dumps(context))


def start_entry(payload: dict, version: str | None) -> dict | None:
    session = _match(SESSION, payload.get("session_id"))
    if session is None:
        return None
    attrs = _clean({"session.key": session, "aidlc.session.source": _member(SOURCES, payload.get("source")),
                    "aidlc.harness.version": _match(VERSION, version)})
    with _locked() as state:
        attrs.update(_context_attrs(_session_context(state, session)))
    return {"event": "aidlc.session.start", "time": str(int(datetime.now().timestamp() * 1_000_000_000)),
            "attrs": attrs, "resource": resource_attributes()}
```

Move `import subprocess` to the top import block. Then add these tests to `ConvertTest`:

```python
    def test_session_context_adds_branch_and_origin(self):
        from tests.helpers import TempRepo, git
        with TempRepo({"a.txt": "a\n"}) as root:
            git(root, "checkout", "-q", "-b", "feat/SHIP-7-x")
            git(root, "remote", "add", "origin", "https://u:secret@github.com/o/r.git")
            telemetry.remember_session({"session_id": "s-1", "cwd": str(root)})
        self.log(decision())
        telemetry.collect()
        [entry] = telemetry.read_outbox()
        self.assertEqual(entry["attrs"]["vcs.ref.head.name"], "feat/SHIP-7-x")
        self.assertEqual(entry["attrs"]["vcs.repository.url.full"], "https://github.com/o/r.git")
        self.assertNotIn("secret", json.dumps(entry))

    def test_start_entry_carries_the_source_and_version(self):
        entry = telemetry.start_entry({"session_id": "s-9", "source": "startup"}, "0.1.0+abc")
        self.assertEqual(entry["event"], "aidlc.session.start")
        self.assertEqual(entry["attrs"]["aidlc.session.source"], "startup")
        self.assertIsNone(telemetry.start_entry({"session_id": "bad id!"}, "0.1.0"))
```

- [ ] **Step 5: Run the tests and watch them pass.** Run the Step 2 command. Expected: all tests pass. Then run `make test`.
- [ ] **Step 6: Commit.** Stage explicit paths and commit with `feat(telemetry): decision log to an enumerated, bounded outbox (no network)`.

### Task 3: Sending: OTLP/JSON, the header helper and the deadline

**Files:**
- Modify: `core/hooks/telemetry.py`
- Test: `tests/unit/test_telemetry_send.py`

**Interfaces:**
- Produces, in `core/hooks/telemetry.py`:
  - `otlp_payload(entries: list[dict]) -> bytes`;
  - `headers_from_helper(helper: str | None, timeout: float = 2.0) -> dict | None`. `None` means "do not send"; `{}` means no helper is configured.
  - `send(body: bytes, endpoint: str, headers: dict, timeout: float) -> bool`;
  - `flush(config: dict, deadline_s: float | None = None) -> tuple[int, str]`. The outcome is one of `"disabled"`, `"empty"`, `"sent"`, `"headers helper failed"`, `"collector unreachable"` or `"endpoint refused"`.
  - `last_result() -> dict`;
  - `run_phase(phase: str, payload: dict) -> int`, which always returns 0.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry_send.py
import http.server
import json
import os
import shutil
import stat
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


class SendTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        Collector.received, Collector.delay, Collector.status, Collector.redirect_to = [], 0.0, 200, None
        self.server = serve()
        self.helper = self.helper_script('print(\'{"Authorization": "Bearer t0ken"}\')')
        telemetry.enqueue([telemetry.start_entry({"session_id": "s-1", "source": "startup"}, "0.1.0+abc")])

    def tearDown(self):
        self.server.shutdown()
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def helper_script(self, body: str, code: int = 0) -> str:
        path = self.tmp / f"helper-{len(list(self.tmp.glob('helper-*')))}.py"
        path.write_text(f"#!/usr/bin/env python3\nimport sys\n{body}\nsys.exit({code})\n")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        return str(path)

    def config(self, **kw):
        port = self.server.server_address[1]
        base = {"enabled": True, "endpoint": f"http://127.0.0.1:{port}", "headers_helper": self.helper,
                "timeout_s": 2.0, "outbox_max_bytes": 5_000_000}
        base.update(kw)
        return base

    def test_flush_posts_otlp_json_to_v1_logs_with_the_helper_header(self):
        sent, outcome = telemetry.flush(self.config())
        self.assertEqual((sent, outcome), (1, "sent"))
        [(path, headers, body)] = Collector.received
        self.assertEqual(path, "/v1/logs")
        self.assertEqual(headers["Authorization"], "Bearer t0ken")
        self.assertEqual(headers["Content-Type"], "application/json")
        doc = json.loads(body)
        resource = doc["resourceLogs"][0]["resource"]["attributes"]
        self.assertIn({"key": "service.name", "value": {"stringValue": "aidlc"}}, resource)
        [record] = doc["resourceLogs"][0]["scopeLogs"][0]["logRecords"]
        self.assertEqual(record["eventName"], "aidlc.session.start")
        keys = {a["key"] for a in record["attributes"]}
        self.assertIn("event.name", keys)
        self.assertEqual(telemetry.read_outbox(), [])

    def test_unreachable_collector_keeps_the_outbox(self):
        self.server.shutdown()
        self.server.server_close()
        sent, outcome = telemetry.flush(self.config())
        self.assertEqual((sent, outcome), (0, "collector unreachable"))
        self.assertEqual(len(telemetry.read_outbox()), 1)

    def test_a_rejected_request_keeps_the_outbox(self):
        Collector.status = 401
        self.assertEqual(telemetry.flush(self.config())[1], "collector unreachable")
        self.assertEqual(len(telemetry.read_outbox()), 1)

    def test_helper_failure_keeps_outbox_and_never_writes_the_header(self):
        for helper in (self.helper_script("print('Bearer leaked-value')"),
                       self.helper_script('print(\'{"Bad Header": "leaked-value"}\')'),
                       self.helper_script('print(\'{"Authorization": "leaked-value"}\')', code=1),
                       self.helper_script("import time; time.sleep(5)"),
                       str(self.tmp / "missing-helper")):
            with self.subTest(helper=helper):
                sent, outcome = telemetry.flush(self.config(headers_helper=helper))
                self.assertEqual((sent, outcome), (0, "headers helper failed"))
        self.assertEqual(Collector.received, [])
        for path in (self.tmp / "home").rglob("*"):
            if path.is_file():
                self.assertNotIn("leaked-value", path.read_text(errors="replace"))

    def test_redirect_is_not_followed(self):
        other = serve()
        try:
            Collector.redirect_to = f"http://127.0.0.1:{other.server_address[1]}/v1/logs"
            sent, outcome = telemetry.flush(self.config())
            self.assertEqual(outcome, "collector unreachable")
            self.assertEqual(len(Collector.received), 1)        # the first server only, never the second
        finally:
            other.shutdown()

    def test_proxy_env_is_ignored(self):
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9"}):
            self.assertEqual(telemetry.flush(self.config())[1], "sent")

    def test_flush_respects_deadline(self):
        Collector.delay = 5
        start = time.monotonic()
        sent, outcome = telemetry.flush(self.config(timeout_s=1.0), deadline_s=1.0)
        self.assertLess(time.monotonic() - start, 3.5)
        self.assertEqual(sent, 0)
        self.assertEqual(len(telemetry.read_outbox()), 1)

    def test_a_non_loopback_endpoint_is_refused_without_a_request(self):
        sent, outcome = telemetry.flush(self.config(endpoint="http://example.com:4318"))
        self.assertEqual((sent, outcome), (0, "endpoint refused"))

    def test_disabled_sends_nothing(self):
        self.assertEqual(telemetry.flush(self.config(enabled=False)), (0, "disabled"))
        self.assertEqual(Collector.received, [])

    def test_large_outboxes_go_in_batches(self):
        telemetry.enqueue([telemetry.start_entry({"session_id": f"s-{n}"}, "v1") for n in range(1200)])
        sent, outcome = telemetry.flush(self.config())
        self.assertEqual((sent, outcome), (1201, "sent"))
        self.assertGreaterEqual(len(Collector.received), 3)

    def test_last_result_records_the_outcome_without_headers(self):
        telemetry.flush(self.config())
        result = telemetry.last_result()
        self.assertEqual(result["outcome"], "sent")
        self.assertNotIn("t0ken", json.dumps(result))


class RunPhaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_run_phase_never_raises_and_returns_zero(self):
        for payload in ({}, {"session_id": None}, {"session_id": "s", "cwd": "/nonexistent"}, {"x": object()}):
            for phase in ("session-start", "session-end", "unknown"):
                self.assertEqual(telemetry.run_phase(phase, payload), 0)

    def test_disabled_writes_no_state(self):
        with mock.patch.dict(os.environ, {"AIDLC_TELEMETRY": "off"}):
            telemetry.run_phase("session-start", {"session_id": "s-1", "source": "startup"})
        self.assertFalse((self.tmp / "home" / "telemetry").exists())
```

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_send -v`. Expected: FAIL, with `AttributeError: ... has no attribute 'flush'`.
- [ ] **Step 3: Implement sending.** Add the following to `core/hooks/telemetry.py`, and add `time`, `urllib.error` and `urllib.request` to the imports:

```python
BATCH = 500                                      # records per request: well under the collector's 8 MiB
HEADER_NAME = re.compile(r"[A-Za-z0-9-]{1,64}")
LOOPBACK = re.compile(r"http://(127\.0\.0\.1|localhost|\[::1\]):[0-9]{1,5}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401 - never follow: a redirect could carry the header away
        return None


_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect)


def _value(v) -> dict:
    return {"intValue": str(v)} if isinstance(v, int) and not isinstance(v, bool) else {"stringValue": str(v)}


def otlp_payload(entries: list[dict]) -> bytes:
    groups: dict[str, list[dict]] = {}
    for entry in entries:
        groups.setdefault(json.dumps(entry.get("resource") or {}, sort_keys=True), []).append(entry)
    resource_logs = []
    for resource_key, items in groups.items():
        resource = json.loads(resource_key)
        records = [{"timeUnixNano": e["time"], "eventName": e["event"],
                    "attributes": [{"key": "event.name", "value": {"stringValue": e["event"]}}]
                                  + [{"key": k, "value": _value(v)} for k, v in sorted(e["attrs"].items())]}
                   for e in items]
        resource_logs.append({"resource": {"attributes": [{"key": k, "value": {"stringValue": v}}
                                                          for k, v in sorted(resource.items())]},
                              "scopeLogs": [{"scope": {"name": SCOPE_NAME}, "logRecords": records}]})
    return json.dumps({"resourceLogs": resource_logs}).encode("utf-8")


def headers_from_helper(helper: str | None, timeout: float = 2.0) -> dict | None:
    """The helper's one-line JSON object of headers. None (do not send) on any failure; the value is
    never logged or stored."""
    if helper is None:
        return {}
    try:
        out = subprocess.run([helper], capture_output=True, timeout=timeout, check=False, stdin=subprocess.DEVNULL)
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


def send(body: bytes, endpoint: str, headers: dict, timeout: float) -> bool:
    request = urllib.request.Request(endpoint + "/v1/logs", data=body, method="POST",
                                     headers={**headers, "Content-Type": "application/json"})
    try:
        with _OPENER.open(request, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _record(state: Path, sent: int, outcome: str) -> None:
    _write_atomic(state / "last.json", json.dumps({"time": int(time.time()), "sent": sent, "outcome": outcome}))


def last_result() -> dict:
    try:
        data = json.loads((state_dir() / "last.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def flush(config: dict, deadline_s: float | None = None) -> tuple[int, str]:
    """Send the outbox in batches until it is empty, the deadline passes, or a request fails."""
    if not config.get("enabled"):
        return 0, "disabled"
    if not LOOPBACK.fullmatch(str(config.get("endpoint") or "")):
        return 0, "endpoint refused"
    budget = float(deadline_s if deadline_s is not None else config.get("timeout_s") or 3.0)
    stop = time.monotonic() + budget
    with _locked() as state:
        lines = _outbox_lines(state)
        if not lines:
            return 0, "empty"
        headers = headers_from_helper(config.get("headers_helper"), timeout=min(2.0, budget))
        if headers is None:
            _record(state, 0, "headers helper failed")
            return 0, "headers helper failed"
        sent, outcome = 0, "sent"
        while sent < len(lines):
            remaining = stop - time.monotonic()
            if remaining <= 0.05:
                outcome = "collector unreachable"
                break
            batch = []
            for line in lines[sent:sent + BATCH]:
                try:
                    batch.append(json.loads(line))
                except ValueError:
                    continue
            if batch and not send(otlp_payload(batch), config["endpoint"], headers, timeout=remaining):
                outcome = "collector unreachable"
                break
            sent += len(lines[sent:sent + BATCH])
        _write_atomic(state / "outbox.jsonl", "".join(lines[sent:]))
        _record(state, sent, outcome)
        return sent, outcome


def run_phase(phase: str, payload: dict) -> int:
    """The session-start and session-end hook phases. Always 0, never prints: telemetry must
    never block or fail a session."""
    try:
        config = load_config()
        if not config["enabled"] or phase not in ("session-start", "session-end"):
            return 0
        if phase == "session-start":
            remember_session(payload)
            version = None
            try:
                version = json.loads((HERE / "harness.json").read_text(encoding="utf-8")).get("version")
            except (OSError, ValueError, AttributeError):
                pass
            entry = start_entry(payload, version)
            if entry is not None:
                enqueue([entry])
        collect()
        flush(config)
    except Exception:  # noqa: BLE001 - telemetry never blocks or fails a session
        pass
    return 0
```

**Batches and the "sent" count.** A batch whose lines all fail to parse is dropped, not retried. That's acceptable, because such lines can't be sent anyway, and `sent` counts them as consumed. `test_large_outboxes_go_in_batches` expects 1201 sent across at least three requests: 500, 500 and 201.

- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, the Task 2 command, and `make test`. Expected: all pass.
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): OTLP/JSON to the loopback collector; helper headers; no redirects or proxies; deadline`.

### Task 4: Hook wiring: session phases, check details, rendering and doctor

**Files:**
- Modify:
  - `core/hooks/claude_shim.py`: the `session-start` and `session-end` phases, and the harness version on post records;
  - `core/hooks/post_check.py`: add `record_check_details(event) -> tuple[dict | None, dict]`; `record_check` keeps its exact contract;
  - `cli/aidlc/adapters/claude_code.py`: `HOOK_FILES` gains `telemetry.py`; SessionStart and SessionEnd hooks;
  - `cli/aidlc/checks/doctor.py`: D4 covers the two session events;
  - `cli/aidlc/hookbridge.py`: `hooks()` also loads `telemetry`;
  - `core/hooks/README.md`, `docs/harness/hooks.md`;
  - `tests/unit/test_claude_settings.py`: the hook-file set gains `telemetry.py`. This is a design change named in this plan.
  - `tests/fixtures/render/claude-code/settings.node.json`: regenerated with the renderer.
- Test: `tests/unit/test_session_hooks.py`

**Interfaces:**
- Consumes `telemetry.run_phase` (Task 3).
- Produces:
  - the rendered `.claude/settings.json` gains `"SessionStart": [{"hooks": [_hook("session-start")]}]` and `"SessionEnd": [{"hooks": [_hook("session-end")]}]`;
  - `check-attempts` decision records gain `passed`, `failing_in_a_row` and `failed_steps`;
  - post records gain `harness`, the harness version;
  - `hooks().telemetry`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_session_hooks.py
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from aidlc.adapters import get_adapter
from aidlc.checks.doctor import check_d4
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git, run_cli


def rendered(root):
    code, out, err = run_cli("render", "--tool", "claude-code", str(root))
    assert code == 0, out + err
    return json.loads((root / ".claude/settings.json").read_text())


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
        return root

    def shim(self, root, phase, stdin):
        return subprocess.run([sys.executable, str(root / ".aidlc/hooks/claude_shim.py"), phase],
                              input=stdin, capture_output=True, text=True, timeout=30, cwd=root)

    def test_settings_carry_both_session_hooks(self):
        root = self.repo()
        settings = rendered(root)
        for event, phase in (("SessionStart", "session-start"), ("SessionEnd", "session-end")):
            with self.subTest(event=event):
                [entry] = settings["hooks"][event]
                [hook] = entry["hooks"]
                self.assertTrue(hook["command"].endswith(f"claude_shim.py\" {phase}"))
                self.assertEqual(hook["onFailure"], "block")
                self.assertNotIn("matcher", entry)
        self.assertTrue((root / ".aidlc/hooks/telemetry.py").is_file())

    def test_session_phases_always_exit_zero_and_print_nothing(self):
        root = self.repo()
        rendered(root)
        for phase in ("session-start", "session-end"):
            for stdin in ("", "not json", "[1]", json.dumps({"session_id": "s-1", "cwd": str(root)})):
                with self.subTest(phase=phase, stdin=stdin[:10]):
                    done = self.shim(root, phase, stdin)
                    self.assertEqual(done.returncode, 0)
                    self.assertEqual(done.stdout, "")

    def test_session_start_queues_the_start_event_when_the_collector_is_down(self):
        root = self.repo()
        rendered(root)
        harness = json.loads((root / ".aidlc/hooks/harness.json").read_text())
        harness["telemetry"]["endpoint"] = "http://127.0.0.1:9"        # nothing listens on port 9
        harness["telemetry"]["headers_helper"] = None
        (root / ".aidlc/hooks/harness.json").write_text(json.dumps(harness))
        self.shim(root, "session-start", json.dumps({"session_id": "s-1", "cwd": str(root), "source": "startup"}))
        outbox = (self.tmp / "home/telemetry/outbox.jsonl").read_text()
        self.assertIn("aidlc.session.start", outbox)

    def test_post_records_carry_the_harness_version_and_check_details(self):
        post_check = __import__("tests.hook_loader", fromlist=["load_hook"]).load_hook("post_check")
        self.assertTrue(hasattr(post_check, "record_check_details"))
        result, details = post_check.record_check_details({"tool": "read"})
        self.assertIsNone(result)
        self.assertEqual(details, {})

    def test_doctor_d4_requires_the_session_hooks(self):
        root = self.repo()
        settings = rendered(root)
        self.assertEqual([f for f in check_d4(root, settings) if "Session" in f.message], [])
        del settings["hooks"]["SessionEnd"]
        messages = [f.message for f in check_d4(root, settings)]
        self.assertTrue(any("D4 SessionEnd" in m for m in messages), messages)
```

The repository's `Finding` type uses `.message`; check `cli/aidlc/checks/findings.py` and adapt the attribute name if it differs. The assertions stay the same.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_session_hooks -v`. Expected: FAIL, with a `KeyError: 'SessionStart'` or "no telemetry.py".
- [ ] **Step 3: Implement the changes.**

**1. Add session phases to `claude_shim.py`.** At the top of `main`, before the existing `try:`, add:

```python
    phase = argv[1] if len(argv) > 1 else ""
    if phase in ("session-start", "session-end"):
        try:                                   # telemetry: never blocks, never prints (Plan 4a)
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            import telemetry  # noqa: E402
            try:
                payload = json.loads(sys.stdin.read())
            except ValueError:
                payload = {}
            return telemetry.run_phase(phase, payload if isinstance(payload, dict) else {})
        except Exception:  # noqa: BLE001
            return 0
```

Then:
- Update the docstring's usage line to `pre|post|post-failure|session-start|session-end`.
- In the post branch, read the version once, as `version = _harness_version(guard)`, and pass it to both `guard._log` calls.
- Use `post_check.record_check_details(event)` there. Log `{**attempt, **details}` for `check-attempts`.

```python
def _harness_version(guard) -> str | None:
    try:
        return guard.load_harness().get("version")
    except Exception:  # noqa: BLE001 - a missing version never changes a decision
        return None
```

**2. In `post_check.py`,** rename the body of `record_check` to `record_check_details(event) -> tuple[dict | None, dict]`. It returns `(result, details)`, where `details = {"passed": passed, "failing_in_a_row": failures, "failed_steps": _failed_steps(root)}` whenever `result` is not None, and `{}` otherwise. Then:

```python
def record_check(event: dict) -> dict | None:
    return record_check_details(event)[0]


def _failed_steps(root: Path) -> list[str]:
    """Names of the failed steps in the check's own record, read without following links."""
    try:
        fd = os.open(root / ".check" / "result.json", os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as fh:
            data = json.loads(fh.read(1_000_001)[:1_000_000].decode("utf-8"))
    except (OSError, ValueError):
        return []
    steps = data.get("steps") if isinstance(data, dict) else None
    return [s["name"] for s in steps or [] if isinstance(s, dict) and s.get("status") == "FAIL"
            and isinstance(s.get("name"), str)][:20]
```

**3. In `claude_code.py`:**
- set `HOOK_FILES = ("guard.py", "post_check.py", "claude_shim.py", "telemetry.py")`;
- in `render_permissions`'s `"hooks"` dict, add `"SessionStart": [{"hooks": [_hook("session-start")]}]` and `"SessionEnd": [{"hooks": [_hook("session-end")]}]`.

**4. In `doctor.check_d4`,** after the existing loop, add:

```python
    for event, phase in (("SessionStart", "session-start"), ("SessionEnd", "session-end")):
        entries = _get(settings, "hooks", event, default=[])
        hooks = [h for e in (entries if isinstance(entries, list) else []) if isinstance(e, dict)
                 for h in e.get("hooks", []) if isinstance(h, dict)
                 and "claude_shim.py" in str(h.get("command", "")) and str(h.get("command", "")).rsplit(" ", 1)[-1] == phase]
        if not hooks:
            out.append(_fail(SETTINGS, f"D4 {event} has no claude_shim.py {phase} hook (telemetry)"))
        elif any(h.get("onFailure") != "block" for h in hooks):
            out.append(_fail(SETTINGS, f"D4 {event} hook must set onFailure: block"))
```

**5. In `hookbridge.hooks()`,** also load `telemetry` as `_load("telemetry", "aidlc_telemetry")`, and return it as `SimpleNamespace(guard=..., post_check=..., telemetry=...)`.

**6. The two named design-change test edits:**
- In `tests/unit/test_claude_settings.py`, the expected hook-file set gains `".aidlc/hooks/telemetry.py"`.
- Regenerate `tests/fixtures/render/claude-code/settings.node.json` with the renderer, using the helper the test module already uses (`scaffolded()`, then `render_permissions`). The diff must be exactly the two new hook events.

**7. Docs.**
- `core/hooks/README.md`: document the two phases, `telemetry.py`, and the `AIDLC_TELEMETRY=off` switch in the environment table.
- `docs/harness/hooks.md`: add a short "Telemetry" section that links to `docs/observability/README.md` (written in Task 7).
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then:
  - `make test`;
  - `make policy-test` with `AIDLC_TOOLS_DIR` set, since `settings.rego` must accept the new hooks;
  - `bin/aidlc render --tool claude-code --check .`;
  - `git diff $(git merge-base main HEAD) -- tests/ | grep '^-.*assert'`, which must show only the named change.

  Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `feat(hooks): session-start and session-end telemetry phases; check details and harness version in the decision log`.

### Task 5: `aidlc telemetry status | flush | show` and doctor D15

**Files:**
- Create: `cli/aidlc/commands/telemetry_cmd.py`, and register it in `cli/aidlc/commands/__init__.py`
- Modify: `cli/aidlc/checks/doctor.py` (add `check_d15`, called from `run_doctor`)
- Test: `tests/unit/test_telemetry_cmd.py`

**Interfaces:**
- Consumes `hooks().telemetry` (`collect`, `read_outbox`, `flush`, `last_result`, `dropped_count`) and `load_policy("telemetry")`.
- Produces the CLI:
  - `aidlc telemetry status` exits 0, or 1 if records were dropped or the helper is missing while telemetry is enabled.
  - `aidlc telemetry flush` exits 0 on sent, empty or disabled, and 1 when records are kept.
  - `aidlc telemetry show [--limit N]` exits 0 and prints JSON lines.
  - Usage errors exit 2.
- Doctor D15 warns, and never fails.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_telemetry_cmd.py
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc.checks.doctor import check_d15
from tests.helpers import run_cli

SECRET = "AKIA" + "ABCDEFGHIJKLMNOP"


class TelemetryCmdTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "logs").mkdir()
        self.env = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": str(self.tmp / "home"),
                                                "AIDLC_LOG_DIR": str(self.tmp / "logs")})
        self.env.start()
        with (self.tmp / "logs/decisions.jsonl").open("w") as fh:
            fh.write(json.dumps({"ts": "2026-10-20T09:00:00+00:00", "hook": "pre-tool-guard", "session": "s-1",
                                 "tool": "shell", "decision": "deny", "rule": "shell-deny",
                                 "target": SECRET, "reason": SECRET, "harness": "0.1.0+abc"}) + "\n")

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_show_prints_exactly_what_would_leave_and_nothing_secret(self):
        code, out, _ = run_cli("telemetry", "show")
        self.assertEqual(code, 0)
        [line] = [l for l in out.splitlines() if l.strip()]
        self.assertEqual(json.loads(line)["event"], "aidlc.hook.decision")
        self.assertNotIn(SECRET, out)

    def test_flush_with_the_collector_down_keeps_records_and_exits_1(self):
        with mock.patch("aidlc.commands.telemetry_cmd._config",
                        return_value={"enabled": True, "endpoint": "http://127.0.0.1:9", "headers_helper": None,
                                      "timeout_s": 1.0, "outbox_max_bytes": 5_000_000}):
            code, out, err = run_cli("telemetry", "flush")
        self.assertEqual(code, 1)
        self.assertIn("kept", out + err)

    def test_status_reports_the_outbox_and_last_result(self):
        run_cli("telemetry", "show")
        code, out, _ = run_cli("telemetry", "status")
        self.assertIn("outbox: 1 record", out)
        self.assertIn("endpoint: http://127.0.0.1:4318", out)

    def test_d15_warns_about_drops_and_a_missing_helper(self):
        (self.tmp / "home/telemetry").mkdir(parents=True)
        (self.tmp / "home/telemetry/dropped").write_text("7")
        with mock.patch("aidlc.checks.doctor._telemetry_policy",
                        return_value={"enabled": True, "headers_helper": str(self.tmp / "missing")}):
            findings = check_d15()
        levels = {f.level for f in findings}
        self.assertEqual(levels, {"WARN"})
        text = " ".join(f.message for f in findings)
        self.assertIn("7 record(s) dropped", text)
        self.assertIn("header helper", text)
```

Before writing these tests, check `cli/aidlc/checks/findings.py` for the exact `Finding` level constant ("WARN" or "warn") and attribute names. Use the module's own `_warn` helper in D15.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_telemetry_cmd -v`. Expected: FAIL, because the command doesn't exist.
- [ ] **Step 3: Write `telemetry_cmd.py`.**

```python
"""aidlc telemetry: inspect and send the harness's own telemetry (guide 3.4; design §10). A person's
command: run it outside an agent session (the agent's sandbox cannot write ~/.aidlc)."""
from __future__ import annotations

import argparse
import json
import sys

from ..cli import command
from ..hookbridge import hooks
from ..policy import PolicyError, load_policy

KEYS = ("enabled", "endpoint", "headers_helper", "timeout_s", "outbox_max_bytes")


def _config() -> dict:
    data = load_policy("telemetry")
    config = {k: data[k] for k in KEYS}
    import os
    if os.environ.get("AIDLC_TELEMETRY", "").lower() == "off":
        config["enabled"] = False
    return config


def _run(args: argparse.Namespace) -> int:
    tel = hooks().telemetry
    try:
        config = _config()
        tel.collect()
        if args.action == "show":
            for entry in tel.read_outbox()[: args.limit]:
                print(json.dumps(entry, sort_keys=True))
            return 0
        if args.action == "flush":
            sent, outcome = tel.flush(config)
            kept = len(tel.read_outbox())
            print(f"telemetry: {outcome}; {sent} sent, {kept} kept")
            return 0 if outcome in ("sent", "empty", "disabled") else 1
        entries = tel.read_outbox()
        last = tel.last_result()
        print(f"telemetry: {'enabled' if config['enabled'] else 'disabled'}")
        print(f"endpoint: {config['endpoint']}")
        print(f"header helper: {config['headers_helper'] or 'none'}")
        print(f"outbox: {len(entries)} record(s); dropped: {tel.dropped_count()}")
        print(f"last send: {last.get('outcome', 'never')}")
        return 1 if tel.dropped_count() else 0
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

Move `import os` to the top of the file. Register the module in `cli/aidlc/commands/__init__.py`, keeping the existing import order style.

Then write `check_d15` in `doctor.py`:

```python
def _telemetry_policy() -> dict:
    return load_policy("telemetry")


def check_d15() -> list[Finding]:
    """D15 telemetry: warnings only (telemetry never fails a check)."""
    out = []
    try:
        data = _telemetry_policy()
    except PolicyError as exc:
        return [_warn("core/policy/telemetry.yaml", f"D15 telemetry policy unreadable: {exc}")]
    if not data.get("enabled"):
        return out
    helper = data.get("headers_helper")
    if helper and not os.access(helper, os.X_OK):
        out.append(_warn(helper, "D15 the telemetry header helper is missing or not executable; records wait in the outbox"))
    dropped = hooks().telemetry.dropped_count()
    if dropped:
        out.append(_warn("~/.aidlc/telemetry", f"D15 {dropped} record(s) dropped from a full outbox; run aidlc telemetry flush"))
    return out
```

Call it from `run_doctor` after D14, matching how the other checks are appended. Add D15 to `docs/harness/doctor.md`.

- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command and `make test`. Expected: all pass.
- [ ] **Step 5: Commit.** Commit with `feat(telemetry): aidlc telemetry status|flush|show; doctor D15 (warnings only)`.

### Task 6: The metric catalogue, dashboard and alert rules

**Files:**
- Create:
  - `core/observability/metrics.yaml`;
  - `core/observability/grafana/aidlc-harness.json`;
  - `core/observability/grafana/alerting/aidlc.yaml`;
  - `docs/observability/runbooks.md`.
- Modify: `cli/aidlc/trace.py` (`collect` also scans `core/observability/*.yaml` `meta.guide`, kind `observability`), `tests/unit/test_trace.py` (a new test only).
- Test: `tests/unit/test_observability_assets.py`

**Interfaces:** Consumes `load_policy("telemetry")["events"]`. Produces the files that Task 7's platform kit copies.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_observability_assets.py
import json
import re
import unittest
from pathlib import Path

import yaml

from aidlc.paths import framework_root
from aidlc.policy import load_policy

OBS = framework_root() / "core" / "observability"
RUNBOOKS = framework_root() / "docs" / "observability" / "runbooks.md"


def known_labels() -> set[str]:
    events = load_policy("telemetry")["events"]
    keys = {k for keys in events.values() for k in keys}
    return {k.replace(".", "_") for k in keys} | {"event_name", "service_name", "session_key", "ticket_key",
                                                   "branch", "repo", "team", "cost_usd", "decision", "tool_name"}


def queries(dashboard: dict) -> list[str]:
    return [t["expr"] for p in dashboard["panels"] for t in p.get("targets", []) if "expr" in t]


class ObservabilityAssetsTest(unittest.TestCase):
    def test_dashboard_uses_lab_datasources_and_known_labels_only(self):
        dash = json.loads((OBS / "grafana/aidlc-harness.json").read_text())
        self.assertEqual(dash["uid"], "aidlc-harness")
        for panel in dash["panels"]:
            for target in panel.get("targets", []):
                self.assertIn(target["datasource"]["uid"], {"loki", "mimir"})
        for expr in queries(dash):
            with self.subTest(expr=expr[:60]):
                self.assertRegex(expr, r'service_name="(aidlc|claude-code)"')
                for label in re.findall(r"\b(aidlc_[a-z_]+)\b", expr):
                    self.assertIn(label, known_labels())

    def test_every_alert_has_threshold_window_owner_and_runbook(self):
        doc = yaml.safe_load((OBS / "grafana/alerting/aidlc.yaml").read_text())
        rules = [r for g in doc["groups"] for r in g["rules"]]
        self.assertEqual({r["uid"] for r in rules},
                         {"aidlc-fail-safe", "aidlc-retry-limit", "aidlc-session-cost", "aidlc-decisions-stopped"})
        anchors = set(re.findall(r"^## (aidlc-[a-z0-9-]+)$", RUNBOOKS.read_text(), re.M))
        for rule in rules:
            with self.subTest(rule=rule["uid"]):
                self.assertIn("for", rule)
                self.assertIn("owner", rule["labels"])
                anchor = rule["annotations"]["runbook_url"].rsplit("#", 1)[-1]
                self.assertIn(anchor, anchors)
                exprs = [d["model"].get("expr", "") for d in rule["data"]]
                self.assertTrue(any(exprs))

    def test_cost_alert_threshold_is_the_policy_budget(self):
        doc = yaml.safe_load((OBS / "grafana/alerting/aidlc.yaml").read_text())
        [rule] = [r for g in doc["groups"] for r in g["rules"] if r["uid"] == "aidlc-session-cost"]
        threshold = [d for d in rule["data"] if d["refId"] == "C"][0]["model"]["conditions"][0]["evaluator"]["params"][0]
        self.assertEqual(threshold, load_policy("telemetry")["budget_usd_per_session"])

    def test_metric_catalogue_entries_have_owner_source_and_action(self):
        doc = yaml.safe_load((OBS / "metrics.yaml").read_text())
        self.assertEqual(doc["meta"]["id"], "observability-metrics")
        names = {m["id"] for m in doc["metrics"]}
        self.assertTrue({"first_attempt_green_rate", "retries_per_task", "denial_rate", "override_rate",
                         "asks_per_task", "cost_per_successful_task", "approval_time"} <= names)
        for metric in doc["metrics"]:
            with self.subTest(metric=metric["id"]):
                for key in ("definition", "source", "owner", "read_with", "action", "status"):
                    self.assertIn(key, metric)
                self.assertIn(metric["status"], {"dashboard", "query", "not-available"})
```

Add this test to `tests/unit/test_trace.py`:

```python
    def test_observability_files_are_traced(self):
        from aidlc.trace import collect
        kinds = {e.kind for e in collect(framework_root())}   # adapt to collect()'s real signature
        self.assertIn("observability", kinds)
```

Read `cli/aidlc/trace.py` and the existing tests first, and adapt the call to `collect()`'s real signature and element type. The assertion stays the same.

- [ ] **Step 2: Run the tests and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets tests.unit.test_trace -v`. Expected: FAIL, because the files are missing.
- [ ] **Step 3: Write the files.**

**`core/observability/metrics.yaml`** starts with `meta: {id: observability-metrics, owner: "@harness-owners", review_by: "2027-04-20", guide: ["3.4", "12.11", "12.12"]}`. It has one entry per metric, each with `id`, `definition`, `source`, `owner`, `read_with`, `action`, `status`, and `query` where the status is `dashboard` or `query`. These are the entries:

| id | definition | source | read_with | status |
|---|---|---|---|---|
| `first_attempt_green_rate` | Tasks (`ticket.key`) whose first `aidlc.check.result` is PASS, divided by tasks with any check result | `aidlc.check.result` | `retries_per_task` | `query` (LogQL by `ticket_key`; the dashboard shows the per-task first result) |
| `retries_per_task` | FAIL check results per `ticket.key` | `aidlc.check.result` | `first_attempt_green_rate` | `dashboard` |
| `denial_rate` | `aidlc.decision="deny"` divided by all pre-tool-guard decisions | `aidlc.hook.decision` | `override_rate` | `dashboard` |
| `override_rate` | Pre-tool-guard `ask` decisions, divided by the asks a person approved. Approvals come from Claude Code `tool_decision` events with `decision="accept"` and `decision_source="user"` for the same `session_key`. | `aidlc.hook.decision` and `claude-code` `tool_decision` | `denial_rate` | `query` |
| `asks_per_task` | `aidlc.decision="ask"` per `ticket.key` | `aidlc.hook.decision` | `approval_time` | `dashboard` |
| `approval_time` | Time from an ask to the person's answer | — | `asks_per_task` | `not-available`. Claude Code's events carry no wait time, so this is recorded as a gap. |
| `cost_per_successful_task` | The sum of `cost_usd` per `ticket.key` (Claude Code `api_request`) over tasks with a PASS check result | `claude-code` `api_request` plus `aidlc.check.result` | `retries_per_task` | `query` (two LogQL queries joined on `ticket_key` in the dashboard) |
| `retry_limit_hits` | `aidlc.check.retry_limit="true"` | `aidlc.check.result` | `retries_per_task` | `dashboard` |
| `fail_safe_blocks` | `aidlc.rule="fail-safe"` | `aidlc.hook.decision` | `denial_rate` | `dashboard` |

Every entry also gets:
- `owner: "@harness-owners"`;
- `action`: what a person does when the number moves. Make it specific, for example "a first-attempt green rate falling two weeks running: review the failing step and the harness version".

**`core/observability/grafana/aidlc-harness.json`** follows the platform style: `uid: "aidlc-harness"`, `title: "aidlc harness"`, `tags: ["aidlc"]`, `schemaVersion: 39`, a `team` template variable like `agent-flow.json`'s, and `time: {"from": "now-7d", "to": "now"}`. It has these panels, each with a `loki` datasource `{"type": "loki", "uid": "loki"}`:
1. "Decisions by rule and outcome": `sum by (aidlc_rule, aidlc_decision) (count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | team=~"$team" [$__range]))`
2. "Denial rate": `sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_decision="deny" | team=~"$team" [$__range])) / sum(count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_hook="pre-tool-guard" | team=~"$team" [$__range]))`
3. "Asks per task": `sum by (ticket_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.hook.decision" | aidlc_decision="ask" | team=~"$team" [$__range]))`
4. "Check results": `sum by (aidlc_check_result) (count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | team=~"$team" [$__range]))`
5. "Retries per task": `sum by (ticket_key) (count_over_time({service_name="aidlc"} | event_name="aidlc.check.result" | aidlc_check_result="FAIL" | team=~"$team" [$__range]))`
6. "Retry-limit hits and fail-safe blocks": two targets, each a `count_over_time` with `aidlc_check_retry_limit="true"` and `aidlc_rule="fail-safe"` respectively.
7. "Cost per task": `sum by (ticket_key) (sum_over_time({service_name="claude-code"} | event_name="api_request" | team=~"$team" | unwrap cost_usd [$__range]))`
8. "Sessions by harness version": `sum by (aidlc_harness_version) (count_over_time({service_name="aidlc"} | event_name="aidlc.session.start" | team=~"$team" [$__range]))`

**`core/observability/grafana/alerting/aidlc.yaml`** is in Grafana file-provisioning format, `apiVersion: 1`. It has one group, `{orgId: 1, name: aidlc, folder: aidlc, interval: 5m, rules: [...]}`, with these four rules:

| uid | A (expression, datasource `loki`) | condition C | `for` |
|---|---|---|---|
| `aidlc-fail-safe` | `sum(count_over_time({service_name="aidlc"} \| event_name="aidlc.hook.decision" \| aidlc_rule="fail-safe" [15m])) or vector(0)` | `> 0` | `0m` |
| `aidlc-retry-limit` | `sum(count_over_time({service_name="aidlc"} \| event_name="aidlc.check.result" \| aidlc_check_retry_limit="true" [15m])) or vector(0)` | `> 0` | `0m` |
| `aidlc-session-cost` | `max(sum by (session_key) (sum_over_time({service_name="claude-code"} \| event_name="api_request" \| unwrap cost_usd [1h])))` | `> 5` | `0m` |
| `aidlc-decisions-stopped` | A: `sum(count_over_time({service_name="claude-code"} \| event_name="tool_decision" [6h])) or vector(0)`. B: `sum(count_over_time({service_name="aidlc"} \| event_name="aidlc.hook.decision" [6h])) or vector(0)`. C (math): `$A > 0 && $B == 0` | | `30m` |

Rules A, B and C use the standard Grafana model:
- each query is `{refId, relativeTimeRange: {from: 21600, to: 0}, datasourceUid: loki, model: {expr, refId, queryType: "range"}}`;
- the threshold is `{refId: C, datasourceUid: __expr__, model: {type: threshold, expression: A, conditions: [{evaluator: {type: gt, params: [<n>]}}], refId: C}}`;
- the math condition is `{type: math, expression: "$A > 0 && $B == 0"}`.

Every rule has `labels: {owner: harness-owners, severity: warning}`, `annotations: {summary, runbook_url: "docs/observability/runbooks.md#<anchor>"}`, `noDataState: OK` and `execErrState: Error`. The cost threshold must equal `budget_usd_per_session` (5); the test pins it.

**`docs/observability/runbooks.md`** has one section per alert. Each heading is exactly the rule uid, so the anchor equals it: `## aidlc-fail-safe`, `## aidlc-retry-limit`, `## aidlc-session-cost` and `## aidlc-decisions-stopped`. Each section gives the threshold, the window, the owner, what it means, the first three things to check, and how to close it.

The decisions-stopped section must say that hook decisions arrive at session end, so a long session can trigger it briefly. The six-hour window absorbs this.

**`cli/aidlc/trace.py`:** in `collect`, add `core/observability/*.yaml` with `meta.guide` and kind `observability`, mirroring the `core/ci/*/setup.yaml` block. Then run `bin/aidlc trace`. `docs/traceability.md` gains the new rows; commit it.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `bin/aidlc trace --check` and `make test`. Expected: all pass.
- [ ] **Step 5: Commit.** Commit with `feat(observability): metric catalogue, Grafana dashboard and alert rules with runbooks (guide 3.4, 12.11)`.

### Task 7: The platform kit, docs and ADR 0003

**Files:**
- Create:
  - `docs/observability/README.md`;
  - `docs/observability/platform-patch.md`;
  - `docs/adr/0003-telemetry-hook-network.md`.
- Modify:
  - `docs/codebase-map.md` (areas: `core/hooks/telemetry.py`, `core/observability/`, `cli/aidlc/commands/telemetry_cmd.py`; "Where common changes go": a new telemetry key);
  - `docs/design/2026-10-18-aidlc-framework-design.md` §10 (a note that `aidlc.bundle` and `aidlc.tier` are deferred to Plan 5, when skills produce bundles; that the PR id is added by Plan 4b or 6; and that the framework does not emit a second `session_manifest`);
  - `README.md` (docs list).
- Test: `tests/unit/test_observability_assets.py` (add one test).

- [ ] **Step 1: Write the failing test.** Add it to `ObservabilityAssetsTest`:

```python
    def test_platform_patch_quotes_the_policy_allowlist_pattern(self):
        text = (framework_root() / "docs/observability/platform-patch.md").read_text()
        self.assertIn(load_policy("telemetry")["allowlist_pattern"], text)
        for name in ("aidlc-harness.json", "alerting/aidlc.yaml", "render_lookups", "force-recreate otel-collector"):
            self.assertIn(name, text)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_observability_assets -v`. Expected: FAIL, because the file is missing.
- [ ] **Step 3: Write the docs.** Use short sentences, British spelling, and "you"; link to sources rather than copying values.

1. **`docs/observability/README.md`** covers:
   - **what is sent**: the three events and their keys, linked to `core/policy/telemetry.yaml`;
   - **what is never sent**: the list in Global Constraints;
   - **when it is sent**: the session-start and session-end hooks, and `aidlc telemetry flush`;
   - **where it waits**: the outbox, its cap, and dropped counts;
   - **how to inspect it**: `aidlc telemetry show`, and turning it off with `AIDLC_TELEMETRY=off`;
   - **what is not emitted**: events for checks a person runs outside a session, and for GitHub CI runs (their records are artifacts);
   - **joining on `ticket.key`**: the branch naming it relies on;
   - **the dashboard, the alerts and the metric catalogue.**

   It should also say that, until the platform patch is applied, records arrive with `event.name` and the contract keys only.
2. **`docs/observability/platform-patch.md`** is the kit for the platform owner. It applies nothing itself, and it has five numbered steps, each with the exact file and command:
   1. Add the `allowlist_pattern` line, quoted from the policy, under `patterns:` in `PC/policy/telemetry/metadata-allowlist.yaml`.
   2. Run `cd PC && uv run python -m tools.render_lookups`.
   3. Copy `core/observability/grafana/alerting/aidlc.yaml` to `PC/lab/grafana/provisioning/alerting/aidlc.yaml`, and decide the contact point.
   4. Add the dashboard: either copy `core/observability/grafana/aidlc-harness.json` into `PC/grafana/dashboards/`, or add it to `PC/tools/grafana_dashboards.py`, which is the platform's own convention. Note `disableDeletion`.
   5. Run `docker compose up -d --force-recreate otel-collector` and restart Grafana from `PC/lab` (runbook `docs/runbooks/lab-deployment.md`).

   Add a verification section:
   - `aidlc telemetry flush`;
   - then a LogQL query in Grafana Explore: `{service_name="aidlc"} | event_name="aidlc.hook.decision"`;
   - checking that `aidlc_rule` is present.

   Also record the Loki/Mimir `/ready` 503 finding of 2026-10-20 as a platform note.
3. **`docs/adr/0003-telemetry-hook-network.md`**, with Status, Context, Decision and Consequences. Its decision:
   - The guard and post-check stay network-free.
   - One telemetry module may use the network, only in the session hooks and the person-run CLI, only to a loopback collector, with no redirects or proxies and a deadline. It always exits 0.
   - It never ships content.

   The platform's own session-manifest hook is the precedent. The ADR records the alternatives rejected:
   - shipping from the agent's sandboxed CLI, which cannot write `~/.aidlc` and may not reach loopback;
   - a background daemon, which is more moving parts.
4. **The codebase map, the design note and the README** as listed under Files. Run `bin/aidlc check context-drift .`.
- [ ] **Step 4: Run the test and the checks, and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check`, `bin/aidlc check context-drift .` and `make test`. Expected: all pass.
- [ ] **Step 5: Commit.** Commit with `docs(observability): what is sent and never sent, the platform kit, runbooks, ADR 0003`.

### Task 8: Live evidence (controller, with the user's go-ahead at each step)

**Files:**
- Create: `docs/verification/<date>-telemetry-live.md`

- [ ] **Step 1: Restart Loki and Mimir, with the user's OK.** Ask first. Then, from `PC/lab`, run `docker compose restart loki mimir` and wait until `curl -s 127.0.0.1:3100/ready` and `curl -s 127.0.0.1:9009/ready` both return `ready`. If they still return 503, record the output and stop. Telemetry then waits in the outbox, which Step 3 proves anyway.
- [ ] **Step 2: Run one live session.** Build the `tests/harness_live/fixture.py` repository in a temporary directory, with a temporary `AIDLC_HOME_DIR` and `AIDLC_LOG_DIR`. Render it, then run one short `claude -p --model haiku --setting-sources project,local --strict-mcp-config` session that makes one denied call (`git push`) and one allowed read. Expected:
  - the outbox gains a `aidlc.session.start` entry, at least one `aidlc.hook.decision` with `aidlc.rule=shell-deny`, and a matching decision;
  - after session end, `aidlc telemetry status` shows "last send: sent" (or records kept, if the collector is down).
- [ ] **Step 3: Confirm in Loki.** Query `{service_name="aidlc"} | event_name="aidlc.hook.decision"` through Grafana's API (`/api/ds/query`, using the `loki` datasource uid) or `logcli`, if it exists. Expected: the record is present, with `session_key` and `event_name`. `aidlc_rule` is absent until the platform patch is applied: record that exact state.
- [ ] **Step 4: Apply the platform kit, only if the user chooses to.** Re-run Step 3 and expect `aidlc_rule="shell-deny"`. Load the dashboard and record a screenshot or the panel query results.
- [ ] **Step 5: Write the evidence.** Write `docs/verification/<date>-telemetry-live.md` with the commands, the outbox entries (enumerated metadata only), the Loki results, the patch state, and what was not verified. Commit it through the plan's pull request.

---

## Self-review notes

- **Design §10 coverage:**

  | Design §10 row | Where |
  |---|---|
  | Correlation ids | `session.key` on every event; `ticket.key` derived by the collector from `vcs.ref.head.name`. `aidlc.bundle` and `aidlc.tier` are deferred to Plan 5 (Task 7 design note). The PR id goes to Plan 4b or 6. |
  | Session start | Task 4 (`aidlc.session.start`, joined with the platform's `session_manifest` on `session.key`; no second manifest) |
  | Tool call, decision, deciding control | Tasks 2–4 (`aidlc.hook.decision`, with `aidlc.rule` as the deciding control) |
  | Check results and attempts | Task 4 (`check-attempts` details) and Task 2 (`aidlc.check.result`). Checks a person runs outside a session, and GitHub CI runs, are not emitted (Task 7 doc). |
  | Tokens and cost | Claude Code native (`api_request`), joined on `session_key` and `ticket_key` (Task 6) |
  | Paired metrics | Task 6 `metrics.yaml`. Approval time is recorded as not available. |
  | Redaction | Global Constraints, Task 2 tests, and the platform strip |
  | Alerts | Task 6 (fail-safe, retry limit, cost, decisions stopped) |
  | Eval runs | Plan 4b |
  | Delivery measures | Plan 6 (`aidlc metrics`, deferred by the user) |
  | Retention and access | Platform-owned (Loki 720h, Langfuse 30 days), documented in Task 7 |
- **Open questions, decided here:**
  - "Override" is defined as an ask a person approved (Task 6).
  - The guide's "alert when decisions stop" is implemented over a six-hour window, because shipping happens at session end.
- **Out of scope:**
  - traces and spans (Plan 4b's eval runner nests headless sessions with `TRACEPARENT`);
  - Mimir counters (aidlc metrics come from Loki queries, so nothing depends on Mimir);
  - editing the platform.
