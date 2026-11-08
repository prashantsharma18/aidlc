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

    def test_the_readme_and_every_quickstart_point_to_both(self):
        self.assertIn("docs/operating-model/routes.md", read("README.md"))
        self.assertIn("docs/operating-model/adoption.md", read("README.md"))
        for rel in ("docs/quickstart/claude-code.md", "docs/quickstart/copilot.md", "docs/quickstart/codex-cursor.md"):
            text = read(rel)
            self.assertIn("../operating-model/routes.md", text, rel)
            self.assertIn("../operating-model/adoption.md", text, rel)

    def test_no_document_still_waits_for_the_routes_page(self):
        self.assertNotIn("arrive in `routes.md` with Plan 17", read("docs/operating-model/lifecycle.md"))
        self.assertNotIn("Plan 17", read("docs/operating-model/workspace-and-repositories.md"))

    def test_links_in_the_new_documents_resolve(self):
        for rel in (ROUTES, ADOPTION):
            base = (ROOT / rel).parent
            for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", read(rel)):
                self.assertTrue((base / target).exists(), f"{rel}: {target}")


def slug(heading: str) -> str:
    """The anchor GitHub gives a heading: lower case, punctuation dropped, spaces as hyphens."""
    return re.sub(r"[^a-z0-9 -]", "", heading.lower()).replace(" ", "-")


class ReviewFixesTest(unittest.TestCase):
    """Plan 18 final review: each test was seen failing before its fix. The skills are the source of truth."""

    def setUp(self):
        self.routes = " ".join(read(ROUTES).split())
        self.adoption = " ".join(read(ADOPTION).split())
        self.sheet = self.adoption.split("## Who approves what", 1)[1]

    def test_i1_unaffected_is_a_line_in_the_story_index(self):
        self.assertNotIn("The tech lead records why, on the tracker", self.routes)
        self.assertIn("`UNAFFECTED <repository> spec v<n>: <why>, <who>, <date>` line in the story index", self.routes)
        self.assertIn("The story index (an `UNAFFECTED` line)", self.sheet)

    def test_i2_the_status_command_writes_with_write(self):
        self.assertIn("python3 scripts/story_status.py <KEY> --write", self.routes)

    def test_i3_a_defect_without_a_reproduction_stops(self):
        self.assertIn('ask["Ask the reporter, and stop"]', read(ROUTES))

    def test_i4_route_i_starts_at_aidlc_operate(self):
        self.assertNotIn('kind -->|"an alert fires"|', read(ROUTES))
        self.assertIn("one of seven routes", self.routes)
        self.assertIn("The eighth, I, does not start there", self.routes)

    def test_i5_the_sheet_holds_every_stage_gate(self):
        for row in ("The provisional tier", "Proceed, escalate or raise the tier after discovery", "A wireframe",
                    "Each review finding", "A specialist review (Tier 3)", "The incident follow-up item",
                    "The rules file and the codebase map", "Monitoring and rollback"):
            self.assertIn(f"| {row} |", self.sheet, row)

    def test_i6_the_tech_lead_approves_the_plan_at_every_tier(self):
        roles = read("docs/operating-model/roles.md")
        self.assertNotIn("| 1 | In the PR description |", roles)
        self.assertIn("| 1 | Tech lead, on the work item (a short plan) |", roles)

    def test_minors_in_routes(self):
        for phrase in ("Root->>A: status marks part 1 re-plan", "once `aidlc-plan` or `aidlc-build` reads the code",
                       "for D1, the written expected behaviour and the three design questions",
                       "Tech lead or architect approves, or records none needed", "revision <r>: <what>",
                       'start["aidlc-start: which repositories change?"]',
                       "an `explorer` agent goes into each repository", "each skill's Produces section",
                       "`stories/<KEY>/contract/`", "or the tier rises"):
            self.assertIn(phrase, read(ROUTES) + self.routes, phrase)

    def test_minors_in_adoption(self):
        for phrase in ("`ANTHROPIC_API_KEY`", "writes that test first, or stops", "asks whether this is a new system",
                       "chooses its MODE", "\"confirmed by\" line", "| Change management |", "RECORDED BY",
                       "posts only when you ask"):
            self.assertIn(phrase, self.adoption, phrase)
        self.assertNotIn("ships with stop criteria", self.adoption)
        self.assertNotIn("](../quickstart/)", self.adoption)

    def test_anchors_in_the_new_documents_resolve(self):
        for rel in (ROUTES, ADOPTION):
            text = read(rel)
            anchors = {slug(h) for h in re.findall(r"(?m)^#+ (.+)$", text)}
            for target in re.findall(r"\]\(#([^)]+)\)", text):
                self.assertIn(target, anchors, f"{rel}: #{target}")



class SkillWordingTest(unittest.TestCase):
    """Follow-ups from Plan 18: the skills say what the documents say."""

    TIERS = [f"skills/{s}/assets/tiers.md" for s in
             ("aidlc-start", "aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-plan", "aidlc-review")]

    def test_route_i_starts_at_aidlc_operate_everywhere(self):
        for rel in ("skills/using-aidlc/SKILL.md", "docs/operating-model/lifecycle.md"):
            text = " ".join(read(rel).split())
            self.assertNotIn("`aidlc-start` chooses one.", text, rel)
            self.assertNotIn("`aidlc-start` chooses one;", text, rel)
            self.assertIn("route I starts at `aidlc-operate` when an alert fires", text, rel)

    def test_the_tech_lead_approves_the_plan_at_every_tier(self):
        for rel in self.TIERS + ["docs/operating-model/tiers-table.md"]:
            row = next(line for line in read(rel).splitlines() if line.startswith("| Approvals"))
            tier1 = row.split("|")[2]
            self.assertIn("tech lead approves the plan", tier1, rel)
            self.assertIn("the engineer confirms a fast-path brief", tier1, rel)


class CommandsTest(unittest.TestCase):
    """The stage skills are the commands a person types: each shows its arguments, and the README lists them."""

    HINTS = {"aidlc-start": "[KEY or a short description]", "aidlc-onboard": "[new prepare | new confirm]",
             "aidlc-intent": "[KEY or a short description]", "aidlc-specify": "[KEY]", "aidlc-discover": "[KEY]",
             "aidlc-design": "[KEY]", "aidlc-plan": "[KEY]", "aidlc-build": "[KEY] [slice]", "aidlc-verify": "[KEY]",
             "aidlc-review": "[KEY]", "aidlc-release": "[KEY]", "aidlc-operate": "[incident ID]",
             "aidlc-feedback": "[incident ID or topic]"}

    def test_every_stage_skill_shows_its_arguments(self):
        stages = sorted(p.name for p in (ROOT / "skills").glob("aidlc-*") if p.is_dir())
        self.assertEqual(stages, sorted(self.HINTS))
        for name, hint in self.HINTS.items():
            head = read(f"skills/{name}/SKILL.md").split("\n---", 1)[0]
            self.assertIn(f'argument-hint: "{hint}"', head, name)

    def test_the_readme_lists_the_commands_you_type(self):
        readme = read("README.md")
        self.assertIn("## Commands you type", readme)
        table = readme.split("## Commands you type", 1)[1].split("\n## ", 1)[0]
        for name in self.HINTS:
            self.assertIn(f"`/aidlc:{name}", table, name)

    def test_every_quickstart_points_to_the_commands(self):
        for rel in ("docs/quickstart/claude-code.md", "docs/quickstart/copilot.md", "docs/quickstart/codex-cursor.md"):
            self.assertIn("../../README.md#commands-you-type", read(rel), rel)

if __name__ == "__main__":
    unittest.main()
