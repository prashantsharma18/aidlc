# tests/unit/test_ai_gates_docs.py
import unittest

from aidlc.paths import framework_root
from aidlc.policy import load_policy

ROOT = framework_root()


class AiGatesDocsTest(unittest.TestCase):
    def test_required_checks_name_the_real_jobs(self):
        checks = load_policy("branch-protection")["required_checks"]
        self.assertIn("ai-review", checks)
        self.assertIn("agent-config-evals", checks)
        self.assertNotIn("ai-review-dispositioned", checks)
        self.assertTrue(load_policy("branch-protection")["require_resolved_comments"])

    def test_the_guide_page_covers_operation(self):
        text = (ROOT / "docs/checks/ai-gates.md").read_text()
        for needle in ("Fixed:", "Dismissed:", "never approves", "Require conversation resolution",
                       "ai-gates", "fork", "make harness-live", "/code-review", "claude plugin eval",
                       "only `docs/`", "already commented", "Read the diff before you approve",
                       "rotate the key", "gh secret set ANTHROPIC_API_KEY --env ai-gates"):
            self.assertIn(needle, text)

    def test_adr_records_the_exception_and_the_unpinned_plugin(self):
        text = (ROOT / "docs/adr/0004-ai-gates.md").read_text()
        for needle in ("pull-requests: write", "can_approve_pull_request_reviews", "not pinned",
                       "6fed3ca145920b639991cb756090506e1bcaf515", "Claude GitHub App",
                       "CLAUDE_CODE_SUBPROCESS_ENV_SCRUB", "gh pr comment", "same process"):
            self.assertIn(needle, text)

    def test_no_claim_that_the_review_tools_are_read_only(self):
        self.assertNotIn("tools are read-only, plus the inline-comment tool",
                         (ROOT / "docs/adr/0004-ai-gates.md").read_text())
        self.assertNotIn("A clean review posts nothing", (ROOT / "docs/checks/ai-gates.md").read_text())
