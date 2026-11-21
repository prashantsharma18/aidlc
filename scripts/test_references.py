"""Plan 26: shorter stage skills. Five stage skills keep their main path and every gate in `SKILL.md`, and move the
steps of one route or case into `references/<case>.md`, read on a named condition. A reference never holds a gate,
`SKILL.md` names every reference with the condition to read it, and a rule is written once
(docs/design/2026-11-21-shorter-stage-skills.md)."""
import importlib
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
DESIGN = "docs/design/2026-11-21-shorter-stage-skills.md"
DECIDE = ("A person decides here only where the tiers file's decisions table lists this decision; otherwise state "
          "what you did and go on.")
LANE = "In a lane, release at your gate as `parallel-lanes` says."
APPROVE = "You draft; you never approve."
SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Produces", "## Gate", "## Stop if", "## Common excuses",
            "## Red flags", "## Rules")
GATE_SECTIONS = SECTIONS[4:]
# The nine test files whose `skill(name)` helper reads a skill's text (test_validate.py's `skill` builds a fixture).
HELPER_FILES = ("test_fast_path", "test_fewer_approvals", "test_greenfield", "test_instructions_first",
                "test_multirepo", "test_parallel_lanes", "test_recording", "test_route_and_log", "test_routes")
OPENING = re.compile(r"Sent here from `(aidlc-[a-z]+)` [^\n;]+; this skill's Gate, Stop if and Rules still apply\.")
LOAD = re.compile(r"\b[Ll]oad the `([a-z0-9-]+)` skill")
STOP_WORD = re.compile(r"\b[Ss]tops?\b")
NAMED_FILE = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9._-]+)`")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """The text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(text.split())


def skill_md(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


def references(name: str) -> dict:
    """A skill's references, by file name, in name order."""
    return {p.name: p.read_text(encoding="utf-8")
            for p in sorted((ROOT / "skills" / name / "references").glob("*.md"))}


def words(name: str) -> int:
    """The words in a skill's SKILL.md, front matter included, as `wc -w` counts them: runs of non-whitespace."""
    return len(skill_md(name).split())


def section(text: str, heading: str) -> str:
    """One `## ` section of a raw text, from its heading to the next `## ` heading."""
    start = text.index("\n" + heading + "\n")
    end = text.find("\n## ", start + len(heading) + 2)
    return text[start:] if end < 0 else text[start:end]


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def stop_sentences(text: str) -> list:
    """The sentences outside code that tell the AI to stop: each holds the word "stop" or "stops", in lower case or
    with a capital S. The bundle field `STOP IF`, in capitals or in a code span, is a field name, not a stop. A
    sentence ends at ". ", "? " or "! ", at a blank line, or where a list item or a table row begins."""
    parts = re.split(r"(?<=[.!?])\s+|\n\s*\n|\n(?=\s*(?:[-*]|\d+\.|\|)\s)", outside_code(text))
    return [re.sub(r"^(?:[-*]|\d+\.|\|)\s+", "", flat(p)) for p in parts if STOP_WORD.search(p)]


class ToolingTest(unittest.TestCase):
    """Task 1: the tests read a skill's references, and the stop rule finds a stop, not a field name."""

    def test_every_skill_helper_reads_skill_md_then_its_references(self):
        own = flat(read("skills/aidlc-onboard/SKILL.md"))
        ref = flat(read("skills/aidlc-onboard/references/suppression-rules.md"))
        for module in HELPER_FILES:
            text = importlib.import_module(module).skill("aidlc-onboard")
            self.assertTrue(text.startswith(own), module)
            self.assertIn(ref, text, module)

    def test_the_stop_rule_finds_a_stop_and_not_the_field_name(self):
        sample = ("1. Fill STOP IF with the limits.\n2. Copy `STOP IF` from the class.\n3. Any yes, stop: it is "
                  "route D2.\n4. A package it adds is a stop for the approver. Stop as this skill's Stop if says.\n")
        self.assertEqual(stop_sentences(sample), ["Any yes, stop: it is route D2.",
                                                  "A package it adds is a stop for the approver.",
                                                  "Stop as this skill's Stop if says."])

    def test_the_opening_line_names_the_skill(self):
        line = ("Sent here from `aidlc-plan` step 5, a plan with independent slices; this skill's Gate, Stop if and "
                "Rules still apply.")
        self.assertEqual(OPENING.fullmatch(line).group(1), "aidlc-plan")


class Layout:
    """The checks every shortened skill passes. A class sets NAME, REFS (its reference files, in name order) and
    LIMIT (the word target), and mixes this in with unittest.TestCase."""

    NAME, REFS, LIMIT = "", (), 0

    def ref(self, file_name: str) -> str:
        return read(f"skills/{self.NAME}/references/{file_name}")

    def test_skill_md_meets_its_word_target(self):
        self.assertLess(words(self.NAME), self.LIMIT, self.NAME)

    def test_its_references_are_the_planned_files(self):
        self.assertEqual(tuple(references(self.NAME)), self.REFS)

    def test_skill_md_names_each_reference_with_its_condition(self):
        text = flat(skill_md(self.NAME))
        for file_name in self.REFS:
            self.assertIn(f"read `references/{file_name}` now and follow it", text, file_name)

    def test_each_reference_opens_with_where_it_is_sent_from(self):
        for file_name in self.REFS:
            lines = self.ref(file_name).split("\n")
            self.assertTrue(lines[0].startswith("# "), file_name)
            self.assertEqual(lines[1], "", file_name)
            found = OPENING.fullmatch(lines[2])
            self.assertIsNotNone(found, (file_name, lines[2]))
            self.assertEqual(found.group(1), self.NAME, file_name)

    def test_the_gates_stay_whole_in_skill_md(self):
        raw = skill_md(self.NAME)
        positions = [raw.find("\n" + s + "\n") for s in SECTIONS]
        self.assertNotIn(-1, positions)
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(raw.count(DECIDE), 1)
        gate = flat(section(raw, "## Gate"))
        self.assertTrue(gate.endswith(DECIDE + " " + (LANE + " " if LANE in raw else "") + APPROVE), self.NAME)
        for file_name in self.REFS:
            text = self.ref(file_name)
            for heading in GATE_SECTIONS:
                self.assertNotIn("\n" + heading + "\n", "\n" + text, (file_name, heading))
            for line in (DECIDE, LANE, APPROVE):
                self.assertNotIn(line, flat(text), (file_name, line))

    def test_every_file_a_reference_names_exists(self):
        for file_name in self.REFS:
            for named in NAMED_FILE.findall(self.ref(file_name)):
                self.assertTrue((ROOT / "skills" / self.NAME / named).is_file(), (file_name, named))

    def test_load_phrases_stay_in_skill_md(self):
        for file_name in self.REFS:
            self.assertEqual(LOAD.findall(flat(self.ref(file_name))), [], file_name)

    def test_a_stop_in_a_reference_points_to_stop_if(self):
        for file_name in self.REFS:
            for sentence in stop_sentences(self.ref(file_name)):
                self.assertIn("Stop if", sentence, (file_name, sentence))


if __name__ == "__main__":
    unittest.main()
