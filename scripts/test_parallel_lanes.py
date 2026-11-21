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


WORKFLOW_BODY = """# Title

## When to use
x
## Inputs
x
## Steps
1. x
## Stop if
x
## Common excuses
x
## Red flags
x
## Rules
- You draft; you never approve.
"""


def workflow(name: str, body: str = WORKFLOW_BODY, kind: str = "workflow") -> str:
    return (f"---\nname: {name}\ndescription: Runs work across sessions. Use when needed.\nmetadata:\n  kind: {kind}\n"
            f"  invocation: auto\n---\n{body}")


class WorkflowKindTest(unittest.TestCase):
    """Task 2: a third kind of skill, workflow, with its own sections and two naming rules (ADR 0025)."""

    def check(self, skills: dict) -> list:
        with tempfile.TemporaryDirectory() as tmp:
            package(Path(tmp), skills, assets=())
            return validate.validate(Path(tmp))

    def test_a_workflow_in_the_workflow_format_has_no_problems(self):
        self.assertEqual(self.check({"parallel-lanes": workflow("parallel-lanes")}), [])
        self.assertEqual(validate.WORKFLOW_SECTIONS, ("## When to use", "## Inputs", "## Steps", "## Stop if",
                                                      "## Common excuses", "## Red flags", "## Rules"))

    def test_a_workflow_needs_every_workflow_section(self):
        body = WORKFLOW_BODY.replace("## Inputs\nx\n", "")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("missing section '## Inputs'" in p for p in problems), problems)

    def test_a_workflow_keeps_the_sections_in_order(self):
        body = WORKFLOW_BODY.replace("## Inputs\nx\n## Steps\n1. x\n", "## Steps\n1. x\n## Inputs\nx\n")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("out of order" in p for p in problems), problems)

    def test_a_workflow_ends_its_rules_with_the_gate_line(self):
        body = WORKFLOW_BODY.replace("- You draft; you never approve.", "- ok")
        problems = self.check({"parallel-lanes": workflow("parallel-lanes", body)})
        self.assertTrue(any("You draft; you never approve." in p for p in problems), problems)

    def test_a_workflow_name_never_starts_with_aidlc(self):
        problems = self.check({"aidlc-lanes": workflow("aidlc-lanes")})
        self.assertTrue(any("a workflow name never starts with 'aidlc-'" in p for p in problems), problems)
        self.assertFalse(any("'## Produces'" in p for p in problems), problems)

    def test_a_workflow_name_never_starts_with_an_ing_word(self):
        for name in ("running-lanes", "queueing"):
            problems = self.check({name: workflow(name)})
            self.assertTrue(any("a workflow name never starts with an '-ing' word" in p for p in problems),
                            (name, problems))

    def test_a_quoted_workflow_kind_or_one_with_a_comment_is_still_a_workflow(self):
        for kind in ("'workflow'", "workflow  # see ADR 0025"):
            problems = self.check({"parallel-lanes": workflow("parallel-lanes", "# Essay\n", kind)})
            self.assertTrue(any("missing section '## Inputs'" in p for p in problems), (kind, problems))

    def test_the_rules_file_names_the_workflow_kind(self):
        standards = flat("AGENTS.md").split("## Standards", 1)[1].split(" ## ", 1)[0]
        self.assertIn("Workflow skills (`metadata.kind: workflow`, ADR 0025) run work across sessions and keep: When "
                      "to use, Inputs, Steps, Stop if, Common excuses, Red flags, Rules", standards)
        self.assertIn("a workflow name never starts with `aidlc-` or with an \"-ing\" word", standards)
        self.assertIn("`using-aidlc` (`metadata.kind: map`) keeps the open format", standards)

    def test_a_workflow_name_may_start_with_a_noun_that_ends_in_ing(self):
        for name in ("ring-buffer", "thing-map", "string-tools", "spring-lanes", "ingest-queue"):
            self.assertEqual(self.check({name: workflow(name)}), [], name)

    def test_the_other_kinds_are_unaffected_next_to_a_workflow(self):
        stage_body = WORKFLOW_BODY.replace("## Steps\n1. x\n", "## Steps\n1. x\n## Produces\nx\n## Gate\nx\n")
        practice_body = WORKFLOW_BODY.replace("## Inputs\nx\n", "").replace("## Stop if", "## Checks\nx\n## Stop if")
        skills = {"parallel-lanes": workflow("parallel-lanes"),
                  "aidlc-stage": workflow("aidlc-stage", stage_body, "stage"),
                  "doing-checks": workflow("doing-checks", practice_body, "practice")}
        self.assertEqual(self.check(skills), [])
        broken = dict(skills, **{"aidlc-stage": workflow("aidlc-stage", WORKFLOW_BODY, "stage")})
        self.assertTrue(any("missing section '## Produces'" in p for p in self.check(broken)))

    def test_a_workflow_kind_in_the_body_or_unindented_is_not_a_workflow(self):
        in_body = workflow("parallel-lanes", "# Essay\n  kind: workflow\n", "other")
        top_level = ("---\nname: parallel-lanes\ndescription: Runs work. Use when needed.\nkind: workflow\n---\n"
                     "# Essay\n")
        self.assertEqual(self.check({"parallel-lanes": in_body}), [])
        self.assertEqual(self.check({"parallel-lanes": top_level}), [])


LANES = "skills/parallel-lanes/SKILL.md"
QUEUE = "skills/parallel-lanes/assets/queue.md"


def outside_code(text: str) -> str:
    """The text a renderer treats as Markdown: fenced blocks, HTML comments and code spans removed."""
    text = re.sub(r"(?ms)^```[a-z]*\n.*?^```$", "", text)
    text = re.sub(r"(?s)<!--.*?-->", "", text)
    return re.sub(r"`[^`\n]*`", "", text)


def command(text: str, start: str) -> str:
    """The first backticked command in a whitespace-collapsed text that starts with `start`."""
    return re.search("`(" + re.escape(start) + "[^`]*)`", text).group(1)


class ParallelLanesTest(unittest.TestCase):
    """Task 3: the workflow skill's two modes, its lock, its clash rules, the stacked-slice update and its queue
    template, as the design says."""

    def test_it_is_a_workflow_only_a_person_starts(self):
        front = read(LANES).split("\n---", 1)[0]
        self.assertIn("\n  kind: workflow\n", front)
        self.assertIn("\n  invocation: manual\n", front)
        self.assertIn("\n  templates:\n  - queue\ndisable-model-invocation: true", front)
        self.assertEqual(validate.check_skill(ROOT / LANES, ROOT), [])
        self.assertIn("Starting it is the person's go-ahead for the run.", section(skill("parallel-lanes"), "## When to use"))

    def test_the_run_reaches_its_lanes_by_path(self):
        text = skill("parallel-lanes")
        for phrase in ("Every stage skill, and this one, starts only when a person names it",
                       "A sub-agent lane cannot start such a skill, so it reads the skill's file by its absolute path "
                       "and follows it in full.",
                       "the stage skills are the folders beside this one",
                       "only to build, verify and review, and only on a row whose plan a person approved (ADR 0023)",
                       "A person starts intent, specify, design and plan"):
            self.assertIn(phrase, section(text, "## Inputs"), phrase)
        lane = text.split("Lane mode, step by step:", 1)[1].split("Coordinator mode, step by step:")[0]
        self.assertIn("a sub-agent lane reads the stage skill's file at the absolute path its brief names and follows it "
                      "in full", lane)
        self.assertIn("releases with `waiting: start <stage> by <who>`", lane)
        coordinator = text.split("Coordinator mode, step by step:", 1)[1].split("**A stacked slice", 1)[0]
        for phrase in ("build, verify or review, on a row whose plan a person approved: start a sub-agent lane",
                       "Its brief opens with `Read <absolute path>/skills/parallel-lanes/SKILL.md before anything "
                       "else.` and names the row and the stage skill's absolute path "
                       "(`<plugin root>/skills/aidlc-build/SKILL.md`, `aidlc-verify` or `aidlc-review`)",
                       "intent, specify, design or plan, or a tool with no such feature: give the person the exact "
                       "words to start the lane by hand: lane mode of this skill, the row, and the row's next stage",
                       "A lane a person starts by hand counts toward MAX LANES."):
            self.assertIn(phrase, coordinator, phrase)
        self.assertIn("A sub-agent lane started for intent, specify, design or plan, or for a row whose plan no person "
                      "approved.", section(text, "## Red flags"))

    def test_lane_mode_follows_the_design(self):
        lane = skill("parallel-lanes").split("Lane mode, step by step:", 1)[1].split("Coordinator mode, step by step:")[0]
        order = [lane.index(p) for p in ("Fetch (`git fetch`), and read `QUEUE.md` on the default branch",
                                         "Take the first ready row, in queue order, that clashes with no running lane",
                                         "`git worktree add -b <branch> .worktrees/<folder> origin/<default branch>`",
                                         "`git worktree add .worktrees/<folder> <branch>`",
                                         "read the row's state on its branch again",
                                         "run the row's next unfinished stage",
                                         "Release when any of these happens, then end")]
        self.assertEqual(order, sorted(order))
        for phrase in ("Its gates, the evidence file, the verdict from someone who did not write the change, and every "
                       "Stop if hold unchanged", "Commit after every step.",
                       "write `waiting: <decision> by <who>` in the row's stage row", "write `stopped: <reason>`",
                       "write `waiting: push and open the pull request by <who>`, unless the team's `AGENTS.md` lets a "
                       "lane push its own branch",
                       "Release means: commit, `git worktree remove .worktrees/<folder>` (never `--force`)",
                       "Never write `QUEUE.md`, never write to another repository, never approve, never merge."):
            self.assertIn(phrase, lane, phrase)

    def test_coordinator_mode_follows_the_design(self):
        coordinator = skill("parallel-lanes").split("Coordinator mode, step by step:", 1)[1].split(
            "**A stacked slice after its parent merges.**", 1)[0]
        for phrase in ("Fetch every repository the queue names (`git -C <repository> fetch`)",
                       "remove one only after the person confirms, because it may hold uncommitted work",
                       "Start lanes up to MAX LANES minus the lanes running now", "each told only its row",
                       "with your AI tool's own way of starting background sessions or sub-agents, where it has one",
                       "give the person the exact words to start the lane by hand",
                       "When a lane reports back, read its row's state and start the next ready row",
                       "Report one table to the person: running, waiting on whom, stopped and why, next in line",
                       "Draft new queue rows", "Never write `QUEUE.md`, never approve, never merge."):
            self.assertIn(phrase, coordinator, phrase)

    def test_the_clash_rules(self):
        text = skill("parallel-lanes")
        for phrase in ("| Order | It depends on a row that is not done. |",
                       "Only once building starts: its approved bundle shares a MAY CHANGE path with a bundle another "
                       "lane is building. When in doubt, it waits. Planning and specs run side by side.",
                       "one open change per contract", "Nothing is opened automatically.",
                       "A row held back is skipped, not dropped"):
            self.assertIn(phrase, text, phrase)

    def test_a_rows_state_lives_in_its_own_files(self):
        text = skill("parallel-lanes")
        for phrase in ("| waiting: `<decision> by <who>` | its stage row's Status in the index, or the progress "
                       "note's STATUS (`paused: …` counts as waiting) |",
                       "| done | the index's merged row, on the default branch (`git show origin/<default "
                       "branch>:plans/<KEY>/README.md`) |",
                       "`git -C <repository> show <branch>:plans/<KEY>/README.md`",
                       "A row whose item has no index yet is not ready",
                       "A lane never records a decision it has not checked.",
                       "may start once the parent's progress note reads STATUS `done`"):
            self.assertIn(phrase, text, phrase)

    def test_the_lock_and_its_limit(self):
        text = skill("parallel-lanes")
        for phrase in ("`.worktrees/<KEY>` for an item or a part", "`.worktrees/<KEY>-s<n>` for a slice",
                       "`.worktrees/<KEY>-p<n>` for a second part in the same repository",
                       "Never pass `--force` or `-f`, never use `-B`",
                       "`git check-ignore -q .worktrees/` must succeed",
                       "Lanes for one repository start from one clone on one machine",
                       "A person does not check out a queued branch in their own working copy while lanes may claim "
                       "it"):
            self.assertIn(phrase, text, phrase)

    def test_git_lets_only_one_lane_claim_a_row(self):
        text = skill("parallel-lanes")
        first, later = command(text, "git worktree add -b "), command(text, "git worktree add .worktrees/")
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            git(repo, "init", "-q", "-b", "main")
            (repo / "README.md").write_text("x\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            git(repo, "remote", "add", "origin", str(repo))
            git(repo, "fetch", "-q", "origin")

            def claim(line: str, folder_name: str) -> int:
                return sh(line.replace("<branch>", "feat/SHIP-12-eta-limit").replace("<folder>", folder_name)
                          .replace("<default branch>", "main"), repo).returncode

            self.assertEqual(claim(first, "SHIP-12"), 0)
            self.assertNotEqual(claim(later, "SHIP-12"), 0)
            self.assertNotEqual(claim(later, "SHIP-12-copy"), 0)
            self.assertNotEqual(claim(first, "SHIP-12-copy"), 0)
            self.assertIn(".worktrees/SHIP-12", git(repo, "worktree", "list").stdout)

    def test_the_stacked_slice_update_follows_the_design(self):
        stacked = skill("parallel-lanes").split("**A stacked slice after its parent merges.**", 1)[1].split(
            "## Stop if", 1)[0]
        for phrase in ("`git show origin/<default branch>:plans/<KEY>/slice-2/README.md`",
                       "`git merge-base <slice 3's branch> origin/<slice 2's branch>`", "Never guess it.",
                       "`git rebase --onto origin/<default branch> <slice 2's last commit> <slice 3's branch>`",
                       "this works when the code host squashed slice 2 into one commit", "`git push --force-with-lease`",
                       "Ask the person first, unless the team's `AGENTS.md` lets a lane push its own branch.",
                       "If the team forbids force-push (a rule in its `AGENTS.md`), stop and ask.",
                       "Many code hosts retarget it themselves when slice 2's branch is deleted; otherwise a person "
                       "retargets it.",
                       "`git diff --name-only <judged commit> HEAD -- ':(top)' ':(top,exclude)plans/<KEY>/'`",
                       "write `stopped: rebase conflict in <files>`",
                       "Never merge the default branch into slice 3 yourself."):
            self.assertIn(phrase, stacked, phrase)

    def test_it_names_git_and_no_tool_or_script(self):
        text = read(LANES) + read(QUEUE)
        for name in ("Claude Code", "Copilot", "Codex", "Cursor", "/aidlc:", "$ARGUMENTS", "${CLAUDE_", "scripts/",
                     "run_queue", "Load the `"):
            self.assertNotIn(name, text, name)
        self.assertEqual(validate.portability(LANES, read(LANES)), [])

    def test_the_queue_template_matches_the_design(self):
        queue = read(QUEUE)
        example = read(DESIGN).split("### `QUEUE.md`", 1)[1].split("\n## ", 1)[0]
        rows = [line for line in example.splitlines() if line.startswith("|")]
        self.assertEqual(len(rows), 6)
        for row in rows:
            self.assertIn(row + "\n", queue, row)
        self.assertIn("```text\nMAX LANES   3\n```", queue)
        for opening in re.findall(r"(?m)^```(\S*)$", queue)[::2]:
            self.assertEqual(opening, "text")
        self.assertEqual(re.findall(r"<(?!!--)[^<>\n]+>", outside_code(queue)), [])
        text = flat(QUEUE)
        for phrase in ("A person writes this file and commits it on the default branch", "lanes never write it",
                       "never an `aidlc/` prefix", "The default is 3, because people's review time is the real limit",
                       "For parts it copies the coordination plan's order; for slices it copies the bundles' `DEPENDS "
                       "ON` lines"):
            self.assertIn(phrase, text, phrase)
        self.assertIn("`assets/queue.md`", skill("parallel-lanes"))


if __name__ == "__main__":
    unittest.main()
