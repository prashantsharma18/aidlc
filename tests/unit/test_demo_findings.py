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


class SkillTextFindingsTest(unittest.TestCase):
    def skill(self, name):
        return (framework_root() / f"core/skills/{name}/SKILL.md").read_text(encoding="utf-8")

    def test_design_says_where_seen_to_fail_comes_from_in_a_workspace(self):
        # F6: a workspace-root session is read-only and cannot run tests.
        self.assertIn("shown red at the first step of its slice", self.skill("aidlc-design"))

    def test_plan_marks_protected_paths_as_person_applied(self):
        # F11: api/** and other protected paths are never edited by the agent, even when MAY CHANGE lists them.
        self.assertIn("a person applies", self.skill("aidlc-plan"))

    def test_build_slice_rescopes_after_merging_the_base(self):
        # F17: the scope records its base; after the base branch is merged in, the scope must be regenerated.
        self.assertIn("after the base branch is merged into this branch", self.skill("aidlc-build-slice"))
