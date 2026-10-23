# tests/unit/test_skills_docs.py
import unittest

from aidlc.paths import framework_root

ROOT = framework_root()


class SkillsDocsTest(unittest.TestCase):
    def test_the_guide_page_covers_install_use_and_flow(self):
        text = (ROOT / "docs/skills/README.md").read_text(encoding="utf-8")
        for needle in ("extraKnownMarketplaces", "enabledPlugins", '"aidlc@aidlc": true', "sha",
                       "/aidlc:aidlc-intent", "--plugin-dir", "explorer", "implementer",
                       "no Jira sub-tasks", "spec v2", "failing test", "claude plugin eval",
                       "start on their own", "/aidlc:aidlc-verify"):
            self.assertIn(needle, text)

    def test_adr_records_the_decision(self):
        text = (ROOT / "docs/adr/0005-skills-plugin.md").read_text(encoding="utf-8")
        for needle in ("plugin", "tool-neutral", "Copilot", "cannot carry permission", "content hash",
                       "invocation", "agent-skills", "MIT", "pressure"):
            self.assertIn(needle, text)

    def test_no_stale_plan_references(self):
        self.assertNotIn("aidlc eval --suite", (ROOT / "docs/context-engineering/procedure-a.md").read_text(encoding="utf-8"))
        self.assertNotIn("Copilot Plan 5", (ROOT / "docs/adapters/interface.md").read_text(encoding="utf-8"))

    def test_the_guide_lists_every_stage_skill(self):
        text = (ROOT / "docs/skills/README.md").read_text(encoding="utf-8")
        for name in ("aidlc-discover", "aidlc-design", "aidlc-review", "aidlc-release", "aidlc-operate",
                     "aidlc-feedback"):
            self.assertIn(name, text)
