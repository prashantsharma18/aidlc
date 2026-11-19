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


REPO_DENIES = ["Edit(/.claude/**)", "Edit(/scripts/check_*.py)", "Edit(/scripts/run_slices.py)",
               "Edit(/.github/workflows/ai-review.yml)", "Edit(/CODEOWNERS)", "Edit(/.github/CODEOWNERS)"]


class DenyTest(unittest.TestCase):
    """A4: a session cannot edit the files that enforce its own rules."""

    def settings(self, kind):
        return json.loads(read(f"starter/{kind}/.claude/settings.json"))["permissions"]

    def test_the_repository_denies_edits_to_its_controls(self):
        deny = self.settings("repo")["deny"]
        for rule in REPO_DENIES:
            self.assertIn(rule, deny)

    def test_agents_md_and_ci_stay_editable(self):
        deny = " ".join(self.settings("repo")["deny"])
        self.assertNotIn("AGENTS.md", deny)
        self.assertNotIn("ci.yml", deny)

    def test_the_workspace_denies_edits_to_its_controls(self):
        deny = self.settings("workspace")["deny"]
        self.assertIn("Edit(/.claude/**)", deny)
        self.assertIn("Edit(/scripts/story_status.py)", deny)

    def test_onboard_copies_the_settings_last(self):
        onboard = " ".join(read("skills/aidlc-onboard/SKILL.md").split())
        self.assertIn("copy `.claude/settings.json` last", onboard)
        self.assertIn("its deny rules then protect the files copied before it", onboard)


class WhereGatesHoldTest(unittest.TestCase):
    """A8 and D6: the docs say which controls hold in which tool and on which GitHub plan."""

    def test_the_readme_has_the_table(self):
        readme = read("README.md")
        self.assertIn("## Where the gates hold", readme)
        for tool in ("Claude Code", "GitHub Copilot, Codex, Cursor"):
            self.assertIn(tool, readme.split("## Where the gates hold", 1)[1].split("\n## ", 1)[0])

    def test_the_github_free_limit_is_stated(self):
        readme = " ".join(read("README.md").split())
        self.assertIn("On GitHub Free, branch protection, rulesets and required checks work only on public repositories", readme)
        self.assertIn("Never turn on auto-merge without required checks", readme)

    def test_onboard_says_it_too(self):
        onboard = " ".join(read("skills/aidlc-onboard/SKILL.md").split())
        self.assertIn("Say which controls hold in the team's tool and on its GitHub plan", onboard)


class AdrTest(unittest.TestCase):
    """ADRs 0019 to 0021 record the Plan 20 decisions as Proposed, each with a decider."""

    ADRS = ("0019-gates-enforced-by-code.md", "0020-approved-documents-merge-first.md",
            "0021-several-repositories-at-least-tier-2.md")

    def test_each_decision_is_recorded_with_a_decider(self):
        for name in self.ADRS:
            text = read(f"docs/adr/{name}")
            self.assertRegex(text, r"Status: (Proposed|Accepted)")
            self.assertIn("Decider: Prashant Sharma", text)
            for heading in ("## Context", "## Decision", "## Consequences"):
                self.assertIn(heading, text, name)


class WiringTest(unittest.TestCase):
    """A1 and A5: CI and the session run the slice check; the guide and the skills name it."""

    def test_the_stop_hook_runs_the_slice_check(self):
        hooks = json.loads(read("starter/repo/.claude/settings.json"))["hooks"]["Stop"]
        commands = [h["command"] for group in hooks for h in group["hooks"]]
        self.assertTrue(any("scripts/check_slice.py" in c and "--hook" in c for c in commands), commands)

    def test_ci_runs_the_base_branchs_copy_on_the_head_commit(self):
        ci = read("starter/repo/.github/workflows/ci.yml")
        self.assertIn("slice-check:", ci)
        self.assertIn("ref: ${{ github.event.pull_request.head.sha }}", ci)
        self.assertIn('git show "origin/$BASE_REF:scripts/check_slice.py"', ci)
        self.assertEqual(pinned_uses(ci), [])
        for block in run_blocks(ci):
            self.assertNotRegex(block, r"\$\{\{\s*github\.(head_ref|base_ref|event)", block)

    def test_the_guide_names_the_commands_and_the_exception_format(self):
        for rel in ("starter/repo/AGENTS.md", "skills/aidlc-onboard/assets/agents-md.md"):
            text = read(rel)
            self.assertIn("python3 scripts/check_slice.py", text, rel)
            self.assertIn("python3 scripts/check_plan.py", text, rel)
            self.assertIn("aidlc-exception: reason=...; owner=...; expires=YYYY-MM-DD", text, rel)

    def test_build_and_compliance_use_it(self):
        build = " ".join(read("skills/aidlc-build/SKILL.md").split())
        self.assertIn("Run the slice check named in AGENTS.md", build)
        self.assertIn("slice check", read("agents/reviewer-compliance.md"))


if __name__ == "__main__":
    unittest.main()
