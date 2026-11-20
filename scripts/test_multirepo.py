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
            self.assertIn("a person adds or removes the repository's line in the root's `.gitignore`", text, rel)
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

    def test_the_pin_job_decides_from_the_base_on_a_pull_request(self):
        block = "\n".join(run_blocks(job_text(self.ci, "contract-pin")))
        pr, push = block.split("elif", 1)
        self.assertIn('[ "$EVENT_NAME" = "pull_request" ]', pr)
        self.assertIn('git cat-file -e "origin/$BASE_REF:scripts/check_contract_pin.py"', pr)
        self.assertNotIn("-f scripts/", pr)
        self.assertIn("-f scripts/check_contract_pin.py", push)

    def test_publish_documents_the_skipped_middle_version(self):
        text = " ".join(self.publish.replace("# ", " ").split())
        self.assertIn("one pending run", text)
        self.assertIn("tag the skipped commit by hand", text)


class TemplateTest(unittest.TestCase):
    """F3, F4, F5, F13: the templates carry the pin, the criteria copy, the ADR scope and permalinks."""

    def test_the_part_index_and_the_bundle_pin_the_home_commit(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/task-bundle.md"):
            self.assertIn("spec v<n> @ <home commit>", read(rel), rel)
        self.assertIn("GitHub permalinks at a commit", flat("skills/aidlc-start/assets/story-index.md"))

    def test_the_criteria_copy_names_its_source(self):
        text = read("skills/aidlc-plan/assets/criteria.md")
        self.assertIn("## For the reviewer", text)
        self.assertIn("```text\nSOURCE     {{home repository}} stories/{{KEY}}/spec.md @ {{home commit}}", text)
        for heading in ("## Acceptance criteria", "## Edge cases", "## Non-goals"):
            self.assertIn(heading, text)
        self.assertIn("  - criteria\n", read("skills/aidlc-plan/SKILL.md"))

    def test_adrs_carry_their_scope_and_draft_name(self):
        self.assertIn("Scope: {{one repository", read("skills/aidlc-design/assets/adr.md"))
        self.assertIn("`{{KEY}}-adr-{{n}}.md`", read("skills/aidlc-design/assets/adr.md"))
        self.assertNotIn("adr-draft", read("starter/workspace/stories/README.md") + read("skills/aidlc-design/assets/new-system.md"))

    def test_the_coordination_plan_names_the_pins(self):
        self.assertIn("api-v<version> in contracts/<provider>/SOURCE", read("skills/aidlc-design/assets/coordination-plan.md"))

    def test_the_story_folder_says_who_owns_each_fact(self):
        text = flat("starter/workspace/stories/README.md")
        self.assertIn("## Who owns each fact (ADR 0022)", text)
        self.assertIn("`plans/<KEY>/criteria.md`", text)
        self.assertIn("nothing under `stories/<KEY>/` is moved or renamed", text)


class PlacementTest(unittest.TestCase):
    """F2, F3, F4, F5: the stages place each fact with its owner and read the criteria copy."""

    def test_design_places_each_fact_and_files_adrs_by_scope(self):
        design = skill("aidlc-design")
        self.assertIn("Each fact has one owner, and only the owner changes it (ADR 0022)", design)
        self.assertIn("Name the draft `<KEY>-adr-<n>.md` and fill its Scope", design)
        self.assertIn("each affected repository gets a one-line ADR that links it at the home commit", design)
        self.assertNotIn("adr-draft", design)

    def test_plan_pins_the_home_commit_and_writes_the_copy(self):
        plan = skill("aidlc-plan")
        self.assertIn("`spec v<n> @ <commit>`", plan)
        self.assertIn("nothing under `stories/<KEY>/` is moved or renamed", plan)
        self.assertIn("write `plans/<KEY>/criteria.md` from `assets/criteria.md`", plan)

    def test_verify_review_build_and_compliance_read_the_copy(self):
        for rel in ("skills/aidlc-verify/SKILL.md", "skills/aidlc-review/SKILL.md", "skills/aidlc-build/SKILL.md",
                    "agents/reviewer-compliance.md"):
            self.assertIn("`plans/<KEY>/criteria.md`", flat(rel), rel)
        self.assertIn("names the same commit on its SOURCE line", flat("agents/reviewer-compliance.md"))


class DecisionsTest(unittest.TestCase):
    """F1, F6, F11, F13, F14: one repository when code ships together, Decision 2, permalinks and status."""

    def test_code_that_ships_together_goes_in_one_repository(self):
        self.assertIn("Code that ships together goes in one repository (ADR 0022)", skill("aidlc-onboard"))
        self.assertIn("Recommend one repository for code that ships together (ADR 0022)", skill("aidlc-design"))
        self.assertIn("code that ships together belongs in one repository (ADR 0022)", skill("aidlc-start"))

    def test_decision_2_across_repositories_is_two_pull_requests(self):
        self.assertIn("Decision 2 (design and plan) is this design's pull request in the home repository, then each "
                      "part's plan pull request in its own repository", gate("aidlc-design"))
        self.assertIn("Decision 2 is the home design pull request plus this plan's pull request, titled "
                      "`[<KEY>] part <n> of <m>, plan v<n>: <what>`", gate("aidlc-plan"))

    def test_tracker_links_are_permalinks(self):
        self.assertIn("GitHub permalink at a commit", skill("aidlc-start"))
        self.assertIn("Link the spec by its GitHub permalink at the commit where it merged", skill("aidlc-specify"))

    def test_release_reads_the_real_merge_state(self):
        self.assertIn("its `merged` row reads done", skill("aidlc-release"))

    def test_onboard_sets_up_the_home_repository(self):
        onboard = skill("aidlc-onboard")
        self.assertIn("copy `CODEOWNERS` from aidlc's `starter/workspace/` to `.github/CODEOWNERS`", onboard)
        self.assertIn("Then write the root's `.gitignore`: one line per repository", onboard)
        self.assertIn("propose the consumer's (`sha256sum -c` against each copy's SOURCE)", onboard)


class ContractGuidanceTest(unittest.TestCase):
    """F9: designing-apis teaches the rule; design's amendment mode follows the tags and pins."""

    def test_designing_apis_teaches_the_spec_kit_rule(self):
        text = flat("skills/designing-apis/SKILL.md")
        self.assertIn("## A Contract Across Repositories", read("skills/designing-apis/SKILL.md"))
        for phrase in ("`api-v<info.version>`", "Consumers pin a copy", "never \"latest\"", "Propose changes at the source",
                       "Pact and its `can-i-deploy` check"):
            self.assertIn(phrase, text, phrase)

    def test_the_amendment_follows_tags_and_pins(self):
        design = skill("aidlc-design")
        self.assertIn("its default branch publishes the tag `api-v<version>`", design)
        self.assertIn("Never point a consumer at an unpublished version", design)
        self.assertIn("The provider's contract check (oasdiff against the last published tag) must agree", design)


class RecordTest(unittest.TestCase):
    def test_the_map_names_the_new_scripts_and_workflows(self):
        mapping = read("docs/codebase-map.md")
        for name in ("check_contract_version.py", "check_contract_pin.py", "contract-check.yml", "contract-publish.yml"):
            self.assertIn(name, mapping, name)

    def test_the_plan_is_recorded(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        self.assertIn("Plan 20", changes)
        self.assertIn("Plan 21", changes)
        self.assertTrue((ROOT / "docs/verification/2026-11-20-plan-21.md").is_file())


class ContractWorkflowFinalReviewTest(unittest.TestCase):
    """The final review: the check decides from the base, every job is bounded, and the headers say what protects a
    published version."""

    def setUp(self):
        self.check = read("starter/repo/.github/workflows/contract-check.yml")
        self.publish = read("starter/repo/.github/workflows/contract-publish.yml")
        self.ci = read("starter/repo/.github/workflows/ci.yml")

    @staticmethod
    def header(text: str) -> str:
        return " ".join(line.lstrip("# ") for line in text.split("\nname:", 1)[0].splitlines()).strip()

    def test_the_check_decides_from_the_base_on_a_pull_request(self):
        block = "\n".join(run_blocks(job_text(self.check, "contract-check")))
        self.assertIn('git cat-file -e "origin/$BASE_REF:scripts/check_contract_version.py"', block)
        self.assertNotIn("cp scripts/", block)
        self.assertNotIn("python3 scripts/check_contract_version.py", block)
        found, missing = block.split("else", 1)
        self.assertIn('python3 "$RUNNER_TEMP/aidlc/check_contract_version.py"', found)
        self.assertIn("no contract check in this repository", missing)

    def test_the_pin_job_has_a_timeout(self):
        self.assertRegex(job_text(self.ci, "contract-pin"), r"(?m)^    timeout-minutes: [0-9]+$")

    def test_the_check_asks_for_up_to_date_branches(self):
        self.assertIn("require branches to be up to date before merging", self.header(self.check))

    def test_the_tag_ruleset_restricts_creation_too(self):
        adr = flat("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md")
        for name, text in (("publish", self.header(self.publish)), ("adr", adr)):
            self.assertIn("restricts creation, updates and deletions", text, name)
            self.assertIn("anyone with write access can create a version that consumers will pin", text, name)


class OnlinePinCheckTest(unittest.TestCase):
    """The final review: someone runs the online pin check, a pin move is reviewed, and a contract pin has one
    format."""

    def test_the_adr_and_the_publish_job_say_who_runs_it(self):
        publish = ContractWorkflowFinalReviewTest.header(read("starter/repo/.github/workflows/contract-publish.yml"))
        for name, text in (("adr", flat("docs/adr/0022-one-owner-per-fact-and-pinned-parts.md")), ("publish", publish)):
            self.assertIn("No job runs the online pin check yet", text, name)
            self.assertIn("a person or the release stage runs it in each consumer before a release", text, name)
            self.assertIn("phase 2b", text, name)

    def test_release_runs_the_online_check(self):
        release = skill("aidlc-release")
        self.assertIn("checks its copy before release with the commands in `designing-apis`", release)
        self.assertIn("a moved tag stops the release", release)

    def test_the_reviewer_checks_a_pin_move_and_its_pins_item(self):
        text = flat("agents/reviewer-compliance.md")
        self.assertIn("the new tag's commit is on the provider's default branch", text)
        self.assertIn("matches the tag in `contracts/<provider>/SOURCE`", text)

    def test_the_leads_own_the_vendored_contracts(self):
        self.assertRegex(read("starter/repo/CODEOWNERS"), r"(?m)^contracts/\s+@your-org/your-team-leads$")

    def test_a_contract_pin_is_the_tags_version(self):
        start, plan = read("skills/aidlc-start/assets/story-index.md"), read("skills/aidlc-plan/assets/story-index.md")
        self.assertEqual(start, plan)
        for rel in ("skills/aidlc-plan/assets/task-bundle.md", "skills/aidlc-start/assets/story-index.md"):
            text = read(rel)
            self.assertIn("contract <provider> v<MAJOR.MINOR.PATCH>", text, rel)
            self.assertNotIn("contract <name> v<n>", text, rel)
        self.assertIn("the tag in contracts/<provider>/SOURCE", flat("skills/aidlc-plan/assets/task-bundle.md"))
        self.assertIn("as its published tag's, v<MAJOR.MINOR.PATCH>", flat("skills/aidlc-design/assets/coordination-plan.md"))


if __name__ == "__main__":
    unittest.main()
