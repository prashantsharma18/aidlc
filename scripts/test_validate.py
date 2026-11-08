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
    base = root
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
            version="2.0.0"):
    write_plugin(root, "aidlc", skills, agents or {"explorer": EXPLORER}, assets, version=version)
    entries = [{"name": "aidlc", "source": "./"}]
    (root / ".claude-plugin").mkdir(exist_ok=True)
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

    def test_a_practice_kind_with_a_comment_is_still_a_practice(self):
        problems = self.check({"writing-tests": practice("writing-tests", body="# Essay\n",
                                                         kind="practice  # see ADR 0013")})
        self.assertTrue(any("missing section '## Steps'" in p for p in problems), problems)

    def test_the_earlier_practice_list_only_shrinks(self):
        eight = {"adding-observability", "building-user-interfaces", "debugging-failures", "designing-apis",
                 "migrating-safely", "reviewing-code", "securing-code", "tuning-performance"}
        self.assertLessEqual(set(validate.EARLIER_PRACTICES), eight)

    def test_an_earlier_practice_keeps_its_shape_until_rewritten(self):
        essay = practice("reviewing-code", body="# Reviewing Code\n\nAn essay.\n")
        self.assertEqual(self.check({"reviewing-code": essay}), [])

    def test_the_earlier_practices_are_real_core_skills(self):
        core = Path(__file__).resolve().parents[1] / "skills"
        for name in sorted(validate.EARLIER_PRACTICES):
            self.assertTrue((core / name / "SKILL.md").is_file(), name)

    def test_the_quality_bar_exception_reads_the_same_everywhere(self):
        root = Path(__file__).resolve().parents[1]
        files = ("skills/aidlc-onboard/assets/agents-md.md", "starter/repo/AGENTS.md",
                 "skills/aidlc-build/SKILL.md", "agents/reviewer-compliance.md")
        for rel in files:
            self.assertIn("a reason, an owner and an expiry date", (root / rel).read_text(encoding="utf-8"), rel)

    def test_the_plugin_source_must_be_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./plugins/aidlc"}]}))
            self.assertTrue(any("source" in p and "'./'" in p for p in validate.validate(root)))

    def test_harness_references_in_assets_are_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / "skills" / "aidlc-plan" / "assets" / "plan.md").write_text("See core/policy/tiers.yaml.")
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
            for f in (root / "agents").iterdir():
                f.unlink()
            (root / "agents").rmdir()
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


    def test_the_plugin_requires_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            manifest = root / ".claude-plugin" / "plugin.json"
            manifest.write_text(json.dumps({"name": "aidlc", "version": "2.0.0", "dependencies": ["other"]}))
            self.assertTrue(any("requires nothing" in p for p in validate.validate(root)))

    def test_versions_are_semantic(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, version="latest")
        self.assertTrue(any("semantic version" in p for p in problems), problems)

    def test_a_named_reference_or_script_must_exist(self):
        body = STAGE_BODY.replace("## Produces", "Read `references/hop.md`; run `scripts/go.py`.\n## Produces")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
        self.assertTrue(any("references/hop.md" in p for p in problems), problems)
        self.assertTrue(any("scripts/go.py" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
