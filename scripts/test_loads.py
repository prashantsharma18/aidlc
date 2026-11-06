"""Stage skills load the practices they need, by name; the map names every stage and practice."""
import re
import unittest
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "plugins" / "aidlc" / "skills"
LOAD = re.compile(r"\b[Ll]oad the `([a-z0-9-]+)` skill")


def text(name: str) -> str:
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    end = body.find("\n## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


STAGES = sorted(p.name for p in SKILLS.iterdir() if p.name.startswith("aidlc-"))
PRACTICES = sorted(p.name for p in SKILLS.iterdir()
                   if (p / "SKILL.md").is_file() and re.search(r"^\s+kind:\s*practice\b", text(p.name), re.M))


class MapTest(unittest.TestCase):
    def test_the_map_names_every_stage_in_the_lifecycle(self):
        lifecycle = section(text("using-aidlc"), "## The lifecycle")
        for stage in STAGES:
            self.assertIn(f"`{stage}`", lifecycle, stage)

    def test_the_map_names_every_practice_in_the_practice_map(self):
        practices = section(text("using-aidlc"), "## The practice map")
        for practice in PRACTICES:
            self.assertIn(f"`{practice}`", practices, practice)

    def test_writing_documentation_is_a_practice(self):
        self.assertIn("writing-documentation", PRACTICES)


LOADS = {
    "aidlc-start": {"using-aidlc"},
    "aidlc-onboard": {"building-ci-pipelines"},
    "aidlc-intent": set(),
    "aidlc-specify": set(),
    "aidlc-discover": {"designing-apis", "writing-tests"},
    "aidlc-design": {"securing-code", "migrating-safely", "stress-testing-decisions", "checking-official-docs",
                     "designing-apis", "writing-tests", "building-ci-pipelines", "tuning-performance",
                     "adding-observability", "writing-documentation"},
    "aidlc-plan": {"stress-testing-decisions", "checking-official-docs", "writing-tests", "testing-in-browser",
                   "using-aidlc"},
    "aidlc-build": {"checking-official-docs", "writing-tests", "testing-in-browser", "committing-changes",
                    "debugging-failures", "reviewing-code"},
    "aidlc-verify": set(),
    "aidlc-review": {"reviewing-code", "securing-code"},
    "aidlc-release": {"adding-observability", "migrating-safely", "committing-changes", "writing-documentation"},
    "aidlc-operate": {"adding-observability"},
    "aidlc-feedback": {"writing-tests", "building-ci-pipelines", "adding-observability", "writing-documentation"},
}
OLD_PHRASES = ("says how to write each test well", "skill helps", "shapes each commit",
               "adds a browser test per criterion", "challenge the draft with `stress-testing-decisions`",
               "check it with `checking-official-docs`", "challenge the recommended option with",
               "check it first (`checking-official-docs`)", "changelog entry too (`committing-changes`)",
               "design it with the `building-ci-pipelines` skill")


class LoadsTest(unittest.TestCase):
    def test_every_stage_is_in_the_table(self):
        self.assertEqual(sorted(LOADS), STAGES)

    def test_each_stage_loads_exactly_its_practices(self):
        for stage, expected in LOADS.items():
            self.assertEqual(set(LOAD.findall(text(stage))), expected, stage)

    def test_every_loaded_skill_exists_and_the_model_can_load_it(self):
        for stage in LOADS:
            for name in LOAD.findall(text(stage)):
                self.assertTrue((SKILLS / name / "SKILL.md").is_file(), (stage, name))
                self.assertNotIn("disable-model-invocation: true", text(name), (stage, name))

    def test_no_passing_mention_is_left(self):
        for stage in LOADS:
            for phrase in OLD_PHRASES:
                self.assertNotIn(phrase, text(stage), (stage, phrase))

    def test_the_plan_chooses_core_practices_from_the_map(self):
        self.assertIn("the core practices the slice needs", text("aidlc-plan"))

    def test_a_commanded_load_that_fails_is_a_stop(self):
        self.assertIn("Every skill a step below tells you to load is loaded the same way", text("aidlc-build"))

    def test_writing_tests_covers_characterisation_tests(self):
        self.assertIn("A characterisation test is the exception", text("writing-tests"))

    def test_the_bundle_template_takes_core_practices(self):
        template = (SKILLS / "aidlc-plan" / "assets" / "task-bundle.md").read_text(encoding="utf-8")
        self.assertNotIn("only skills AGENTS.md declares", template)
        self.assertIn("core practices from the `using-aidlc` practice map", template)

    def test_a_practice_the_bundle_missed_is_a_recorded_deviation(self):
        self.assertIn("load it and record it as a deviation", text("aidlc-build"))
        note = (SKILLS / "aidlc-build" / "assets" / "progress-note.md").read_text(encoding="utf-8")
        self.assertIn("## Deviations", note)

    def test_compliance_knows_which_loads_the_build_commands(self):
        agent = (SKILLS.parents[0] / "agents" / "reviewer-compliance.md").read_text(encoding="utf-8")
        self.assertIn("Always: `writing-tests`, `committing-changes`, `reviewing-code`", agent)
        self.assertIn("`debugging-failures` when the note records a failing check", agent)

if __name__ == "__main__":
    unittest.main()
