import unittest

from aidlc.paths import framework_root

ROOT = framework_root()


class MultiToolDocsTest(unittest.TestCase):
    def test_adr_records_the_foundation(self):
        text = (ROOT / "docs/adr/0006-multi-tool-foundation.md").read_text(encoding="utf-8")
        for needle in ("owner", "render_outputs", "core/adapters", "dialect", "fail-open", "also_runs"):
            self.assertIn(needle, text)

    def test_copilot_notes_are_current(self):
        text = (ROOT / "docs/adapters/copilot.md").read_text(encoding="utf-8")
        for needle in (".agent.md", "managed-settings.json", "chat.agent.sandbox", "cloud agent", "Local",
                       ".claude/settings.json", "fail open", "capabilities.md"):
            self.assertIn(needle, text)
        self.assertNotIn("no direct permissions.yaml equivalent", text)

    def test_interface_lists_six_functions(self):
        text = (ROOT / "docs/adapters/interface.md").read_text(encoding="utf-8")
        for needle in ("render_skills", "render_agents", "render_outputs", "core/adapters"):
            self.assertIn(needle, text)
