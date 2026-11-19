"""Plan 20: the rules hold by code (ADR 0019), approved documents merge first (ADR 0020), a story across repositories is
at least Tier 2 (ADR 0021), and the docs say where the gates hold."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA_PIN = re.compile(r"uses:\s*\S+@[0-9a-f]{40}\b")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def run_blocks(yaml_text: str) -> list[str]:
    """The text of every `run:` step, single-line or block."""
    blocks, lines = [], yaml_text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", line)
        if not m:
            continue
        if m.group(2) not in ("|", ">", ""):
            blocks.append(m.group(2))
            continue
        indent, body = len(m.group(1)), []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                break
            body.append(nxt)
        blocks.append("\n".join(body))
    return blocks


def pinned_uses(yaml_text: str) -> list[str]:
    """Every `uses:` line that is NOT pinned to a full commit SHA."""
    return [line.strip() for line in yaml_text.splitlines()
            if re.search(r"\buses:", line) and not SHA_PIN.search(line)]


class StarterReviewTest(unittest.TestCase):
    """A3: adopters get the same hardened AI review the framework runs on itself."""

    def setUp(self):
        self.review = read("starter/repo/.github/workflows/ai-review.yml")

    def test_every_action_is_pinned_to_a_commit(self):
        self.assertEqual(pinned_uses(self.review), [])

    def test_the_key_lives_in_an_approved_environment_and_is_scrubbed(self):
        self.assertIn("environment: ai-gates", self.review)
        self.assertIn('CLAUDE_CODE_SUBPROCESS_ENV_SCRUB: "1"', self.review)

    def test_the_required_check_fails_closed(self):
        self.assertIn("ai-review:", self.review)
        self.assertIn("needs: ai-review-passes", self.review)
        self.assertIn("if: always()", self.review)
        self.assertIn('report.get("reviewed") is True', self.review)

    def test_the_review_reads_the_base_branchs_rules(self):
        self.assertIn('git checkout "origin/$BASE_REF" -- "$f"', self.review)

    def test_no_run_block_interpolates_a_ref(self):
        for block in run_blocks(self.review):
            self.assertNotRegex(block, r"\$\{\{\s*github\.(head_ref|base_ref|event)", block)

    def test_it_never_approves(self):
        self.assertIn("never approve", self.review.lower())

    def test_code_owners_own_the_workflows_and_scripts(self):
        owners = read("starter/repo/CODEOWNERS")
        self.assertIn(".github/           @your-org/your-team-leads", owners)
        self.assertIn("scripts/           @your-org/your-team-leads", owners)


if __name__ == "__main__":
    unittest.main()
