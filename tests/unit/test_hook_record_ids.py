# tests/unit/test_hook_record_ids.py
"""The local hook record is matched to Claude Code's telemetry by tool_use_id (Anthropic: "tool_use_id
matches the tool_use_id passed to hooks, allowing correlation between OTel events and hook-captured
data"). Every record the shim writes must carry the session and tool-use ids it was given."""
import json
import os
import unittest

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
