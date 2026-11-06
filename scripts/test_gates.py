"""Tests that the gates read the same in every file that states them. These read the repository's own skills."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = "plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md"
STARTER = "starter/repo/AGENTS.md"
BUILD = "plugins/aidlc/skills/aidlc-build/SKILL.md"
COMPLIANCE = "plugins/aidlc/agents/reviewer-compliance.md"
EXCEPTION = ("An exception carries a reason, an owner and an expiry date (next to the code for a suppression, in the "
             "Quality bar section for a threshold), and a person approves it in the pull request; without all of "
             "these, or past its expiry date, it is a violation.")


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


class GatesTest(unittest.TestCase):
    def test_the_quality_bar_exception_is_one_sentence_everywhere(self):
        for rel in (TEMPLATE, STARTER, BUILD, COMPLIANCE):
            self.assertIn(EXCEPTION, read(rel), rel)

    def test_the_boundaries_line_leaves_exceptions_to_a_person(self):
        for rel in (TEMPLATE, STARTER):
            self.assertIn("Stop and report; only a person grants an exception (see Quality bar).", read(rel), rel)

    def test_compliance_reports_every_exception_the_change_adds(self):
        self.assertIn("Report every exception the change adds", read(COMPLIANCE))

    def test_compliance_counts_only_the_skills_the_bundle_names(self):
        self.assertIn("core practices that load on their own are not counted", read(COMPLIANCE))

    def test_a_recipe_commit_is_the_one_commit_that_may_not_build(self):
        self.assertEqual(read("plugins/aidlc/skills/committing-changes/SKILL.md").count(
            "except an approved recipe commit, which holds only the tool's output"), 2)

    def test_quarantining_a_test_is_an_exception_a_person_approves(self):
        text = read("plugins/aidlc/skills/building-ci-pipelines/SKILL.md")
        self.assertIn("Taking it out of the required run (quarantine) is an exception under the Quality bar", text)
        self.assertNotIn("goes on a quarantine list with an owner and a date", text)

    def test_the_explorer_gets_one_question_per_brief(self):
        self.assertIn("one question per brief", read("plugins/aidlc/skills/stress-testing-decisions/SKILL.md"))

    def test_third_party_types_are_faked_behind_your_own_adapter(self):
        for rel in ("plugins/aidlc/skills/writing-tests/SKILL.md", "plugins/aidlc/agents/reviewer-tests.md"):
            text = read(rel)
            self.assertNotIn("Mock only what you do not own", text, rel)
            self.assertNotIn("Mocks sit only at edges the repository does not own", text, rel)
            self.assertIn("own adapter", text, rel)


    def test_debugging_never_changes_an_existing_test(self):
        text = read("plugins/aidlc/skills/debugging-failures/SKILL.md")
        self.assertNotIn("Update the test", text)
        self.assertNotIn("fix the test", text)
        self.assertIn("never change an existing assertion", text)

    def test_debugging_writes_the_failing_test_before_the_fix(self):
        text = read("plugins/aidlc/skills/debugging-failures/SKILL.md")
        self.assertLess(text.index("4. GUARD"), text.index("5. FIX the root cause"))
        self.assertLess(text.index("### Step 4: Guard First"), text.index("### Step 5: Fix the Root Cause"))

    def test_debugging_adds_no_fallback_to_get_green(self):
        text = read("plugins/aidlc/skills/debugging-failures/SKILL.md")
        self.assertNotIn("Safe Fallback Patterns", text)
        self.assertIn("Never add one to make a failing check pass", text)

    def test_the_stop_wording_matches_in_build_and_debugging(self):
        for rel in (BUILD, "plugins/aidlc/skills/debugging-failures/SKILL.md"):
            self.assertIn("a test that passed before now fails", read(rel), rel)
        self.assertEqual(read(BUILD).count("a test that passed before now fails"), 2)

    def test_debugging_in_production_only_proposes(self):
        self.assertIn("In production you propose only", read("plugins/aidlc/skills/debugging-failures/SKILL.md"))

    def test_reviewing_code_can_be_loaded_by_a_stage(self):
        text = (ROOT / "plugins/aidlc/skills/reviewing-code/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("disable-model-invocation", text)
        self.assertIn("invocation: auto", text)
        self.assertNotIn("constraint-driven-development", text)

    def test_one_severity_scheme_everywhere(self):
        rubric = read("plugins/aidlc/skills/reviewing-code/SKILL.md")
        self.assertNotIn("**Critical:**", rubric)
        for label in ("**high**", "**medium**", "**low**", "**question**"):
            self.assertIn(label, rubric)
        record = read("plugins/aidlc/skills/aidlc-review/assets/review-record.md")
        self.assertNotIn("[blocking]", record)
        for label in ("[high]", "[medium]", "[low]", "[question]"):
            self.assertIn(label, record)
        for agent in ("reviewer-bug", "reviewer-security", "reviewer-tests", "reviewer-compliance"):
            text = read(f"plugins/aidlc/agents/{agent}.md")
            self.assertIn("high, medium or low", text, agent)
            self.assertIn("`question`", text, agent)

    def test_review_blocks_on_high_and_medium(self):
        self.assertIn("High and medium findings block the merge", read("plugins/aidlc/skills/aidlc-review/SKILL.md"))

    def test_the_rubric_reviews_in_the_stage_order(self):
        text = read("plugins/aidlc/skills/reviewing-code/SKILL.md")
        self.assertLess(text.index("### Step 2: Verify the Verification"), text.index("### Step 3: Review the Tests First"))

if __name__ == "__main__":
    unittest.main()
