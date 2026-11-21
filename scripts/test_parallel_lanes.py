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


class SiblingSlicesTest(unittest.TestCase):
    """Task 6: a slice on its own branch edits only its own files; a stacked slice is moved with `git rebase --onto`,
    never merged."""

    def test_a_slice_on_its_own_branch_edits_only_its_own_files(self):
        build = section(skill("aidlc-build"), "## Inputs")
        self.assertIn("it keeps its index, its evidence file and its pull request's documents in "
                      "`plans/<KEY>/slice-<n>/`, and its progress note stays `plans/<KEY>/progress-<n>.md`", build)
        self.assertIn("It edits only its own row, its own progress note and its own evidence file, so sibling pull "
                      "requests never edit the same file.", build)
        self.assertIn("are in `plans/<KEY>/slice-<n>/` (ADR 0025): read and write them there, so sibling pull requests "
                      "never edit the same file.", section(skill("aidlc-review"), "## Inputs"))
        self.assertIn("read the evidence file and write the evidence table in `plans/<KEY>/slice-<n>/` (ADR 0025)",
                      section(skill("aidlc-verify"), "## Inputs"))
        self.assertIn("Check that the pull request is one part: one repository's share of the story, within the "
                      "pull-request size `reviewing-code` gives; or one slice that the plan gave its own branch "
                      "(`<branch>-s<n>`, ADR 0025)", skill("aidlc-review"))
        self.assertIn("(or `<branch>-s<n>` for a slice on its own branch)", section(skill("aidlc-build"), "## Produces"))

    def test_a_stacked_slice_is_moved_never_merged(self):
        step1 = section(skill("aidlc-build"), "## Steps").split(" 2. Read the bundle's TIER", 1)[0]
        self.assertIn("is moved first, as `parallel-lanes` says under \"A stacked slice after its parent merges\"", step1)
        self.assertIn("(read its `SKILL.md`, in the folder beside this skill's)", step1)
        self.assertIn("its own commits only, with `git rebase --onto`, never by merging the default branch into it",
                      step1)
        self.assertIn("Then run the repository's test and lint commands, named in `AGENTS.md`, before any change.", step1)
        self.assertIn("**A stacked slice after its parent merges.**", read(LANES))

    def test_rows_in_one_table_conflict_and_own_indexes_do_not(self):
        def second_merge_conflicts(path_for: dict) -> bool:
            with tempfile.TemporaryDirectory() as folder:
                repo = Path(folder)
                git(repo, "init", "-q", "-b", "main")
                for n, rel in path_for.items():
                    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                    with open(repo / rel, "a", encoding="utf-8") as index:
                        index.write(f"| merged slice {n} | repository | to do |\n")
                git(repo, "add", "-A")
                git(repo, "commit", "-q", "-m", "plan")
                for n, rel in path_for.items():
                    git(repo, "checkout", "-q", "-b", f"s{n}", "main")
                    text = (repo / rel).read_text(encoding="utf-8")
                    (repo / rel).write_text(text.replace(f"slice {n} | repository | to do", f"slice {n} | repository | done"),
                                            encoding="utf-8")
                    git(repo, "commit", "-q", "-am", f"slice {n} merged row")
                git(repo, "checkout", "-q", "main")
                git(repo, "merge", "-q", "--squash", "s2")
                git(repo, "commit", "-q", "-m", "slice 2")
                return git(repo, "merge", "-q", "--squash", "s3", check=False).returncode != 0

        self.assertTrue(second_merge_conflicts({2: "plans/SHIP-40/README.md", 3: "plans/SHIP-40/README.md"}))
        self.assertFalse(second_merge_conflicts({2: "plans/SHIP-40/slice-2/README.md",
                                                 3: "plans/SHIP-40/slice-3/README.md"}))

    def test_the_onto_rebase_replays_only_the_slices_own_commits(self):
        stacked = skill("parallel-lanes").split("**A stacked slice after its parent merges.**", 1)[1]
        onto, base = command(stacked, "git rebase --onto origin/"), command(stacked, "git merge-base ")
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            eta = repo / "eta.py"
            git(repo, "init", "-q", "-b", "main")
            eta.write_text("LIMIT = 1\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            git(repo, "checkout", "-q", "-b", "s2")
            for limit in (2, 3):
                eta.write_text(f"LIMIT = {limit}\n", encoding="utf-8")
                git(repo, "commit", "-q", "-am", f"slice 2, limit {limit}")
            git(repo, "checkout", "-q", "-b", "s3")
            (repo / "labels.py").write_text("from eta import LIMIT\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "slice 3")
            git(repo, "checkout", "-q", "main")
            git(repo, "merge", "-q", "--squash", "s2")
            git(repo, "commit", "-q", "-m", "slice 2 (squashed)")
            (repo / "delivery.md").write_text("other work\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "other work")
            git(repo, "remote", "add", "origin", str(repo))
            git(repo, "fetch", "-q", "origin")
            git(repo, "checkout", "-q", "s3")
            judged = git(repo, "rev-parse", "HEAD").stdout.strip()
            self.assertNotEqual(git(repo, "rebase", "origin/main", check=False).returncode, 0)
            git(repo, "rebase", "--abort")
            old = sh(base.replace("<slice 3's branch>", "s3").replace("<slice 2's branch>", "s2"), repo).stdout.strip()
            moved = sh(onto.replace("<default branch>", "main").replace("<slice 2's last commit>", old)
                       .replace("<slice 3's branch>", "s3"), repo)
            self.assertEqual(moved.returncode, 0, moved.stderr)
            self.assertEqual(git(repo, "log", "--format=%s", "origin/main..s3").stdout.split("\n")[:-1], ["slice 3"])
            self.assertEqual(eta.read_text(encoding="utf-8"), "LIMIT = 3\n")
            void = git(repo, "diff", "--name-only", judged, "HEAD").stdout.split()
            self.assertEqual(void, ["delivery.md"])


class SliceEvidencePathTest(unittest.TestCase):
    """Task 6 fix: every stage that writes or reads the evidence file names the slice folder's copy."""

    def test_the_slice_evidence_path_is_named_everywhere(self):
        path = "`plans/<KEY>/slice-<n>/review-evidence.md`"
        build, review = skill("aidlc-build"), skill("aidlc-review")
        self.assertIn(f"commit it on its own ({path} for a slice on its own branch); its Recipe", build)
        self.assertIn(f"and the evidence file `plans/<KEY>/review-evidence.md` ({path} for a slice on its own branch).",
                      section(build, "## Produces"))
        self.assertIn(f"commit it on its own ({path} for a slice on its own branch), at the "
                      "pull request's head.", review)
        self.assertIn(f"In `plans/<KEY>/` (`plans/<KEY>/slice-<n>/` for a slice on its own branch), on the part's branch",
                      section(review, "## Produces"))
        self.assertIn("A slice on its own branch edits the same documents in `plans/<KEY>/slice-<n>/`.",
                      section(build, "## Rules"))
        for name in ("reviewer-tests", "reviewer-compliance"):
            self.assertIn(f"{path} for a slice on its own branch", read(f"agents/{name}.md").replace("\n  ", " "), name)


class OnboardLanesTest(unittest.TestCase):
    """Task 7: onboarding keeps the lanes' worktrees out of every commit, in the clone they start from, and says the
    one-clone rule."""

    def test_onboard_ignores_the_worktrees_and_says_the_rule(self):
        onboard = skill("aidlc-onboard")
        for phrase in ("**Parallel lanes.**", "`git check-ignore -q .worktrees/`",
                       "add the line `.worktrees/` to git's own exclude file",
                       "`echo '.worktrees/' >> \"$(git rev-parse --git-common-dir)/info/exclude\"`",
                       "lanes for one repository start from one clone on one machine",
                       "nobody checks out a queued branch in their own working copy while lanes may claim it"):
            self.assertIn(phrase, onboard, phrase)

    def test_the_commands_keep_a_worktree_out_of_git_status(self):
        add = command(skill("aidlc-onboard"), "echo '.worktrees/'")
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            git(repo, "init", "-q", "-b", "main")
            (repo / "README.md").write_text("x\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
            self.assertNotEqual(git(repo, "check-ignore", "-q", ".worktrees/", check=False).returncode, 0)
            self.assertEqual(sh(add, repo).returncode, 0)
            self.assertEqual(git(repo, "check-ignore", "-q", ".worktrees/", check=False).returncode, 0)
            git(repo, "worktree", "add", "-q", "-b", "feat/SHIP-12-eta-limit", ".worktrees/SHIP-12")
            self.assertEqual(git(repo, "status", "--porcelain").stdout, "")


LANE_CASES = ("gate-lane-worktree-taken", "gate-lane-plan-approval", "gate-coordinator-clash",
              "gate-lane-stacked-rebase")
# For each Bash or Agent grader: inputs a correct run may give (they must not match a `max: 0` grader, and must match
# a `min: 1` grader) and inputs a wrong run would give (the reverse). A Bash input is a command; an Agent input is the
# sub-agent's prompt.
BRIEF = ("Read /home/dev/aidlc/skills/parallel-lanes/SKILL.md before anything else. You are a lane for the row SHIP-32. "
         "Its stage skill is /home/dev/aidlc/skills/aidlc-build/SKILL.md: read it and follow it in full.")
SAMPLES = {
    ("gate-lane-worktree-taken", "claims-the-next-row.md"): (
        ["git worktree add -b feat/SHIP-15-label-prefix .worktrees/SHIP-15 origin/main",
         'git worktree add -b feat/SHIP-15-label-prefix "/work/shipments/.worktrees/SHIP-15" origin/main',
         "git fetch && git worktree add -b feat/SHIP-15-label-prefix .worktrees/SHIP-15 origin/main"],
        ["git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit"]),
    ("gate-lane-worktree-taken", "never-forces-a-claim.md"): (
        ["git worktree add -b feat/SHIP-15-label-prefix .worktrees/SHIP-15 origin/main",
         "git worktree add .worktrees/SHIP-12 feat/SHIP-12-eta-limit"],
        ["git worktree add -f .worktrees/SHIP-12 feat/SHIP-12-eta-limit",
         "git worktree add --force .worktrees/SHIP-12b feat/SHIP-12-eta-limit",
         "git worktree add -B feat/SHIP-12-eta-limit .worktrees/SHIP-12b origin/main",
         'git worktree add --force "/work/shipments/.worktrees/SHIP-12b" feat/SHIP-12-eta-limit',
         "git worktree add -f .worktrees/SHIP-12b feat/SHIP-12-eta-limit && git worktree list"]),
    ("gate-lane-worktree-taken", "leaves-the-other-lane-alone.md"): (
        ["git worktree list", "git worktree remove .worktrees/SHIP-15"],
        ["git worktree remove .worktrees/SHIP-12", "git worktree remove --force .worktrees/SHIP-12",
         'git worktree remove "/work/shipments/.worktrees/SHIP-12"']),
    ("gate-lane-worktree-taken", "no-bash-in-the-other-worktree.md"): (
        ["git -C .worktrees/SHIP-12 status", "git -C .worktrees/SHIP-15 commit -m x", "git worktree list",
         "git -C .worktrees/SHIP-12-again status"],
        ["git -C .worktrees/SHIP-12 commit -am x", "cd .worktrees/SHIP-12 && git checkout .",
         'git -C "/work/shipments/.worktrees/SHIP-12" stash', "git -C .worktrees/SHIP-12/ reset --hard"]),
    ("gate-lane-plan-approval", "removes-its-worktree.md"): (
        ["git worktree remove .worktrees/SHIP-21", 'git worktree remove "/work/shipments/.worktrees/SHIP-21"'],
        ["git worktree list"]),
    ("gate-lane-plan-approval", "never-forces-removal.md"): (
        ["git worktree remove .worktrees/SHIP-21"],
        ["git worktree remove --force .worktrees/SHIP-21", "git worktree remove -f .worktrees/SHIP-21",
         'git worktree remove -f "/work/shipments/.worktrees/SHIP-21"',
         "git worktree remove --force .worktrees/SHIP-21 && git worktree prune"]),
    ("gate-coordinator-clash", "no-claim-held-back.md"): (
        ["git worktree add -b feat/SHIP-32-label-prefix .worktrees/SHIP-32 origin/main", "git worktree list"],
        ["git worktree add .worktrees/SHIP-31 feat/SHIP-31-short-trips",
         "git worktree add -b feat/SHIP-33-tracking-link .worktrees/SHIP-33 origin/main",
         "git worktree add -b feat/SHIP-34-depot-hours .worktrees/SHIP-34 origin/main"]),
    ("gate-coordinator-clash", "leaves-the-running-lane.md"): (
        ["git worktree list", "git worktree remove .worktrees/SHIP-32"],
        ["git worktree remove .worktrees/SHIP-30", "git worktree remove .worktrees/SHIP-35",
         'git worktree remove "/work/shipments/.worktrees/SHIP-35"']),
    ("gate-coordinator-clash", "one-lane.md"): ([BRIEF], []),
    ("gate-coordinator-clash", "brief-reads-the-workflow-skill.md"): (
        [BRIEF, BRIEF.replace("Read /home/dev/aidlc/skills/parallel-lanes/SKILL.md",
                              "Read `/home/dev/aidlc/skills/parallel-lanes/SKILL.md`")],
        ["Run lane mode for SHIP-32.", "Use the parallel-lanes skill for SHIP-32, then /aidlc:aidlc-build."]),
    ("gate-coordinator-clash", "brief-names-the-stage-skill.md"): (
        [BRIEF], ["Read /home/dev/aidlc/skills/parallel-lanes/SKILL.md before anything else. Row SHIP-32: run "
                  "/aidlc:aidlc-build."]),
    ("gate-coordinator-clash", "brief-names-the-row.md"): (
        [BRIEF], [BRIEF.replace("SHIP-32", "the next ready row")]),
    ("gate-coordinator-clash", "no-lane-for-the-clash.md"): ([BRIEF], [BRIEF.replace("SHIP-32", "SHIP-31")]),
    ("gate-coordinator-clash", "no-sub-agent-for-the-plan-row.md"): (
        [BRIEF], [BRIEF.replace("SHIP-32", "SHIP-33").replace("aidlc-build", "aidlc-plan")]),
    ("gate-coordinator-clash", "no-lane-past-the-limit.md"): ([BRIEF], [BRIEF.replace("SHIP-32", "SHIP-34")]),
    ("gate-lane-stacked-rebase", "rebases-onto.md"): (
        ["git -C .worktrees/SHIP-40-s3 rebase --onto origin/main 1a2b3c4 feat/SHIP-40-eta-limit-s3"],
        ["git rebase origin/main", "git merge origin/main"]),
    ("gate-lane-stacked-rebase", "never-merges-main.md"): (
        ["git merge-base feat/SHIP-40-eta-limit-s3 origin/feat/SHIP-40-eta-limit-s2",
         "git merge-base --is-ancestor origin/feat/SHIP-40-eta-limit-s3 feat/SHIP-40-eta-limit-s3",
         "git merge --ff-only origin/feat/SHIP-40-eta-limit-s3",
         "git show origin/main:plans/SHIP-40/slice-2/README.md",
         "git merge --ff-only origin/feat/SHIP-40-eta-limit-s3 && git log origin/main..HEAD",
         "git fetch origin && git merge-base --is-ancestor origin/feat/SHIP-40-eta-limit-s3 HEAD && git show origin/main:QUEUE.md"],
        ["git merge origin/main", "git merge --no-ff origin/main", "git -C .worktrees/SHIP-40-s3 merge --no-edit origin/main", "git merge main"]),
    ("gate-lane-stacked-rebase", "never-pulls.md"): (
        ["git fetch origin", "git -C .worktrees/SHIP-40-s3 fetch"],
        ["git pull", "git -C .worktrees/SHIP-40-s3 pull origin main", "git -c core.editor=true pull"]),
    ("gate-lane-stacked-rebase", "asks-before-pushing.md"): (
        ["git fetch", "git log --oneline origin/main..HEAD",
         "git merge-base --is-ancestor origin/feat/SHIP-40-eta-limit-s3 feat/SHIP-40-eta-limit-s3"],
        ["git push --force-with-lease", "git -C .worktrees/SHIP-40-s3 push --force-with-lease origin HEAD",
         "git push --force-with-lease --force-if-includes origin feat/SHIP-40-eta-limit-s3",
         "git -c push.default=simple push origin HEAD", "git -C .worktrees/SHIP-40-s3 -c k=v push"]),
}

# Write and Edit graders: the tool's input (a dict) a correct run may give, and one a wrong run would give.
FILE_SAMPLES = {
    ("gate-lane-worktree-taken", "no-edit-in-the-other-worktree.md"): (
        [{"file_path": "/work/.worktrees/SHIP-15/plans/SHIP-15/intent.md", "new_string": "x"}],
        [{"file_path": "/work/.worktrees/SHIP-12/plans/SHIP-12/progress-1.md", "new_string": "x"}]),
    ("gate-lane-worktree-taken", "no-write-in-the-other-worktree.md"): (
        [{"file_path": "/work/.worktrees/SHIP-15/plans/SHIP-15/spec.md", "content": "x"}],
        [{"file_path": "/work/.worktrees/SHIP-12/src/shipments/eta.py", "content": "x"}]),
    ("gate-lane-plan-approval", "no-code-edit.md"): (
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/plan.md", "new_string": "x"}],
        [{"file_path": "/work/.worktrees/SHIP-21/src/shipments/eta.py", "new_string": "x"},
         {"file_path": "/work/.worktrees/SHIP-21/tests/test_eta.py", "new_string": "x"}]),
    ("gate-lane-plan-approval", "no-code-write.md"): (
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/plan.md", "content": "x"}],
        [{"file_path": "/work/.worktrees/SHIP-21/src/shipments/eta.py", "content": "x"},
         {"file_path": "/work/.worktrees/SHIP-21/tests/test_eta.py", "content": "x"}]),
    ("gate-lane-plan-approval", "no-approval-record-write.md"): (
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/plan.md",
          "content": "# Plan\n\nAPPROVAL   waiting: plan approval by Ana (tech lead)\n"}],
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/plan.md",
          "content": "# Plan\n\nAPPROVAL   plan.md v1 approved by Ana (tech lead), 2026-11-21, in the session.\n"}]),
    ("gate-lane-plan-approval", "no-approval-record-edit.md"): (
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/README.md", "old_string": "to do",
          "new_string": "waiting: plan approval by Ana (tech lead)"}],
        [{"file_path": "/work/.worktrees/SHIP-21/plans/SHIP-21/plan.md", "old_string": "APPROVAL",
          "new_string": "APPROVAL   plan.md v1 approved by Ana (tech lead), 2026-11-21"}]),
    ("gate-coordinator-clash", "no-queue-edit.md"): (
        [{"file_path": "/work/plans/SHIP-32/plan.md", "new_string": "x"}],
        [{"file_path": "/work/QUEUE.md", "new_string": "x"}]),
    ("gate-coordinator-clash", "no-queue-write.md"): (
        [{"file_path": "/work/plans/SHIP-32/plan.md", "content": "x"}],
        [{"file_path": "/work/QUEUE.md", "content": "x"}]),
}


def front(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---") else ""


def scaffold(case: str, folder: Path) -> None:
    """Build a case's scaffold in an empty folder, as the eval runner does."""
    subprocess.run(["bash", str(ROOT / "evals" / case / "setup.sh")], cwd=folder, env=clean_env(), check=True,
                   capture_output=True, text=True)


class LaneCasesTest(unittest.TestCase):
    """Task 8: four behaviour cases for the lanes, tagged gate; each grader tells a right run from a wrong one, and each
    scaffold holds the state its graders assume."""

    def test_the_four_cases_exist_and_are_listed(self):
        readme = " ".join(read("evals/README.md").split())
        self.assertIn("there are 36 cases", readme)
        for case in LANE_CASES:
            prompt = read(f"evals/{case}/prompt.md")
            self.assertIn("tags: [gate]", front(prompt), case)
            self.assertTrue(prompt.split("---", 2)[2].strip().startswith("/aidlc:parallel-lanes "), case)
            self.assertTrue(list((ROOT / "evals" / case / "graders").glob("*.md")), case)
            self.assertIn(f"`{case}`", readme, case)

    def test_each_bash_and_agent_grader_tells_right_from_wrong(self):
        for (case, name), (right, wrong) in SAMPLES.items():
            fm = front(read(f"evals/{case}/graders/{name}"))
            tool = re.search(r"(?m)^tool: (Bash|Agent)$", fm).group(1)
            field = "command" if tool == "Bash" else "prompt"
            pattern = re.search(r"(?m)^input_match: '(.*)'$", fm).group(1)
            wanted = re.search(r"(?m)^min: 1$", fm) is not None
            for given, should_match in [(c, wanted) for c in right] + [(c, not wanted) for c in wrong]:
                found = re.search(pattern, json.dumps({field: given})) is not None
                self.assertEqual(found, should_match, f"{case}/{name}: {given}")
        graded = {(c, g.name) for c in LANE_CASES for g in (ROOT / "evals" / c / "graders").glob("*.md")
                  if re.search(r"(?m)^tool: (Bash|Agent)$", g.read_text(encoding="utf-8"))}
        self.assertEqual(graded, set(SAMPLES))

    def test_each_write_and_edit_grader_tells_right_from_wrong(self):
        for (case, name), (right, wrong) in FILE_SAMPLES.items():
            fm = front(read(f"evals/{case}/graders/{name}"))
            tool = re.search(r"(?m)^tool: (Write|Edit)$", fm).group(1)
            pattern = re.search(r"(?m)^input_match: '(.*)'$", fm).group(1)
            for given, should_match in [(g, False) for g in right] + [(g, True) for g in wrong]:
                found = re.search(pattern, json.dumps(given)) is not None
                self.assertEqual(found, should_match, f"{case}/{name}: {given}")
            self.assertEqual(tool, "Write" if "content" in wrong[0] else "Edit", f"{case}/{name}")
        graded = {(c, g.name) for c in LANE_CASES for g in (ROOT / "evals" / c / "graders").glob("*.md")
                  if re.search(r"(?m)^tool: (Write|Edit)$", g.read_text(encoding="utf-8"))}
        self.assertEqual(graded, set(FILE_SAMPLES))

    def test_the_taken_row_is_locked_and_the_next_one_is_free(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-lane-worktree-taken", repo)
            self.assertEqual(git(repo, "check-ignore", "-q", ".worktrees/", check=False).returncode, 0)
            self.assertIn(".worktrees/SHIP-12", git(repo, "worktree", "list").stdout)
            taken = git(repo, "worktree", "add", ".worktrees/SHIP-12-again", "feat/SHIP-12-eta-limit", check=False)
            self.assertNotEqual(taken.returncode, 0)
            queue = git(repo, "show", "origin/main:QUEUE.md").stdout
            self.assertIn("| 1 | SHIP-12 | . | feat/SHIP-12-eta-limit | none |", queue)
            self.assertIn("| 2 | SHIP-15 | . | feat/SHIP-15-label-prefix | none |", queue)
            self.assertIn("| aidlc-specify | repository | to do |", git(repo, "show", "origin/main:plans/SHIP-15/README.md").stdout)
            claim = git(repo, "worktree", "add", "-b", "feat/SHIP-15-label-prefix", ".worktrees/SHIP-15", "origin/main")
            self.assertEqual(claim.returncode, 0)

    def test_the_plan_row_is_ready_and_its_prompt_names_the_stage(self):
        prompt = read("evals/gate-lane-plan-approval/prompt.md")
        self.assertIn("/aidlc:aidlc-plan", prompt)
        self.assertNotIn("/aidlc:aidlc-build", prompt)
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-lane-plan-approval", repo)
            index = git(repo, "show", "origin/main:plans/SHIP-21/README.md").stdout
            self.assertIn("| aidlc-design | repository | done |", index)
            self.assertIn("| aidlc-plan | repository | to do |", index)
            self.assertNotEqual(git(repo, "rev-parse", "--verify", "-q", "feat/SHIP-21-weekend-days", check=False)
                                .returncode, 0)
            git(repo, "worktree", "add", "-q", "-b", "feat/SHIP-21-weekend-days", ".worktrees/SHIP-21", "origin/main")
            self.assertEqual(git(repo, "worktree", "remove", ".worktrees/SHIP-21", check=False).returncode, 0)

    def test_the_coordinator_case_has_one_free_slot_one_clash_and_one_plan_row(self):
        prompt = read("evals/gate-coordinator-clash/prompt.md")
        self.assertNotIn("/aidlc:aidlc-", prompt)
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-coordinator-clash", repo)
            queue = git(repo, "show", "origin/main:QUEUE.md").stdout
            # The one sub-agent, SHIP-32, is correct whatever lane reports arrive: SHIP-31 waits for the running
            # SHIP-30 (same files), SHIP-33 is a plan row (a person starts it), SHIP-34 waits for SHIP-32 (order),
            # and two running lanes plus SHIP-32 and the hand-started SHIP-33 fill MAX LANES 4.
            self.assertIn("MAX LANES   4", queue)
            self.assertEqual(len(re.findall(r"(?m)^\| [1-6] \| SHIP-3[0-5] \|", queue)), 6)
            self.assertIn("| 5 | SHIP-34 | . | feat/SHIP-34-depot-hours | SHIP-32 |", queue)
            for key in ("SHIP-31", "SHIP-32", "SHIP-33", "SHIP-35"):
                self.assertRegex(queue, rf"(?m)^\| \d \| {key} \|.*\| none \|$")
            listing = git(repo, "worktree", "list").stdout
            self.assertIn(".worktrees/SHIP-30", listing)
            self.assertIn(".worktrees/SHIP-35", listing)
            self.assertEqual(listing.count(".worktrees/"), 2)

            def may_change(key: str, branch: str) -> str:
                bundle = git(repo, "show", f"{branch}:plans/{key}/bundle-1.md").stdout
                return re.search(r"(?m)^MAY CHANGE  (.*)$", bundle).group(1)

            running = may_change("SHIP-30", "feat/SHIP-30-eta-cap")
            self.assertIn("src/shipments/eta.py", running)
            self.assertIn("src/shipments/eta.py", may_change("SHIP-31", "feat/SHIP-31-short-trips"))
            self.assertNotIn("src/shipments/eta.py", may_change("SHIP-32", "feat/SHIP-32-label-prefix"))
            self.assertEqual(may_change("SHIP-34", "feat/SHIP-34-depot-hours"), "docs/delivery.md")
            self.assertNotIn("src/shipments/eta.py", may_change("SHIP-35", "feat/SHIP-35-delivery-rules"))
            for key, branch in (("SHIP-32", "feat/SHIP-32-label-prefix"), ("SHIP-34", "feat/SHIP-34-depot-hours")):
                index = git(repo, "show", f"{branch}:plans/{key}/README.md").stdout
                self.assertIn("| aidlc-plan | repository | done |", index, key)
                self.assertIn("approved by Ana (tech lead)", git(repo, "show", f"{branch}:plans/{key}/plan.md").stdout)
            self.assertIn("| aidlc-plan | repository | to do |",
                          git(repo, "show", "origin/main:plans/SHIP-33/README.md").stdout)

    def test_the_stacked_slice_rebases_cleanly_only_with_onto(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            scaffold("gate-lane-stacked-rebase", repo)
            self.assertIn("| merged | repository | done |",
                          git(repo, "show", "origin/main:plans/SHIP-40/slice-2/README.md").stdout)
            git(repo, "worktree", "add", "-q", ".worktrees/SHIP-40-s3", "feat/SHIP-40-eta-limit-s3")
            lane = repo / ".worktrees" / "SHIP-40-s3"
            judged = git(lane, "rev-parse", "HEAD").stdout.strip()
            self.assertNotEqual(git(lane, "rebase", "origin/main", check=False).returncode, 0)
            git(lane, "rebase", "--abort")
            old = git(lane, "merge-base", "feat/SHIP-40-eta-limit-s3", "origin/feat/SHIP-40-eta-limit-s2").stdout.strip()
            git(lane, "rebase", "-q", "--onto", "origin/main", old, "feat/SHIP-40-eta-limit-s3")
            void = git(lane, "diff", "--name-only", judged, "HEAD", "--", ":(top)", ":(top,exclude)plans/SHIP-40/")
            self.assertEqual(void.stdout.split(), ["docs/delivery.md"])
            result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=lane,
                                    env=clean_env(), capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)


def workflow_skills() -> list:
    """Every skill whose metadata says `kind: workflow`."""
    found = []
    for path in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        if validate.KIND_WORKFLOW.search(text[: text.find("\n---", 4)]):
            found.append(path.parent.name)
    return found


class DocsTest(unittest.TestCase):
    """Task 9: the four kinds of skill are listed where a team reads, and the change list says what Plan 23 covers."""

    def test_the_readme_lists_the_workflow_skill_and_its_command(self):
        readme = read("README.md")
        self.assertIn("| Stage skills | Practice skills | Workflow skills |", readme)
        self.assertIn("`testing-in-browser`, `writing-documentation` | `parallel-lanes` |", readme)
        commands = readme.split("## Commands you type", 1)[1].split("\n## ", 1)[0]
        self.assertIn("| `/aidlc:parallel-lanes coordinator` |", commands)
        text = flat("README.md")
        self.assertIn("**Several at once:** the `parallel-lanes` workflow skill runs lanes, each in its own git worktree",
                      text)
        self.assertIn("The map of the four kinds of skill (stage, practice, workflow and map)", text)

    def test_the_map_skill_names_the_four_kinds(self):
        text = skill("using-aidlc")
        self.assertIn("aidlc has four kinds of skill.", text)
        self.assertNotIn("two kinds of skill", text)
        for kind in ("**Stage skills**", "**Practice skills**", "**Workflow skills**", "**The map**"):
            self.assertIn(kind, text, kind)

    def test_every_workflow_skill_is_named_where_a_team_reads(self):
        self.assertEqual(workflow_skills(), ["parallel-lanes"])
        for name in workflow_skills():
            for rel in ("README.md", "skills/using-aidlc/SKILL.md", "AGENTS.md", "docs/codebase-map.md"):
                self.assertIn(name, read(rel), f"{rel}: {name}")

    def test_the_codebase_map_says_where_a_workflow_skill_goes(self):
        mapping = flat("docs/codebase-map.md")
        self.assertIn("`skills/parallel-lanes/` the workflow skill", mapping)
        self.assertIn("A new workflow skill: `skills/<noun-phrase>/SKILL.md` with `metadata.kind: workflow`", mapping)
        self.assertIn("Last verified: 2026-11-21", mapping)

    def test_the_change_list_marks_what_plan_23_covers(self):
        changes = read("docs/design/2026-11-19-aidlc-6-change-list.md")
        table = changes.split("## 7. After Plan 23 (2026-11-21)", 1)[1]
        for item in ("D1", "D2", "E1", "E2", "E3", "E4", "E5", "Decision D1", "Decision D7"):
            self.assertRegex(table, rf"(?m)^\| {item} \|", item)
        self.assertIn("`docs/plans/2026-11-21-plan-23-parallel-lanes.md`", table)


if __name__ == "__main__":
    unittest.main()
