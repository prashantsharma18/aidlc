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

    def test_the_review_restores_the_base_branchs_session_settings(self):
        step = self.review.split("- name: Review under the base branch's rules", 1)[1].split("- name:", 1)[0]
        for name in (".claude", ".mcp.json", "AGENTS.md", "CLAUDE.md"):
            self.assertIn(name, step)
        self.assertIn("git rm -r -q --cached --ignore-unmatch", step)
        owners = read("starter/repo/CODEOWNERS")
        self.assertRegex(owners, r"(?m)^CLAUDE\.md\s+@your-org/your-team-leads$")

    def test_both_passes_load_no_repository_settings_or_hooks(self):
        self.assertEqual(self.review.count("--setting-sources user"), 2)
        self.assertEqual(self.review.count("""--settings '{"disableAllHooks": true}'"""), 2)

    def test_the_restore_loop_names_every_path_the_action_restores(self):
        step = self.review.split("- name: Review under the base branch's rules", 1)[1].split("- name:", 1)[0]
        loop = re.search(r"for f in ([^;]+); do", step).group(1).split()
        for name in ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md", ".claude", ".claude.json", ".mcp.json",
                     ".gitmodules", ".ripgreprc", ".husky"):
            self.assertIn(name, loop)

    def test_no_run_block_interpolates_any_expression(self):
        for block in run_blocks(self.review):
            self.assertNotIn("${{", block)

    def test_code_owners_own_the_mcp_config(self):
        self.assertRegex(read("starter/repo/CODEOWNERS"), r"(?m)^\.mcp\.json\s+@your-org/your-team-leads$")

    def test_strict_mcp_config_is_not_used(self):
        # Unverified: it may also drop the action's own inline-comment tool.
        self.assertNotIn("--strict-mcp-config", self.review)


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
            self.assertRegex(text, r"Status: (Proposed|Accepted|Superseded by ADR 0024)")
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


class FinalReviewFixesTest(unittest.TestCase):
    """Plan 20's final review: the CI comment tells the truth, CI falls back only when the base has no script, and the
    Stop hook tolerates a repository without the script and cannot hang the session."""

    def setUp(self):
        self.ci = read("starter/repo/.github/workflows/ci.yml")

    def test_the_ci_comment_says_who_holds_the_workflow(self):
        self.assertNotIn("cannot weaken its own check", " ".join(self.ci.split()))
        self.assertIn("CODEOWNERS", self.ci)
        section = read("README.md").split("## Where the gates hold", 1)[1].split("\n## ", 1)[0]
        self.assertIn("ci.yml", section)
        self.assertIn("CODEOWNERS", section)

    def test_ci_falls_back_only_when_the_base_has_no_script(self):
        self.assertIn('git cat-file -e "origin/$BASE_REF:scripts/check_slice.py"', self.ci)
        self.assertNotIn('if ! git show "origin/$BASE_REF:scripts/check_slice.py"', self.ci)

    def test_the_stop_hook_skips_a_missing_script_and_times_out(self):
        hooks = json.loads(read("starter/repo/.claude/settings.json"))["hooks"]["Stop"]
        entries = [h for group in hooks for h in group["hooks"] if "check_slice.py" in h["command"]]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["command"].startswith(
            'test -f "$CLAUDE_PROJECT_DIR/scripts/check_slice.py" || exit 0; '), entries[0]["command"])
        self.assertEqual(entries[0].get("timeout"), 60)


class WorkspaceDenyRulesTest(unittest.TestCase):
    """T7: the workspace settings deny edits to .claude/, so the per-repository rules go in before the copy, and a
    repository added later gets its rule from the person."""

    def test_the_rules_are_written_before_the_settings_are_copied(self):
        onboard = " ".join(read("skills/aidlc-onboard/SKILL.md").split())
        self.assertIn("add one deny rule per repository, `Edit(/<repository>/**)`, to the settings before you copy "
                      "them in", onboard)
        self.assertIn("ask the person to add its deny rule to `.claude/settings.json`", onboard)
        self.assertNotIn("give it its deny rule", onboard)


class MergeFirstTest(unittest.TestCase):
    """A2 (ADR 0020): the approval is still recorded on the work item, and at Tier 2 and 3 it is also a merge."""

    def gate(self, name):
        return " ".join(read(f"skills/{name}/SKILL.md").split("## Gate", 1)[1].split("\n## ", 1)[0].split())

    def test_each_approving_stage_merges_first_at_tier_2_and_3(self):
        for name in ("aidlc-specify", "aidlc-design", "aidlc-plan"):
            self.assertIn("At Tier 2 and 3", self.gate(name), name)
            self.assertIn("merges to the default branch first, in its own pull request", self.gate(name), name)
            self.assertIn("ADR 0020", self.gate(name), name)

    def test_the_work_item_record_stays(self):
        self.assertIn("records the approval on the work item with the plan's version and commit", self.gate("aidlc-plan"))

    def test_build_starts_only_from_the_merged_bundle(self):
        build = " ".join(read("skills/aidlc-build/SKILL.md").split())
        self.assertIn("At Tier 2 and 3, the bundle is the copy merged on the default branch", build)


TIER_TABLES = ["docs/operating-model/tiers-table.md"] + [
    f"skills/{s}/assets/tiers.md" for s in
    ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review")]
SEVERAL = ("A story that changes two or more repositories is at least Tier 2 (ADR 0021): its parts never merge on "
           "their own, and its release has a release approver.")


class SeveralRepositoriesTierTest(unittest.TestCase):
    """F12 (ADR 0021): a story across several repositories is at least Tier 2."""

    def test_every_tier_table_says_it(self):
        for rel in TIER_TABLES:
            self.assertIn(SEVERAL, " ".join(read(rel).split()), rel)

    def test_start_and_plan_apply_it(self):
        start = " ".join(read("skills/aidlc-start/SKILL.md").split())
        plan = " ".join(read("skills/aidlc-plan/SKILL.md").split())
        self.assertIn("A story across several repositories is at least Tier 2", start)
        self.assertIn("A part of a story across several repositories is at least Tier 2 (ADR 0021)", plan)


class PlanCheckTest(unittest.TestCase):
    def test_plan_runs_the_plan_check(self):
        plan = " ".join(read("skills/aidlc-plan/SKILL.md").split())
        self.assertIn("run the plan check named in AGENTS.md and fix every problem it reports", plan)


class FeedbackTest(unittest.TestCase):
    """A6: the /correct ranking, proof on a past mistake, and the rule table."""

    def setUp(self):
        self.feedback = " ".join(read("skills/aidlc-feedback/SKILL.md").split())

    def test_the_layers_are_ranked_highest_first(self):
        order = ["make the mistake impossible to write", "A type, or a lint rule whose error names the fix",
                 "A test of the behaviour", "The context or the review checklist, only for what needs judgement"]
        positions = [self.feedback.index(step) for step in order]
        self.assertEqual(positions, sorted(positions))

    def test_each_check_is_proved_on_the_past_mistake(self):
        self.assertIn("Prove each new check fails on the real past mistake", self.feedback)

    def test_a_repeat_goes_higher(self):
        self.assertIn("A lesson whose rule is already in the table with no enforcer is a repeat", self.feedback)

    def test_the_guide_keeps_the_rule_table(self):
        for rel in ("starter/repo/AGENTS.md", "skills/aidlc-onboard/assets/agents-md.md"):
            text = read(rel)
            self.assertIn("## Rules and what enforces them", text, rel)
            self.assertIn("| Rule | Enforced by | Seen failing on |", text, rel)


class EvalsWorkflowTest(unittest.TestCase):
    """A7: the 28 behaviour evals, Bash cases included, run in a CI container on demand and before each release."""

    def setUp(self):
        self.wf = read(".github/workflows/evals.yml")

    def test_it_runs_on_demand_only(self):
        self.assertIn("workflow_dispatch:", self.wf)
        self.assertNotIn("pull_request", self.wf)

    def test_the_key_needs_an_approved_run(self):
        self.assertIn("environment: ai-gates", self.wf)
        self.assertIn("permissions: {contents: read}", self.wf)

    def test_tools_are_pinned(self):
        self.assertEqual(pinned_uses(self.wf), [])
        self.assertIn("@anthropic-ai/claude-code@2.1.296", self.wf)
        self.assertIn("--model claude-sonnet-5-5", self.wf)

    def test_inputs_reach_the_shell_through_env(self):
        for block in run_blocks(self.wf):
            self.assertNotIn("${{", block, block)

    def test_the_readme_points_to_it(self):
        self.assertIn("## In CI", read("evals/README.md"))


class RecordTest(unittest.TestCase):
    def test_the_map_names_the_new_scripts(self):
        mapping = read("docs/codebase-map.md")
        for name in ("check_slice.py", "check_plan.py", "evals.yml"):
            self.assertIn(name, mapping)

    def test_the_plan_is_recorded(self):
        self.assertIn("Plan 20", read("docs/design/2026-11-19-aidlc-6-change-list.md"))
        self.assertTrue((ROOT / "docs/verification/2026-11-19-plan-20.md").is_file())


class SuppressionRulesTest(unittest.TestCase):
    """Item 2, second layer: onboard proposes each stack's own rules against blanket and unused suppressions."""

    def test_the_reference_names_each_stacks_rules(self):
        path = ROOT / "skills/aidlc-onboard/references/suppression-rules.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        for rule in ("PGH004", "RUF100", "ignore-without-code", "warn_unused_ignores", "useless-suppression",
                     "reportUnusedDisableDirectives", "no-unlimited-disable", "require-description",
                     "@typescript-eslint/ban-ts-comment", "nolintlint", "IDE0079"):
            self.assertIn(rule, text)
        self.assertIn("official documentation", text)

    def test_onboard_points_to_it(self):
        onboard = " ".join(read("skills/aidlc-onboard/SKILL.md").split())
        self.assertIn("`references/suppression-rules.md`", onboard)
        self.assertIn("blanket and unused suppressions", onboard)


class VerificationRecordTest(unittest.TestCase):
    """T8: the record shows the hook blocking on a keyed branch and names what claude-code-action may load."""

    def test_the_record_has_a_blocking_hook_probe_and_the_open_question(self):
        record = read("docs/verification/2026-11-19-plan-20.md")
        self.assertIn("feat/SHIP-7-probe", record)
        self.assertIn("    exit 2", record)
        self.assertIn("claude-code-action loads project settings and hooks from the pull request's checkout",
                      " ".join(record.split()))


if __name__ == "__main__":
    unittest.main()
