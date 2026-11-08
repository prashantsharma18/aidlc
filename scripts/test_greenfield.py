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

    def test_design_decides_a_new_system(self):
        design = skill("aidlc-design")
        self.assertIn("**New system** (route G)", section(design, "## When to use"))
        self.assertIn("`assets/new-system.md`", design)
        self.assertIn("approving this design is the approval to add them", design)
        self.assertIn("On route G there is no codebase map, rules file or ADR yet", section(design, "## Inputs"))
        template = read("plugins/aidlc/skills/aidlc-design/assets/new-system.md")
        for field in ("STACK", "DEPENDENCIES", "LAYOUT", "CONTRACTS", "NFR CHECKS", "QUALITY BAR", "COMMANDS",
                      "SCAFFOLD", "CI", "UI", "APPROVED"):
            self.assertIn(field, template, field)

    def test_a_stack_without_a_generator_has_no_scaffold(self):
        self.assertIn("| none: slice 0 writes the skeleton by hand", read("plugins/aidlc/skills/aidlc-design/assets/new-system.md"))

    def test_several_repositories_get_one_slice_0_part_each(self):
        self.assertIn("one slice-0 part each", skill("aidlc-design"))

    def test_onboard_has_a_new_mode_in_two_steps(self):
        onboard = skill("aidlc-onboard")
        self.assertIn("**New mode** (route G)", section(onboard, "## When to use"))
        self.assertIn("Prepare, before slice 0", onboard)
        self.assertIn("Confirm, after slice 0 merges", onboard)
        self.assertIn("each marked `(not yet run)`", onboard)
        self.assertIn("it is not a new system", section(onboard, "## Stop if"))
        self.assertIn("never run and is not marked `(not yet run)`", section(onboard, "## Red flags"))
        self.assertIn("(not yet run)", read("plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md"))

    def test_confirm_stops_on_a_command_that_fails(self):
        self.assertIn("stop on any that does not", skill("aidlc-onboard"))

    def test_plan_writes_slice_0(self):
        plan = skill("aidlc-plan")
        self.assertIn("**Slice 0** (route G)", section(plan, "## When to use"))
        self.assertIn("marked `(scaffold)`", plan)
        self.assertIn("seen red once", plan)
        self.assertIn("(scaffold)", read("plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md"))

    def test_slice_0_without_a_scaffold_is_written_by_hand(self):
        self.assertIn("When SCAFFOLD is none, there is no RECIPE", skill("aidlc-plan"))

    def test_build_runs_slice_0_under_the_usual_gates(self):
        build = skill("aidlc-build")
        self.assertIn("skip this step; the scaffold recipe commit comes first", build)
        self.assertIn("`Recipe: <tool>@<version> (scaffold)`", build)
        self.assertIn("is not checked by the recipe check", build)
        self.assertIn("(scaffold)", read("plugins/aidlc/agents/reviewer-compliance.md"))

    def test_the_docs_describe_route_g(self):
        self.assertNotIn("G, from aidlc 4.1", read("docs/operating-model/lifecycle.md"))
        self.assertIn("| New system |", read("docs/operating-model/workspace-and-repositories.md"))
        self.assertIn("route G", read("README.md"))
        self.assertTrue((ROOT / "docs/adr/0016-greenfield-entry.md").is_file())


if __name__ == "__main__":
    unittest.main()
