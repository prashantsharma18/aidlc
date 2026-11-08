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

    def test_no_stage_produces_only_in_the_reply(self):
        for stage in STAGES:
            self.assertNotIn("in your reply", skill(stage).lower(), stage)

    def test_design_review_and_release_name_their_files(self):
        self.assertIn("design-note.md", section(skill("aidlc-design"), "## Produces"))
        self.assertIn("review-record.md", section(skill("aidlc-review"), "## Produces"))
        for name in ("readiness.md", "change-record.md", "release-runbook.md", "follow-ups.md"):
            self.assertIn(name, section(skill("aidlc-release"), "## Produces"), name)
        self.assertIn("release/<KEY>", skill("aidlc-release"))

    def test_start_routes_and_never_drafts_the_story(self):
        text = skill("aidlc-start")
        self.assertNotIn("Draft the story from", text)
        self.assertNotIn("is only a pointer", text)
        self.assertIn("`aidlc-intent` interviews", text)
        self.assertIn("write nothing at the workspace root", text)
        self.assertFalse((SKILLS / "aidlc-start" / "assets" / "intent.md").exists())

    def test_start_hands_over_an_old_pointer_index(self):
        self.assertIn("an index left by aidlc 3 that only points to a repository", skill("aidlc-start"))

    def test_the_story_index_template_has_the_tracked_lines(self):
        template = read("plugins/aidlc/skills/aidlc-start/assets/story-index.md")
        for line in ("SOURCE", "KIND", "ROUTE", "LEVEL", "CURRENT", "PINS", "UNAFFECTED", "| Stage | Runs in | Status |"):
            self.assertIn(line, template, line)
        self.assertIn("`assets/story-index.md`", skill("aidlc-start"))

    def test_the_workspace_keeps_nothing_for_a_one_repository_story(self):
        for rel in ("starter/workspace/stories/README.md", "starter/workspace/WORKSPACE.md",
                    "plugins/aidlc/skills/aidlc-onboard/assets/workspace.md"):
            text = read(rel)
            self.assertNotIn("pointer", text, rel)
            self.assertIn("A story that changes one repository has nothing here", text, rel)

    def test_design_always_runs_and_only_discover_is_optional(self):
        for name in ("aidlc-start", "using-aidlc"):
            text = skill(name)
            self.assertNotIn("`aidlc-discover` and `aidlc-design` (only when", text, name)
            self.assertNotIn("`aidlc-discover` or `aidlc-design` when the tier asks", text, name)
        self.assertIn('`aidlc-design` (always; at Tier 1 usually a recorded "none needed")', skill("aidlc-start"))
        self.assertIn("the approved design note (always)", skill("aidlc-plan"))

    def test_discover_records_findings_instead_of_drafting(self):
        text = skill("aidlc-discover")
        self.assertNotIn("draft one for its owner to review", text)
        self.assertNotIn("draft characterisation tests that record today's behaviour", text)
        self.assertIn("as a finding for `aidlc-design`", text)
        self.assertIn("as a finding for `aidlc-plan`", text)

    def test_a_pull_request_is_one_part(self):
        self.assertNotIn("Check that the pull request is one slice", skill("aidlc-review"))
        self.assertIn("Check that the pull request is one part", skill("aidlc-review"))
        commits = skill("committing-changes")
        self.assertNotIn("one slice, one reason", commits)
        self.assertIn("one part of the story", commits)
        self.assertIn("the pull-request size `reviewing-code` gives", commits)
        self.assertIn("split it into two parts", skill("aidlc-plan"))

    def test_verify_writes_one_evidence_file_per_part(self):
        self.assertNotIn("evidence-<slice>.md", skill("aidlc-verify"))
        self.assertIn("plans/<KEY>/evidence.md", skill("aidlc-verify"))
        self.assertIn("{{PART}}", read("plugins/aidlc/skills/aidlc-verify/assets/evidence-table.md"))


if __name__ == "__main__":
    unittest.main()
