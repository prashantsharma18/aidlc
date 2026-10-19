import tempfile
import unittest
from datetime import date
from pathlib import Path

from aidlc.repo import init_repo, load_config
from tests.helpers import TempRepo, run_cli

EXPECTED = {".aidlc/config.yaml", "AGENTS.md", "docs/codebase-map.md", ".aidlc/rules/README.md",
            ".aidlc/probe.yaml", ".openwikiignore", "plans/approved-bundles.txt",
            ".aidlc/permissions.yaml"}


class InitRepoTest(unittest.TestCase):
    def test_creates_expected_files(self):
        with TempRepo() as root:
            report = dict(init_repo(root, "shipments-api", "Logistics team", "dotnet",
                                    "Shipments API", date(2026, 10, 18)))
            self.assertEqual(set(report), EXPECTED)
            self.assertTrue(all(v == "created" for v in report.values()))
            cfg = load_config(root)
            self.assertEqual(cfg.profile, "dotnet")
            self.assertIn("test", cfg.commands)
            self.assertIn("aidlc check", (root / "AGENTS.md").read_text(encoding="utf-8"))
            self.assertIn("Last verified: 2026-10-18",
                          (root / "docs/codebase-map.md").read_text(encoding="utf-8"))

    def test_never_overwrites_existing_files(self):
        with TempRepo({"AGENTS.md": "# hand written\n"}) as root:
            report = dict(init_repo(root, "x", "o", "node", "p", date(2026, 10, 18)))
            self.assertEqual(report["AGENTS.md"], "skipped (exists)")
            self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), "# hand written\n")

    def test_unknown_profile_is_rejected(self):
        with TempRepo() as root:
            with self.assertRaises(ValueError):
                init_repo(root, "x", "o", "cobol", "p", date(2026, 10, 18))

    def test_cli_requires_git_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = run_cli("init-repo", tmp, "--name", "x", "--owner", "o",
                                   "--profile", "node", "--purpose", "p")
            self.assertEqual(code, 2)
            self.assertIn("not the root of a git repository", out)

    def test_cli_from_subdirectory_rejected(self):
        with TempRepo({"src/a.txt": "a\n"}) as root:
            code, out, _ = run_cli("init-repo", str(root / "src"), "--name", "x", "--owner", "o",
                                   "--profile", "node", "--purpose", "p")
            self.assertEqual(code, 2)

    def test_missing_config_raises(self):
        with TempRepo() as root:
            with self.assertRaises(FileNotFoundError):
                load_config(Path(root))
