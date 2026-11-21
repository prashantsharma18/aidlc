"""Plan 21: a story's facts have one owner, and parts pin by version and commit (ADR 0022). The skills, templates,
starters and workflows say so in the same words."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VANISHING = re.compile(r"<[A-Za-z][^<>\n]*>")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    """The skill's SKILL.md, then its references/*.md in name order, whitespace-collapsed (Plan 26)."""
    files = sorted((ROOT / "skills" / name / "references").glob("*.md"))
    return " ".join([flat(f"skills/{name}/SKILL.md")] + [flat(p.relative_to(ROOT).as_posix()) for p in files])


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


class TemplateTest(unittest.TestCase):
    """F3, F4, F5, F13: the templates carry the pin, the criteria copy, the ADR scope and permalinks."""

    def test_the_part_index_and_the_bundle_pin_the_home_commit(self):
        for rel in ("skills/aidlc-start/assets/story-index.md", "skills/aidlc-plan/assets/task-bundle.md"):
            self.assertIn("spec v<n> @ <home commit>", read(rel), rel)
        self.assertIn("permalinks at a commit (the full commit hash in the address)", flat("skills/aidlc-start/assets/story-index.md"))

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
        self.assertIn("permalink at a commit: the file's address on the code host", skill("aidlc-start"))
        self.assertIn("Link the spec by its permalink at the commit where it merged", skill("aidlc-specify"))

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


class OnlinePinCheckTest(unittest.TestCase):
    """The final review: someone runs the online pin check, a pin move is reviewed, and a contract pin has one
    format."""

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
