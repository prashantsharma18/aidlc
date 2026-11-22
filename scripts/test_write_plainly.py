"""Plan 29: write plainly. Five practices adapted from pstack, keeping pstack's names, and the lines that call them."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRACTICE_SECTIONS = ("## When to use", "## Steps", "## Checks", "## Stop if", "## Common excuses", "## Red flags",
                     "## Rules")
NEVER = ("Never change code, commands, file paths, identifiers, quoted text, test output or a template's fixed "
         "lines: leave them byte for byte.")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def skill(name: str) -> str:
    files = sorted((ROOT / "skills" / name / "references").glob("*.md"))
    return " ".join([flat(skill_md(name))] + [flat(p.read_text(encoding="utf-8")) for p in files])


def section(text: str, heading: str) -> str:
    return flat(text).split(heading, 1)[1].split(" ## ", 1)[0]


def front(name: str) -> str:
    return skill_md(name).split("\n---", 1)[0]


class PracticeShape:
    """Mixed into each task's test: a pstack practice with aidlc's practice sections."""
    NAME = ""
    SOURCE = ""

    def test_it_is_a_practice_the_model_can_load(self):
        head = front(self.NAME)
        self.assertIn(f"name: {self.NAME}", head)
        self.assertIn("  kind: practice", head)
        self.assertIn("  invocation: auto", head)
        self.assertNotIn("disable-model-invocation", head)
        self.assertIn("Use when", head)
        text = skill_md(self.NAME)
        for heading in PRACTICE_SECTIONS:
            self.assertIn("\n" + heading + "\n", text, heading)
        self.assertTrue(text.rstrip().endswith("- You draft; you never approve."))

    def test_it_credits_pstack(self):
        self.assertIn(f"Adapted from pstack's `{self.SOURCE}` (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan); "
                      "its notice is in `skills/NOTICE`.", flat(skill_md(self.NAME)))
        self.assertIn(f"`{self.NAME}`", flat(read("skills/NOTICE")))

    def test_it_is_named_where_a_team_reads(self):
        self.assertIn(f"`{self.NAME}`", section(skill_md("using-aidlc"), "## The practice map"))
        cell = next(line for line in read("README.md").splitlines() if line.startswith("| `aidlc-start`"))
        self.assertIn(f"`{self.NAME}`", cell.split("|")[2])
        self.assertIn(self.NAME, json.loads(read("scripts/routing_cases.json")))

    def test_it_is_never_a_gate(self):
        self.assertIn("None of its own: this skill never stops a stage.", section(skill_md(self.NAME), "## Stop if"))


class UnslopTest(PracticeShape, unittest.TestCase):
    """Task 1: `unslop`, the base layer."""
    NAME, SOURCE = "unslop", "unslop"

    def test_the_catalog_keeps_pstacks_numbers(self):
        catalog = read("skills/unslop/references/ai-tells.md")
        numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\. ", catalog)]
        self.assertEqual(numbers, [3, 5] + list(range(7, 21)) + list(range(22, 34)))
        self.assertIn("Rule numbers are stable ids that other skills cite. A removed rule leaves a gap; a new rule "
                      "takes the next number.", flat(catalog))
        self.assertIn("13. No em dashes, en dashes, or hyphens used as dashes", catalog)
        self.assertIn("`references/ai-tells.md`", section(skill_md("unslop"), "## Steps"))

    def test_it_never_changes_technical_text_and_calls_no_skill(self):
        self.assertIn(NEVER, section(skill_md("unslop"), "## Steps"))
        self.assertNotRegex(skill("unslop"), r"[Ll]oad the `[a-z0-9-]+` skill")


class TechnicalWritingTest(PracticeShape, unittest.TestCase):
    """Task 1: `technical-writing`, the sentences; its last pass is `unslop`."""
    NAME, SOURCE = "technical-writing", "technical-writing"

    def test_its_steps(self):
        steps = section(skill_md("technical-writing"), "## Steps")
        self.assertIn(NEVER, steps)
        self.assertIn("`references/sentences.md`", steps)
        self.assertIn("A pull request description or a commit body is a briefing a reviewer reads in under a minute: "
                      "link logs, run histories and long tables, never paste them.", steps)
        self.assertTrue(steps.rstrip().endswith("Load the `unslop` skill as the last pass."))
        sentences = flat(read("skills/technical-writing/references/sentences.md"))
        for heading in ("Write so a tired engineer understands on the first read.", "## Vary the rhythm",
                        "## Write sentences to the reader (Google developer style)",
                        "## Make statements load one at a time (STE rules)",
                        "## Leave no sentence open to two readings (Global English)"):
            self.assertIn(heading, sentences, heading)
        self.assertNotIn("Diátaxis", sentences)
        self.assertNotIn("Indent code snippets with tabs", sentences)

    def test_the_naming_rule(self):
        self.assertIn("A practice adapted from pstack keeps pstack's name (`unslop`, `technical-writing`, "
                      "`in-your-own-words`, `how`, `why`).", flat(read("docs/codebase-map.md")))


if __name__ == "__main__":
    unittest.main()
