"""Tests for starter/repo/scripts/run_slices.py: each builds a small repository and a fake agent."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import run_slices  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false"]
COMMAND = ["agent", "-p"]
PROMPT = "/aidlc:aidlc-build {key} {slice}"


def bundle(mode="delegate", tier="1"):
    return (f"TASK BUNDLE · SHIP-7 · 1\nTIER        {tier} (the plan's rating)\n"
            f"MODE        {mode}   (approved with the bundle)\nDONE WHEN   tests green\n")


def brief(confirmed="Ana, 2026-11-08"):
    return f"FEATURE BRIEF · SHIP-7 · x\nTIER        1 (one repository)\nMODE        delegate\nCONFIRMED   {confirmed}\n"


class Repo:
    def __init__(self, files, branch="feat/SHIP-7-x"):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=self.root, check=True)
        self.commit("base")
        if branch != "main":
            subprocess.run(["git", "switch", "-q", "-c", branch], cwd=self.root, check=True)

    def commit(self, message):
        subprocess.run(["git", "add", "-A"], cwd=self.root, check=True)
        subprocess.run(GIT + ["commit", "-q", "--allow-empty", "-m", message], cwd=self.root, check=True)

    def agent(self, outcomes):
        """A fake agent: for each call, writes the slice's note with the next STATUS and commits it."""
        calls = []

        def invoke(argv, cwd):
            calls.append(argv)
            slice_name = argv[-1].split()[-1]
            state, code, dirty = outcomes.pop(0)
            if state is not None:
                note = self.root / "plans/SHIP-7" / f"progress-{slice_name}.md"
                note.write_text(f"# Progress\n\nSTATUS      {state}   (doing | done)\n", encoding="utf-8")
            self.commit(f"slice {slice_name}")
            if dirty:
                (self.root / "stray.txt").write_text("x", encoding="utf-8")
            return code

        return invoke, calls

    def run(self, slices, invoke, part=None):
        lines = []
        code = run_slices.run(self.root, "SHIP-7", slices, invoke, COMMAND, PROMPT, part=part, out=lines.append)
        return code, lines


class FieldTest(unittest.TestCase):
    def test_a_field_drops_its_note(self):
        self.assertEqual(run_slices.field("MODE        delegate with checkpoints   (approved)\n", "MODE"),
                         "delegate with checkpoints")

    def test_a_placeholder_is_no_value(self):
        self.assertIsNone(run_slices.field("MODE        <hands-on | delegate>   (x)\n", "MODE"))
        self.assertIsNone(run_slices.field("CONFIRMED   <engineer>, <YYYY-MM-DD>   (x)\n", "CONFIRMED"))

    def test_a_missing_field_is_none(self):
        self.assertIsNone(run_slices.field("GOAL  x\n", "MODE"))

    def test_tier_reads_the_number(self):
        self.assertEqual(run_slices.tier("TIER        2 (contract)\n"), 2)
        self.assertIsNone(run_slices.tier("TIER        <1 | 2 | 3>\n"))

    def test_documents_by_slice_name(self):
        plans = Path("plans/K")
        self.assertEqual(run_slices.document(plans, "fix"), plans / "fix.md")
        self.assertEqual(run_slices.document(plans, "brief"), plans / "brief.md")
        self.assertEqual(run_slices.document(plans, "2"), plans / "bundle-2.md")

    def test_curly_placeholders_are_no_value(self):
        self.assertIsNone(run_slices.field("MODE        {{hands-on | delegate}}\n", "MODE"))

    def test_fields_inside_a_fence_are_read(self):
        text = "# x\n\n```text\nTIER        1 (why)\nMODE        delegate   (note)\n```\n"
        self.assertEqual((run_slices.field(text, "MODE"), run_slices.tier(text)), ("delegate", 1))


class RunTest(unittest.TestCase):
    def test_every_slice_done_runs_in_order_and_exits_0(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle(), "plans/SHIP-7/bundle-2.md": bundle()})
        invoke, calls = repo.agent([("done", 0, False), ("done", 0, False)])
        code, lines = repo.run(["1", "2"], invoke)
        self.assertEqual(code, 0)
        self.assertEqual([c[-1] for c in calls], ["/aidlc:aidlc-build SHIP-7 1", "/aidlc:aidlc-build SHIP-7 2"])
        self.assertEqual(calls[0][:2], COMMAND)
        self.assertTrue(any("git diff" in line for line in lines))

    def test_a_stopped_slice_ends_the_run(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle() for n in (1, 2, 3)})
        invoke, calls = repo.agent([("done", 0, False), ("stopped: a new dependency", 0, False)])
        code, lines = repo.run(["1", "2", "3"], invoke)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 2)
        self.assertTrue(any("stopped: a new dependency" in line for line in lines))

    def test_a_checkpoint_pause_ends_the_run(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle("delegate with checkpoints", "2") for n in (1, 2)})
        invoke, calls = repo.agent([("paused: checkpoint 1", 0, False)])
        self.assertEqual(repo.run(["1", "2"], invoke)[0], 1)
        self.assertEqual(len(calls), 1)

    def test_a_session_that_leaves_doing_stops_the_run(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle() for n in (1, 2)})
        invoke, calls = repo.agent([("doing", 0, False)])
        self.assertEqual(repo.run(["1", "2"], invoke)[0], 1)
        self.assertEqual(len(calls), 1)

    def test_a_missing_note_stops_the_run(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle() for n in (1, 2)})
        invoke, calls = repo.agent([(None, 0, False)])
        code, lines = repo.run(["1", "2"], invoke)
        self.assertEqual(code, 1)
        self.assertTrue(any("missing" in line for line in lines))

    def test_a_failed_session_stops_the_run_even_when_done(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle() for n in (1, 2)})
        invoke, calls = repo.agent([("done", 1, False)])
        self.assertEqual(repo.run(["1", "2"], invoke)[0], 1)
        self.assertEqual(len(calls), 1)

    def test_uncommitted_changes_after_a_session_stop_the_run(self):
        repo = Repo({f"plans/SHIP-7/bundle-{n}.md": bundle() for n in (1, 2)})
        invoke, calls = repo.agent([("done", 0, True)])
        code, lines = repo.run(["1", "2"], invoke)
        self.assertEqual(code, 1)
        self.assertTrue(any("uncommitted" in line for line in lines))

    def test_briefs_run_as_fix_and_brief(self):
        repo = Repo({"plans/SHIP-7/brief.md": brief()})
        invoke, calls = repo.agent([("done", 0, False)])
        self.assertEqual(repo.run(["brief"], invoke)[0], 0)

    def test_a_part_reads_its_own_folder(self):
        repo = Repo({"plans/SHIP-7/part-2/bundle-1.md": bundle()})
        calls = []

        def invoke(argv, cwd):
            calls.append(argv)
            note = repo.root / "plans/SHIP-7/part-2/progress-1.md"
            note.write_text("STATUS      done\n", encoding="utf-8")
            repo.commit("slice")
            return 0

        lines = []
        code = run_slices.run(repo.root, "SHIP-7", ["1"], invoke, COMMAND, PROMPT + " part {part}", part=2,
                              out=lines.append)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][-1], "/aidlc:aidlc-build SHIP-7 1 part 2")


class RefuseTest(unittest.TestCase):
    """Every refusal happens before any session starts: exit 2, no call."""

    def refused(self, files, slices, branch="feat/SHIP-7-x", dirty=False):
        repo = Repo(files, branch)
        if dirty:
            (repo.root / "stray.txt").write_text("x", encoding="utf-8")
        invoke, calls = repo.agent([])
        code, lines = repo.run(slices, invoke)
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        return " ".join(lines)

    def test_a_hands_on_bundle_is_refused(self):
        self.assertIn("hands-on", self.refused({"plans/SHIP-7/bundle-1.md": bundle("hands-on")}, ["1"]))

    def test_a_bundle_without_mode_is_refused(self):
        self.assertIn("no MODE", self.refused({"plans/SHIP-7/bundle-1.md": "TIER        1\n"}, ["1"]))

    def test_a_mode_above_its_tier_is_refused(self):
        text = self.refused({"plans/SHIP-7/bundle-1.md": bundle("delegate", "2"),
                             "plans/SHIP-7/bundle-2.md": bundle("delegate with checkpoints", "3")}, ["1", "2"])
        self.assertIn("not allowed at Tier 2", text)
        self.assertIn("not allowed at Tier 3", text)

    def test_delegate_with_checkpoints_is_allowed_at_tier_2(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints", "2")})
        invoke, calls = repo.agent([("done", 0, False)])
        self.assertEqual(repo.run(["1"], invoke)[0], 0)

    def test_a_missing_bundle_is_refused(self):
        self.assertIn("not found", self.refused({"plans/SHIP-7/bundle-1.md": bundle()}, ["1", "2"]))

    def test_an_unconfirmed_brief_is_refused(self):
        self.assertIn("not confirmed", self.refused(
            {"plans/SHIP-7/brief.md": brief("<engineer>, <YYYY-MM-DD>")}, ["brief"]))

    def test_a_done_slice_is_refused(self):
        self.assertIn("already done", self.refused(
            {"plans/SHIP-7/bundle-1.md": bundle(), "plans/SHIP-7/progress-1.md": "STATUS      done\n"}, ["1"]))

    def test_a_slice_named_twice_is_refused(self):
        self.assertIn("twice", self.refused({"plans/SHIP-7/bundle-1.md": bundle()}, ["1", "1"]))

    def test_a_dirty_tree_is_refused(self):
        self.assertIn("uncommitted", self.refused({"plans/SHIP-7/bundle-1.md": bundle()}, ["1"], dirty=True))

    def test_the_default_branch_is_refused(self):
        self.assertIn("default branch", self.refused({"plans/SHIP-7/bundle-1.md": bundle()}, ["1"], branch="main"))


class MainTest(unittest.TestCase):
    def test_main_refuses_without_slices(self):
        with self.assertRaises(SystemExit):
            run_slices.main(["SHIP-7"])


class ReviewFixesTest(unittest.TestCase):
    """Plan 15 final review: each test was seen failing before its fix."""

    def test_i2_the_default_prompt_names_the_part(self):
        repo = Repo({"plans/SHIP-7/part-2/bundle-1.md": bundle()})
        calls = []

        def invoke(argv, cwd):
            calls.append(argv)
            (repo.root / "plans/SHIP-7/part-2/progress-1.md").write_text("STATUS      done\n", encoding="utf-8")
            repo.commit("slice")
            return 0

        code = run_slices.run(repo.root, "SHIP-7", ["1"], invoke, COMMAND, run_slices.DEFAULT_PROMPT, part=2,
                              out=lambda line: None)
        self.assertEqual(code, 0)
        self.assertEqual(calls[0][-1], "/aidlc:aidlc-build SHIP-7 1 part 2")

    def test_i3_a_paused_slice_needs_the_persons_confirmation(self):
        paused = "STATUS      paused: checkpoint 1\n"
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints"),
                     "plans/SHIP-7/progress-1.md": paused})
        invoke, calls = repo.agent([])
        code, lines = repo.run(["1"], invoke)
        self.assertEqual((code, calls), (2, []))
        self.assertIn("not confirmed", " ".join(lines))

    def test_i3_a_confirmed_pause_runs(self):
        note = ("STATUS      paused: checkpoint 1\n\n## Pauses confirmed (by the person)\n"
                "- checkpoint 1 confirmed by Ana, 2026-11-08\n")
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints"),
                     "plans/SHIP-7/progress-1.md": note})
        invoke, calls = repo.agent([("done", 0, False)])
        self.assertEqual(repo.run(["1"], invoke)[0], 0)

    def test_plan19_a_pause_confirmed_by_a_curly_placeholder_is_not_confirmed(self):
        note = ("STATUS      paused: checkpoint 1\n\n## Pauses confirmed (by the person)\n"
                "- checkpoint 1 confirmed by {{name}}, {{YYYY-MM-DD}}\n")
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints"),
                     "plans/SHIP-7/progress-1.md": note})
        invoke, calls = repo.agent([])
        code, lines = repo.run(["1"], invoke)
        self.assertEqual((code, calls), (2, []))

    def test_m1_a_branch_without_the_key_is_refused(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle()}, branch="trunk-work")
        invoke, calls = repo.agent([])
        code, lines = repo.run(["1"], invoke)
        self.assertEqual((code, calls), (2, []))
        self.assertIn("does not name SHIP-7", " ".join(lines))

    def test_m2_outside_a_repository_is_refused_plainly(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = []
            code = run_slices.run(Path(tmp), "SHIP-7", ["1"], lambda a, c: 0, COMMAND, PROMPT, out=lines.append)
        self.assertEqual(code, 2)
        self.assertIn("not a git repository", " ".join(lines))
        self.assertNotIn("detached", " ".join(lines))

    def test_m3_an_agent_that_cannot_start_is_a_clean_refusal(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle()})

        def invoke(argv, cwd):
            raise FileNotFoundError("agent")

        code, lines = repo.run(["1"], invoke)
        self.assertEqual(code, 2)
        self.assertIn("could not start", " ".join(lines))

    def test_m3_an_unknown_prompt_placeholder_is_refused(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle()})
        invoke, calls = repo.agent([])
        lines = []
        code = run_slices.run(repo.root, "SHIP-7", ["1"], invoke, COMMAND, "{nope}", out=lines.append)
        self.assertEqual((code, calls), (2, []))
        self.assertIn("--prompt", " ".join(lines))

    def test_m4_field_stays_on_its_line_and_reads_common_markup(self):
        self.assertIsNone(run_slices.field("STATUS\n\nMODE        delegate\n", "STATUS"))
        self.assertEqual(run_slices.field("STATUS:  `done`\n", "STATUS"), "done")
        self.assertEqual(run_slices.field("**STATUS** done\n", "STATUS"), "done")

    def test_m5_the_default_command_denies_push(self):
        argv = __import__("shlex").split(run_slices.DEFAULT_COMMAND)
        self.assertIn("--disallowedTools", argv)
        self.assertEqual(argv[argv.index("--disallowedTools") + 1], "Bash(git push*)")
        self.assertLess(argv.index("--disallowedTools"), argv.index("-p"))


class ApprovedOnDefaultTest(unittest.TestCase):
    """ADR 0020: a Tier 2 or 3 bundle runs only as the copy merged on the default branch."""

    def test_a_tier_2_bundle_only_on_the_branch_cannot_start(self):
        repo = Repo({"plans/SHIP-7/README.md": "# index\n"})
        (repo.root / "plans/SHIP-7/bundle-1.md").write_text(bundle("delegate with checkpoints", "2"), encoding="utf-8")
        repo.commit("plan on the branch")
        invoke, calls = repo.agent([("done", 0, False)])
        code, lines = repo.run(["1"], invoke)
        self.assertEqual(code, 2)
        self.assertIn("not there yet (ADR 0020)", "\n".join(lines))
        self.assertEqual(calls, [])

    def test_a_tier_2_bundle_changed_on_the_branch_cannot_start(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints", "2")})
        (repo.root / "plans/SHIP-7/bundle-1.md").write_text(bundle("delegate with checkpoints", "2") + "DO   more\n",
                                                            encoding="utf-8")
        repo.commit("edit")
        code, lines = repo.run(["1"], repo.agent([("done", 0, False)])[0])
        self.assertEqual(code, 2)
        self.assertIn("differs from the copy merged on main", "\n".join(lines))

    def test_a_tier_1_bundle_may_travel_with_the_code(self):
        repo = Repo({"plans/SHIP-7/README.md": "# index\n"})
        (repo.root / "plans/SHIP-7/bundle-1.md").write_text(bundle("delegate", "1"), encoding="utf-8")
        repo.commit("plan on the branch")
        code, _ = repo.run(["1"], repo.agent([("done", 0, False)])[0])
        self.assertEqual(code, 0)


class LoweredTierTest(unittest.TestCase):
    """T6: the check is decided by the higher of the merged copy's tier and the working copy's, so lowering TIER on
    the branch does not skip it."""

    def test_a_tier_2_bundle_on_main_lowered_to_tier_1_on_the_branch_cannot_start(self):
        repo = Repo({"plans/SHIP-7/bundle-1.md": bundle("delegate with checkpoints", "2")})
        (repo.root / "plans/SHIP-7/bundle-1.md").write_text(bundle("delegate", "1"), encoding="utf-8")
        repo.commit("lower the tier")
        invoke, calls = repo.agent([("done", 0, False)])
        code, lines = repo.run(["1"], invoke)
        self.assertEqual(code, 2)
        self.assertIn("differs from the copy merged on main", "\n".join(lines))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
