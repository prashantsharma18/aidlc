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


CITATIONS = {
    "skills/debugging-failures/SKILL.md": (
        "When two fixes that share one premise fail the same way, write the premise down, and the observation that "
        "tests it, in the stop's report (`attack-the-premise`).",
        "Fix the underlying issue, not the symptom. Trace the symptom to the first place the system went wrong and "
        "fix it there; a guard is a fix only when the state it handles is legitimate (`fix-root-causes`)."),
    "skills/story-run/references/playbook-bug-fix.md": (
        "Fix it where the system first went wrong, and every same fault inside MAY CHANGE (`fix-root-causes`). When "
        "two attempts fail the same way, write down the premise they share, and the observation that would test it, "
        "for the report the attempt limit asks for (`attack-the-premise`).",),
    "skills/writing-tests/SKILL.md": (
        "And the second edit: would it still pass if only the internals changed, with the same behaviour? It should "
        "(`test-behavior-not-implementation`).",),
    "agents/reviewer-tests.md": (
        "A test that would fail when only the internals change, with the same behaviour, is a finding too "
        "(`test-behavior-not-implementation`).",),
    "skills/tuning-performance/SKILL.md": (
        "Then name what limits the number, and rule out that it measured something other than the work "
        "(`explain-the-number`).",),
    "skills/story-run/references/playbook-performance.md": ("The full rule is `explain-the-number`.",),
    "skills/story-run/references/playbook-spike.md": (
        "Comparing two or three options side by side before you recommend one is `exhaust-the-design-space`.",),
    "skills/aidlc-design/SKILL.md": (
        "For a decision with no precedent, compare the options by spike before you recommend one "
        "(`exhaust-the-design-space`).",),
}


class CitationsTest(unittest.TestCase):
    """Task 2: each principle is cited at the steps where it applies; the decision log may name it."""

    def test_each_citation(self):
        for rel, lines in CITATIONS.items():
            for line in lines:
                self.assertIn(line, flat(read(rel)), (rel, line))
        for name in NAMES:
            places = [rel for rel, lines in CITATIONS.items() if any(f"`{name}`" in line for line in lines)]
            self.assertGreaterEqual(len(places), 2, name)

    def test_no_playbook_citation_says_stop(self):
        for rel in ("skills/story-run/references/playbook-bug-fix.md",
                    "skills/story-run/references/playbook-performance.md",
                    "skills/story-run/references/playbook-spike.md"):
            for line in CITATIONS[rel]:
                self.assertNotIn("stop", line.lower(), rel)

    def test_the_decision_log(self):
        self.assertIn("When one of the principle skills shaped a call (`attack-the-premise`, `fix-root-causes`, "
                      "`test-behavior-not-implementation`, `explain-the-number`, `exhaust-the-design-space`), the "
                      "row's why names it in brackets.", flat(read("skills/aidlc-build/assets/progress-note.md")))
        self.assertIn("- A row whose why names a principle skill (its file is `skills/<name>/SKILL.md`): its trigger "
                      "happened in that call; one that did not is a low finding. A row with no principle is not a finding, and a principle never turns a stop "
                      "into a row.", flat(read("agents/reviewer-compliance.md")))


if __name__ == "__main__":
    unittest.main()
