"""Plan 12: the routes, the part model and the tracking read the same in every file that states them."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "aidlc" / "skills"
AGENTS = ROOT / "plugins" / "aidlc" / "agents"
STAGES = sorted(p.name for p in SKILLS.iterdir() if p.name.startswith("aidlc-"))


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def skill(name: str) -> str:
    return read(f"plugins/aidlc/skills/{name}/SKILL.md")


def section(body: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed body."""
    start = body.index(heading)
    end = body.find(" ## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


class RoutesTest(unittest.TestCase):
    def test_the_orphan_agents_are_gone(self):
        for name in ("implementer", "planner"):
            self.assertFalse((AGENTS / f"{name}.md").exists(), name)

    def test_every_agent_is_named_by_a_core_skill(self):
        texts = [p.read_text(encoding="utf-8") for p in SKILLS.glob("*/SKILL.md")]
        for agent in sorted(p.stem for p in AGENTS.glob("*.md")):
            self.assertTrue(any(f"`{agent}`" in t for t in texts), agent)

    def test_no_document_lists_the_removed_agents(self):
        for rel in ("README.md", "docs/quickstart/copilot.md", "docs/codebase-map.md"):
            text = read(rel)
            self.assertNotIn("`implementer`", text, rel)
            self.assertNotIn("`planner`", text, rel)

    def test_operate_and_feedback_need_no_story(self):
        for name in ("aidlc-operate", "aidlc-feedback"):
            text = skill(name)
            self.assertNotIn("No index: ask the person to run `aidlc-start` first", text, name)
            self.assertIn("No story is needed", text, name)
            self.assertIn("incidents/<ID>/", text, name)
        self.assertIn("feedback/<YYYY-MM-DD>-<topic>/", skill("aidlc-feedback"))

    def test_the_workspace_root_may_write_incidents_and_feedback(self):
        allow = json.loads((ROOT / "starter/workspace/.claude/settings.json").read_text(encoding="utf-8"))[
            "permissions"]["allow"]
        for rule in ("Edit(/stories/**)", "Edit(/incidents/**)", "Edit(/feedback/**)"):
            self.assertIn(rule, allow)
        for rel in ("starter/workspace/WORKSPACE.md", "plugins/aidlc/skills/aidlc-onboard/assets/workspace.md"):
            self.assertIn("write only under `stories/`, `incidents/` and `feedback/`", read(rel), rel)


if __name__ == "__main__":
    unittest.main()
