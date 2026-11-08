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

    TIER_TABLES = [f"plugins/aidlc/skills/{s}/assets/tiers.md" for s in
                   ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review")]

    def test_the_tier_tables_name_the_modes(self):
        rows = []
        for rel in self.TIER_TABLES + ["docs/operating-model/tiers-table.md"]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            row = next(line for line in text.splitlines() if line.startswith("| Agent autonomy"))
            rows.append(row)
            self.assertIn("delegate with checkpoints", row, rel)
            self.assertIn("Hands-on only", row, rel)
            self.assertIn("`brief.md` for a feature", text, rel)
        self.assertEqual(len(set(rows)), 1)
        tables = {tuple(line for line in (ROOT / rel).read_text(encoding="utf-8").splitlines()
                        if line.startswith("|")) for rel in self.TIER_TABLES}
        self.assertEqual(len(tables), 1)  # the copies' headings differ; their tables do not

    def test_bundle_and_briefs_carry_the_mode(self):
        bundle = (SKILLS / "aidlc-plan/assets/task-bundle.md").read_text(encoding="utf-8")
        self.assertRegex(bundle, r"(?m)^TIER\s+<1 \| 2 \| 3>")
        self.assertRegex(bundle, r"(?m)^MODE\s+<hands-on \| delegate with checkpoints \| delegate>")
        self.assertIn("CHECKPOINT: <what the person checks here>", bundle)
        for name in ("fix-brief", "feature-brief"):
            text = (SKILLS / f"aidlc-plan/assets/{name}.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^MODE\s+<hands-on", name)

    def test_plan_proposes_a_mode_within_the_tier(self):
        plan = skill("aidlc-plan")
        self.assertIn("If unsure, choose the more hands-on mode.", plan)
        self.assertIn("hands-on (every tier), delegate with checkpoints (Tiers 1 and 2) or delegate (Tier 1)", plan)
        self.assertIn("a CHECKPOINT in DO before each step that touches a contract or another owner's code", plan)
        self.assertIn("Propose MODE; the engineer chooses it when confirming.", plan)

    def test_build_reads_the_mode(self):
        build = skill("aidlc-build")
        self.assertIn("Read the bundle's TIER and MODE.", build)
        self.assertIn("Hands-on: wait for the person to confirm.", build)
        self.assertIn("go on without waiting", build)
        self.assertIn("hands-on and delegate with checkpoints stop", build)
        self.assertIn("the slice runner named in AGENTS.md", build)
        self.assertNotIn("claude -p", build)

    def test_a_bundle_without_mode_runs_hands_on(self):
        self.assertIn("A bundle with no MODE line runs hands-on.", skill("aidlc-build"))

    def test_build_stops_on_a_mode_the_tier_does_not_allow(self):
        stops = section(skill("aidlc-build"), "## Stop if")
        self.assertIn("The bundle's MODE is not allowed at its TIER", stops)

    def test_every_mode_keeps_every_stop(self):
        build = skill("aidlc-build")
        self.assertIn("The modes change only when the build waits for the person, never what stops it.", build)
        self.assertIn("in every mode", section(build, "## Steps"))
        self.assertIn("`stopped: <reason>`", build)

    def test_the_progress_note_has_a_status_and_is_committed_first(self):
        note = (SKILLS / "aidlc-build/assets/progress-note.md").read_text(encoding="utf-8")
        self.assertRegex(note, r"(?m)^STATUS\s+doing\s+\(")
        self.assertRegex(note, r"(?m)^MODE\s+")
        self.assertIn("## Restatement", note)
        build = skill("aidlc-build")
        self.assertIn("commit the note on its own before any other commit of the slice", build)
        self.assertNotIn("commit it with the slice's first commit", build)

    def test_compliance_checks_status_and_mode(self):
        compliance = read("plugins/aidlc/agents/reviewer-compliance.md")
        self.assertIn("Each progress note's STATUS reads done", compliance)
        self.assertIn("a MODE its TIER does not allow is a high finding", compliance)

    def test_the_runner_is_named_where_it_is_used(self):
        self.assertIn("python3 scripts/run_slices.py <KEY> <slice>", read("starter/repo/AGENTS.md"))
        self.assertIn("`run_slices.py`", skill("aidlc-onboard"))


if __name__ == "__main__":
    unittest.main()
