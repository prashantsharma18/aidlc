import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from aidlc.workspace import init_workspace
from tests.helpers import run_cli

PLUGINS = ["superpowers@claude-plugins-official", "baseline@local"]


def _workspace(tmp: str) -> Path:
    root = Path(tmp)
    for name in ("shipments-api", "customer-portal"):
        subprocess.run(["git", "init", "-q", str(root / name)], check=True)
    return root


class WorkspaceInitTest(unittest.TestCase):
    def test_writes_the_guide_the_import_and_a_read_only_harness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            report = dict(init_workspace(root, "SHIP-1", "Delivery window",
                                         [("shipments-api", "Logistics team"), ("customer-portal", "Web team")],
                                         PLUGINS))
            self.assertEqual(report, {"WORKSPACE.md": "created", "CLAUDE.md": "created",
                                      ".claude/settings.json": "created"})
            guide = (root / "WORKSPACE.md").read_text(encoding="utf-8")
            self.assertIn("SHIP-1 (Delivery window)", guide)
            self.assertIn("| shipments-api | Logistics team |", guide)
            self.assertIn("| customer-portal | Web team |", guide)
            self.assertNotIn("| <repo> |", guide)
            self.assertIn("@WORKSPACE.md", (root / "CLAUDE.md").read_text(encoding="utf-8"))
            s = json.loads((root / ".claude/settings.json").read_text(encoding="utf-8"))
            for denied in ("Edit", "Write", "NotebookEdit", "Bash(git commit*)", "Bash(git push*)"):
                self.assertIn(denied, s["permissions"]["deny"])
            self.assertIn("Read(.env)", s["permissions"]["deny"])   # the policy's secret_paths, as render writes them
            self.assertEqual(s["permissions"]["disableBypassPermissionsMode"], "disable")
            self.assertEqual(s["sandbox"]["filesystem"]["denyWrite"], ["./"])
            self.assertFalse(s["sandbox"]["autoAllowBashIfSandboxed"])
            self.assertEqual(s["enabledPlugins"], {p: False for p in PLUGINS})
            self.assertFalse(s["autoMemoryEnabled"])

    def test_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            (root / "WORKSPACE.md").write_text("# hand written\n", encoding="utf-8")
            report = dict(init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], []))
            self.assertEqual(report["WORKSPACE.md"], "skipped (exists)")
            self.assertEqual((root / "WORKSPACE.md").read_text(encoding="utf-8"), "# hand written\n")
            again = dict(init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], []))
            self.assertTrue(all(v == "skipped (exists)" for v in again.values()))

    def test_rejects_non_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            (root / "notes").mkdir()
            with self.assertRaisesRegex(ValueError, "not the root of a git repository"):
                init_workspace(root, "SHIP-1", "t", [("notes", "o")], [])
            self.assertFalse((root / "WORKSPACE.md").exists())

    def test_rejects_escaping_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            with self.assertRaisesRegex(ValueError, "a folder directly inside the workspace"):
                init_workspace(root, "SHIP-1", "t", [("../shipments-api", "o")], [])

    def test_rejects_a_bad_plugin_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            with self.assertRaisesRegex(ValueError, "<plugin>@<marketplace>"):
                init_workspace(root, "SHIP-1", "t", [("shipments-api", "o")], ["superpowers"])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _workspace(tmp)
            code, out, _ = run_cli("workspace", "init", str(root), "--key", "SHIP-1", "--title", "t",
                                   "--repo", "shipments-api=Logistics team",
                                   "--disable-plugin", "superpowers@claude-plugins-official")
            self.assertEqual(code, 0)
            self.assertIn("created", out)
            code, _, err = run_cli("workspace", "init", str(root), "--key", "SHIP-1", "--title", "t",
                                   "--repo", "no-equals-sign")
            self.assertEqual(code, 2)
            self.assertIn("NAME=OWNER", err)
