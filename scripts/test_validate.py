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


def package(root: Path, skills: dict[str, str], agents: dict[str, str] | None = None, assets=("plan.md",)):
    for name, text in skills.items():
        d = root / "skills" / name
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
        for a in assets:
            (d / "assets" / a).write_text("x", encoding="utf-8")
    (root / "agents").mkdir()
    for name, text in (agents or {"explorer": "---\nname: explorer\ndescription: Reads.\n---\nbody\n"}).items():
        (root / "agents" / f"{name}.md").write_text(text, encoding="utf-8")
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "aidlc"}), encoding="utf-8")
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./"}]}), encoding="utf-8")
    for kind, settings in (("repo", REPO_SETTINGS), ("workspace", WORKSPACE_SETTINGS)):
        (root / "starter" / kind / ".claude").mkdir(parents=True)
        (root / "starter" / kind / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")


def skill(name, description="Does things. Use when needed.", body=STAGE_BODY):
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}"


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

    def test_the_plugin_must_point_at_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./plugins/aidlc"}]}))
            self.assertTrue(any("marketplace" in p for p in validate.validate(root)))

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


if __name__ == "__main__":
    unittest.main()
