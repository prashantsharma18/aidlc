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
