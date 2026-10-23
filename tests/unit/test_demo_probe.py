# tests/unit/test_demo_probe.py
"""The demo's clean-harness probe (docs/demo/probe.py): only aidlc may load in the demo's folders."""
import importlib.util
import unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "probe", Path(__file__).resolve().parents[2] / "docs" / "demo" / "probe.py")
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

CLEAN = {"plugins": [{"name": "aidlc", "source": "aidlc@inline"},
                     {"name": "aidlc-practice", "source": "aidlc-practice@inline"},
                     {"name": "cc-plugin-telemetry", "source": "cc-plugin-telemetry@builtin"}],
         "skills": ["aidlc:aidlc-intent", "aidlc-practice:security-and-hardening", "init"],
         "mcp_servers": [{"name": "lab-jira", "status": "connected"}]}


class ProbeTest(unittest.TestCase):
    def test_aidlc_builtins_and_lab_jira_are_clean(self):
        self.assertEqual(probe.foreign(CLEAN, deny=[]), [])

    def test_a_user_plugin_is_foreign(self):
        init = {**CLEAN, "plugins": CLEAN["plugins"] + [{"name": "superpowers",
                                                          "source": "superpowers@claude-plugins-official"}]}
        self.assertEqual(probe.foreign(init, deny=[]), ["plugin superpowers@claude-plugins-official"])

    def test_a_synced_skill_is_foreign_unless_denied(self):
        init = {**CLEAN, "skills": CLEAN["skills"] + ["anthropic-skills:pdf"]}
        self.assertEqual(probe.foreign(init, deny=[]), ["skill anthropic-skills:pdf"])
        self.assertEqual(probe.foreign(init, deny=["Skill(anthropic-skills *)"]), [])
        self.assertEqual(probe.foreign(init, deny=["Skill(anthropic-skills:pdf)"]), [])
        self.assertEqual(probe.foreign(init, deny=["Skill(anthropic-skills:docx)"]), ["skill anthropic-skills:pdf"])

    def test_another_mcp_server_is_foreign(self):
        init = {**CLEAN, "mcp_servers": CLEAN["mcp_servers"] + [{"name": "claude.ai Gmail", "status": "needs-auth"}]}
        self.assertEqual(probe.foreign(init, deny=[]), ["mcp claude.ai Gmail"])
