# tests/unit/test_account_extensions.py
"""Plan 6 finding F2: claude.ai connectors and account-synced skills load in every session unless the
project switches them off (harness.disable_claude_ai_connectors, harness.deny_skills)."""
import json
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path

import yaml

from aidlc.adapters import get_adapter
from aidlc.repo import CONFIG, init_repo
from aidlc.workspace import init_workspace
from tests.helpers import TempRepo


class RepoAccountExtensionsTest(unittest.TestCase):
    def settings(self, harness):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            data = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
            data["harness"].update(harness)
            (root / CONFIG).write_text(yaml.safe_dump(data), encoding="utf-8")
            [f] = get_adapter("claude-code").render_permissions(root)
            return json.loads(f.content)

    def test_default_leaves_them_alone(self):
        s = self.settings({})
        self.assertNotIn("disableClaudeAiConnectors", s)
        self.assertFalse([d for d in s["permissions"]["deny"] if d.startswith("Skill(")])

    def test_connectors_can_be_switched_off(self):
        self.assertIs(self.settings({"disable_claude_ai_connectors": True})["disableClaudeAiConnectors"], True)

    def test_skills_can_be_denied(self):
        s = self.settings({"deny_skills": ["anthropic-skills *", "other:one"]})
        self.assertIn("Skill(anthropic-skills *)", s["permissions"]["deny"])
        self.assertIn("Skill(other:one)", s["permissions"]["deny"])

    def test_bad_values_fail_render(self):
        for harness in ({"disable_claude_ai_connectors": "yes"}, {"deny_skills": "anthropic-skills *"},
                        {"deny_skills": [""]}, {"deny_skills": ["a)b"]}):
            with self.subTest(harness=harness), self.assertRaises(ValueError):
                self.settings(harness)


class WorkspaceAccountExtensionsTest(unittest.TestCase):
    def test_the_read_only_harness_switches_them_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", str(root / "svc")], check=True)
            init_workspace(root, "SHIP-1", "t", [("svc", "team")], [])
            s = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
            self.assertIs(s["disableClaudeAiConnectors"], True)
            self.assertIn("Skill(anthropic-skills *)", s["permissions"]["deny"])
