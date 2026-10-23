import contextlib
import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from tests.hook_loader import load_hook
from tests.unit.test_guard import GuardEnv

shim = load_hook("claude_shim")


def fake_dialect():
    """A Copilot-like dialect: camelCase payload, top-level permissionDecision."""
    def to_generic(payload, phase):
        return {"session": payload.get("sessionId"), "call": None, "tool": payload["toolName"],
                "args": payload.get("toolArgs") or {}, "cwd": payload.get("cwd") or os.getcwd()}

    def encode_pre(result, redact):
        if result["decision"] in ("ask", "deny"):
            return json.dumps({"permissionDecision": result["decision"],
                               "permissionDecisionReason": redact(f"[aidlc {result['rule']}] {result['reason']}")})
        return None

    return SimpleNamespace(phases=("pre",), to_generic=to_generic, encode_pre=encode_pre,
                           encode_post=lambda result, redact: None, error_exit=2)


def run(dialect, argv, stdin):
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(io.StringIO()):
        code = shim.run(argv, dialect)
    return code, out.getvalue()


class ShimDialectTest(unittest.TestCase):
    def test_claude_is_a_dialect_of_the_same_flow(self):
        self.assertEqual(shim.CLAUDE.phases, ("pre", "post", "post-failure"))
        self.assertIs(shim.CLAUDE.to_generic, shim.to_generic)
        self.assertEqual(shim.CLAUDE.error_exit, 2)

    def test_a_second_dialect_uses_the_same_flow(self):
        with GuardEnv():
            code, out = run(fake_dialect(), ["x", "pre"],
                            json.dumps({"sessionId": "s", "toolName": "shell", "toolArgs": {"command": "git push"}}))
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertEqual(body["permissionDecision"], "deny")
        self.assertIn("[aidlc shell-deny]", body["permissionDecisionReason"])

    def test_a_second_dialect_fails_closed_on_bad_input(self):
        with GuardEnv():
            code, out = run(fake_dialect(), ["x", "pre"], "not json")
        self.assertEqual((code, out), (2, ""))

    def test_a_phase_the_dialect_lacks_fails_closed(self):
        with GuardEnv():
            code, _ = run(fake_dialect(), ["x", "post"], "{}")
        self.assertEqual(code, 2)

    def test_a_dialect_without_an_error_exit_still_blocks(self):
        dialect = fake_dialect()
        del dialect.error_exit
        with GuardEnv():
            code, _ = run(dialect, ["x", "pre"], "not json")
        self.assertEqual(code, 2)
