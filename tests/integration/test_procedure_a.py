"""Procedure A end to end on a fixture Node repository, through the CLI only."""
import unittest

from tests.helpers import TempRepo, git, run_cli


class ProcedureATest(unittest.TestCase):
    def test_init_render_drift_openwiki_scope(self):
        with TempRepo({"package.json": '{"scripts": {"lint": "x", "typecheck": "x", "test": "x"}}\n',
                       "src/app.ts": "export {}\n"}) as root:
            code, out, _ = run_cli("init-repo", str(root), "--name", "portal", "--owner", "Web team",
                                   "--profile", "node", "--purpose", "Customer portal")
            self.assertEqual(code, 0, out)
            (root / ".aidlc/rules/ui.md").write_text(
                "---\npaths: [\"src/**\"]\n---\nUse the design system.\n", encoding="utf-8")
            code, out, _ = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 0, out)
            self.assertTrue((root / ".claude/rules/ui.md").is_file())

            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "procedure A")
            sha = git(root, "rev-parse", "--short", "HEAD")
            cmap = root / "docs/codebase-map.md"
            cmap.write_text(cmap.read_text(encoding="utf-8").replace("<sha>", sha), encoding="utf-8")

            code, out, _ = run_cli("check", "context-drift", str(root))
            self.assertEqual(code, 0, out)
            code, out, _ = run_cli("check", "openwiki", str(root))
            self.assertEqual(code, 0, out)

            (root / "AGENTS.md").write_text(
                (root / "AGENTS.md").read_text(encoding="utf-8") + "- See `src/gone.ts`\n",
                encoding="utf-8")
            code, out, _ = run_cli("check", "context-drift", str(root))
            self.assertEqual(code, 1)
            self.assertIn("src/gone.ts", out)
