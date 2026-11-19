"""Tests for starter/repo/scripts/check_slice.py: each builds a small repository whose main holds the approved bundle."""
import datetime as dt
import io
import json
import subprocess
import sys
import tempfile
import unittest
import weakref
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_slice  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "core.hooksPath=/dev/null",
       "-c", "commit.gpgsign=false"]
TODAY = dt.date(2026, 11, 19)
APP = "def total(a, b):\n    return a + b\n"
BASE_TEST = "from src.app import total\n\n\ndef test_total():\n    assert total(1, 2) == 3\n"


def bundle(tier="1", may="src/**, tests/**", must_not="AGENTS.md, api/**", amended="none"):
    return ("```text\nTASK BUNDLE · SHIP-7 · 1\n"
            f"TIER        {tier} (the plan's rating)\nMODE        hands-on   (approved)\n"
            f"MAY CHANGE  {may}\n            (a note on its own line)\n"
            f"MUST NOT    {must_not}, existing assertions\n"
            f"AMENDED ASSERTIONS  {amended}\nDONE WHEN   tests green\n```\n")


class Repo:
    """main holds the approved bundle, src/app.py and tests/test_app.py; work happens on feat/SHIP-7-x."""

    def __init__(self, bundle_text=None, extra=None):
        self.tmp = tempfile.TemporaryDirectory()
        weakref.finalize(self, self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        files = {"src/app.py": APP, "tests/test_app.py": BASE_TEST, "AGENTS.md": "# rules\n"}
        if bundle_text is not None:
            files["plans/SHIP-7/bundle-1.md"] = bundle_text
        files.update(extra or {})
        self.write(files)
        self.git("init", "-q", "-b", "main")
        self.commit("base")
        self.git("switch", "-q", "-c", "feat/SHIP-7-x")

    def git(self, *args):
        return subprocess.run(GIT + list(args), cwd=self.root, check=True, capture_output=True, text=True).stdout

    def write(self, files):
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def commit(self, message, files=None):
        if files:
            self.write(files)
        self.git("add", "-A")
        self.git("commit", "-q", "--allow-empty", "-m", message)

    def check(self, part=None):
        return check_slice.check(self.root, "main", "SHIP-7", part, today=TODAY)


class ParseTest(unittest.TestCase):
    def test_fields_join_continuation_lines(self):
        text = "MAY CHANGE  src/**,\n            tests/**\n            (slice 2 adds docs)\nMUST NOT    AGENTS.md\n"
        found = check_slice.fields(text)
        self.assertEqual(check_slice.path_tokens(found["MAY CHANGE"]), ["src/**", "tests/**"])
        self.assertEqual(check_slice.path_tokens(found["MUST NOT"]), ["AGENTS.md"])

    def test_path_tokens_drop_prose_and_anchor_at_the_root(self):
        self.assertEqual(check_slice.path_tokens("`/api/**`, ./web/x.ts, plans/<KEY>/**, existing assertions; none"),
                         ["api/**", "web/x.ts"])

    def test_globs_follow_path_segments(self):
        m = check_slice.matches
        self.assertTrue(m("src/a/b.py", ["src/**"]))
        self.assertFalse(m("srcx/a.py", ["src/**"]))
        self.assertTrue(m("src/b.py", ["src/*.py"]))
        self.assertFalse(m("src/a/b.py", ["src/*.py"]))
        self.assertTrue(m("x.md", ["**/x.md"]))
        self.assertTrue(m("docs/x.md", ["**/x.md"]))
        self.assertTrue(m("web/page.ts", ["web/"]))
        self.assertTrue(m(".github/workflows/ci.yml", [".github/workflows/ci.yml"]))

    def test_the_key_comes_from_the_branch(self):
        k = check_slice.key_from_branch
        self.assertEqual(k("feat/SHIP-12-api"), "SHIP-12")
        self.assertEqual(k("fix/PAY-7"), "PAY-7")
        self.assertIsNone(k("main"))
        self.assertIsNone(k("docs/plan-20-gates-that-hold"))

    def test_a_bundle_reads_its_tier_and_lists(self):
        b = check_slice.parse_bundle("bundle-1.md", bundle(tier="2"))
        self.assertEqual((b.tier, b.may_change, b.must_not, b.amended), (2, ["src/**", "tests/**"], ["AGENTS.md", "api/**"], ""))


class ScopeTest(unittest.TestCase):
    def test_a_change_inside_may_change_is_clean(self):
        r = Repo(bundle())
        r.commit("s1", {"src/app.py": "def total(a, b):\n    return b + a\n"})
        self.assertEqual(r.check(), ([], []))

    def test_a_path_outside_may_change_is_a_problem(self):
        r = Repo(bundle())
        r.commit("s1", {"web/page.ts": "export {}\n"})
        self.assertEqual(r.check()[0], ["web/page.ts: outside every bundle's MAY CHANGE"])

    def test_a_must_not_path_is_a_problem_even_inside_may_change(self):
        r = Repo(bundle(may="**", must_not="AGENTS.md"))
        r.commit("s1", {"AGENTS.md": "# looser rules\n"})
        self.assertEqual(r.check()[0], ["AGENTS.md: changed, but a bundle's MUST NOT names it"])

    def test_the_story_folder_is_exempt(self):
        r = Repo(bundle())
        r.commit("note", {"src/app.py": "x = 1\n", "plans/SHIP-7/progress-1.md": "STATUS      doing\n"})
        self.assertEqual(r.check(), ([], []))

    def test_code_with_a_plan_note_is_not_documents_only(self):
        r = Repo(bundle())
        r.commit("mixed", {"web/page.ts": "export {}\n", "plans/SHIP-7/progress-1.md": "STATUS      doing\n"})
        self.assertEqual(r.check()[0], ["web/page.ts: outside every bundle's MAY CHANGE"])

    def test_no_bundle_is_a_problem(self):
        r = Repo(None)
        r.commit("s1", {"src/app.py": "x = 1\n"})
        self.assertEqual(r.check()[0], ["plans/SHIP-7: no bundle or brief found; "
                                        "there is nothing approved to check this branch against"])

    def test_a_documents_only_branch_needs_no_bundle(self):
        r = Repo(None)
        r.commit("spec", {"plans/SHIP-7/spec.md": "# Spec\n"})
        self.assertEqual(r.check(), ([], []))

    def test_long_field_names_take_one_space(self):
        found = check_slice.fields("LIKELY AREA src/a.py:4 FACT\nDEPENDENCIES none new\nDONE WHEN   green\n")
        self.assertEqual(found, {"LIKELY AREA": "src/a.py:4 FACT", "DEPENDENCIES": "none new", "DONE WHEN": "green"})

    def test_a_part_reads_its_own_folder(self):
        r = Repo(None, {"plans/SHIP-7/part-2/bundle-1.md": bundle(may="web/**")})
        r.commit("s1", {"web/page.ts": "export {}\n"})
        self.assertEqual(r.check(part=2), ([], []))

    def test_a_manifest_needs_its_name_in_may_change(self):
        r = Repo(bundle(may="**"))
        r.commit("dep", {"package.json": '{"dependencies": {"left-pad": "1.3.0"}}\n'})
        problems = r.check()[0]
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("package.json: a dependency manifest changed"), problems)

    def test_a_manifest_named_in_may_change_is_allowed(self):
        r = Repo(bundle(may="src/**, package.json"))
        r.commit("dep", {"package.json": "{}\n"})
        self.assertEqual(r.check(), ([], []))

    def test_merging_main_into_the_branch_adds_no_problems(self):
        r = Repo(bundle())
        r.commit("s1", {"src/app.py": "x = 1\n"})
        r.git("switch", "-q", "main")
        r.commit("other work", {"web/other.ts": "export {}\n"})
        r.git("switch", "-q", "feat/SHIP-7-x")
        r.git("merge", "-q", "--no-edit", "main")
        self.assertEqual(r.check(), ([], []))

    def test_a_non_ascii_path_in_must_not_is_reported(self):
        r = Repo(bundle(may="**"))
        r.commit("s1", {"api/caf\u00e9.py": "x = 1\n"})
        self.assertEqual(r.check()[0], ["api/caf\u00e9.py: changed, but a bundle's MUST NOT names it"])

    def test_a_path_with_a_tab_outside_may_change_is_reported(self):
        r = Repo(bundle())
        r.commit("s1", {"web/a\tb.ts": "export {}\n"})
        self.assertEqual(r.check()[0], ["web/a\tb.ts: outside every bundle's MAY CHANGE"])


class ApprovedCopyTest(unittest.TestCase):
    def test_a_tier_2_bundle_on_main_wins_over_the_branch_copy(self):
        r = Repo(bundle(tier="2"))
        r.commit("widen", {"plans/SHIP-7/bundle-1.md": bundle(tier="2", may="src/**, tests/**, web/**"),
                           "web/page.ts": "export {}\n"})
        self.assertEqual(r.check()[0], ["web/page.ts: outside every bundle's MAY CHANGE"])

    def test_a_tier_1_bundle_travels_with_the_branch(self):
        r = Repo(bundle(tier="1"))
        r.commit("widen", {"plans/SHIP-7/bundle-1.md": bundle(tier="1", may="src/**, web/**"),
                           "web/page.ts": "export {}\n"})
        self.assertEqual(r.check(), ([], []))

    def test_a_bundle_added_only_on_the_branch_is_used(self):
        r = Repo(None)
        r.commit("add", {"plans/SHIP-7/bundle-1.md": bundle(may="web/**"), "web/page.ts": "export {}\n",
                         "src/app.py": "x = 1\n"})
        self.assertEqual(r.check()[0], ["src/app.py: outside every bundle's MAY CHANGE"])

    def test_a_bundle_deleted_on_the_branch_falls_back_to_main(self):
        r = Repo(bundle())
        (r.root / "plans/SHIP-7/bundle-1.md").unlink()
        r.commit("drop", {"web/page.ts": "export {}\n"})
        self.assertEqual(r.check()[0], ["web/page.ts: outside every bundle's MAY CHANGE"])

    def test_a_tier_line_with_a_reason_reads_as_its_number(self):
        self.assertEqual(check_slice.tier_of("TIER        2 (touches payments)\n"), 2)

    def test_path_tokens_keep_bare_file_names(self):
        self.assertEqual(check_slice.path_tokens("Gemfile, Dockerfile, e.g. src/**, existing assertions"),
                         ["Gemfile", "Dockerfile", "src/**"])


if __name__ == "__main__":
    unittest.main()
