"""Tests for starter/workspace/scripts/story_status.py: each builds a small workspace in a temporary folder."""
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock
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

    # Plan 19: filled documents may fence their FIELD lines and write placeholders as {{...}}
    def test_parts_inside_a_fence_are_read(self):
        plan = ("# Coordination plan · SHIP-1 · x · v1\n\n```text\n"
                "OUTCOME    something. Tier 2\n"
                "PARTS      #  Repository     Owner    Change\n"
                "           1  shipments-api  core     add the field\n"
                "           2  web-portal     web      show the field\n"
                "```\n")  # the closing fence falls inside the PARTS block
        parts, unread = story_status.read_parts(plan)
        self.assertEqual(parts, [(1, "shipments-api"), (2, "web-portal")])
        self.assertEqual(unread, [])

    def test_a_note_after_a_fenced_parts_block_is_not_a_part(self):
        plan = ("```text\nPARTS      #  Repository     Owner\n           1  shipments-api  core\n```\n\n"
                "Approved by Bo on the work item.\n")
        parts, unread = story_status.read_parts(plan)
        self.assertEqual((parts, unread), ([(1, "shipments-api")], []))

    def test_curly_placeholders_are_not_versions(self):
        self.assertEqual(story_status.items("spec v{{n}}"), [])


# Plan 21: pins name the home commit, and each part keeps a read-only copy of its criteria (ADR 0022)

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null"]
SPEC = ("# SHIP-1 · Track shipments · specification\n\nVersion: v1\n\n## Scope and non-goals\n"
        "Non-goals: carrier rates\n\n## Acceptance criteria\nAC1 the API returns the shipment's status\n"
        "    Given a shipment in transit\n    When its status is asked for\n    Then 200 with \"in transit\"\n")
COPIED = ("AC1 the API returns the shipment's status", "Given a shipment in transit",
          "When its status is asked for", 'Then 200 with "in transit"')
SPEC2 = SPEC + ("AC2 the portal shows it\n    Given a shipment\n    Then the portal lists it\n"
                "AC3 an unknown id is a 404\n    When the id is unknown\n    Then 404\n")


def run_git(folder: Path, *args: str) -> str:
    return subprocess.run(GIT + ["-C", str(folder), *args], check=True, capture_output=True, text=True).stdout.strip()


def criteria(root: Path, repo: str, commit: str, lines=COPIED, source: bool = True) -> None:
    head = f"```text\nSOURCE     home stories/SHIP-1/spec.md @ {commit} (spec v1)\n```\n\n" if source else ""
    text = f"# SHIP-1 · part · acceptance criteria (read-only copy)\n\n{head}## Acceptance criteria\n" + "\n".join(lines)
    (root / repo / "plans" / "SHIP-1" / "criteria.md").write_text(text + "\n", encoding="utf-8")


class Home:
    """A workspace root that is itself a git repository (the home repository): SHIP-1's documents on main."""

    def __init__(self, root: Path, current: str = "spec v1 · contract tracking-api v1", extra: str = ""):
        self.root = root
        story(root, current=current, extra=extra)
        (root / "stories" / "SHIP-1" / "spec.md").write_text(SPEC, encoding="utf-8")
        run_git(root, "init", "-q", "-b", "main")
        self.first = self.commit("spec v1")

    def commit(self, message: str, files: dict[str, str] | None = None) -> str:
        for rel, text in (files or {}).items():
            (self.root / rel).write_text(text, encoding="utf-8")
        run_git(self.root, "add", "stories")
        run_git(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return run_git(self.root, "rev-parse", "HEAD")

    def status(self) -> dict:
        return {r.repository: r for r in story_status.story_status(self.root, "SHIP-1")}


class HomeCommitTest(unittest.TestCase):
    """F4: a part pins the spec by version and by the home commit; the drift check reads the home repository."""

    def home(self, **kwargs) -> Home:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Home(Path(tmp.name), **kwargs)

    def pinned(self, home: Home, commit: str, with_criteria: bool = True) -> None:
        part(home.root, "shipments-api", pins=f"spec v1 @ {commit} · plan v1 · contract tracking-api v1")
        part(home.root, "web-portal", pins=f"spec v1 @ {commit} · plan v1 · contract tracking-api v1")
        if with_criteria:
            criteria(home.root, "shipments-api", commit)
            criteria(home.root, "web-portal", commit)

    def test_a_pin_with_a_commit_is_parsed(self):
        text = "spec v2 @ 1A2B3C4 · plan v1 · contract tracking-api v2.1.0"
        self.assertEqual(story_status.parse_versions(text), {"spec": 2, "plan": 1, "contract tracking-api": (2, 1, 0)})
        self.assertEqual(story_status.parse_commits(text), {"spec": "1a2b3c4"})
        self.assertEqual(story_status.unread_items(text), [])

    def test_without_a_home_repository_a_commit_pin_adds_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story(root)
            part(root, "shipments-api", pins="spec v1 @ 1a2b3c4 · plan v1 · contract tracking-api v1")
            part(root, "web-portal")
            rows = {r.repository: r for r in story_status.story_status(root, "SHIP-1")}
        self.assertEqual(rows["shipments-api"].needs, [])

    def test_a_pin_at_the_current_home_commit_is_clean(self):
        home = self.home()
        self.pinned(home, home.first)
        self.assertEqual(home.status()["shipments-api"].needs, [])

    def test_a_pin_without_a_home_commit_is_reported(self):
        home = self.home()
        self.pinned(home, home.first)
        part_dir = home.root / "web-portal" / "plans" / "SHIP-1"
        (part_dir / "README.md").write_text((part_dir / "README.md").read_text(encoding="utf-8").replace(
            f" @ {home.first}", ""), encoding="utf-8")
        self.assertIn("the spec pin names no home commit (spec v<n> @ <commit>)", home.status()["web-portal"].needs)

    def test_a_spec_changed_since_the_pin_needs_a_re_plan(self):
        home = self.home()
        self.pinned(home, home.first)
        home.commit("edit the spec in place", {"stories/SHIP-1/spec.md": SPEC + "AC2 the portal shows it\n"})
        self.assertIn(f"re-plan: stories/SHIP-1/spec.md changed on main since {home.first[:7]}",
                      home.status()["shipments-api"].needs)

    def test_a_raised_version_is_one_re_plan_not_two(self):
        home = self.home(current="spec v2 · contract tracking-api v1")
        self.pinned(home, home.first)
        home.commit("spec v2", {"stories/SHIP-1/spec.md": SPEC.replace("v1", "v2") + "AC2 the portal shows it\n"})
        needs = home.status()["shipments-api"].needs
        self.assertIn("re-plan: spec v1 < v2", needs)
        self.assertFalse(any("changed on main" in n for n in needs), needs)

    def test_an_unaffected_record_clears_the_commit_re_plan(self):
        extra = "UNAFFECTED shipments-api spec v1: only the portal changes, Ana (tech lead), 2026-11-20"
        home = self.home(extra=extra)
        self.pinned(home, home.first)
        home.commit("edit the spec in place", {"stories/SHIP-1/spec.md": SPEC + "AC2 the portal shows it\n"})
        self.assertFalse(any("changed on main" in n for n in home.status()["shipments-api"].needs))

    def test_a_pin_off_the_default_branch_is_reported(self):
        home = self.home()
        run_git(home.root, "switch", "-q", "-c", "draft")
        draft = home.commit("an unapproved spec", {"stories/SHIP-1/spec.md": SPEC + "AC2 draft\n"})
        run_git(home.root, "switch", "-q", "main")
        self.pinned(home, draft, with_criteria=False)
        criteria(home.root, "shipments-api", draft)
        self.assertIn(f"pinned home commit {draft[:7]} is not on the home repository's main",
                      home.status()["shipments-api"].needs)

    def test_an_unknown_home_commit_is_reported(self):
        home = self.home()
        self.pinned(home, "deadbee")
        self.assertEqual(home.status()["shipments-api"].needs,
                         ["pinned home commit deadbee not found: run git fetch in the home repository"])


class CriteriaCopyTest(unittest.TestCase):
    """F5: each part's read-only copy of its criteria matches the home spec at the commit it names."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Home(Path(tmp.name))
        pins = f"spec v1 @ {self.home.first} · plan v1 · contract tracking-api v1"
        part(self.home.root, "shipments-api", pins=pins)
        part(self.home.root, "web-portal", pins=pins)
        criteria(self.home.root, "web-portal", self.home.first)

    def needs(self) -> list[str]:
        return self.home.status()["shipments-api"].needs

    def test_a_missing_copy_is_reported(self):
        self.assertEqual(self.needs(), ["no criteria.md beside the part index (the part's read-only copy of its "
                                        "criteria, ADR 0022)"])

    def test_an_edited_copy_is_reported(self):
        criteria(self.home.root, "shipments-api", self.home.first,
                 lines=("AC1 the API returns the shipment's status within 1 second",))
        self.assertEqual(self.needs(), [f"criteria.md differs from stories/SHIP-1/spec.md at {self.home.first[:7]}: "
                                        "AC1 the API returns the shipment's status within 1 second"])

    def test_a_copy_of_another_commit_is_reported(self):
        later = self.home.commit("the index moves on", {"stories/SHIP-1/coordination-plan.md": PLAN + "\n"})
        part_dir = self.home.root / "shipments-api" / "plans" / "SHIP-1"
        (part_dir / "README.md").write_text((part_dir / "README.md").read_text(encoding="utf-8").replace(
            f"spec v1 @ {self.home.first}", f"spec v1 @ {later}"), encoding="utf-8")
        criteria(self.home.root, "shipments-api", self.home.first)
        self.assertEqual(self.needs(), [f"criteria.md copies {self.home.first[:7]}, but the spec pin names {later[:7]}"])

    def test_a_copy_without_a_source_line_is_reported(self):
        criteria(self.home.root, "shipments-api", self.home.first, source=False)
        self.assertEqual(self.needs(), ["criteria.md has no SOURCE line naming the home repository, the spec's path "
                                        "and its commit"])

    def test_only_the_copied_lines_are_compared(self):
        text = ("# x\n```text\nSOURCE     home stories/SHIP-1/spec.md @ abc1234\n```\n## Acceptance criteria\n"
                "AC1  a   b\n\n```text\n## Non-goals\nNon-goals: {{x}}\nNon-goals: rates\n")
        self.assertEqual(story_status.copied_lines(text), ["AC1 a b", "Non-goals: rates"])


class CriteriaBlockTest(unittest.TestCase):
    """The copy is compared by criterion ID: each block equals the spec's block, in the spec's order."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Home(Path(tmp.name))
        self.home.commit("three criteria", {"stories/SHIP-1/spec.md": SPEC2})
        self.at = run_git(self.home.root, "rev-parse", "HEAD")
        pins = f"spec v1 @ {self.at} · plan v1 · contract tracking-api v1"
        part(self.home.root, "shipments-api", pins=pins)
        part(self.home.root, "web-portal", pins=pins)
        criteria(self.home.root, "web-portal", self.at, lines=COPIED)

    def needs(self, lines) -> list[str]:
        criteria(self.home.root, "shipments-api", self.at, lines=lines)
        return self.home.status()["shipments-api"].needs

    def test_a_dropped_then_line_is_reported(self):
        self.assertTrue(self.needs(COPIED[:3]))

    def test_reordered_lines_in_a_block_are_reported(self):
        self.assertTrue(self.needs((COPIED[0], COPIED[2], COPIED[1], COPIED[3])))

    def test_a_then_moved_under_another_criterion_is_reported(self):
        self.assertTrue(self.needs(COPIED[:3] + ("AC3 an unknown id is a 404", 'Then 200 with "in transit"',
                                                 "When the id is unknown", "Then 404")))

    def test_an_empty_copy_is_reported(self):
        self.assertEqual(self.needs(()), ["plans/SHIP-1/criteria.md holds no criteria"])

    def test_a_correct_subset_in_order_is_clean(self):
        self.assertEqual(self.needs(COPIED + ("AC3 an unknown id is a 404", "When the id is unknown", "Then 404")), [])

    def test_ids_out_of_order_are_reported(self):
        out = self.needs(("AC3 an unknown id is a 404", "When the id is unknown", "Then 404") + COPIED)
        self.assertTrue(any("order" in n for n in out), out)

    def test_a_source_naming_another_story_is_reported(self):
        criteria(self.home.root, "shipments-api", self.at)
        path = self.home.root / "shipments-api" / "plans" / "SHIP-1" / "criteria.md"
        path.write_text(path.read_text(encoding="utf-8").replace("stories/SHIP-1/", "stories/SHIP-2/"), encoding="utf-8")
        self.assertEqual(self.home.status()["shipments-api"].needs,
                         ["criteria.md SOURCE names stories/SHIP-2/spec.md, not stories/SHIP-1/spec.md"])


class DriftCouldNotRunTest(unittest.TestCase):
    """When the home repository cannot be read, the release check says so instead of reading as ready."""

    def release(self, root: Path) -> str:
        out = io.StringIO()
        with redirect_stdout(out):
            story_status.main(["SHIP-1", "--root", str(root), "--check-release"])
        return out.getvalue()

    def test_release_warns_when_the_root_is_not_a_git_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            story(Path(tmp))
            part(Path(tmp), "shipments-api")
            part(Path(tmp), "web-portal")
            self.assertIn("Warning: the workspace root is not a git repository, so pins and criteria copies were "
                          "not checked", self.release(Path(tmp)))

    def test_a_missing_git_binary_reads_as_not_a_git_repository(self):
        import os
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as empty:
            story(Path(tmp))
            part(Path(tmp), "shipments-api")
            part(Path(tmp), "web-portal")
            old = os.environ["PATH"]
            os.environ["PATH"] = empty
            try:
                self.assertFalse(story_status.own_repository(Path(tmp)))
                self.assertEqual(story_status.story_status(Path(tmp), "SHIP-1")[0].needs, [])
                self.assertIn("Warning: the workspace root is not a git repository", self.release(Path(tmp)))
            finally:
                os.environ["PATH"] = old


class MergeStateTest(unittest.TestCase):
    """F6: a part's merge state comes from GitHub when it can say, else from git; a hand-marked row that disagrees
    is reported."""

    PRS = [{"number": 4, "title": "[SHIP-1] part 1 of 2: add tracking endpoint", "state": "MERGED"},
           {"number": 7, "title": "[SHIP-1] part 1 of 2, plan v2: re-plan", "state": "MERGED"},
           {"number": 9, "title": "[SHIP-1] part 1 of 2, revision 2: rename the field", "state": "OPEN"},
           {"number": 10, "title": "[SHIP-1] part 1 of 2, revision 2: abandoned", "state": "CLOSED"},
           {"number": 12, "title": "[SHIP-12] part 1 of 1: another story", "state": "MERGED"}]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        story(self.root)
        part(self.root, "web-portal")
        self.repo = self.root / "shipments-api"
        self.index = self.repo / "plans" / "SHIP-1" / "README.md"

    def commit_index(self, done, branch=None):
        if not (self.repo / ".git").exists():
            part(self.root, "shipments-api", done=done)
            run_git(self.repo, "init", "-q", "-b", "main")
        else:
            if branch:
                run_git(self.repo, "switch", "-q", "-c", branch)
            rows = "\n".join(f"| {s} | shipments-api | {'done' if s in done else 'to do'} |" for s in ALL)
            self.index.write_text(f"PINS       {PINS}\n\n| Stage | Runs in | Status |\n|---|---|---|\n{rows}\n",
                                  encoding="utf-8")
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", "index")

    def status(self, use_github=True):
        return {r.repository: r for r in story_status.story_status(self.root, "SHIP-1", use_github)}["shipments-api"]

    def test_the_default_branchs_index_is_the_git_merge_state(self):
        self.commit_index(ALL)
        row = self.status()
        self.assertEqual((row.merge, row.needs), ("merged (git)", []))

    def test_a_merged_row_marked_on_a_branch_is_reported(self):
        self.commit_index(ALL[:4])
        self.commit_index(ALL, branch="feat/SHIP-1-1")
        row = self.status()
        self.assertEqual(row.merge, "not merged (git)")
        self.assertIn("the merged row is done, but git says not merged", row.needs)

    def test_a_checkout_behind_the_merge_is_reported(self):
        self.commit_index(ALL[:4])
        run_git(self.repo, "branch", "old")
        self.commit_index(ALL)
        run_git(self.repo, "switch", "-q", "old")
        self.assertIn("git says merged, but this checkout's merged row is not done (git pull the default branch)",
                      self.status().needs)

    def test_a_folder_with_no_committed_index_adds_nothing(self):
        part(self.root, "shipments-api", done=ALL)
        run_git(self.repo, "init", "-q", "-b", "main")
        run_git(self.repo, "commit", "-q", "--allow-empty", "-m", "x")
        row = self.status()
        self.assertEqual((row.merge, row.needs), ("-", []))

    def test_github_says_first_from_the_newest_code_pull_request(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        calls = []

        def gh(folder, args):
            calls.append(args)
            return json.dumps(self.PRS)

        with mock.patch.object(story_status, "run_gh", gh):
            row = self.status()
        self.assertEqual(row.merge, "not merged (GitHub #9)")
        self.assertIn("the merged row is done, but GitHub #9 says not merged", row.needs)
        self.assertIn("SHIP-1 in:title", calls[0])

    def test_no_github_reads_only_git(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        with mock.patch.object(story_status, "run_gh", side_effect=AssertionError("gh was called")):
            self.assertEqual(self.status(use_github=False).merge, "merged (git)")

    def test_a_remote_that_is_not_github_never_calls_gh(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://gitlab.example.com/acme/shipments-api.git")
        with mock.patch.object(story_status, "run_gh", side_effect=AssertionError("gh was called")):
            self.assertEqual(self.status().merge, "merged (git)")

    def test_gh_output_that_is_not_a_list_falls_back_to_git(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        with mock.patch.object(story_status, "run_gh", lambda folder, args: "null"):
            self.assertEqual(self.status().merge, "merged (git)")

    def test_a_matching_pull_request_with_a_bad_number_falls_back_to_git(self):
        self.commit_index(ALL)
        run_git(self.repo, "remote", "add", "origin", "https://github.com/acme/shipments-api.git")
        for number in ("x", None):
            prs = [{"number": number, "title": "[SHIP-1] part 1 of 2: add", "state": "OPEN"}]
            with mock.patch.object(story_status, "run_gh", lambda folder, args: json.dumps(prs)):
                self.assertEqual(self.status().merge, "merged (git)")

    def test_run_gh_never_waits_for_input(self):
        done = subprocess.CompletedProcess([], 0, stdout="[]")
        with mock.patch.object(story_status.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(story_status.subprocess, "run", return_value=done) as run:
            self.assertEqual(story_status.run_gh(self.root, ["pr", "list"]), "[]")
        self.assertEqual(run.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(run.call_args.kwargs["env"]["GH_PROMPT_DISABLED"], "1")

    def test_run_gh_treats_undecodable_output_as_a_failed_call(self):
        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")
        with mock.patch.object(story_status.shutil, "which", return_value="/usr/bin/gh"), \
                mock.patch.object(story_status.subprocess, "run", side_effect=error):
            self.assertIsNone(story_status.run_gh(self.root, ["pr", "list"]))

    def test_the_status_file_has_the_merge_state_column(self):
        self.commit_index(ALL)
        with redirect_stdout(io.StringIO()):
            story_status.main(["SHIP-1", "--root", str(self.root), "--write", "--no-github"])
        status = (self.root / "stories" / "SHIP-1" / "status.md").read_text(encoding="utf-8")
        self.assertIn("| Part | Repository | Reached | Pins | Needs | Merge state |", status)
        self.assertIn("| merged (git) |", status)


if __name__ == "__main__":
    unittest.main()
