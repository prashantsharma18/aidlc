# tests/unit/test_practice_docs.py
import unittest

from aidlc.paths import framework_root

ROOT = framework_root()


class PracticeDocsTest(unittest.TestCase):
    def test_adr(self):
        text = (ROOT / "docs/adr/0008-practice-layer-and-plugin-levels.md").read_text(encoding="utf-8")
        for needle in ("practice", "stage", "aidlc-practice", "enable_plugins", "approved marketplace",
                       "aeac41d", "MIT", "ci-cd-and-automation", "context"):
            self.assertIn(needle, text)

    def test_guides(self):
        readme = (ROOT / "docs/skills/README.md").read_text(encoding="utf-8")
        for needle in ("ORGANISATION", "DOMAIN", "PERSONAL", "aidlc-practice@aidlc", "harness.enable_plugins"):
            self.assertIn(needle, readme)
        practices = (ROOT / "docs/skills/practices.md").read_text(encoding="utf-8")
        for name in ("api-and-interface-design", "debugging-and-error-recovery", "security-and-hardening",
                     "observability-and-instrumentation", "performance-optimization", "frontend-ui-engineering",
                     "deprecation-and-migration", "code-review-and-quality", "browser-testing-with-devtools"):
            self.assertIn(name, practices)

    def test_the_rules_template_carries_the_working_behaviours(self):
        text = (ROOT / "core/templates/agents-md.md").read_text(encoding="utf-8")
        for needle in ("## How to work", "State your assumptions", "stop and ask", "Push back",
                       "simplest", "Touch only", "evidence", "using-agent-skills of addyosmani/agent-skills (MIT)"):
            self.assertIn(needle, text)
