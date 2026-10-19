import unittest

import yaml

from aidlc.paths import framework_root
from aidlc.templates import parse_front_matter

CTX = framework_root() / "core" / "context"


class ContextStandardsTest(unittest.TestCase):
    def test_standards_have_front_matter_with_guide(self):
        for path in [CTX / "authority.md", *sorted((CTX / "standards").glob("*.md")),
                     CTX / "openwiki" / "governance.md"]:
            meta, _ = parse_front_matter(path.read_text(encoding="utf-8"), path)
            self.assertTrue(meta.get("guide"), path)

    def test_openwikiignore_baseline_covers_secrets_and_evals(self):
        lines = (CTX / "openwiki" / "openwikiignore.baseline").read_text(encoding="utf-8").split("\n")
        for pattern in (".env", ".env.*", "*.pem", "*.key", "secrets/", ".aidlc/evals/"):
            self.assertIn(pattern, lines)

    def test_probe_template_has_five_questions(self):
        data = yaml.safe_load((CTX / "probe.yaml.tmpl").read_text(encoding="utf-8"))
        self.assertEqual(len(data["questions"]), 5)
        for q in data["questions"]:
            self.assertTrue({"id", "ask", "expect"} <= set(q))
