"""Plan 13: a new system enters through route G and reaches an ordinary repository."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def read(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join((ROOT / rel).read_text(encoding="utf-8").split())


def skill(name: str) -> str:
    return read(f"skills/{name}/SKILL.md")


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
        for rel in ("skills/aidlc-start/assets/story-index.md",
                    "skills/aidlc-plan/assets/story-index.md"):
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
        template = read("skills/aidlc-design/assets/new-system.md")
        for field in ("STACK", "DEPENDENCIES", "LAYOUT", "CONTRACTS", "NFR CHECKS", "QUALITY BAR", "COMMANDS",
                      "SCAFFOLD", "CI", "UI", "APPROVED"):
            self.assertIn(field, template, field)

    def test_a_stack_without_a_generator_has_no_scaffold(self):
        self.assertIn("| none: slice 0 writes the skeleton by hand", read("skills/aidlc-design/assets/new-system.md"))

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
        self.assertIn("(not yet run)", read("skills/aidlc-onboard/assets/agents-md.md"))

    def test_confirm_stops_on_a_command_that_fails(self):
        self.assertIn("stop on any that does not", skill("aidlc-onboard"))

    def test_plan_writes_slice_0(self):
        plan = skill("aidlc-plan")
        self.assertIn("**Slice 0** (route G)", section(plan, "## When to use"))
        self.assertIn("marked `(scaffold)`", plan)
        self.assertIn("seen red once", plan)
        self.assertIn("(scaffold)", read("skills/aidlc-plan/assets/task-bundle.md"))

    def test_slice_0_without_a_scaffold_is_written_by_hand(self):
        self.assertIn("When SCAFFOLD is none, there is no RECIPE", skill("aidlc-plan"))

    def test_build_runs_slice_0_under_the_usual_gates(self):
        build = skill("aidlc-build")
        self.assertIn("skip this step; the scaffold recipe commit comes first", build)
        self.assertIn("`Recipe: <tool>@<version> (scaffold)`", build)
        self.assertIn("is not checked by the recipe check", build)
        self.assertIn("(scaffold)", read("agents/reviewer-compliance.md"))

    def test_the_docs_describe_route_g(self):
        self.assertNotIn("G, from aidlc 4.1", read("docs/operating-model/lifecycle.md"))
        self.assertIn("| New system |", read("docs/operating-model/workspace-and-repositories.md"))
        self.assertIn("route G", read("README.md"))
        self.assertTrue((ROOT / "docs/adr/0016-greenfield-entry.md").is_file())

    # Final review fixes
    def test_confirm_does_not_stop_on_the_skeleton_it_needs(self):
        stop = section(skill("aidlc-onboard"), "## Stop if")
        self.assertNotIn("In new mode, the folder already holds code", stop)
        self.assertIn("In new mode, prepare finds source code or a build manifest", stop)

    def test_plan_runs_slice_0_without_a_map(self):
        self.assertIn("On slice 0 of route G there is no map yet", section(skill("aidlc-plan"), "## Inputs"))

    def test_slice_0_may_add_only_the_approved_dependencies(self):
        plan, build = skill("aidlc-plan"), skill("aidlc-build")
        self.assertIn("lists the approved DEPENDENCIES", plan)
        self.assertIn("pins each direct dependency", plan)
        self.assertIn("a dependency listed in the approved `new-system.md` is not new", build)
        self.assertIn("DEPENDENCIES", read("agents/reviewer-compliance.md"))

    def test_route_g_has_one_sequence_of_pull_requests(self):
        start = skill("aidlc-start")
        self.assertIn("each step's pull request merges before the next starts", start)
        self.assertIn("re-runs `aidlc-onboard` at the workspace root", start)
        self.assertIn("`feat/<KEY>-slice-0`", start)
        self.assertIn("`aidlc-onboard (prepare)`, `slice 0` and `aidlc-onboard (confirm)`", start)
        self.assertIn("ends with `aidlc-release`", start)
        self.assertIn("When repositories are added on route G", skill("aidlc-onboard"))
        self.assertIn("even for one repository", skill("aidlc-design"))
        self.assertIn("the system and the first criteria it must meet", skill("aidlc-specify"))
        self.assertIn("On slice 0 of route G, the rows are the bundle's DONE WHEN checks", skill("aidlc-verify"))
        self.assertIn("and `aidlc-release`", section(skill("using-aidlc"), "## The routes"))

    def test_new_system_has_one_block_per_repository(self):
        import re
        text = (ROOT / "skills/aidlc-design/assets/new-system.md").read_text(encoding="utf-8")
        for field in ("STACK", "DEPENDENCIES", "LAYOUT", "CONTRACTS", "NFR CHECKS", "QUALITY BAR", "COMMANDS",
                      "SCAFFOLD", "CI", "UI", "APPROVED", "REPOSITORY", "PATHS"):
            self.assertRegex(text, rf"(?m)^\s*{field}\s", field)
        self.assertIn("one REPOSITORY block per repository", text)

    def test_ci_and_branch_protection_have_owners(self):
        onboard, plan = skill("aidlc-onboard"), skill("aidlc-plan")
        self.assertIn("slice 0 writes the CI workflow", onboard)
        self.assertIn("branch protection", onboard)
        self.assertIn("marks slice 0's checks as required", onboard)
        self.assertIn("`.github/workflows/ci.yml`", plan)
        self.assertIn("`ai-review.yml`", plan)

    def test_a_scaffold_trailer_outside_slice_0_is_a_finding(self):
        compliance = read("agents/reviewer-compliance.md")
        self.assertIn("outside slice 0 of a story whose index ROUTE is G", compliance)
        self.assertIn("does not apply to a `(scaffold)` commit", compliance)

    def test_review_minors_are_closed(self):
        onboard, start, plan, design = (skill(n) for n in ("aidlc-onboard", "aidlc-start", "aidlc-plan", "aidlc-design"))
        self.assertIn("mark its row in the index", onboard)
        self.assertIn("no source code and no build manifest", start)
        self.assertIn("On route G, step 9 runs after", design)
        self.assertIn("in slice 0 of route G, the approved scaffold", plan)
        self.assertIn("<!-- On route G", read("skills/aidlc-onboard/assets/agents-md.md"))
        fm = (SKILLS / "aidlc-start/SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertIn("new system", fm)
        self.assertIn("`../stories/<KEY>/new-system.md`", onboard)


if __name__ == "__main__":
    unittest.main()
