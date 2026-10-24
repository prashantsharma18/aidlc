# tests/unit/test_demo_findings.py
"""Plan 6 demo findings, each pinned: F8 (MAY CHANGE holds paths only), F9 (the dotnet profile runs
inside Claude Code's sandbox), F10 (the sandbox's placeholders are not changes)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

from aidlc.checks import onecheck
from aidlc.paths import framework_root
from tests.helpers import TempRepo


class MayChangeIsPathsOnlyTest(unittest.TestCase):
    def test_the_plan_skill_says_so(self):
        text = (framework_root() / "core/skills/aidlc-plan/SKILL.md").read_text(encoding="utf-8")
        self.assertIn("MAY CHANGE holds only paths and globs", text)

    def test_the_bundle_template_says_so(self):
        text = (framework_root() / "core/templates/task-bundle.md").read_text(encoding="utf-8")
        self.assertIn("paths and globs only", text)


class DotnetProfileInTheSandboxTest(unittest.TestCase):
    def setUp(self):
        self.commands = yaml.safe_load((framework_root() / "core/context/profiles.yaml").read_text(
            encoding="utf-8"))["dotnet"]["commands"]

    def test_msbuild_runs_in_process(self):
        # The sandbox refuses the pipe MSBuild uses to talk to its worker nodes.
        for step in ("build", "test"):
            self.assertIn("-m:1", self.commands[step])
            self.assertIn("--disable-build-servers", self.commands[step])

    def test_the_build_does_not_query_git(self):
        # The Git task reads .gitmodules, which the sandbox replaces with an unreadable placeholder.
        self.assertIn("-p:EnableSourceControlManagerQueries=false", self.commands["build"])

    def test_format_needs_no_msbuild_host(self):
        # dotnet format's workspace mode starts a build host over a named pipe; whitespace --folder does not.
        self.assertTrue(self.commands["format"].startswith("dotnet format whitespace --folder --verify-no-changes"))


class SandboxPlaceholdersTest(unittest.TestCase):
    def test_a_character_device_is_a_placeholder(self):
        self.assertTrue(onecheck.sandbox_placeholder(Path("/dev/null")))

    def test_a_file_a_directory_and_a_symlink_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "f"
            f.write_text("x")
            link = Path(tmp) / "l"
            os.symlink("/dev/null", link)
            for p in (f, Path(tmp), link):
                with self.subTest(p=p):
                    self.assertFalse(onecheck.sandbox_placeholder(p))

    def test_untracked_placeholders_are_not_changes(self):
        with TempRepo({"a.txt": "a\n"}) as root:
            base = onecheck.git(root, "rev-parse", "HEAD").strip()
            (root / ".bashrc").write_text("")
            (root / "new.txt").write_text("n\n")
            real = onecheck.sandbox_placeholder
            with mock.patch.object(onecheck, "sandbox_placeholder",
                                   side_effect=lambda p: p.name == ".bashrc" or real(p)):
                self.assertEqual(onecheck.changed_paths(root, base), ["new.txt"])
