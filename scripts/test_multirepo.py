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


class ContractWorkflowTest(unittest.TestCase):
    """F9: the provider publishes from its default branch and checks every change; the consumer checks its copy."""

    def setUp(self):
        self.check = read("starter/repo/.github/workflows/contract-check.yml")
        self.publish = read("starter/repo/.github/workflows/contract-publish.yml")
        self.ci = read("starter/repo/.github/workflows/ci.yml")

    def test_every_action_is_pinned_and_no_run_block_interpolates(self):
        for name, text in (("contract-check", self.check), ("contract-publish", self.publish), ("ci", self.ci)):
            self.assertEqual(pinned_uses(text), [], name)
            for block in run_blocks(text):
                self.assertNotIn("${{", block, name)

    def test_oasdiff_is_pinned_by_version_and_checksum(self):
        self.assertIn("OASDIFF_VERSION: 1.35.0", self.check)
        self.assertIn("OASDIFF_SHA256: a8023002fcb2eaa7f5758148a9303cb63d33b939886df312268bc0fc7b939140", self.check)
        self.assertIn("sha256sum -c -", self.check)
        script = read("starter/repo/scripts/check_contract_version.py")
        self.assertIn('"breaking", "--fail-on", "ERR", "--allow-external-refs=false"', script)

    def test_the_check_runs_the_base_branchs_script_read_only(self):
        self.assertIn('git show "origin/$BASE_REF:scripts/check_contract_version.py"', self.check)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", self.check)
        self.assertNotIn("contents: write", self.check)

    def test_only_the_publish_job_writes_and_only_from_main(self):
        self.assertEqual(self.publish.count("contents: write"), 1)
        self.assertIn("branches: [main]", self.publish)
        self.assertIn("--publish-tag", self.publish)
        self.assertIn("rulesets need a public repository on GitHub Free", " ".join(self.publish.split()))

    def test_ci_checks_the_vendored_contracts(self):
        self.assertIn("contract-pin:", self.ci)
        self.assertIn("python3 scripts/check_contract_pin.py", self.ci)

    def test_the_guide_names_the_commands(self):
        for rel in ("starter/repo/AGENTS.md", "skills/aidlc-onboard/assets/agents-md.md"):
            text = read(rel)
            self.assertIn("python3 scripts/check_contract_pin.py --update <provider> api-v<version>", text, rel)
            self.assertIn("python3 scripts/check_contract_version.py --contract <path>", text, rel)

    def test_the_session_cannot_edit_the_contract_scripts(self):
        deny = json.loads(read("starter/repo/.claude/settings.json"))["permissions"]["deny"]
        self.assertIn("Edit(/scripts/check_*.py)", deny)


if __name__ == "__main__":
    unittest.main()
