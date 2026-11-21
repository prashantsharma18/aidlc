"""The behaviour suite's structure, checked for free: every case loads, scaffolds safely and is tagged."""
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"
TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
TAGS = {"gate", "routing", "route", "language"}
GATES = {"gate-spec-approval", "gate-assertion-change", "gate-amended-assertion", "gate-scope", "gate-dependency",
         "gate-injected-ticket", "gate-ai-review-approval", "gate-release-stop-criteria", "gate-defect-no-repro",
         "gate-payments-quick-fix", "gate-evidence-deleted-test", "gate-evidence-weakened-assertion",
         "gate-stale-verdict", "gate-review-writes-evidence"}


def cases() -> list[Path]:
    return sorted(p.parent for p in EVALS.glob("*/prompt.md"))


def scaffold_env() -> dict[str, str]:
    """The environment for a scaffold or a fixture run: the caller's, minus every GIT_* variable. A scaffold runs
    `git init` and commits; an inherited GIT_DIR or GIT_WORK_TREE would point those at the caller's repository."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def front(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---") else ""


class EvalsTest(unittest.TestCase):
    def test_every_case_has_a_known_tag_and_a_grader(self):
        self.assertTrue(cases())
        for case in cases():
            fm = front((case / "prompt.md").read_text(encoding="utf-8"))
            tags = set(re.findall(r"[a-z]+", (re.search(r"tags:\s*\[([^\]]*)\]", fm) or [None, ""])[1]))
            self.assertTrue(tags & TAGS, case.name)
            graders = list((case / "graders").glob("*.md"))
            self.assertTrue(graders, case.name)
            for g in graders:
                kind = re.search(r"(?m)^type:\s*(\S+)", front(g.read_text(encoding="utf-8")))
                self.assertIn(kind and kind.group(1), TYPES, f"{case.name}/{g.name}")

    def test_every_scaffold_script_is_executable_and_strict(self):
        for case in cases():
            yaml = case / "case.yaml"
            if not yaml.is_file():
                continue
            name = re.search(r"scaffold_script:\s*(\S+)", yaml.read_text(encoding="utf-8")).group(1)
            script = case / name
            self.assertTrue(script.is_file(), case.name)
            text = script.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!/usr/bin/env bash\nset -euo pipefail"), case.name)
            self.assertIn("user.email=eval@example.com", text, case.name)
            self.assertTrue(script.stat().st_mode & 0o111, case.name)

    def test_the_fixtures_build_a_green_repository(self):
        result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                                cwd=EVALS / "fixtures" / "shipments", capture_output=True, text=True,
                                env=scaffold_env())
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_results_are_ignored(self):
        self.assertIn("evals/results/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_every_gate_has_a_case(self):
        names = {c.name for c in cases()}
        self.assertEqual(GATES - names, set())

    def test_build_cases_confirm_in_advance(self):
        for case in cases():
            body = (case / "prompt.md").read_text(encoding="utf-8")
            if "/aidlc:aidlc-build" in body:
                self.assertIn("I confirm your restatement and the steps in advance", body, case.name)

    # Final review: catch for free what the smoke and the review caught for money
    PROMPT_KEYS = {"schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome", "model",
                   "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env"}

    def test_every_scaffold_builds_from_a_clean_copy(self):
        import shutil, tempfile
        for case in cases():
            if not (case / "case.yaml").is_file():
                continue
            with tempfile.TemporaryDirectory() as tmp:
                result = subprocess.run(["bash", str(case / "setup.sh")], cwd=tmp, capture_output=True, text=True,
                                        env=scaffold_env())
                self.assertEqual(result.returncode, 0, f"{case.name}: {result.stderr[-300:]}")

    def test_scaffold_commits_ignore_the_operators_hooks_and_signing(self):
        for case in cases():
            script = case / "setup.sh"
            if script.is_file():
                text = script.read_text(encoding="utf-8")
                self.assertIn("core.hooksPath=/dev/null", text, case.name)
                self.assertIn("commit.gpgsign=false", text, case.name)

    def test_no_fixture_file_is_ignored_by_git(self):
        files = [str(p.relative_to(ROOT)) for p in (EVALS / "fixtures").rglob("*") if p.is_file()]
        result = subprocess.run(["git", "check-ignore", "--no-index", *files], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), "", "git ignores these fixture files")

    def test_no_regex_uses_an_inline_flag(self):
        for case in cases():
            for g in (case / "graders").glob("*.md"):
                fm = front(g.read_text(encoding="utf-8"))
                self.assertNotIn("(?m)", fm, f"{case.name}/{g.name}")
                self.assertNotIn("(?i)", fm, f"{case.name}/{g.name}")
                self.assertNotIn("(?s)", fm, f"{case.name}/{g.name}")

    def test_prompt_front_matter_uses_only_known_keys(self):
        for case in cases():
            fm = front((case / "prompt.md").read_text(encoding="utf-8"))
            keys = set(re.findall(r"(?m)^([a-z_]+):", fm))
            self.assertEqual(keys - self.PROMPT_KEYS, set(), case.name)

    def test_file_edit_graders_anchor_on_the_path_and_cover_write(self):
        for case in cases():
            graders = {g.name: front(g.read_text(encoding="utf-8")) for g in (case / "graders").glob("*.md")}
            for name, fm in graders.items():
                path_like = re.search(r"input_match:.*(\.py|src/|tests/)", fm)
                if re.search(r"(?m)^tool:\s*(Edit|Write)", fm) and path_like:
                    self.assertIn("file_path", fm, f"{case.name}/{name}")
                if re.search(r"before:|after:", fm):
                    self.assertIn("file_path", fm, f"{case.name}/{name}")


class ScaffoldIsolationTest(unittest.TestCase):
    """A scaffold runs `git init` and commits. It must never reach the caller's repository through an inherited
    GIT_DIR or GIT_WORK_TREE (this once rewrote aidlc's own repository during a test run)."""

    def test_a_scaffold_never_touches_the_callers_repository(self):
        import tempfile
        from unittest import mock
        clean = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        case = next(c for c in cases() if (c / "setup.sh").is_file())
        with tempfile.TemporaryDirectory() as victim, tempfile.TemporaryDirectory() as tmp:
            git = ["git", "-c", "user.email=v@example.com", "-c", "user.name=v", "-c", "commit.gpgsign=false",
                   "-c", "core.hooksPath=/dev/null"]
            subprocess.run(["git", "init", "-q", victim], check=True, env=clean)
            subprocess.run([*git, "-C", victim, "commit", "-q", "--allow-empty", "-m", "victim"], check=True, env=clean)
            head = subprocess.run(["git", "-C", victim, "rev-parse", "HEAD"], capture_output=True, text=True,
                                  env=clean).stdout
            # GIT_DIR alone is the dangerous case: the scaffold's `git init` and commit then land in the victim.
            with mock.patch.dict(os.environ, {"GIT_DIR": f"{victim}/.git"}):
                result = subprocess.run(["bash", str(case / "setup.sh")], cwd=tmp, capture_output=True, text=True,
                                        env=scaffold_env())
            self.assertEqual(result.returncode, 0, result.stderr[-300:])
            after = subprocess.run(["git", "-C", victim, "rev-parse", "HEAD"], capture_output=True, text=True,
                                   env=clean).stdout
            worktree = subprocess.run(["git", "-C", victim, "config", "--local", "--get", "core.worktree"],
                                      capture_output=True, text=True, env=clean).stdout
            self.assertEqual(after, head)
            self.assertEqual(worktree, "")


class ContainerTest(unittest.TestCase):
    """The local eval container (maintainer tooling): the same Claude Code as CI, a non-root user, and a run command
    that takes credentials by name and never mounts a credential file or runs privileged."""
    CONTAINER = EVALS / "container"
    CREDENTIAL_PATHS = (".claude", ".docker", ".config", ".aws", ".ssh", ".netrc", ".git-credentials", ".npmrc",
                        ".anthropic", "credentials")

    def dockerfile(self) -> str:
        return (self.CONTAINER / "Dockerfile").read_text(encoding="utf-8")

    def run_commands(self) -> list[str]:
        """Every `docker run` command in the README's code blocks, with its continuation lines joined."""
        text = (self.CONTAINER / "README.md").read_text(encoding="utf-8")
        blocks = re.findall(r"(?ms)^```[a-z]*\n(.*?)^```", text)
        commands = []
        for block in blocks:
            for command in re.sub(r"\\\n\s*", " ", block).splitlines():
                if re.match(r"\s*docker run\b", command):
                    commands.append(command)
        return commands

    def test_claude_code_matches_the_evals_workflow(self):
        workflow = (ROOT / ".github" / "workflows" / "evals.yml").read_text(encoding="utf-8")
        pinned = re.findall(r"@anthropic-ai/claude-code@(\S+)", workflow)
        image = re.findall(r"@anthropic-ai/claude-code@(\S+)", self.dockerfile())
        self.assertEqual(len(pinned), 1, pinned)
        self.assertEqual(image, pinned)

    def test_the_base_image_is_pinned(self):
        base = re.search(r"(?m)^FROM\s+(\S+)", self.dockerfile()).group(1)
        self.assertRegex(base, r":[0-9][^@]*@sha256:[0-9a-f]{64}$")

    def test_the_image_runs_as_a_non_root_user(self):
        users = re.findall(r"(?m)^USER\s+(\S+)", self.dockerfile())
        self.assertTrue(users, "no USER line")
        self.assertNotIn(users[-1].split(":")[0], {"root", "0"})

    def test_the_run_command_takes_credentials_by_name_and_mounts_none(self):
        commands = self.run_commands()
        self.assertTrue(commands, "the README gives no docker run command")
        for command in commands:
            self.assertNotIn("--env-file", command)
            for name, value in re.findall(r"(?:-e|--env)[ =]([A-Za-z_][A-Za-z0-9_]*)(=\S*)?", command):
                self.assertEqual(value, "", f"{name} is given a value in: {command}")
            mounts = re.findall(r"(?:-v|--volume)[ =](\S+)|--mount[ =](\S+)", command)
            self.assertTrue(any(":/work" in v for v, _ in mounts), f"the repository is not mounted at /work: {command}")
            for volume, mount in mounts:
                for path in self.CREDENTIAL_PATHS:
                    self.assertNotIn(path, volume + mount, command)

    def test_nothing_runs_privileged(self):
        readme = (self.CONTAINER / "README.md").read_text(encoding="utf-8")
        for command in self.run_commands():
            self.assertNotIn("--privileged", command)
            self.assertNotIn("SYS_ADMIN", command)
        self.assertNotIn("--privileged", self.dockerfile())
        self.assertIn("seccomp=unconfined", readme)


if __name__ == "__main__":
    unittest.main()
