import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from aidlc.paths import framework_root

ROOT = framework_root()
GUARD = ROOT / "core" / "managed" / "aidlc_root_guard.py"
SNIPPET = ROOT / "core" / "managed" / "managed-settings.hooks.json"
INSTALLED = "/etc/claude-code/hooks/aidlc_root_guard.py"


def make_repo(path: Path, aidlc: bool = True) -> Path:
    (path / ".git").mkdir(parents=True)
    (path / "sub").mkdir()
    if aidlc:
        (path / ".aidlc").mkdir()
        (path / ".aidlc" / "config.yaml").write_text("name: x\n", encoding="utf-8")
    return path


def run(payload, project_dir):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    done = subprocess.run([sys.executable, "-I", str(GUARD)], input=stdin, capture_output=True, text=True,
                          env=env, timeout=30)
    return done.returncode, done.stdout


def denied(out):
    body = json.loads(out)["hookSpecificOutput"]
    return body["permissionDecision"] == "deny" and "repository root" in body["permissionDecisionReason"]


class RootGuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.repo = make_repo(self.base / "svc")

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_session_started_in_a_subdirectory_is_refused(self):
        sub = self.repo / "sub"
        code, out = run({"tool_name": "Read", "tool_input": {"file_path": str(sub / "x.py")}, "cwd": str(sub)}, sub)
        self.assertEqual(code, 0)
        self.assertTrue(denied(out))
        self.assertIn(str(self.repo), out)

    def test_a_session_started_at_the_root_is_left_alone(self):
        code, out = run({"tool_name": "Edit", "tool_input": {"file_path": str(self.repo / "sub" / "x.py")},
                         "cwd": str(self.repo / "sub")}, self.repo)
        self.assertEqual((code, out), (0, ""))

    def test_a_repository_without_aidlc_is_left_alone(self):
        other = make_repo(self.base / "plain", aidlc=False)
        code, out = run({"tool_name": "Bash", "tool_input": {"command": "ls"}, "cwd": str(other / "sub")}, other / "sub")
        self.assertEqual((code, out), (0, ""))

    def test_editing_an_aidlc_repository_from_elsewhere_is_refused(self):
        outside = self.base / "elsewhere"
        outside.mkdir()
        code, out = run({"tool_name": "Write", "tool_input": {"file_path": str(self.repo / "new.py")},
                         "cwd": str(outside)}, outside)
        self.assertEqual(code, 0)
        self.assertTrue(denied(out))

    def test_another_aidlc_repository_is_refused_even_from_a_root(self):
        second = make_repo(self.base / "second")
        code, out = run({"tool_name": "Edit", "tool_input": {"file_path": str(second / "a.py")},
                         "cwd": str(self.repo)}, self.repo)
        self.assertTrue(denied(out))

    def test_relative_paths_resolve_against_the_working_directory(self):
        outside = self.base / "elsewhere"
        outside.mkdir()
        code, out = run({"tool_name": "Read", "tool_input": {"file_path": "../svc/sub/x.py"}, "cwd": str(outside)},
                        outside)
        self.assertTrue(denied(out))

    def test_bad_input_fails_closed(self):
        for payload in ("not json", "[]"):
            with self.subTest(payload=payload):
                code, out = run(payload, self.repo)
                self.assertEqual((code, out), (2, ""))

    def test_the_guard_uses_the_standard_library_only(self):
        imports = {line.split()[1].split(".")[0] for line in GUARD.read_text(encoding="utf-8").splitlines()
                   if line.startswith(("import ", "from "))}
        self.assertLessEqual(imports, {"__future__", "json", "os", "sys", "pathlib"})

    def test_the_managed_settings_snippet_runs_the_installed_guard_and_blocks_on_failure(self):
        hooks = json.loads(SNIPPET.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
        [entry] = hooks
        self.assertEqual(entry["matcher"], ".*")
        [hook] = entry["hooks"]
        # An absolute interpreter: the session's PATH must not choose the program that judges it (PR #4 review).
        self.assertEqual(hook["command"], f"/usr/bin/python3 -I {INSTALLED}")
        self.assertEqual(hook["onFailure"], "block")
        doc = (ROOT / "docs" / "harness" / "root-guard.md").read_text(encoding="utf-8")
        self.assertIn(INSTALLED, doc)
        self.assertIn("managed-settings.json", doc)
        self.assertNotIn("/tmp/managed-settings.json", doc)   # no fixed, world-writable staging file
        self.assertIn("mktemp", doc)
