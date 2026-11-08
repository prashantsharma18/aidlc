"""Tests for starter/workspace/scripts/story_status.py: each builds a small workspace in a temporary folder."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "workspace" / "scripts"))
import story_status  # noqa: E402

PLAN = """Coordination plan · SHIP-1 · Track shipments · v1
OUTCOME    Customers see where a shipment is. Tier 2
PARTS      #  Repository     Owner    Change                 Flag          Waits for     Undo       Status
           1  <repository>   <team>   <what changes>         <flag, off>   <tag or ->    flag off   waiting
           1  shipments-api  core     add tracking endpoint  track-v1      -             flag off   see status.md
           2  web-portal     web      show tracking          track-v1      part 1        flag off   see status.md
TRACKING   Branch feat/SHIP-1-<part> in each repository
"""
PINS = "spec v1 · plan v1 · contract tracking-api v1"


def story(root: Path, current: str = "spec v1 · contract tracking-api v1", extra: str = "") -> None:
    d = root / "stories" / "SHIP-1"
    d.mkdir(parents=True)
    (d / "README.md").write_text(f"# SHIP-1 · Track shipments\n\nCURRENT    {current}\n{extra}\n", encoding="utf-8")
    (d / "coordination-plan.md").write_text(PLAN, encoding="utf-8")


def part(root: Path, repo: str, pins: str | None = PINS, done=(), stopped=None, word: str = "done",
         newline: str = "\n") -> None:
    d = root / repo / "plans" / "SHIP-1"
    d.mkdir(parents=True)
    rows = []
    for stage in story_status.STAGES:
        status = word if stage in done else "to do"
        if stopped and stage == stopped[0]:
            status = f"stopped: {stopped[1]}"
        rows.append(f"| {stage} | {repo} | {status} |")
    lines = ["# SHIP-1 · part", ""] + ([f"PINS       {pins}"] if pins is not None else []) + [
        "", "| Stage | Runs in | Status |", "|---|---|---|", *rows, ""]
    (d / "README.md").write_bytes(newline.join(lines).encode("utf-8"))


ALL = story_status.STAGES


class StoryStatusTest(unittest.TestCase):
    def run_status(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            return {r.repository: r for r in story_status.story_status(root, "SHIP-1")}

    def test_template_rows_are_ignored(self):
        self.assertEqual(story_status.parts(PLAN), [(1, "shipments-api"), (2, "web-portal")])

    def test_versions_are_parsed(self):
        self.assertEqual(story_status.parse_versions(PINS), {"spec": 1, "plan": 1, "contract tracking-api": 1})
        self.assertEqual(story_status.parse_versions("none"), {})

    def test_a_part_with_no_index_is_waiting(self):
        rows = self.run_status(lambda r: (story(r), (r / "shipments-api").mkdir(), (r / "web-portal").mkdir()))
        self.assertEqual(rows["shipments-api"].reached, "waiting")

    def test_the_stage_reached_is_the_last_done_row(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL[:3]), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "aidlc-verify")
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_stale_spec_pin_needs_a_re_plan_even_when_merged(self):
        rows = self.run_status(lambda r: (story(r, current="spec v2 · contract tracking-api v1"),
                                          part(r, "shipments-api", done=ALL), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "merged")
        self.assertIn("re-plan: spec v1 < v2", rows["shipments-api"].needs)

    def test_an_unaffected_record_clears_the_spec_re_plan(self):
        extra = "UNAFFECTED shipments-api spec v2: only the portal shows the new label, Ana (tech lead), 2026-11-09"
        rows = self.run_status(lambda r: (story(r, current="spec v2 · contract tracking-api v1", extra=extra),
                                          part(r, "shipments-api", done=ALL), part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_stale_contract_pin_needs_a_re_plan(self):
        rows = self.run_status(lambda r: (story(r, current="spec v1 · contract tracking-api v2"),
                                          part(r, "shipments-api"), part(r, "web-portal")))
        self.assertIn("re-plan: contract tracking-api v1 < v2", rows["web-portal"].needs)

    def test_a_missing_repository_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api")))
        self.assertEqual(rows["web-portal"].reached, "missing")
        self.assertIn("web-portal is not in the workspace", rows["web-portal"].needs)

    def test_a_stopped_stage_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL[:1],
                                                         stopped=("aidlc-build", "assertion would change")),
                                          part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "aidlc-plan")
        self.assertIn("aidlc-build stopped: assertion would change", rows["shipments-api"].needs)

    def test_release_is_ready_only_when_every_part_is_merged_at_current_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal", done=ALL[:4])
            self.assertFalse(story_status.release_ready(story_status.story_status(root, "SHIP-1")))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal", done=ALL)
            self.assertTrue(story_status.release_ready(story_status.story_status(root, "SHIP-1")))

    def test_write_saves_status_md_and_check_release_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal")
            with redirect_stdout(io.StringIO()):
                code = story_status.main(["SHIP-1", "--root", tmp, "--write", "--check-release"])
            self.assertEqual(code, 1)
            status = (root / "stories" / "SHIP-1" / "status.md").read_text(encoding="utf-8")
            self.assertIn("| 1 | shipments-api | merged |", status)
            self.assertIn("Release: not ready", status)

    def test_a_missing_story_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(story_status.main(["SHIP-9", "--root", tmp]), 2)

    def test_case_and_crlf_are_tolerated(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", done=ALL, word="Done", newline="\r\n"),
                                          part(r, "web-portal")))
        self.assertEqual(rows["shipments-api"].reached, "merged")

    def test_a_pin_on_a_contract_the_story_dropped_is_reported(self):
        rows = self.run_status(lambda r: (story(r, current="spec v1"), part(r, "shipments-api"), part(r, "web-portal")))
        self.assertIn("pins contract tracking-api, which the story no longer lists", rows["shipments-api"].needs)

    def test_a_part_without_pins_is_reported(self):
        rows = self.run_status(lambda r: (story(r), part(r, "shipments-api", pins=None, done=ALL[:2]),
                                          part(r, "web-portal")))
        self.assertIn("no PINS line", rows["shipments-api"].needs)

    # Final review fixes (C2, I1, I2, I3, I7, M6)
    def problems_for(self, build):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build(root)
            return (story_status.story_status(root, "SHIP-1"), story_status.story_problems(root, "SHIP-1"))

    def test_a_story_without_a_current_spec_is_not_releasable(self):
        for current in ("spec v<n> · contract <name> v<n>", ""):
            rows, problems = self.problems_for(lambda r: (story(r, current=current), part(r, "shipments-api", done=ALL),
                                                          part(r, "web-portal", done=ALL)))
            self.assertIn("the story index has no CURRENT spec version", problems, current)
            self.assertFalse(story_status.release_ready(rows, problems), current)

    def test_a_part_without_a_spec_pin_needs_a_re_plan(self):
        rows, _ = self.problems_for(lambda r: (story(r, current="spec v2 · contract tracking-api v1"),
                                               part(r, "shipments-api", pins="plan v1 · contract tracking-api v1", done=ALL),
                                               part(r, "web-portal")))
        self.assertIn("no spec pin", {r.repository: r for r in rows}["shipments-api"].needs)

    def test_parts_rows_with_a_path_or_a_dotted_number_are_read(self):
        plan = "PARTS      #  Repository\n           1. services/orders  core  x\n           2  web-portal  web\nTRACKING x\n"
        self.assertEqual(story_status.parts(plan), [(1, "services/orders"), (2, "web-portal")])

    def test_a_parts_row_that_cannot_be_read_is_reported(self):
        plan = PLAN.replace("TRACKING", "           three  billing  core  x\nTRACKING")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            (root / "stories" / "SHIP-1" / "coordination-plan.md").write_text(plan, encoding="utf-8")
            problems = story_status.story_problems(root, "SHIP-1")
        self.assertTrue(any(p.startswith("PARTS row not understood") for p in problems), problems)

    def test_a_plan_with_no_parts_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            (root / "stories" / "SHIP-1" / "coordination-plan.md").write_text("PARTS  #  Repository\n", encoding="utf-8")
            self.assertIn("no parts found in the coordination plan", story_status.story_problems(root, "SHIP-1"))

    def test_dotted_versions_are_compared(self):
        rows, _ = self.problems_for(lambda r: (story(r, current="spec v1 · contract tracking-api v2.1.0"),
                                               part(r, "shipments-api", pins="spec v1 · plan v1 · contract tracking-api v2.0.3"),
                                               part(r, "web-portal", pins="spec v1 · plan v1 · contract tracking-api v2.1.0")))
        by = {r.repository: r for r in rows}
        self.assertIn("re-plan: contract tracking-api v2.0.3 < v2.1.0", by["shipments-api"].needs)
        self.assertEqual(by["web-portal"].needs, [])

    def test_a_version_item_that_cannot_be_read_is_reported(self):
        rows, _ = self.problems_for(lambda r: (story(r), part(r, "shipments-api", pins="spec v1 · contract tracking-api vNext"),
                                               part(r, "web-portal")))
        self.assertIn("PINS item not understood: contract tracking-api vNext",
                      {r.repository: r for r in rows}["shipments-api"].needs)

    def test_stage_names_in_backticks_or_capitals_are_read(self):
        def build(r):
            story(r)
            part(r, "web-portal")
            d = r / "shipments-api" / "plans" / "SHIP-1"
            d.mkdir(parents=True)
            rows = "\n".join(f"| `{s.upper() if s == 'merged' else s}` | x | done |" for s in story_status.STAGES)
            (d / "README.md").write_text(f"PINS       {PINS}\n{rows}\n", encoding="utf-8")
        rows, _ = self.problems_for(build)
        self.assertEqual({r.repository: r for r in rows}["shipments-api"].reached, "merged")

    def test_an_index_with_no_stage_rows_is_reported(self):
        def build(r):
            story(r)
            part(r, "web-portal")
            d = r / "shipments-api" / "plans" / "SHIP-1"
            d.mkdir(parents=True)
            (d / "README.md").write_text(f"PINS       {PINS}\n", encoding="utf-8")
        rows, _ = self.problems_for(build)
        self.assertIn("no stage rows recognised in the part index", {r.repository: r for r in rows}["shipments-api"].needs)

    def test_a_second_part_in_one_repository_reads_its_own_folder(self):
        plan = PLAN.replace("           2  web-portal", "           2  shipments-api")
        def build(r):
            story(r)
            (r / "stories" / "SHIP-1" / "coordination-plan.md").write_text(plan, encoding="utf-8")
            for n, done in ((1, ALL), (2, ALL[:2])):
                d = r / "shipments-api" / "plans" / "SHIP-1" / f"part-{n}"
                d.mkdir(parents=True)
                rows = "\n".join(f"| {s} | x | {'done' if s in done else 'to do'} |" for s in story_status.STAGES)
                (d / "README.md").write_text(f"PINS       {PINS}\n{rows}\n", encoding="utf-8")
        rows, _ = self.problems_for(build)
        self.assertEqual([r.reached for r in rows], ["merged", "aidlc-build"])

    def test_a_byte_order_mark_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            index = root / "stories" / "SHIP-1" / "README.md"
            index.write_bytes(b"\xef\xbb\xbf" + index.read_bytes().lstrip())
            self.assertEqual(story_status.story_problems(root, "SHIP-1"), [])

    def test_check_release_needs_each_repository_on_its_default_branch(self):
        import subprocess
        def git(repo, *args):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            for repo in ("shipments-api", "web-portal"):
                part(root, repo, done=ALL)
                git(root / repo, "init", "-q", "-b", "main")
                git(root / repo, "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-q", "--allow-empty", "-m", "x")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(story_status.main(["SHIP-1", "--root", tmp, "--check-release"]), 0)
            git(root / "web-portal", "checkout", "-q", "-b", "feat/SHIP-1-2-r2")
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(story_status.main(["SHIP-1", "--root", tmp, "--check-release"]), 1)
            self.assertIn("web-portal: on branch feat/SHIP-1-2-r2, not its default branch main", out.getvalue())

    def test_check_release_refuses_a_folder_that_is_not_a_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", done=ALL)
            part(root, "web-portal", done=ALL)
            out = io.StringIO()
            with redirect_stdout(out):
                self.assertEqual(story_status.main(["SHIP-1", "--root", tmp, "--check-release"]), 1)
            self.assertIn("shipments-api: not a git repository", out.getvalue())


if __name__ == "__main__":
    unittest.main()
