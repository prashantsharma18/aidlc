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


def job_text(yaml_text: str, job: str) -> str:
    """The lines of one job under `jobs:` (two-space indent), up to the next job."""
    lines, out, on = yaml_text.splitlines(), [], False
    for line in lines:
        if re.match(r"^  [\w-]+:", line):
            on = line.strip() == f"{job}:"
        if on:
            out.append(line)
    return "\n".join(out)


class ContractWorkflowHardeningTest(unittest.TestCase):
    """Fix round 1: least privilege, no manual or privileged triggers, the base branch's scripts, full history."""

    def setUp(self):
        self.check = read("starter/repo/.github/workflows/contract-check.yml")
        self.publish = read("starter/repo/.github/workflows/contract-publish.yml")
        self.ci = read("starter/repo/.github/workflows/ci.yml")

    def test_publish_writes_on_the_job_only_and_serialises(self):
        top = self.publish.split("\njobs:")[0]
        self.assertIn("permissions:\n  contents: read", top)
        self.assertNotIn("contents: write", top)
        self.assertIn("contents: write", job_text(self.publish, "contract-publish"))
        self.assertIn("concurrency:", top)

    def test_no_privileged_or_manual_trigger(self):
        for name, text in (("check", self.check), ("publish", self.publish)):
            self.assertNotIn("pull_request_target", text, name)
            self.assertNotIn("workflow_dispatch", text, name)
        self.assertNotIn("workflow_dispatch", self.ci)

    def test_every_job_that_runs_a_contract_script_fetches_all_history(self):
        for name, text in (("check", job_text(self.check, "contract-check")),
                           ("publish", job_text(self.publish, "contract-publish")),
                           ("pin", job_text(self.ci, "contract-pin"))):
            self.assertIn("fetch-depth: 0", text, name)

    def test_the_checksum_is_verified_before_the_archive_is_extracted(self):
        block = run_blocks(self.check)[0]
        self.assertLess(block.index("sha256sum -c -"), block.index("tar -xzf"))

    def test_the_pin_job_runs_the_base_branchs_scripts(self):
        job = job_text(self.ci, "contract-pin")
        block = "\n".join(run_blocks(job))
        self.assertIn("BASE_REF: ${{ github.base_ref }}", job)
        self.assertIn("github.event_name", job)
        for script in ("check_contract_pin.py", "check_contract_version.py"):
            self.assertIn(f'git show "origin/$BASE_REF:scripts/{script}"', block)
        self.assertIn('python3 "$RUNNER_TEMP/aidlc/check_contract_pin.py"', block)
        self.assertIn("python3 scripts/check_contract_pin.py", block)

    def test_publish_documents_the_skipped_middle_version(self):
        text = " ".join(self.publish.replace("# ", " ").split())
        self.assertIn("one pending run", text)
        self.assertIn("tag the skipped commit by hand", text)


if __name__ == "__main__":
    unittest.main()
