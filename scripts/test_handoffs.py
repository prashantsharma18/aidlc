"""Plan 19: hand-off documents a person reviews show every gap, open with the decision, and read as sections."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VANISHING = re.compile(r"<[A-Za-z][^<>\n]*>")  # GitHub reads <word ...> as an HTML tag and drops it
FENCED = ["aidlc-intent/assets/intent.md", "aidlc-discover/assets/evidence-pack.md",
          "aidlc-design/assets/design-note.md", "aidlc-design/assets/new-system.md",
          "aidlc-design/assets/coordination-plan.md", "aidlc-design/assets/decision-frame.md",
          "aidlc-plan/assets/plan.md", "aidlc-plan/assets/task-bundle.md", "aidlc-plan/assets/fix-brief.md",
          "aidlc-plan/assets/feature-brief.md", "aidlc-discover/assets/explorer-brief.md",
          "aidlc-onboard/assets/explorer-brief.md", "aidlc-review/assets/security-review.md",
          "aidlc-release/assets/release-runbook.md", "aidlc-operate/assets/runbook.md",
          "aidlc-start/assets/story-index.md", "aidlc-plan/assets/story-index.md"]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def vanishing(rel: str) -> list[str]:
    return VANISHING.findall(outside_code(read(rel)))


class HandoffsTest(unittest.TestCase):
    def test_field_blocks_sit_in_text_fences(self):
        for name in FENCED:
            rel = f"skills/{name}"
            text = read(rel)
            self.assertIn("```text\n", text, rel)
            self.assertEqual(text.count("```") % 2, 0, rel)
            self.assertEqual(vanishing(rel), [], rel)
            self.assertNotRegex(outside_code(text), r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S", rel)

    def test_every_fence_is_a_text_fence(self):
        for path in sorted((ROOT / "skills").glob("aidlc-*/assets/*.md")):
            for opening in re.findall(r"(?m)^```(\S*)$", path.read_text(encoding="utf-8"))[::2]:
                self.assertEqual(opening, "text", path)

    def test_copies_stay_identical(self):
        self.assertEqual(read("skills/aidlc-start/assets/story-index.md"),
                         read("skills/aidlc-plan/assets/story-index.md"))
        self.assertEqual(read("skills/aidlc-discover/assets/explorer-brief.md"),
                         read("skills/aidlc-onboard/assets/explorer-brief.md"))


    CONVERTED = ["aidlc-design/assets/adr.md", "aidlc-onboard/assets/agents-md.md",
                 "aidlc-onboard/assets/codebase-map.md", "aidlc-release/assets/compat-matrix.md",
                 "aidlc-build/assets/progress-note.md", "aidlc-specify/assets/spec.md",
                 "aidlc-onboard/assets/workspace.md", "aidlc-review/assets/review-record.md"]

    def test_heading_documents_write_placeholders_in_braces(self):
        for name in self.CONVERTED:
            rel = f"skills/{name}"
            self.assertEqual(vanishing(rel), [], rel)
            self.assertIn("{{", read(rel), rel)

    REWRITTEN = ["aidlc-review/assets/pr-description.md", "aidlc-verify/assets/evidence-table.md",
                 "aidlc-release/assets/readiness.md", "aidlc-release/assets/change-record.md",
                 "aidlc-operate/assets/incident.md"]

    def test_rendered_documents_read_as_sections(self):
        for name in self.REWRITTEN:
            rel = f"skills/{name}"
            text = read(rel)
            self.assertRegex(text, r"(?m)^# ", rel)
            self.assertGreaterEqual(len(re.findall(r"(?m)^## ", text)), 3, rel)
            self.assertNotRegex(outside_code(text), r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S", rel)
            self.assertEqual(vanishing(rel), [], rel)
        self.assertEqual(read("skills/aidlc-operate/assets/incident.md"),
                         read("skills/aidlc-feedback/assets/incident.md"))

    def test_rewritten_documents_keep_the_labels_skills_name(self):
        incident = read("skills/aidlc-operate/assets/incident.md")
        self.assertIn("## Prevention", incident)
        self.assertIn("## Measures", incident)
        evidence = read("skills/aidlc-verify/assets/evidence-table.md")
        self.assertIn("## Unproved", evidence)
        self.assertIn("plans/<KEY>/** exempt", evidence)
        self.assertIn("| Criterion | Test | Local | Trusted CI |", evidence)
        readiness = read("skills/aidlc-release/assets/readiness.md")
        self.assertEqual(readiness.count("- [ ] "), 10)
        verify = " ".join(read("skills/aidlc-verify/SKILL.md").split())
        self.assertNotIn("UNPROVED", verify)
        release = " ".join(read("skills/aidlc-release/SKILL.md").split())
        self.assertNotIn("in a column of `assets/readiness.md`", release)
        self.assertIn("under its heading in `assets/readiness.md`", release)

    APPROVALS = {
        "aidlc-intent/assets/intent.md": ("aidlc-intent", "product owner", "tracker"),
        "aidlc-specify/assets/spec.md": ("aidlc-specify", "spec owner", "work item"),
        "aidlc-discover/assets/evidence-pack.md": ("aidlc-discover", "tech lead", "DECISION line"),
        "aidlc-design/assets/design-note.md": ("aidlc-design", "tech lead or architect", "APPROVED"),
        "aidlc-design/assets/new-system.md": ("aidlc-design", "tech lead or architect", "APPROVED line"),
        "aidlc-plan/assets/plan.md": ("aidlc-plan", "tech lead", "work item"),
        "aidlc-plan/assets/task-bundle.md": ("aidlc-plan", "tech lead", "work item"),
        "aidlc-plan/assets/fix-brief.md": ("aidlc-plan", "engineer", "CONFIRMED line"),
        "aidlc-plan/assets/feature-brief.md": ("aidlc-plan", "engineer", "CONFIRMED line"),
        "aidlc-review/assets/pr-description.md": ("aidlc-review", "code owner", "pull request"),
        "aidlc-review/assets/review-record.md": ("aidlc-review", "code owner", "DECISION"),
        "aidlc-review/assets/security-review.md": ("aidlc-review", "specialist", "GATE line"),
        "aidlc-release/assets/readiness.md": ("aidlc-release", "release approver", "change management"),
        "aidlc-release/assets/change-record.md": ("aidlc-release", "release approver", "change management"),
    }

    def test_each_approval_document_opens_with_the_decision(self):
        for name in self.APPROVALS:
            text = read(f"skills/{name}")
            block = text.index("## For the reviewer")
            first_fence = text.find("```")
            other_sections = [m.start() for m in re.finditer(r"(?m)^## (?!For the reviewer)", text)]
            self.assertTrue(first_fence < 0 or block < first_fence, name)
            self.assertTrue(not other_sections or block < min(other_sections), name)
            for label in ("**Asked of:**", "**Record it:**", "**Tier and main risk:**",
                          "**Changed since the last version:**"):
                self.assertIn(label, text, name)
            self.assertEqual(vanishing(f"skills/{name}"), [], name)

    def test_each_decision_block_matches_its_gate(self):
        for name, (skill, who, where) in self.APPROVALS.items():
            block = read(f"skills/{name}").split("## For the reviewer", 1)[1].split("\n## ", 1)[0]
            block = " ".join(block.split())
            gate = " ".join(read(f"skills/{skill}/SKILL.md").split("## Gate", 1)[1].split("\n## ", 1)[0].split())
            self.assertIn(who, block.lower(), name)
            self.assertIn(where, block, name)
            self.assertIn(who.split(" or ")[0], gate.lower(), f"{name}: the Gate of {skill} does not name {who}")

    def test_no_template_has_a_placeholder_that_vanishes(self):
        offenders = {}
        for path in sorted((ROOT / "skills").glob("aidlc-*/assets/*.md")):
            rel = str(path.relative_to(ROOT))
            found = vanishing(rel)
            if found:
                offenders[rel] = found[:3]
        self.assertEqual(offenders, {})

    def test_agents_md_states_the_template_rule(self):
        text = " ".join(read("AGENTS.md").split())
        self.assertIn("a placeholder outside a code block is written `{{…}}`", text)
        self.assertIn("a block of FIELD lines sits in a ```text fence", text)
        self.assertIn("opens with a `## For the reviewer` section", text)


class ReviewFixesTest(unittest.TestCase):
    """Plan 19 final review: each test was seen failing before its fix."""

    def test_i2_the_review_record_names_who_gives_the_decision(self):
        block = " ".join(read("skills/aidlc-review/assets/review-record.md").split("## For the reviewer", 1)[1]
                         .split("Reviewer:", 1)[0].split())
        self.assertIn("the reviewer named below, to give the DECISION", block)

    def test_m1_every_template_keeps_the_rule(self):
        for path in sorted((ROOT / "skills").glob("aidlc-*/assets/*.md")):
            out = outside_code(path.read_text(encoding="utf-8"))
            self.assertEqual(re.findall(r"<(?!!--)[^<>\n]+>", out), [], path)
            self.assertNotRegex(out, r"(?m)^[A-Z][A-Z /-]{2,}\s{2,}\S", path)
        for name in ("aidlc-design/assets/adr.md", "aidlc-design/assets/coordination-plan.md"):
            self.assertIn("## For the reviewer", read(f"skills/{name}"), name)

    def test_m3_m4_skills_match_the_templates(self):
        feedback = " ".join(read("skills/aidlc-feedback/SKILL.md").split())
        self.assertNotIn("Prevention line", feedback)
        self.assertIn("Prevention section", feedback)
        for skill in ("aidlc-intent", "aidlc-specify", "aidlc-plan", "aidlc-verify"):
            self.assertIn("leaving every approval slot for the person who approves",
                          " ".join(read(f"skills/{skill}/SKILL.md").split()), skill)

    def test_m5_blocks_match_the_gate_and_the_sheet(self):
        self.assertIn("Tier 3 adds the specialists", read("skills/aidlc-design/assets/design-note.md"))
        self.assertIn("the owning team's confirmation in this record", read("skills/aidlc-release/assets/readiness.md"))

    def test_m6_m7_fences_cannot_be_broken_by_accident(self):
        self.assertNotRegex(read("AGENTS.md"), r"(?m)^\s*```text")
        for name in ("fix-brief", "feature-brief", "task-bundle"):
            self.assertIn("three backticks would end the block", read(f"skills/aidlc-plan/assets/{name}.md"), name)


if __name__ == "__main__":
    unittest.main()
