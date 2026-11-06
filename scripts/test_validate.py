"""Tests for scripts/validate.py: each builds a small package in a temporary folder."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

STAGE_BODY = """# Title

## When to use
x
## Inputs
x
## Steps
1. See `assets/plan.md`.
## Produces
x
## Gate
You draft; you never approve.
## Stop if
x
## Common excuses
x
## Red flags
x
## Rules
x
"""

SECRET_DENIES = ["Read(**/.env)", "Read(~/.ssh/**)"]
REPO_SETTINGS = {"permissions": {"deny": SECRET_DENIES}}
WORKSPACE_SETTINGS = {"permissions": {"allow": ["Edit(/stories/**)"], "deny": SECRET_DENIES}}
EXPLORER = "---\nname: explorer\ndescription: Reads.\n---\nbody\n"


def write_plugin(root: Path, name: str, skills: dict[str, str], agents: dict[str, str] | None = None,
                 assets=("plan.md",), version="2.0.0", deps=None):
    base = root / "plugins" / name
    for skill_name, text in skills.items():
        d = base / "skills" / skill_name
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
        for a in assets:
            (d / "assets" / a).write_text("x", encoding="utf-8")
    if agents is not None:
        (base / "agents").mkdir(parents=True, exist_ok=True)
        for agent_name, text in agents.items():
            (base / "agents" / f"{agent_name}.md").write_text(text, encoding="utf-8")
    (base / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "version": version}
    if deps is not None:
        manifest["dependencies"] = deps
    (base / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")


def package(root: Path, skills: dict[str, str], agents: dict[str, str] | None = None, assets=("plan.md",),
            packs=()):
    write_plugin(root, "aidlc", skills, agents or {"explorer": EXPLORER}, assets)
    for pack in packs:
        write_plugin(root, **pack)
    entries = [{"name": "aidlc", "source": "./plugins/aidlc"}]
    entries += [{"name": p["name"], "source": f"./plugins/{p['name']}"} for p in packs]
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "aidlc", "plugins": entries}), encoding="utf-8")
    for kind, settings in (("repo", REPO_SETTINGS), ("workspace", WORKSPACE_SETTINGS)):
        (root / "starter" / kind / ".claude").mkdir(parents=True)
        (root / "starter" / kind / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")


def skill(name, description="Does things. Use when needed.", body=STAGE_BODY):
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}"


PRACTICE_BODY = """# Title

## When to use
x
## Steps
1. x
## Checks
x
## Stop if
x
## Common excuses
x
## Red flags
x
## Rules
- You draft; you never approve.
"""


def practice(name, body=PRACTICE_BODY, kind="practice"):
    return (f"---\nname: {name}\ndescription: Does things. Use when needed.\nmetadata:\n  kind: {kind}\n"
            f"  invocation: auto\n---\n{body}")


class ValidateTest(unittest.TestCase):
    def check(self, skills, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            package(Path(tmp), skills, **kw)
            return validate.validate(Path(tmp))

    def test_a_good_package_has_no_problems(self):
        self.assertEqual(self.check({"aidlc-plan": skill("aidlc-plan")}), [])

    def test_name_must_equal_the_folder(self):
        problems = self.check({"aidlc-plan": skill("aidlc-planner")})
        self.assertTrue(any("does not match its folder" in p for p in problems), problems)

    def test_description_needs_use_when(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan", description="Does things.")})
        self.assertTrue(any("Use when" in p for p in problems), problems)

    def test_stage_skills_keep_the_sections_and_the_gate_line(self):
        body = STAGE_BODY.replace("## Red flags\nx\n", "").replace("You draft; you never approve.", "ok")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
        self.assertTrue(any("## Red flags" in p for p in problems), problems)
        self.assertTrue(any("You draft; you never approve." in p for p in problems), problems)

    def test_a_removed_harness_command_is_a_problem(self):
        body = STAGE_BODY.replace("1. See `assets/plan.md`.\n", "1. See `assets/plan.md`.\n2. Run `aidlc check` first.\n")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
        self.assertTrue(any("removed harness command" in p for p in problems), problems)

    def test_a_named_asset_must_exist(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, assets=())
        self.assertTrue(any("assets/plan.md" in p for p in problems), problems)

    def test_agents_need_name_and_description(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, agents={"x": "---\nname: x\n---\nbody\n"})
        self.assertTrue(any("agents/x.md" in p and "description" in p for p in problems), problems)

    def test_practice_skills_need_only_the_open_format(self):
        practice = "---\nname: debugging\ndescription: Debugs. Use when a test fails.\n---\n# Debugging\n"
        self.assertEqual(self.check({"debugging": practice}, assets=()), [])

    def test_a_practice_in_the_practice_format_has_no_problems(self):
        self.assertEqual(self.check({"writing-tests": practice("writing-tests")}), [])

    def test_a_practice_needs_every_practice_section(self):
        body = PRACTICE_BODY.replace("## Checks\nx\n", "")
        problems = self.check({"writing-tests": practice("writing-tests", body=body)})
        self.assertTrue(any("missing section '## Checks'" in p for p in problems), problems)

    def test_a_practice_keeps_the_sections_in_order(self):
        body = PRACTICE_BODY.replace("## Steps\n1. x\n## Checks\nx\n", "## Checks\nx\n## Steps\n1. x\n")
        problems = self.check({"writing-tests": practice("writing-tests", body=body)})
        self.assertTrue(any("out of order" in p for p in problems), problems)

    def test_a_practice_ends_its_rules_with_the_gate_line(self):
        body = PRACTICE_BODY.replace("- You draft; you never approve.", "- ok")
        problems = self.check({"writing-tests": practice("writing-tests", body=body)})
        self.assertTrue(any("You draft; you never approve." in p for p in problems), problems)

    def test_a_quoted_practice_kind_is_still_a_practice(self):
        problems = self.check({"writing-tests": practice("writing-tests", body="# Essay\n", kind="'practice'")})
        self.assertTrue(any("missing section '## Steps'" in p for p in problems), problems)

    def test_an_earlier_practice_keeps_its_shape_until_rewritten(self):
        essay = practice("reviewing-code", body="# Reviewing Code\n\nAn essay.\n")
        self.assertEqual(self.check({"reviewing-code": essay}), [])

    def test_the_earlier_practices_are_real_core_skills(self):
        core = Path(__file__).resolve().parents[1] / "plugins" / "aidlc" / "skills"
        for name in sorted(validate.EARLIER_PRACTICES):
            self.assertTrue((core / name / "SKILL.md").is_file(), name)

    def test_the_quality_bar_exception_reads_the_same_everywhere(self):
        root = Path(__file__).resolve().parents[1]
        files = ("plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md",
                 "plugins/aidlc/skills/aidlc-build/SKILL.md", "plugins/aidlc/agents/reviewer-compliance.md")
        for rel in files:
            self.assertIn("a reason, an owner and an expiry date", (root / rel).read_text(encoding="utf-8"), rel)

    def test_a_plugin_source_outside_plugins_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./"}]}))
            self.assertTrue(any("marketplace" in p for p in validate.validate(root)))

    def test_harness_references_in_assets_are_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / "plugins" / "aidlc" / "skills" / "aidlc-plan" / "assets" / "plan.md").write_text("See core/policy/tiers.yaml.")
            problems = validate.validate(root)
        self.assertTrue(any("assets/plan.md" in p and "core/policy" in p for p in problems), problems)

    def test_removed_commands_are_found_across_spaces_and_line_breaks(self):
        for wrapped in ("Run `aidlc  check`.", "Run aidlc\ncheck first."):
            body = STAGE_BODY.replace("## Produces", wrapped + "\n## Produces")
            problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
            self.assertTrue(any("removed harness command" in p for p in problems), (wrapped, problems))

    def test_tool_specific_syntax_is_a_problem(self):
        for text in ("Run `/aidlc:plan` next.", "Plan $ARGUMENTS."):
            body = STAGE_BODY.replace("## Produces", text + "\n## Produces")
            problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
            self.assertTrue(any("tool-specific" in p for p in problems), (text, problems))

    def test_a_missing_agents_folder_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            for f in (root / "plugins" / "aidlc" / "agents").iterdir():
                f.unlink()
            (root / "plugins" / "aidlc" / "agents").rmdir()
            self.assertTrue(any("agents/" in p for p in validate.validate(root)))

    def test_the_workspace_starter_never_allows_a_whole_tool(self):
        bad = {"permissions": {"allow": ["Read", "Edit(/stories/**)"], "deny": SECRET_DENIES}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / "starter" / "workspace" / ".claude" / "settings.json").write_text(json.dumps(bad))
            problems = validate.validate(root)
        self.assertTrue(any("starter/workspace" in p and "'Read'" in p for p in problems), problems)

    def test_the_workspace_starter_denies_every_secret_the_repo_starter_denies(self):
        thin = {"permissions": {"allow": ["Edit(/stories/**)"], "deny": ["Read(**/.env)"]}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / "starter" / "workspace" / ".claude" / "settings.json").write_text(json.dumps(thin))
            problems = validate.validate(root)
        self.assertTrue(any("starter/workspace" in p and "Read(~/.ssh/**)" in p for p in problems), problems)


    PACK = {"name": "aidlc-modernize", "skills": {"modernize-assess": None}, "version": "0.1.0",
            "deps": [{"name": "aidlc", "version": "^2.0"}]}

    def pack(self, **changes):
        p = dict(self.PACK, **changes)
        p["skills"] = {k: v or skill(k) for k, v in p["skills"].items()}
        return p

    def test_a_core_and_pack_marketplace_has_no_problems(self):
        self.assertEqual(self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack()]), [])

    def test_skill_names_are_unique_across_plugins(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")},
                              packs=[self.pack(skills={"aidlc-plan": None})])
        self.assertTrue(any("unique" in p and "aidlc-plan" in p for p in problems), problems)

    def test_core_never_names_a_pack(self):
        body = STAGE_BODY.replace("## Produces", "Then run modernize-assess.\n## Produces")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)}, packs=[self.pack()])
        self.assertTrue(any("never names a pack" in p and "modernize-assess" in p for p in problems), problems)

    def test_core_requires_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack()])
            core = root / "plugins" / "aidlc" / ".claude-plugin" / "plugin.json"
            core.write_text(json.dumps({"name": "aidlc", "version": "2.0.0", "dependencies": ["aidlc-modernize"]}))
            self.assertTrue(any("core requires nothing" in p for p in validate.validate(root)))

    def test_a_dependency_must_be_in_the_marketplace(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack(deps=["aidlc-elsewhere"])])
        self.assertTrue(any("aidlc-elsewhere" in p for p in problems), problems)

    def test_versions_are_semantic(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack(version="latest")])
        self.assertTrue(any("semantic version" in p for p in problems), problems)

    def test_a_named_reference_or_script_must_exist(self):
        body = STAGE_BODY.replace("## Produces", "Read `references/hop.md`; run `scripts/go.py`.\n## Produces")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
        self.assertTrue(any("references/hop.md" in p for p in problems), problems)
        self.assertTrue(any("scripts/go.py" in p for p in problems), problems)

    def test_pack_stage_skills_keep_the_house_sections(self):
        bare = "---\nname: modernize-assess\ndescription: Assesses. Use when asked.\n---\n# Assess\n"
        problems = self.check({"aidlc-plan": skill("aidlc-plan")},
                              packs=[self.pack(skills={"modernize-assess": bare})])
        self.assertTrue(any("modernize-assess" in p and "## Gate" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
