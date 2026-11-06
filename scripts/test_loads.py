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


if __name__ == "__main__":
    unittest.main()
