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

if __name__ == "__main__":
    unittest.main()
