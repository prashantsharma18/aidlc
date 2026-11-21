"""Plan 23: parallel lanes (ADR 0025). A third kind of skill, workflow, and its first skill, `parallel-lanes`; one
release line at the tracked stages' gates; independent slices as sibling pull requests; the stacked-slice update; and
the behaviour cases that prove a lane holds at a person's decision."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402
from test_validate import package  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DESIGN = "docs/design/2026-11-21-parallel-lanes.md"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(rel: str) -> str:
    """The file's text with every run of whitespace as one space, so wrapped lines compare equal."""
    return " ".join(read(rel).split())


def skill(name: str) -> str:
    return flat(f"skills/{name}/SKILL.md")


def section(text: str, heading: str) -> str:
    """One `## ` section of a whitespace-collapsed text."""
    return text.split(heading, 1)[1].split(" ## ", 1)[0]


def clean_env() -> dict:
    """The environment with every GIT_ variable removed, so a throwaway repository never reaches an outer one, and
    with no user or system configuration, so no global hook runs."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return dict(env, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
                GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
                PYTHONDONTWRITEBYTECODE="1")


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run git in a throwaway repository."""
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args], cwd=cwd, env=clean_env(), check=check,
                          capture_output=True, text=True)


def sh(command: str, cwd: Path) -> subprocess.CompletedProcess:
    """Run one command line from a skill, its placeholders already filled, in a throwaway repository."""
    return subprocess.run(command, shell=True, cwd=cwd, env=clean_env(), capture_output=True, text=True)


class AdrTest(unittest.TestCase):
    """Task 1: the decision is recorded before anything changes."""

    ADR = "docs/adr/0025-parallel-lanes.md"

    def test_adr_0025_is_proposed_with_a_decider(self):
        text = read(self.ADR)
        self.assertIn("Status: Proposed (2026-11-21)", text)
        self.assertIn("Decider: Prashant Sharma", text)
        for heading in ("## Context", "## Decision", "## Consequences"):
            self.assertIn(heading, text)
        body = flat(self.ADR)
        for phrase in ("Amends: ADR 0015", "a third kind of skill, workflow (`metadata.kind: workflow`)", "`QUEUE.md`",
                       "git refuses to check out a branch that another worktree already has",
                       "Lanes for one repository start from one clone on one machine",
                       "`waiting: <decision> by <who>`", "sibling pull requests", "`git rebase --onto`",
                       "`plans/<KEY>/slice-<n>/`", "keeps `disable-model-invocation: true`, and so does `parallel-lanes`",
                       "`Read <absolute path>/skills/parallel-lanes/SKILL.md before anything else.`",
                       "`pstack/skills/poteto-mode/SKILL.md`",
                       "only load from a slash command, so they reach another agent no other way",
                       "aidlc borrows pstack's way of passing instructions, not its autonomy",
                       "aidlc still ships no script and no workflow, and needs no code-host feature"):
            self.assertIn(phrase, body, phrase)

    def test_adr_0015_points_to_the_amendment_and_keeps_its_last_section(self):
        text = read("docs/adr/0015-work-routes-and-the-part-model.md")
        self.assertIn("Amended by ADR 0025 (proposed, 2026-11-21): one pull request per independent slice", text)
        self.assertLess(text.index("Amended by ADR 0025"), text.index("## Context"))
        self.assertTrue(text.rstrip().split("\n## ")[-1].startswith("Amended by ADR 0024 (2026-11-20)"))


if __name__ == "__main__":
    unittest.main()
