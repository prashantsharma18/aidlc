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
                                         "With no row named, take the first ready row, in queue order, that clashes with no running lane",
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
                       "this works when the code host squashed slice 2 into one commit", "`git push --force-with-lease --force-if-includes origin <slice 3's branch>`",
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
        for phrase in ("A person writes this file and commits and pushes it on the default branch", "lanes never write it",
                       "never an `aidlc/` prefix", "The default is 3, because people's review time is the real limit",
                       "For parts it copies the coordination plan's order; for slices it copies the bundles' `DEPENDS "
                       "ON` lines"):
            self.assertIn(phrase, text, phrase)
        self.assertIn("`assets/queue.md`", skill("parallel-lanes"))


class ParallelLanesFixRoundTest(unittest.TestCase):
    """Task 3 fix round: a lane never overwrites a person's push, never reads a stale branch, takes the row it is
    given, and each claim, release and exclude rule is proved against real git."""

    @staticmethod
    def remote_with(folder: str, branch: str):
        """A bare origin, a lane clone and a person's clone, each with the identity git needs."""
        base = Path(folder)
        origin, lane, person = base / "origin.git", base / "lane", base / "person"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, env=clean_env())
        subprocess.run(["git", "clone", "-q", str(origin), str(lane)], check=True, env=clean_env(),
                       stderr=subprocess.DEVNULL)
        for repo in (lane,):
            git(repo, "config", "user.email", "a@example.com")
            git(repo, "config", "user.name", "a")
        git(lane, "checkout", "-q", "-b", "main")
        (lane / "README.md").write_text("x\n", encoding="utf-8")
        git(lane, "add", "-A")
        git(lane, "commit", "-q", "-m", "base")
        git(lane, "push", "-q", "-u", "origin", "main")
        git(lane, "checkout", "-q", "-b", branch)
        (lane / "work.txt").write_text("1\n", encoding="utf-8")
        git(lane, "add", "-A")
        git(lane, "commit", "-q", "-m", "work")
        git(lane, "push", "-q", "-u", "origin", branch)
        subprocess.run(["git", "clone", "-q", str(origin), str(person)], check=True, env=clean_env(),
                       stderr=subprocess.DEVNULL)
        git(person, "config", "user.email", "p@example.com")
        git(person, "config", "user.name", "p")
        git(person, "checkout", "-q", branch)
        return lane, person

    def test_a_persons_push_stops_the_stacked_update(self):
        stacked = skill("parallel-lanes").split("**A stacked slice after its parent merges.**", 1)[1].split(
            "## Stop if", 1)[0]
        ancestry = command(stacked, "git merge-base --is-ancestor").replace("<slice 3's branch>", "feat/s3")
        push = command(stacked, "git push --force-with-lease")
        self.assertIn("--force-if-includes", push)
        self.assertIn("Stop if it fails", stacked)
        with tempfile.TemporaryDirectory() as folder:
            lane, person = self.remote_with(folder, "feat/s3")
            git(lane, "checkout", "-q", "main")
            git(lane, "checkout", "-q", "feat/s3")
            self.assertEqual(sh(ancestry, lane).returncode, 0)
            (person / "theirs.txt").write_text("a person's work\n", encoding="utf-8")
            git(person, "add", "-A")
            git(person, "commit", "-q", "-m", "a person's commit")
            git(person, "push", "-q", "origin", "feat/s3")
            git(lane, "fetch", "-q")
            self.assertNotEqual(sh(ancestry, lane).returncode, 0)
            git(lane, "commit", "-q", "--amend", "-m", "work, rewritten")
            self.assertNotEqual(sh(push, lane).returncode, 0)
            self.assertIn("a person's commit", git(person, "log", "--format=%s", "origin/feat/s3").stdout)
            self.assertNotEqual(sh("git push --force-with-lease --force-if-includes", lane).returncode, 0)
            self.assertEqual(git(lane, "ls-remote", "origin", "feat/s3").stdout.split()[0],
                             git(person, "rev-parse", "HEAD").stdout.strip())

    def test_a_later_claim_fast_forwards_to_the_remote_branch(self):
        lanes = skill("parallel-lanes").split("Lane mode, step by step:", 1)[1].split(
            "Coordinator mode, step by step:")[0]
        later = command(lanes, "git worktree add .worktrees/")
        forward = command(lanes, "git merge --ff-only origin/")
        with tempfile.TemporaryDirectory() as folder:
            lane, person = self.remote_with(folder, "feat/SHIP-12-eta-limit")
            git(lane, "checkout", "-q", "main")
            (person / "more.txt").write_text("more\n", encoding="utf-8")
            git(person, "add", "-A")
            git(person, "commit", "-q", "-m", "ahead")
            git(person, "push", "-q", "origin", "feat/SHIP-12-eta-limit")
            git(lane, "fetch", "-q")
            fill = lambda line: line.replace("<branch>", "feat/SHIP-12-eta-limit").replace("<folder>", "SHIP-12")
            self.assertEqual(sh(fill(later), lane).returncode, 0)
            wt = lane / ".worktrees" / "SHIP-12"
            self.assertNotEqual(git(wt, "rev-parse", "HEAD").stdout, git(wt, "rev-parse", "origin/feat/SHIP-12-eta-limit").stdout)
            self.assertEqual(sh(fill(forward), wt).returncode, 0)
            self.assertEqual(git(wt, "rev-parse", "HEAD").stdout, git(wt, "rev-parse", "origin/feat/SHIP-12-eta-limit").stdout)

    def test_only_a_taken_row_is_read_as_taken(self):
        text = skill("parallel-lanes")
        for phrase in ("`already exists`", "`is already checked out`", "`is already used by worktree`",
                       "`stopped: claim failed: <error>`", "never skipped silently",
                       "a stacked slice starts from its parent's local branch"):
            self.assertIn(phrase, text, phrase)
        with tempfile.TemporaryDirectory() as folder:
            lane, _ = self.remote_with(folder, "feat/SHIP-12-eta-limit")
            git(lane, "checkout", "-q", "main")
            bad = sh("git worktree add -b feat/SHIP-40-s3 .worktrees/SHIP-40-s3 origin/feat/nope", lane)
            self.assertNotEqual(bad.returncode, 0)
            for taken in ("already exists", "is already checked out", "is already used by worktree"):
                self.assertNotIn(taken, bad.stderr)
            self.assertEqual(sh("git worktree add .worktrees/A feat/SHIP-12-eta-limit", lane).returncode, 0)
            held = sh("git worktree add .worktrees/B feat/SHIP-12-eta-limit", lane)
            self.assertTrue(any(w in held.stderr for w in ("is already checked out", "is already used by worktree")))

    def test_a_lane_takes_the_row_it_is_given(self):
        text = skill("parallel-lanes")
        for phrase in ("Take the row your brief or the person names. With no row named, take the first ready row",
                       "ends without claiming, writes no state, and reports back"):
            self.assertIn(phrase, text, phrase)
        self.assertNotIn("releases with `waiting: start <stage> by <who>`", text)

    def test_running_lanes_are_the_worktrees_under_worktrees(self):
        text = skill("parallel-lanes")
        self.assertIn("Every worktree under `.worktrees/` there counts as a running lane; the main copy does not.", text)
        self.assertIn("Show the person any worktree under `.worktrees/` with no running lane", text)

    def test_a_part_runs_its_claim_in_its_repository(self):
        text = skill("parallel-lanes")
        self.assertIn("For a part row, run steps 1 to 3 in the row's repository (`git -C <repository>`", text)

    def test_the_queue_is_committed_and_pushed(self):
        self.assertIn("commits and pushes", skill("parallel-lanes"))
        self.assertIn("commits and pushes it", flat(QUEUE))

    def test_the_stacked_fallbacks_and_release_scope(self):
        text = skill("parallel-lanes")
        for phrase in ("use slice 2's local branch, or `origin/<slice 2's branch>` while it survives, otherwise its head "
                       "commit as the review tool shows it, or ask the person",
                       "Ask before the push and void the earlier verdict as above.",
                       "commit only the row's own work; anything else is reported, never committed"):
            self.assertIn(phrase, text, phrase)

    def test_release_refuses_a_dirty_worktree_and_a_later_claim_succeeds(self):
        text = skill("parallel-lanes")
        remove = command(text, "git worktree remove .worktrees/")
        self.assertNotIn("--force", remove)
        with tempfile.TemporaryDirectory() as folder:
            lane, _ = self.remote_with(folder, "feat/SHIP-12-eta-limit")
            git(lane, "checkout", "-q", "main")
            fill = lambda line: line.replace("<branch>", "feat/SHIP-12-eta-limit").replace("<folder>", "SHIP-12")
            self.assertEqual(sh("git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit", lane).returncode, 0)
            wt = lane / ".worktrees" / "SHIP-12"
            (wt / "work.txt").write_text("dirty\n", encoding="utf-8")
            self.assertNotEqual(sh(fill(remove), lane).returncode, 0)
            self.assertTrue(wt.exists())
            git(wt, "checkout", "--", "work.txt")
            self.assertEqual(sh(fill(remove), lane).returncode, 0)
            self.assertEqual(sh("git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit", lane).returncode, 0)

    def test_the_exclude_file_keeps_worktrees_out_of_every_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            lane, _ = self.remote_with(folder, "feat/SHIP-12-eta-limit")
            git(lane, "checkout", "-q", "main")
            (lane / ".git" / "info").mkdir(exist_ok=True)
            with open(lane / ".git" / "info" / "exclude", "a", encoding="utf-8") as handle:
                handle.write(".worktrees/\n")
            self.assertEqual(sh("git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit", lane).returncode, 0)
            self.assertEqual(git(lane, "check-ignore", "-q", ".worktrees/", check=False).returncode, 0)
            self.assertEqual(git(lane, "status", "--porcelain").stdout, "")


class ParallelLanesRoundTwoTest(unittest.TestCase):
    """Task 3 fix round 2: one rule for a taken row, the coordinator hands stage starts to the person, and the push
    names its branch."""

    def test_a_named_row_that_is_taken_ends_the_lane(self):
        text = skill("parallel-lanes")
        for phrase in ("means another lane holds the row. If your row was named, end and report; with no row named, take "
                       "the next ready row.",
                       "ends the lane with `stopped: claim failed: <error>`, which it reports and writes nowhere, "
                       "because with no worktree there is no row to write it on, and is never skipped silently",
                       "Take no other row: end and report that the row is taken."):
            self.assertIn(phrase, text, phrase)
        self.assertNotIn("Take the next row and say so.", text)

    def test_the_coordinator_hands_stage_starts_to_the_person(self):
        coordinator = skill("parallel-lanes").split("Coordinator mode, step by step:", 1)[1].split(
            "**A stacked slice", 1)[0]
        for phrase in ("When a lane reports that its row needs a stage only a person starts, or that its brief did not "
                       "match, give the person the exact words to start that stage for the row, list the row in your "
                       "report as `needs <stage> started by <who>`, and never send it to a sub-agent again until a "
                       "person has started that stage.",):
            self.assertIn(phrase, coordinator, phrase)

    def test_the_push_names_its_branch_and_a_rebase_not_pushed_is_the_persons(self):
        stacked = skill("parallel-lanes").split("**A stacked slice after its parent merges.**", 1)[1].split(
            "## Stop if", 1)[0]
        self.assertIn("`git push --force-with-lease --force-if-includes origin <slice 3's branch>`", stacked)
        for phrase in ("A slice rebased but not pushed makes a later claim's `--ff-only` and the ancestry check fail",
                       "push it with the same lease command, or tell a lane to (asking first), never a plain push"):
            self.assertIn(phrase, stacked, phrase)

    def test_the_design_agrees(self):
        design = " ".join(read(DESIGN).split())
        for phrase in ("taken: the next row only when no row was named, otherwise end and report; any other error stops",
                       "`needs <stage> started by <who>`",
                       "`git push --force-with-lease --force-if-includes origin <slice 3's branch>`"):
            self.assertIn(phrase, design, phrase)

    def test_the_refspec_push_succeeds_when_nobody_else_pushed(self):
        stacked = skill("parallel-lanes").split("**A stacked slice after its parent merges.**", 1)[1]
        push = command(stacked, "git push --force-with-lease").replace("<slice 3's branch>", "feat/s3")
        with tempfile.TemporaryDirectory() as folder:
            lane, _ = ParallelLanesFixRoundTest.remote_with(folder, "feat/other")
            git(lane, "checkout", "-q", "-b", "feat/s3", "main")
            (lane / "s3.txt").write_text("1\n", encoding="utf-8")
            git(lane, "add", "-A")
            git(lane, "commit", "-q", "-m", "s3")
            git(lane, "push", "-q", "origin", "feat/s3")
            git(lane, "fetch", "-q")
            git(lane, "commit", "-q", "--amend", "-m", "s3, rebased")
            self.assertNotEqual(sh("git push --force-with-lease --force-if-includes", lane).returncode, 0)
            git(lane, "commit", "-q", "--amend", "-m", "s3, rebased again")
            self.assertEqual(sh(push, lane).returncode, 0)
            self.assertEqual(git(lane, "ls-remote", "origin", "feat/s3").stdout.split()[0],
                             git(lane, "rev-parse", "HEAD").stdout.strip())

    def test_a_claim_onto_an_existing_folder_is_read_as_taken(self):
        with tempfile.TemporaryDirectory() as folder:
            lane, _ = ParallelLanesFixRoundTest.remote_with(folder, "feat/SHIP-12-eta-limit")
            git(lane, "checkout", "-q", "main")
            git(lane, "branch", "feat/other")
            self.assertEqual(sh("git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit", lane).returncode, 0)
            taken = sh("git worktree add .worktrees/SHIP-12 feat/other", lane)
            self.assertNotEqual(taken.returncode, 0)
            self.assertIn("already exists", taken.stderr)


LANE_LINE = "In a lane, release at your gate as `parallel-lanes` says."
LANE_STAGES = ("aidlc-intent", "aidlc-specify", "aidlc-discover", "aidlc-design", "aidlc-plan", "aidlc-build",
               "aidlc-verify", "aidlc-review", "aidlc-release")


class LaneLineTest(unittest.TestCase):
    """Task 4: each stage that marks a row in the item's index releases at its gate in a lane, in one identical line;
    the index gains the value the lane writes."""

    def test_each_lane_stage_has_the_line_once_at_the_end_of_its_gate(self):
        for name in LANE_STAGES:
            raw = read(f"skills/{name}/SKILL.md")
            self.assertEqual(raw.count(LANE_LINE), 1, name)
            self.assertEqual(raw.count("In a lane,"), 1, name)
            gate = raw.split("\n## Gate\n", 1)[1].split("\n## ", 1)[0]
            self.assertIn(LANE_LINE + " You draft; you never approve.", gate, name)

    def test_no_other_skill_has_it(self):
        for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
            if path.parent.name not in LANE_STAGES:
                self.assertNotIn("In a lane, release", path.read_text(encoding="utf-8"), path.parent.name)

    def test_the_lane_stages_are_the_ones_that_mark_the_items_row(self):
        for name in LANE_STAGES:
            self.assertIn("Mark this stage's row in the index", section(skill(name), "## Steps"), name)
        for name in ("aidlc-start", "aidlc-operate", "aidlc-feedback"):
            self.assertNotIn("Mark this stage's row in the index", skill(name), name)

    def test_the_index_gains_the_waiting_value(self):
        start, plan = (read(f"skills/{name}/assets/story-index.md") for name in ("aidlc-start", "aidlc-plan"))
        self.assertEqual(start, plan)
        self.assertIn("Each stage marks its own row when it ends: done, `waiting: <decision> by <who>` when it stops for "
                      "a person's decision in a lane (`parallel-lanes`), or `stopped: <reason>`.", " ".join(start.split()))


class SlicePlanTest(unittest.TestCase):
    """Task 5: the plan marks independent slices with DEPENDS ON lines; a plan without them works as before."""

    def test_the_bundle_has_an_optional_depends_on_line(self):
        bundle = read("skills/aidlc-plan/assets/task-bundle.md")
        block = bundle.split("```text\n", 1)[1].split("\n```", 1)[0]
        lines = [line for line in block.splitlines() if line.startswith("DEPENDS ON")]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("DEPENDS ON  none | slice <n>   ("), lines[0])
        self.assertIn("delete this line otherwise, and the part's slices share one branch and one pull request",
                      lines[0])

    def test_the_plan_marks_slices_independent_only_on_purpose(self):
        step5 = skill("aidlc-plan").split(" 5. Slice the work", 1)[1].split(" 6. Rate the tier", 1)[0]
        for phrase in ("**Independent slices (ADR 0025).**",
                       "give every bundle a `DEPENDS ON` line, `none` or the one slice it builds on",
                       "The first slice runs on the part's branch.",
                       "A later slice whose `DEPENDS ON` names the slice before it, on that branch, continues it, as "
                       "today.", "branch `<branch>-s<n>`", "`[<KEY>] slice <n> of <m>: <what>`",
                       "with `none` it starts from the default branch (a sibling pull request)",
                       "a stacked pull request, which merges after it", "A slice's own branch holds that slice only.",
                       "`DEPENDS ON` names at most one slice",
                       "keeps its index and its pull request's documents in `plans/<KEY>/slice-<n>/`",
                       "The plan, its bundles and these indexes merge on the default branch first, in their own pull "
                       "request (ADR 0020)"):
            self.assertIn(phrase, step5, phrase)

    def test_a_plan_without_depends_on_works_as_before(self):
        plan = skill("aidlc-plan")
        self.assertIn("A plan without `DEPENDS ON` lines works as before: one branch, one pull request, slices as "
                      "commits.", plan)
        self.assertIn("The part's slices share one branch and one pull request, so keep the whole part within the "
                      "pull-request size `reviewing-code` gives, unless the plan marks its slices independent", plan)
        self.assertIn("except `DEPENDS ON`, which is written only in a plan that marks its slices independent", plan)
        checklist = flat("skills/aidlc-plan/assets/plan.md")
        self.assertIn('every bundle field filled, or "none"', checklist)
        self.assertIn("DEPENDS ON lines only when the plan marks its slices independent (ADR 0025)", checklist)

    def test_the_plan_writes_each_slices_index_and_the_tech_lead_approves_the_split(self):
        plan = skill("aidlc-plan")
        self.assertIn("also write each such slice's index `plans/<KEY>/slice-<n>/README.md` from "
                      "`assets/story-index.md`", plan)
        self.assertIn("Each slice's stages mark only those rows.", plan)
        self.assertIn("A slice the plan marks independent gets its own branch, `<branch>-s<n>`, and its own pull "
                      "request (ADR 0025).", section(plan, "## Produces"))
        self.assertIn("The tech lead approves the bundles' `DEPENDS ON` lines with the plan", section(plan, "## Gate"))


if __name__ == "__main__":
    unittest.main()
