"""Plan 18: the routes and adoption documents exist, match the skills, keep Mermaid safe, and are linked."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = "docs/operating-model/routes.md"
ADOPTION = "docs/operating-model/adoption.md"
KINDS = ("flowchart", "sequenceDiagram", "stateDiagram-v2")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\n(.*?)```", text, re.S)


class DocsTest(unittest.TestCase):
    def test_every_route_in_using_aidlc_has_a_section(self):
        codes = re.findall(r"^\| (F0|F1|F2|C|D1|D2|I|G) · ", read("skills/using-aidlc/SKILL.md"), re.M)
        self.assertEqual(len(codes), 8)
        routes = read(ROUTES)
        for code in codes:
            self.assertRegex(routes, rf"(?m)^### {code} · ", code)

    def test_routes_covers_choice_parts_amendments_and_re_routing(self):
        routes = read(ROUTES)
        for heading in ("## Choosing a route", "## Linked parts (F2)", "## A criterion changes after code exists (C)",
                        "## Re-routing", "## Where the documents live"):
            self.assertIn(heading, routes)
        self.assertGreaterEqual(len(mermaid_blocks(routes)), 10)

    def test_mermaid_blocks_use_the_safe_subset(self):
        for rel in (ROUTES, ADOPTION):
            if not (ROOT / rel).is_file():
                continue
            for block in mermaid_blocks(read(rel)):
                lines = [line for line in block.splitlines() if line.strip()]
                self.assertTrue(lines[0].split()[0] in KINDS, f"{rel}: {lines[0]}")
                if lines[0].startswith("flowchart"):
                    for line in lines[1:]:
                        bare = re.search(r"\w(\{\{|\(\[|\(\(|\[|\{|\()(?=[^\"{\[(])", line)
                        self.assertIsNone(bare, f"{rel}: unquoted node label: {line.strip()}")
                        edge = re.search(r"\|(?!\")[^|]*\|", line)
                        self.assertIsNone(edge, f"{rel}: unquoted edge label: {line.strip()}")
                        if line.strip().startswith("subgraph"):
                            self.assertRegex(line, r'subgraph \w+ \["[^"]+"\]', f"{rel}: {line.strip()}")

    def test_adoption_covers_day_0_the_phases_and_the_sheet(self):
        adoption = read(ADOPTION)
        for heading in ("## Before you start", "## A new system: day 0", "## An existing system, in phases",
                        "### Phase 1: onboard, and value at low risk", "### Phase 2: pin the code you will change",
                        "### Phase 3: the full routes for new work", "### Phase 4: raise the bar, then delegate",
                        "## Who approves what"):
            self.assertIn(heading, adoption)

    def test_each_phase_names_its_skills(self):
        adoption = read(ADOPTION)
        for phase, skills in (("### Phase 1", ("aidlc-onboard", "aidlc-review", "aidlc-start")),
                              ("### Phase 2", ("writing-tests", "aidlc-discover")),
                              ("### Phase 3", ("aidlc-specify", "aidlc-plan", "aidlc-release")),
                              ("### Phase 4", ("Quality bar", "run_slices.py"))):
            start = adoption.index(phase)
            end = adoption.find("### Phase", start + 10)
            body = adoption[start:end if end > 0 else len(adoption)]
            for name in skills:
                self.assertIn(name, body, f"{phase}: {name}")

    def test_the_sheet_never_lets_the_author_approve(self):
        sheet = read(ADOPTION).split("## Who approves what", 1)[1]
        rows = [line for line in sheet.splitlines() if line.startswith("| ") and not line.startswith("| Decision")]
        self.assertGreaterEqual(len(rows), 15)
        self.assertIn("never the author", sheet)
        for row in rows:
            self.assertNotRegex(row.split("|")[2], r"(?i)\bagent\b|\bAI\b")

if __name__ == "__main__":
    unittest.main()
