import unittest

from aidlc.adapters import adapter_names
from aidlc.adapters.capabilities import agent_config_markers, capabilities_doc, load_capabilities
from aidlc.checks.conftest_check import _fold, _is_agent_config
from tests.helpers import run_cli


class CapabilitiesTest(unittest.TestCase):
    def test_every_tool_has_a_valid_descriptor(self):
        caps = load_capabilities()
        self.assertEqual(set(caps), {"claude-code", "copilot", "cursor", "codex"})
        self.assertEqual(caps["claude-code"]["status"], "supported")
        for name in ("copilot", "cursor", "codex"):
            self.assertEqual(caps[name]["status"], "planned")
        self.assertLessEqual(set(adapter_names()), set(caps))

    def test_failure_behaviour_is_declared_for_every_tool(self):
        caps = load_capabilities()
        expected = {"claude-code": ("fail-closed", "fail-closed"), "copilot": ("fail-closed", "fail-open"),
                    "cursor": ("configurable", "configurable"), "codex": ("fail-open", "fail-open")}
        for name, (error, timeout) in expected.items():
            with self.subTest(tool=name):
                self.assertEqual(caps[name]["hooks"]["on_error"], error)
                self.assertEqual(caps[name]["hooks"]["on_timeout"], timeout)

    def test_claude_code_tool_names_match_the_shim(self):
        from tests.hook_loader import load_hook
        shim = load_hook("claude_shim")
        names = load_capabilities()["claude-code"]["agents"]["tool_names"]
        for cls, tools in names.items():
            for tool in tools:
                with self.subTest(tool=tool):
                    self.assertEqual(shim.CLASSES[tool], cls)

    def test_every_known_tools_config_is_agent_config(self):
        for path in (".cursor/rules/a.mdc", ".github/copilot-instructions.md", ".github/instructions/x.instructions.md",
                     ".github/agents/r.agent.md", ".github/hooks/h.json", ".codex/hooks.json", ".agents/skills/s/SKILL.md",
                     ".claude/settings.json", ".mcp.json", ".cursorrules", "sub/.CURSOR/x"):
            with self.subTest(path=path):
                self.assertTrue(_is_agent_config(_fold(path)))
        for path in (".github/workflows/ci.yml", "src/app.py", "docs/agents/readme.md", "AGENTS.md", "README.md"):
            with self.subTest(path=path):
                self.assertFalse(_is_agent_config(_fold(path)))

    def test_markers_are_case_folded(self):
        dirs, files, prefixes = agent_config_markers()
        self.assertIn(".cursor", dirs)
        self.assertIn("copilot-instructions.md", files)
        self.assertTrue(all(p == p.casefold() for p in prefixes))

    def test_the_comparison_doc_is_generated_and_current(self):
        doc = capabilities_doc()
        for needle in ("claude-code", "copilot", "cursor", "codex", "fail-open", ".agents/skills"):
            self.assertIn(needle, doc)
        code, out, _ = run_cli("trace", "--check")
        self.assertEqual(code, 0, out)
