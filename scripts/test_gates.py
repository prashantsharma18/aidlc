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


if __name__ == "__main__":
    unittest.main()
