"""Plan 15: the feature fast path (route F0) and the build modes."""
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


class FastPathTest(unittest.TestCase):
    def test_start_chooses_f0(self):
        start = skill("aidlc-start")
        self.assertIn("**feature fast path (F0)** when all three hold", start)
        self.assertIn("acceptance criteria written on the work item by its owner", start)
        self.assertIn("F0 (a feature, fast path)", start)
        self.assertIn("**Feature fast path (F0):**", start)

    def test_the_index_and_the_map_know_f0(self):
        for name in ("aidlc-start", "aidlc-plan"):
            self.assertIn("<F0 | F1 | F2 | C | D1 | D2 | G>", read(f"plugins/aidlc/skills/{name}/assets/story-index.md"))
        self.assertIn("| F0 · feature, fast path |", skill("using-aidlc"))

    def test_plan_writes_a_feature_brief(self):
        plan = skill("aidlc-plan")
        self.assertIn("**Brief mode for a feature** (route F0)", plan)
        self.assertIn("`plans/<KEY>/brief.md`", plan)
        self.assertIn("Feature brief mode (route F0):", plan)
        self.assertIn("- feature-brief", (SKILLS / "aidlc-plan/SKILL.md").read_text(encoding="utf-8"))

    def test_the_brief_holds_every_condition(self):
        brief = read("plugins/aidlc/skills/aidlc-plan/assets/feature-brief.md")
        self.assertTrue(brief.startswith("<!-- aidlc template: feature-brief -->"))
        for field in ("CRITERIA", "OWNER", "TIER 1", "DESIGN none needed", "DEPENDENCIES none new",
                      "DATA no change", "MODE", "MAY CHANGE", "DONE WHEN", "STOP IF", "CONFIRMED"):
            self.assertIn(field, brief)

    def test_every_condition_failing_sends_the_feature_to_f1(self):
        steps = section(skill("aidlc-plan"), "Feature brief mode (route F0):")
        for condition in ("the three design questions", "a new dependency", "stored data or a schema changes",
                          "more than one slice"):
            self.assertIn(condition, steps)
        self.assertIn("it is route F1", steps)

    def test_a_late_failure_re_routes_through_start(self):
        start = skill("aidlc-start")
        self.assertIn("**Re-routing.**", start)
        self.assertIn("keeps every row already done", start)
        self.assertIn("F0 to F1, D1 to D2", start)

    def test_build_builds_from_a_feature_brief(self):
        build = skill("aidlc-build")
        self.assertIn("on route F0, the confirmed feature brief `plans/<KEY>/brief.md`", build)
        self.assertIn("(its slice is named `brief`)", build)
        stops = section(build, "## Stop if")
        self.assertIn("The feature brief's CONFIRMED line is empty", stops)
        self.assertIn("its DATA is not \"no change\"", stops)

    def test_verify_and_review_read_the_feature_brief(self):
        self.assertIn("On route F0, the feature brief `plans/<KEY>/brief.md`", skill("aidlc-verify"))
        self.assertIn("on route F0 the feature brief `plans/<KEY>/brief.md`", skill("aidlc-review"))
        compliance = read("plugins/aidlc/agents/reviewer-compliance.md")
        self.assertIn("On route D1 or F0 the brief", compliance)


if __name__ == "__main__":
    unittest.main()
