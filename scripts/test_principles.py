"""Plan 30: five of pstack's principle skills, cited where they apply."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("attack-the-premise", "fix-root-causes", "test-behavior-not-implementation", "explain-the-number",
         "exhaust-the-design-space")
NOTES = {
    "attack-the-premise": "**In aidlc:** A second fix that fails the same way is a stop (`aidlc-build`'s Stop if): "
                          "write the shared premise and the observation that tests it in the stop's report. Testing "
                          "the premise is diagnosis, not another attempt.",
    "fix-root-causes": "**In aidlc:** Every place inside MAY CHANGE; one outside it is a stop. The always-on signal is "
                       "a proposal for its owner (`aidlc-feedback`). In production you propose only "
                       "(`debugging-failures`).",
    "test-behavior-not-implementation": "**In aidlc:** It shapes the tests you write. An existing test that fails the "
                                        "two edits is a finding for its owner, never rewritten or deleted "
                                        "(`writing-tests`).",
    "explain-the-number": "**In aidlc:** aidlc has no `benchmark-checklist`: follow `tuning-performance`. A profiler "
                          "that is not installed is a new dependency, which asks first. A measurement that turns out "
                          "to measure something else is an assertion: changing it is `aidlc-build`'s Stop if.",
    "exhaust-the-design-space": "**In aidlc:** Each prototype is a spike (`playbook-spike.md`): outside the source, "
                                "time-boxed, never committed. You recommend; the decider chooses.",
}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


class PrincipleSkillsTest(unittest.TestCase):
    """Task 1: each principle is pstack's text, word for word, with three lines added."""

    def test_each_is_pstacks_text_plus_three_lines(self):
        for name in NAMES:
            ours = skill_md(name)
            head = ours.split("\n---\n", 1)[0]
            self.assertIn(f"name: {name}\n", head, name)
            self.assertIn("disable-model-invocation: true", head, name)
            self.assertIn("metadata:\n  kind: principle", head, name)
            tail = ("\n\n" + NOTES[name] + "\n\nAdapted from pstack's `principle-" + name + "` (`cursor/plugins`, "
                    "folder `pstack`, MIT, Lauren Tan); its notice is in `skills/NOTICE`.\n\nYou draft; you never "
                    "approve.\n")
            self.assertTrue(ours.endswith(tail), name)
            self.assertIn('\ndescription: "Apply ', "\n" + head, name)

    def test_no_skill_loads_a_principle(self):
        for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
            for name in NAMES:
                self.assertNotRegex(path.read_text(encoding="utf-8"), rf"[Ll]oad the `{name}` skill", (path, name))

    def test_the_map_and_the_notice_name_them(self):
        self.assertIn("The principle skills belong to the map: five short rules from pstack (`attack-the-premise`, "
                      "`fix-root-causes`, `test-behavior-not-implementation`, `explain-the-number`, "
                      "`exhaust-the-design-space`), which the steps where they apply cite by name. Read one at `../<name>/SKILL.md` "
                      "from this skill's folder.",
                      flat(skill_md("using-aidlc")))
        self.assertIn("aidlc has four kinds of skill.", skill_md("using-aidlc"))
        self.assertIn("- A principle adapted from pstack: `skills/<name>/SKILL.md`, pstack's text with "
                      "`metadata.kind: principle`, `disable-model-invocation: true`, an \"In aidlc:\" note and its "
                      "credit; cited by name, never loaded.", flat(read("docs/codebase-map.md")))
        notice = flat(read("skills/NOTICE"))
        for name in NAMES:
            self.assertIn(f"`{name}`", notice, name)


if __name__ == "__main__":
    unittest.main()
