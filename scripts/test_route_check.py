"""Tests for scripts/route_check.py: a lexical stand-in for how a skill's description draws a prompt."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_check  # noqa: E402

DOCS = {
    "writing-tests": "Writes tests that prove behaviour, test first. Use when adding tests or fixing a bug.",
    "reviewing-code": "Reviews a diff or pull request before merge. Use when reviewing changes.",
    "committing-changes": "Shapes commits and commit messages. Use when writing a commit message.",
}


class RouteCheckTest(unittest.TestCase):
    def test_tokens_drop_stop_words_and_stem(self):
        self.assertEqual(route_check.tokens("Writing the tests for a bug"), ["writ", "test", "bug"])

    def test_the_closest_description_ranks_first(self):
        index = route_check.Index(DOCS)
        self.assertEqual(index.rank("please review this pull request")[0][0], "reviewing-code")
        self.assertEqual(index.rank("write a commit message for this diff")[0][0], "committing-changes")

    def test_near_identical_descriptions_collide(self):
        docs = dict(DOCS, **{"reviewing-code-2": DOCS["reviewing-code"]})
        pairs = route_check.collisions(route_check.Index(docs))
        self.assertEqual([(a, b) for a, b, _ in pairs], [("reviewing-code", "reviewing-code-2")])

    def test_check_reports_misses_and_wrong_owners(self):
        cases = {"writing-tests": {"positive": [{"prompt": "review this pull request", "top_k": 1}],
                                   "negative": [{"prompt": "add tests for this bug", "owner": "committing-changes"}]}}
        report = route_check.check(cases, route_check.Index(DOCS))
        self.assertEqual(len(report["misses"]), 1)
        self.assertEqual(len(report["wrong_owner"]), 1)
        self.assertEqual(report["rank1"], 0.0)

    def test_auto_skills_skip_person_only_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, extra in (("auto", ""), ("manual", "disable-model-invocation: true\n")):
                (root / name).mkdir()
                (root / name / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: Does {name} things. Use when needed.\n{extra}---\nbody\n",
                    encoding="utf-8")
            self.assertEqual(sorted(route_check.auto_skills(root)), ["auto"])


if __name__ == "__main__":
    unittest.main()
