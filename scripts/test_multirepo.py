"""Plan 21: a story's facts have one owner, and parts pin by version and commit (ADR 0022). The skills, templates,
starters and workflows say so in the same words."""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_gates_hold import pinned_uses, run_blocks  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
VANISHING = re.compile(r"<[A-Za-z][^<>\n]*>")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def gate(name: str) -> str:
    return " ".join(read(f"skills/{name}/SKILL.md").split("## Gate", 1)[1].split("\n## ", 1)[0].split())


class AdrTest(unittest.TestCase):
    """The decision is recorded before the gates change."""

    def test_adr_0022_is_proposed_with_a_decider(self):
        text = read("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md")
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("Each fact has one owner, and only the owner changes it", "`spec v<n> @ <commit>`",
                       "`plans/<KEY>/criteria.md`", "`api-v<info.version>`", "Code that ships together goes in one repository"):
            self.assertIn(phrase, body, phrase)

    def test_the_change_list_records_d9(self):
        self.assertRegex(read("docs/design/2026-11-19-aidlc-6-change-list.md"), r"(?m)^\| D9 \| \*\*oasdiff")

    def test_adr_0023_says_people_decide_and_the_ai_records(self):
        text = read("docs/adr/0023-people-decide-the-ai-records.md")
        self.assertRegex(text, r"Status: (Proposed|Accepted)")
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = " ".join(text.split())
        for phrase in ("People decide; the AI records", "recording someone else's decision is not approving it",
                       "never invents or fills a name", "`confirmed by Ana in the session, 2026-11-20`",
                       "The AI never merges"):
            self.assertIn(phrase, body, phrase)


class HygieneTest(unittest.TestCase):
    """F14: the home repository's owners, its .gitignore and the runtime environment's owner."""

    def test_the_workspace_has_code_owners(self):
        owners = read("starter/workspace/CODEOWNERS")
        self.assertRegex(owners, r"(?m)^stories/\*\*\s+@your-org/your-team-leads$")
        self.assertRegex(owners, r"(?m)^compose\*\.yaml\s+@your-org/your-runtime-owner$")
        deny = json.loads(read("starter/workspace/.claude/settings.json"))["permissions"]["deny"]
        for rule in ("Edit(/CODEOWNERS)", "Edit(/.github/CODEOWNERS)"):
            self.assertIn(rule, deny)

    def test_the_workspace_guide_names_the_command_and_the_owner(self):
        for rel in ("starter/workspace/WORKSPACE.md", "skills/aidlc-onboard/assets/workspace.md"):
            text = flat(rel)
            self.assertIn("`python3 scripts/story_status.py --write-gitignore`", text, rel)
            self.assertIn("## Runtime environment", read(rel), rel)
            self.assertIn("Each fact has one owner, and only the owner changes it (ADR 0022)", text, rel)
            self.assertNotIn("never by copy", text, rel)
        self.assertEqual(VANISHING.findall(re.sub(r"`[^`\n]*`", "", read("skills/aidlc-onboard/assets/workspace.md"))), [])


if __name__ == "__main__":
    unittest.main()
