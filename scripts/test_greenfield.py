"""Plan 13: a new system enters through route G and reaches an ordinary repository."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "aidlc" / "skills"


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def skill(name: str) -> str:
    return read(f"plugins/aidlc/skills/{name}/SKILL.md")


def section(body: str, heading: str) -> str:
    start = body.index(heading)
    end = body.find(" ## ", start + len(heading))
    return body[start:] if end < 0 else body[start:end]


class GreenfieldTest(unittest.TestCase):
    def test_start_accepts_a_new_system(self):
        start = skill("aidlc-start")
        self.assertIn("the kind is New system (route G)", start)
        self.assertIn("the agent never creates a repository", start)
        self.assertIn("On route G there is no `AGENTS.md` yet: skip this step.", start)
        self.assertIn("G (a new system)", start)
        self.assertIn("**New system (G):**", start)

    def test_start_counts_config_only_folders_as_empty(self):
        self.assertIn("only a README, a licence, a `.gitignore`, `.github/`, `docs/` or `plans/`", skill("aidlc-start"))

    def test_a_folder_with_agents_md_is_never_route_g(self):
        start = skill("aidlc-start")
        self.assertIn("A folder with `AGENTS.md` is never route G", start)
        self.assertIn("name `aidlc-onboard`, and stop", start)

    def test_the_index_and_the_map_know_route_g(self):
        for rel in ("plugins/aidlc/skills/aidlc-start/assets/story-index.md",
                    "plugins/aidlc/skills/aidlc-plan/assets/story-index.md"):
            text = read(rel)
            self.assertIn("| G>", text, rel)
            self.assertIn("| new system>", text, rel)
        self.assertIn("G · new system", section(skill("using-aidlc"), "## The routes"))


if __name__ == "__main__":
    unittest.main()
