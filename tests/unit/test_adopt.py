# tests/unit/test_adopt.py
import unittest

from aidlc import adopt
from tests.helpers import TempRepo, run_cli

KEY = "sk-ant-" + "a" * 40          # secret-shaped, assembled so this file holds none


class SurveyTest(unittest.TestCase):
    def test_stack_commands_and_agent_config(self):
        files = {"pyproject.toml": "[project]\nname='x'\n", "CLAUDE.md": "Use pytest.\n",
                 ".cursor/rules/api.mdc": "---\nglobs: src/api/**\n---\nKeep handlers thin.\n",
                 ".github/workflows/ci.yml": "on: push\n", "src/app.py": "print(1)\n"}
        with TempRepo(files) as root:
            s = adopt.survey(root)
            self.assertEqual([st["name"] for st in s.stacks], ["python"])
            self.assertIn(("CLAUDE.md", "claude-code", "import"), s.agent_config)
            self.assertIn((".cursor/rules/api.mdc", "cursor", "import"), s.agent_config)
            self.assertEqual(s.workflows, [".github/workflows/ci.yml"])
            self.assertEqual((s.secrets, s.installed), ([], False))
            text = adopt.report(s)
            for needle in ("python", "--junitxml", "CLAUDE.md", "aidlc init-repo", "aidlc adopt --import"):
                self.assertIn(needle, text)

    def test_hand_written_skills_need_a_decision(self):
        with TempRepo({".claude/skills/x/SKILL.md": "---\nname: x\n---\n", "README.md": "x\n"}) as root:
            self.assertIn((".claude/skills/x/SKILL.md", "claude-code", "decide"), adopt.survey(root).agent_config)

    def test_secrets_stop_the_adoption(self):
        with TempRepo({"config.py": f"KEY = '{KEY}'\n"}) as root:
            code, out, _ = run_cli("adopt", str(root))
            self.assertEqual(code, 1)
            self.assertIn("config.py", out)
            self.assertNotIn(KEY, out)                 # names the file, never the text

    def test_the_survey_writes_nothing(self):
        with TempRepo({"package.json": "{}\n", "CLAUDE.md": "x\n"}) as root:
            before = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts)
            code, _, _ = run_cli("adopt", str(root))
            after = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if ".git" not in p.parts)
            self.assertEqual((code, before), (0, after))

    def test_not_a_repository_root_is_a_usage_error(self):
        with TempRepo({"sub/x.py": "x\n"}) as root:
            code, _, _ = run_cli("adopt", str(root / "sub"))
            self.assertEqual(code, 2)

    def test_large_files_are_counted_not_claimed_clean(self):
        with TempRepo({"big.txt": "x" * 1_100_000 + "\n", "README.md": "x\n"}) as root:
            text = adopt.report(adopt.survey(root))
            self.assertIn("1 file(s) over 1 MB were not scanned", text)
