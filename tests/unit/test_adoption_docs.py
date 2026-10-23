# tests/unit/test_adoption_docs.py
import unittest

from aidlc.paths import framework_root
from aidlc.templates import parse_front_matter

ROOT = framework_root()


class AdoptionDocsTest(unittest.TestCase):
    def test_guide_covers_the_flow(self):
        text = (ROOT / "docs/adoption/README.md").read_text(encoding="utf-8")
        for needle in ("aidlc adopt", "aidlc init-repo", "--import", "git apply", ".aidlc/baseline.yaml",
                       "report_only", "may only shrink", "review_by", "never baselined", "legacy_paths",
                       "required checks", "generic"):
            self.assertIn(needle, text)

    def test_adr_records_the_decision(self):
        text = (ROOT / "docs/adr/0007-adoption-and-ratchet.md").read_text(encoding="utf-8")
        for needle in ("ratchet", "baseline", "secrets", "report-only", "profile", "agent-skills"):
            self.assertIn(needle, text)

    def test_the_adopt_skill_is_manual(self):
        path = ROOT / "core/skills/aidlc-adopt/SKILL.md"
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
        self.assertEqual(meta["metadata"]["invocation"], "manual")
        for needle in ("aidlc adopt", "--import", "aidlc-context-setup", "baseline"):
            self.assertIn(needle, body)
