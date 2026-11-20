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
        self.assertEqual(r.check()[0], [
            "web/page.ts: outside every bundle's MAY CHANGE",
            "plans/SHIP-7/bundle-1.md: a Tier 2 plan or bundle is changed in a code pull request; "
            "it merges first in its own pull request, approved by the tech lead (ADR 0020)"])

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


class TestIntegrityTest(unittest.TestCase):
    def test_a_changed_assertion_is_a_problem(self):
        r = Repo(bundle())
        r.commit("loosen", {"tests/test_app.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests/test_app.py: assert total(1, 2) == 3"])

    def test_a_deleted_test_file_is_a_problem(self):
        r = Repo(bundle())
        r.git("rm", "-q", "tests/test_app.py")
        r.commit("drop")
        problems = r.check()[0]
        self.assertTrue(any("def test_total" in p for p in problems), problems)

    def test_a_renamed_test_file_is_not_a_problem(self):
        r = Repo(bundle())
        r.git("mv", "tests/test_app.py", "tests/test_total.py")
        r.commit("rename")
        self.assertEqual(r.check(), ([], []))

    def test_an_assertion_added_on_the_branch_may_change(self):
        r = Repo(bundle())
        r.commit("add", {"tests/test_app.py": BASE_TEST + "\n\ndef test_zero():\n    assert total(0, 0) == 1\n"})
        r.commit("fix", {"tests/test_app.py": BASE_TEST + "\n\ndef test_zero():\n    assert total(0, 0) == 0\n"})
        self.assertEqual(r.check(), ([], []))

    def test_a_recipe_commit_may_change_test_syntax(self):
        r = Repo(bundle().replace("MAY CHANGE", "RECIPE      pyupgrade@3.19.0 \u2014 pyupgrade --py312-plus \u2014 tests/**\nMAY CHANGE", 1))
        r.commit("mechanical\n\nRecipe: pyupgrade@3.19.0",
                 {"tests/test_app.py": BASE_TEST.replace("assert total(1, 2) == 3", "assert (total(1, 2) == 3)")})
        self.assertEqual(r.check(), ([], []))

    def test_an_amended_assertion_is_a_note_not_a_problem(self):
        r = Repo(bundle(amended="tests/test_app.py::test_total: checks 4, spec v2, AC1, decided by Bo"))
        r.commit("amend", {"tests/test_app.py": BASE_TEST.replace("== 3", "== 4")})
        problems, notes = r.check()
        self.assertEqual(problems, [])
        self.assertEqual(len(notes), 1)
        self.assertIn("tests/test_app.py", notes[0])

    def test_a_non_ascii_test_file_name_is_still_checked(self):
        r = Repo(bundle(), {"tests/test_caf\u00e9.py": BASE_TEST})
        r.commit("loosen", {"tests/test_caf\u00e9.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests/test_caf\u00e9.py: assert total(1, 2) == 3"])

    def test_unquote_decodes_c_escapes(self):
        self.assertEqual(check_slice.unquote('"a/tests/t\\tab.py"'), "a/tests/t\tab.py")
        self.assertEqual(check_slice.unquote('"a/caf\\303\\251.py"'), "a/caf\u00e9.py")
        self.assertEqual(check_slice.unquote('"a/q\\"x\\\\y"'), 'a/q"x\\y')
        self.assertEqual(check_slice.unquote("a/plain.py"), "a/plain.py")

    def test_a_path_with_a_space_is_still_checked(self):
        r = Repo(bundle(may="**"), {"tests dir/test_x.py": BASE_TEST})
        r.commit("loosen", {"tests dir/test_x.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests dir/test_x.py: assert total(1, 2) == 3"])

    def test_the_same_line_added_in_another_file_earlier_does_not_cover_a_weakened_assertion(self):
        r = Repo(bundle())
        r.commit("new", {"tests/test_new.py": "def test_new():\n    assert total(1, 2) == 3\n"})
        r.commit("weaken", {"tests/test_app.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests/test_app.py: assert total(1, 2) == 3"])

    def test_a_line_added_earlier_in_the_same_file_covers_one_removal_only(self):
        r = Repo(bundle())
        r.commit("dup", {"tests/test_app.py": BASE_TEST + "\n\ndef test_again():\n    assert total(1, 2) == 3\n"})
        r.commit("weaken both", {"tests/test_app.py": (BASE_TEST + "\n\ndef test_again():\n"
                                                        "    assert total(1, 2) == 3\n").replace("== 3", "> 0")})
        self.assertEqual(len(r.check()[0]), 1)

    def test_an_amended_entry_for_one_file_does_not_waive_another(self):
        r = Repo(bundle(amended="tests/a.py::test_a: checks 4, spec v2, AC1, decided by Bo"),
                 {"tests/data.py": BASE_TEST})
        r.commit("loosen", {"tests/data.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests/data.py: assert total(1, 2) == 3"])

    def test_an_amended_entry_waives_only_its_own_path_exactly(self):
        r = Repo(bundle(amended="tests/data.py::test_a: checks 4, spec v2, AC1, decided by Bo"),
                 {"tests/data.py": BASE_TEST})
        r.commit("amend", {"tests/data.py": BASE_TEST.replace("== 3", "== 4")})
        problems, notes = r.check()
        self.assertEqual((problems, len(notes)), ([], 1))


class MarkerTest(unittest.TestCase):
    def test_a_skip_without_an_exception_is_a_problem(self):
        r = Repo(bundle())
        r.commit("skip", {"tests/test_app.py": BASE_TEST.replace("def test_total", "@unittest.skip('flaky')\ndef test_total")})
        problems = r.check()[0]
        self.assertEqual(len(problems), 1)
        self.assertIn("a suppression or skip without a valid aidlc-exception", problems[0])

    def test_a_suppression_with_a_valid_exception_is_allowed(self):
        r = Repo(bundle())
        line = "import os  # noqa: F401  aidlc-exception: reason=read by plugins; owner=Bo; expires=2026-12-31\n"
        r.commit("noqa", {"src/app.py": line + APP})
        self.assertEqual(r.check(), ([], []))

    def test_the_exception_may_sit_on_the_line_above(self):
        r = Repo(bundle())
        text = "# aidlc-exception: reason=read by plugins; owner=Bo; expires=2026-12-31\nimport os  # noqa: F401\n"
        r.commit("noqa", {"src/app.py": text + APP})
        self.assertEqual(r.check(), ([], []))

    def test_an_expired_exception_is_a_problem(self):
        r = Repo(bundle())
        line = "import os  # noqa: F401  aidlc-exception: reason=old; owner=Bo; expires=2026-01-01\n"
        r.commit("noqa", {"src/app.py": line + APP})
        self.assertEqual(len(r.check()[0]), 1)

    def test_prose_is_not_checked(self):
        r = Repo(bundle(may="src/**, tests/**, docs/**"))
        r.commit("doc", {"docs/lint.md": "Use `# noqa` only with an exception.\n"})
        self.assertEqual(r.check(), ([], []))

    def test_two_skips_need_two_exceptions(self):
        r = Repo(bundle())
        text = ("# aidlc-exception: reason=flaky; owner=Bo; expires=2026-12-31\n"
                "@unittest.skip('a')\n@unittest.skip('b')\ndef test_total():\n    pass\n")
        r.commit("skips", {"tests/test_extra.py": text})
        problems = r.check()[0]
        self.assertEqual(len(problems), 1)
        self.assertIn("@unittest.skip('b')", problems[0])


class ApprovalTest(unittest.TestCase):
    ADR = "it merges first in its own pull request, approved by the tech lead (ADR 0020)"

    def test_a_tier_2_bundle_changed_with_code_is_a_problem(self):
        r = Repo(bundle(tier="2"))
        r.commit("s1", {"src/app.py": "x = 1\n",
                        "plans/SHIP-7/bundle-1.md": bundle(tier="2", may="src/**, tests/**, web/**")})
        self.assertEqual(r.check()[0], [f"plans/SHIP-7/bundle-1.md: a Tier 2 plan or bundle is changed in a code "
                                        f"pull request; {self.ADR}"])

    def test_a_tier_2_bundle_added_with_code_is_a_problem(self):
        r = Repo(None)
        r.commit("s1", {"plans/SHIP-7/bundle-1.md": bundle(tier="2"), "src/app.py": "x = 1\n"})
        self.assertEqual(r.check()[0], [f"plans/SHIP-7/bundle-1.md: a Tier 2 plan or bundle is added in a code "
                                        f"pull request; {self.ADR}"])

    def test_a_documents_only_pull_request_may_change_the_plan(self):
        r = Repo(bundle(tier="2"))
        r.commit("re-plan", {"plans/SHIP-7/bundle-1.md": bundle(tier="2", may="src/**, tests/**, web/**"),
                             "plans/SHIP-7/plan.md": "# Plan\n"})
        self.assertEqual(r.check(), ([], []))

    def test_tier_1_documents_travel_with_the_code(self):
        r = Repo(None)
        r.commit("s1", {"plans/SHIP-7/bundle-1.md": bundle(tier="1"), "src/app.py": "x = 1\n"})
        self.assertEqual(r.check(), ([], []))

    def test_scope_uses_the_approved_copy_at_tier_2(self):
        r = Repo(bundle(tier="2"))
        r.commit("s1", {"web/page.ts": "x\n",
                        "plans/SHIP-7/bundle-1.md": bundle(tier="2", may="src/**, tests/**, web/**")})
        self.assertIn("web/page.ts: outside every bundle's MAY CHANGE", r.check()[0])

    def test_a_tier_1_bundle_added_to_a_tier_2_plan_is_a_problem(self):
        r = Repo(bundle(tier="2"))
        r.commit("s1", {"src/app.py": "x = 1\n", "plans/SHIP-7/bundle-2.md": bundle(tier="1")})
        self.assertIn(f"plans/SHIP-7/bundle-2.md: a Tier 2 plan or bundle is added in a code pull request; {self.ADR}",
                      r.check()[0])

    def test_a_tier_2_bundle_removed_in_a_code_pull_request_is_a_problem(self):
        r = Repo(bundle(tier="2"))
        r.git("rm", "-q", "plans/SHIP-7/bundle-1.md")
        r.commit("drop", {"src/app.py": "x = 1\n"})
        self.assertIn(f"plans/SHIP-7/bundle-1.md: a Tier 2 plan or bundle is removed in a code pull request; {self.ADR}",
                      r.check()[0])

    def test_the_story_plan_changed_from_a_part_is_a_problem(self):
        r = Repo(None, {"plans/SHIP-7/plan.md": "TIER        2\n", "plans/SHIP-7/part-2/bundle-1.md": bundle(tier="2", may="web/**")})
        r.commit("s1", {"web/page.ts": "export {}\n", "plans/SHIP-7/plan.md": "TIER        2\nchanged\n"})
        self.assertEqual(r.check(part=2)[0], [f"plans/SHIP-7/plan.md: a Tier 2 plan or bundle is changed in a code "
                                              f"pull request; {self.ADR}"])


class CommandTest(unittest.TestCase):
    def run_main(self, root, argv, stdin=""):
        out, err, old = io.StringIO(), io.StringIO(), sys.stdin
        sys.stdin = io.StringIO(stdin)
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = check_slice.main(argv + ["--root", str(root)])
        finally:
            sys.stdin = old
        return code, out.getvalue(), err.getvalue()

    def test_a_branch_with_no_key_is_not_checked(self):
        r = Repo(bundle())
        r.git("switch", "-q", "-c", "chore/tidy")
        code, out, _ = self.run_main(r.root, ["--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn("names no story key", out)

    def test_problems_exit_1_and_a_clean_branch_exits_0(self):
        r = Repo(bundle())
        r.commit("s1", {"src/app.py": "x = 1\n"})
        self.assertEqual(self.run_main(r.root, ["--base", "main"])[0], 0)
        r.commit("s2", {"web/page.ts": "x\n"})
        code, out, _ = self.run_main(r.root, ["--base", "main"])
        self.assertEqual(code, 1)
        self.assertIn("web/page.ts: outside", out)

    def test_the_branch_can_be_named_for_ci(self):
        r = Repo(bundle())
        r.commit("s2", {"web/page.ts": "x\n"})
        self.assertEqual(self.run_main(r.root, ["--base", "main", "--branch", "feat/SHIP-7-x"])[0], 1)

    def test_the_hook_blocks_with_exit_2_and_sees_untracked_work(self):
        r = Repo(bundle())
        r.write({"web/page.ts": "x\n"})
        code, _, err = self.run_main(r.root, ["--hook"], stdin=json.dumps({"stop_hook_active": False}))
        self.assertEqual(code, 2)
        self.assertIn("web/page.ts: outside", err)

    def test_the_hook_sees_uncommitted_edits_to_tests(self):
        r = Repo(bundle())
        r.write({"tests/test_app.py": BASE_TEST.replace("== 3", "> 0")})
        code, _, err = self.run_main(r.root, ["--hook"], stdin="{}")
        self.assertEqual(code, 2)
        self.assertIn("assert total(1, 2) == 3", err)

    def test_the_hook_lets_the_session_stop_the_second_time(self):
        r = Repo(bundle())
        r.write({"web/page.ts": "x\n"})
        self.assertEqual(self.run_main(r.root, ["--hook"], stdin='{"stop_hook_active": true}')[0], 0)

    def test_the_hook_never_blocks_outside_a_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_main(Path(tmp), ["--hook"], stdin="{}")[0], 0)


EXCEPTION_LINE = "# aidlc-exception: reason=read by plugins; owner=Bo; expires=2026-12-31\n"
SWAPPED = "def total(a, b):\n    return b + a\n"
RECIPE_LINE = "RECIPE      pyupgrade@3.19.0 \u2014 pyupgrade --py312-plus \u2014 tests/**\n"


def with_recipe(text, recipe=RECIPE_LINE):
    return text.replace("MAY CHANGE", recipe + "MAY CHANGE", 1)


def run_main(root, argv, stdin=""):
    out, err, old = io.StringIO(), io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = check_slice.main(argv + ["--root", str(root)])
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class NetResultTest(unittest.TestCase):
    """I1: a slip that a later commit undoes is not a problem for the life of the branch; only the net result counts."""

    def test_an_assertion_removed_then_restored_verbatim_is_clean(self):
        r = Repo(bundle())
        r.commit("c1", {"tests/test_app.py": BASE_TEST.replace("    assert total(1, 2) == 3\n", "    pass\n")})
        r.commit("c2", {"tests/test_app.py": BASE_TEST, "src/app.py": SWAPPED})
        self.assertEqual(r.check(), ([], []))

    def test_an_assertion_removed_and_restored_only_in_the_working_tree_is_clean(self):
        r = Repo(bundle())
        r.commit("c1", {"tests/test_app.py": BASE_TEST.replace("    assert total(1, 2) == 3\n", "    pass\n")})
        r.write({"tests/test_app.py": BASE_TEST, "src/app.py": SWAPPED})
        self.assertEqual(run_main(r.root, ["--hook"], stdin="{}")[0], 0)

    def test_an_assertion_removed_and_not_restored_is_still_a_problem(self):
        r = Repo(bundle())
        r.commit("c1", {"tests/test_app.py": BASE_TEST.replace("    assert total(1, 2) == 3\n", "    pass\n")})
        r.commit("c2", {"tests/test_app.py": BASE_TEST.replace("== 3", "> 0")})
        self.assertEqual(r.check()[0], ["an existing test or assertion is removed or changed: "
                                        "tests/test_app.py: assert total(1, 2) == 3"])

    def test_a_noqa_added_then_removed_is_clean(self):
        r = Repo(bundle())
        r.commit("c1", {"src/app.py": "import os  # noqa: F401\n" + APP})
        r.commit("c2", {"src/app.py": SWAPPED})
        self.assertEqual(r.check(), ([], []))

    def test_a_noqa_given_an_exception_on_the_line_above_later_is_clean(self):
        r = Repo(bundle())
        r.commit("c1", {"src/app.py": "import os  # noqa: F401\n" + APP})
        r.commit("c2", {"src/app.py": EXCEPTION_LINE + "import os  # noqa: F401\n" + APP})
        self.assertEqual(r.check(), ([], []))

    def test_a_noqa_that_survives_without_an_exception_is_reported_once(self):
        r = Repo(bundle())
        r.commit("c1", {"src/app.py": "import os  # noqa: F401\n" + APP})
        r.commit("c2", {"src/app.py": "import os  # noqa: F401\n" + APP + "x = 1\n"})
        self.assertEqual(len(r.check()[0]), 1)


class RecipeTrailerTest(unittest.TestCase):
    """I2: a `Recipe:` trailer exempts a commit only when an approved bundle's RECIPE names that recipe."""

    def forge(self, bundle_text):
        r = Repo(bundle_text)
        r.commit("tidy\n\nRecipe: x@1", {
            "tests/test_app.py": BASE_TEST.replace("    assert total(1, 2) == 3\n", "    pass\n"),
            "src/app.py": "import os  # noqa: F401\n" + APP})
        return r.check()[0]

    def test_a_forged_trailer_with_no_approved_recipe_exempts_nothing(self):
        problems = self.forge(with_recipe(bundle(), "RECIPE      none\n"))
        self.assertIn("an existing test or assertion is removed or changed: tests/test_app.py: assert total(1, 2) == 3",
                      problems)
        self.assertTrue(any("a suppression or skip without a valid aidlc-exception" in p for p in problems), problems)

    def test_a_trailer_naming_another_recipe_exempts_nothing(self):
        problems = self.forge(with_recipe(bundle()))
        self.assertIn("an existing test or assertion is removed or changed: tests/test_app.py: assert total(1, 2) == 3",
                      problems)

    def test_an_approved_recipe_commit_still_answers_for_its_markers(self):
        r = Repo(with_recipe(bundle()))
        r.commit("mechanical\n\nRecipe: pyupgrade@3.19.0", {"src/app.py": "import os  # noqa: F401\n" + APP})
        problems = r.check()[0]
        self.assertEqual(len(problems), 1)
        self.assertIn("a suppression or skip without a valid aidlc-exception", problems[0])

    def test_the_reviewer_is_told_which_recipe_commit_was_exempted(self):
        r = Repo(with_recipe(bundle()))
        r.commit("mechanical\n\nRecipe: pyupgrade@3.19.0",
                 {"tests/test_app.py": BASE_TEST.replace("assert total(1, 2) == 3", "assert (total(1, 2) == 3)")})
        sha = r.git("rev-parse", "--short=12", "HEAD").strip()
        code, out, _ = run_main(r.root, ["--base", "main"])
        self.assertEqual(code, 0)
        self.assertIn(f"for the reviewer: recipe commit {sha} (Recipe: pyupgrade@3.19.0)", out)
        self.assertIn("exempt from the assertion check", out)


class PartFromTheBranchTest(unittest.TestCase):
    """I3: CI and the hook pass no --part; the part comes from the one part folder the branch changes."""

    def part_repo(self, extra=None):
        files = {"plans/SHIP-7/part-2/bundle-1.md": bundle(may="web/**")}
        files.update(extra or {})
        r = Repo(None, files)
        r.git("switch", "-q", "-c", "feat/SHIP-7-2")
        return r

    def test_ci_finds_the_part_from_the_folder_the_branch_changes(self):
        r = self.part_repo()
        r.commit("s1", {"web/w.ts": "export {}\n", "plans/SHIP-7/part-2/progress-1.md": "STATUS      doing\n"})
        code, out, _ = run_main(r.root, ["--base", "main", "--branch", "feat/SHIP-7-2"])
        self.assertEqual(code, 0, out)

    def test_the_inferred_part_still_scopes_the_work(self):
        r = self.part_repo()
        r.commit("s1", {"src/app.py": "x = 1\n", "plans/SHIP-7/part-2/progress-1.md": "STATUS      doing\n"})
        self.assertEqual(r.check()[0], ["src/app.py: outside every bundle's MAY CHANGE"])

    def test_several_parts_on_one_branch_is_a_problem(self):
        r = self.part_repo({"plans/SHIP-7/part-1/bundle-1.md": bundle(may="src/**")})
        r.commit("s1", {"web/w.ts": "export {}\n", "plans/SHIP-7/part-1/progress-1.md": "STATUS      doing\n",
                        "plans/SHIP-7/part-2/progress-1.md": "STATUS      doing\n"})
        problems = r.check()[0]
        self.assertTrue(any("this branch changes several parts; one part per branch" in p for p in problems), problems)


class SuppressedLineTest(unittest.TestCase):
    """I4: a line that already carried a suppression is not a new one when it is edited or moved."""

    def test_an_edited_suppressed_line_is_clean(self):
        r = Repo(bundle(), {"src/calc.py": "value = compute(1)  # type: ignore\n"})
        r.commit("s1", {"src/calc.py": "value = compute(2)  # type: ignore\n"})
        self.assertEqual(r.check(), ([], []))

    def test_a_second_suppression_is_still_reported(self):
        r = Repo(bundle(), {"src/calc.py": "value = compute(1)  # type: ignore\n"})
        r.commit("s1", {"src/calc.py": "value = compute(2)  # type: ignore\nother = compute(3)  # type: ignore\n"})
        problems = r.check()[0]
        self.assertEqual(len(problems), 1)
        self.assertIn("type: ignore", problems[0])

    def test_a_moved_file_keeps_its_suppression(self):
        body = "".join(f"line_{i} = {i}\n" for i in range(10)) + "value = compute(1)  # type: ignore\n"
        r = Repo(bundle(), {"src/calc.py": body})
        r.git("mv", "src/calc.py", "src/calculate.py")
        r.commit("move", {"src/calculate.py": body.replace("line_0", "first")})
        self.assertEqual(r.check(), ([], []))

    def test_another_kind_of_marker_is_not_covered(self):
        r = Repo(bundle(), {"src/calc.py": "value = compute(1)  # type: ignore\n"})
        r.commit("s1", {"src/calc.py": "value = compute(2)  # noqa: E501\n"})
        self.assertEqual(len(r.check()[0]), 1)


WIDER = "a suppression or skip got wider"
NEW = "a suppression or skip without a valid aidlc-exception"


class NeverWiderTest(unittest.TestCase):
    """Item 2: an added marker is covered by a removed one of the same family only when it is no wider: its scope
    no larger, its rules a subset. Narrowing and equal are allowed; widening, or a marker the parser cannot read, is
    not."""

    def edit(self, path, before, after):
        r = Repo(bundle(), {path: before})
        r.commit("s1", {path: after})
        return r.check()[0]

    def assert_widened(self, problems, old, new):
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(WIDER, problems[0])
        self.assertIn(f"({old} → {new})", problems[0])

    def test_an_eslint_line_rule_widened_to_a_blanket_block_is_reported(self):
        problems = self.edit("src/log.js", "// eslint-disable-next-line no-console\nconsole.log(1)\n",
                             "/* eslint-disable */\nconsole.log(1)\n")
        self.assert_widened(problems, "eslint, line, no-console", "eslint, block, all rules")

    def test_a_noqa_code_widened_to_a_blanket_noqa_is_reported(self):
        problems = self.edit("src/calc.py", "import os  # noqa: F401\n", "import os  # noqa\n")
        self.assert_widened(problems, "noqa, line, F401", "noqa, line, all rules")

    def test_a_type_ignore_code_widened_to_a_blanket_ignore_is_reported(self):
        problems = self.edit("src/calc.py", "value = compute(1)  # type: ignore[arg-type]\n",
                             "value = compute(2)  # type: ignore\n")
        self.assert_widened(problems, "mypy, line, arg-type", "mypy, line, all rules")

    def test_a_narrower_noqa_is_clean(self):
        self.assertEqual(self.edit("src/calc.py", "import os  # noqa: F401,E501\n", "import os  # noqa: F401\n"), [])

    def test_reordered_and_respaced_codes_are_clean(self):
        self.assertEqual(self.edit("src/calc.py", "import os  # noqa: E501, F401\n",
                                   "import os  # noqa: F401,E501\n"), [])

    def test_the_same_scope_rank_is_clean(self):
        self.assertEqual(self.edit("src/log.js", "// eslint-disable-next-line no-console\nconsole.log(1)\n",
                                   "console.log(1) // eslint-disable-line no-console\n"), [])

    def test_a_test_skip_widened_to_a_suite_skip_is_reported(self):
        problems = self.edit("tests/total.test.ts", "it.skip('adds', () => {})\n",
                             "describe.skip('adds', () => {})\n")
        self.assert_widened(problems, "skip, test, all rules", "skip, suite, all rules")

    def test_an_added_ts_nocheck_is_reported(self):
        problems = self.edit("src/page.ts", "export const x = 1\n", "// @ts-nocheck\nexport const x = 1\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(NEW, problems[0])
        self.assertIn("@ts-nocheck", problems[0])

    def test_a_ts_ignore_widened_to_ts_nocheck_is_reported(self):
        problems = self.edit("src/page.ts", "// @ts-ignore\nexport const x: number = 'a'\n",
                             "// @ts-nocheck\nexport const x: number = 'a'\n")
        self.assert_widened(problems, "ts, line, all rules", "ts, file, all rules")

    def test_a_marker_the_parser_cannot_read_is_treated_as_new(self):
        problems = self.edit("src/calc.py", "value = compute(1)  # type: ignore[arg-type]\n",
                             "value = compute(2)  # type: ignore[arg-type\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(NEW, problems[0])
        self.assertIn("# type: ignore[arg-type", problems[0])

    def test_a_widened_marker_with_a_valid_exception_is_allowed(self):
        self.assertEqual(self.edit("src/calc.py", "import os  # noqa: F401\n",
                                   EXCEPTION_LINE + "import os  # noqa\n"), [])

    def test_a_moved_file_keeps_its_parsed_markers(self):
        body = "".join(f"line_{i} = {i}\n" for i in range(10)) + "import os  # noqa: F401, E501\n"
        r = Repo(bundle(), {"src/calc.py": body})
        r.git("mv", "src/calc.py", "src/calculate.py")
        r.commit("move", {"src/calculate.py": body.replace("line_0", "first").replace("F401, E501", "E501,F401")})
        self.assertEqual(r.check(), ([], []))

    def test_a_second_added_marker_is_still_reported(self):
        problems = self.edit("src/calc.py", "import os  # noqa: F401,E501\n",
                             "import os  # noqa: F401\nimport sys  # noqa: E501\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(NEW, problems[0])
        self.assertIn("import sys", problems[0])

    def test_each_marker_on_a_line_needs_its_own_cover(self):
        problems = self.edit("src/calc.py", "import os  # type: ignore[import]\n",
                             "import os  # type: ignore[import]  # noqa\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(NEW, problems[0])

    def test_a_skip_moved_from_a_test_to_its_class_is_reported(self):
        before = ("import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.skip('flaky')\n"
                  "    def test_a(self):\n        pass\n")
        after = ("import unittest\n\n\n@unittest.skip('flaky')\nclass T(unittest.TestCase):\n"
                 "    def test_a(self):\n        pass\n")
        self.assert_widened(self.edit("tests/test_flaky.py", before, after), "skip, test, all rules",
                            "skip, suite, all rules")

    def test_a_file_level_noqa_is_wider_than_a_line_noqa(self):
        problems = self.edit("src/calc.py", "import os  # noqa: F401\n", "# ruff: noqa: F401\nimport os\n")
        self.assert_widened(problems, "noqa, line, F401", "noqa, file, F401")


class ParseMarkerTest(unittest.TestCase):
    """Item 2: each marker reads as (family, scope, rules); rules None means every rule; None means unreadable."""

    def read(self, text, following=""):
        m = check_slice.parse_marker(text, following)
        return None if m is None else (m.family, m.scope_name, m.rules)

    def test_markers_read_as_family_scope_and_rules(self):
        line, block, file = check_slice.SCOPE_LINE, check_slice.SCOPE_BLOCK, check_slice.SCOPE_FILE
        self.assertEqual((check_slice.SCOPE_TEST, check_slice.SCOPE_SUITE), (line, block))
        self.assertLess(line, block)
        self.assertLess(block, file)
        cases = {
            "foo() // eslint-disable-line no-console, no-alert -- legacy": ("eslint", "line",
                                                                             {"no-console", "no-alert"}),
            "/* eslint-disable react/no-danger */": ("eslint", "block", {"react/no-danger"}),
            "/* eslint-disable */": ("eslint", "block", None),
            "import os  # noqa": ("noqa", "line", None),
            "import os  # NOQA:F401 E501": ("noqa", "line", {"F401", "E501"}),
            "# flake8: noqa": ("noqa", "file", None),
            "x = f()  # type: ignore[arg-type, union-attr]": ("mypy", "line", {"arg-type", "union-attr"}),
            "# type: ignore": ("mypy", "file", None),
            "# mypy: ignore-errors": ("mypy", "file", None),
            "x = 1  # pylint: disable=invalid-name": ("pylint", "line", {"invalid-name"}),
            "# pylint: disable=invalid-name,too-many-locals": ("pylint", "block",
                                                               {"invalid-name", "too-many-locals"}),
            "# pylint: disable=all": ("pylint", "block", None),
            "# pylint: skip-file": ("pylint", "file", None),
            "// @ts-expect-error: the API returns a string": ("ts", "line", None),
            "// @ts-nocheck": ("ts", "file", None),
            "#pragma warning disable CS0168, CA1062 // legacy": ("csharp-pragma", "block", {"CS0168", "CA1062"}),
            "#pragma warning disable": ("csharp-pragma", "block", None),
            '[SuppressMessage("Design", "CA1062:Validate arguments")]': ("csharp-attr", "block", {"CA1062"}),
            "x, _ := f() //nolint:errcheck,gosec // checked above": ("go-nolint", "line", {"errcheck", "gosec"}),
            "return err //nolint": ("go-nolint", "line", None),
            '@SuppressWarnings({"unchecked", "rawtypes"})': ("java", "block", {"unchecked", "rawtypes"}),
            '@SuppressWarnings("all")': ("java", "block", None),
            "String s = q; // NOSONAR": ("sonar", "line", None),
            "/* istanbul ignore next */": ("coverage", "line", None),
            "/* c8 ignore start */": ("coverage", "block", None),
            "/* istanbul ignore file */": ("coverage", "file", None),
            "it.skip('adds', () => {})": ("skip", "test", None),
            "xdescribe('totals', () => {})": ("skip", "suite", None),
            "it.only('adds', () => {})": ("skip", "file", None),
            "@pytest.mark.skip(reason='slow')": ("skip", "test", None),
            "pytestmark = pytest.mark.skip(reason='slow')": ("skip", "suite", None),
            'pytest.skip("no db", allow_module_level=True)': ("skip", "suite", None),
            '[Fact(Skip = "flaky")]': ("skip", "test", None),
            "t.Skip(\"needs docker\")": ("skip", "test", None),
        }
        for text, (family, scope, rules) in cases.items():
            with self.subTest(text=text):
                self.assertEqual(self.read(text), (family, scope, None if rules is None else frozenset(rules)))

    def test_a_skip_on_a_class_is_a_suite(self):
        self.assertEqual(self.read("@Disabled", "public class OrderTest {"), ("skip", "suite", None))
        self.assertEqual(self.read("@Disabled", "void totals() {"), ("skip", "test", None))

    def test_unreadable_details_are_none(self):
        for text in ("x = f()  # type: ignore[arg-type", "import os  # noqa : E501", "import os  # noqa: bad",
                     "# pylint: disable", "// eslint-disabled", "/* c8 ignore sometimes */", "@SuppressWarnings("):
            with self.subTest(text=text):
                self.assertIsNone(check_slice.parse_marker(text))


def edit_one(path, before, after):
    r = Repo(bundle(), {path: before})
    r.commit("s1", {path: after})
    return r.check()[0]


class ClassScopeTest(unittest.TestCase):
    """Item 2 fix 1: whether a marker sits on a class is read from the file, past decorators; unknown is fail safe."""

    def test_a_skip_moved_onto_a_decorated_class_is_reported(self):
        methods = "".join(f"    def test_{i}(self, m):\n        pass\n\n" for i in range(4))
        before = ("import unittest\nfrom unittest import mock\n\n\n@mock.patch('x')\nclass T(unittest.TestCase):\n"
                  + methods + "    @unittest.skip('f')\n    def test_a(self, m):\n        pass\n")
        after = ("import unittest\nfrom unittest import mock\n\n\n@unittest.skip('f')\n@mock.patch('x')\n"
                 "class T(unittest.TestCase):\n" + methods + "    def test_a(self, m):\n        pass\n")
        problems = edit_one("tests/test_patched.py", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("(skip, test, all rules → skip, suite, all rules)", problems[0])

    def test_a_suppression_moved_onto_an_annotated_class_is_reported(self):
        methods = "".join(f"    void g{i}() {{}}\n\n" for i in range(4))
        before = '@Entity\npublic class A {\n' + methods + '    @SuppressWarnings("unchecked")\n    void f() {}\n}\n'
        after = '@SuppressWarnings("unchecked")\n@Entity\npublic class A {\n' + methods + '    void f() {}\n}\n'
        problems = edit_one("src/A.java", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("(java, block, unchecked → java, file, unchecked)", problems[0])

    def test_a_skip_moved_between_two_methods_is_clean(self):
        before = ("import unittest\n\n\nclass T(unittest.TestCase):\n    @unittest.skip('f')\n"
                  "    def test_a(self):\n        pass\n\n    def test_b(self):\n        pass\n")
        after = ("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_a(self):\n        pass\n\n"
                 "    @unittest.skip('f')\n    def test_b(self):\n        pass\n")
        self.assertEqual(edit_one("tests/test_moved.py", before, after), [])

    def test_a_multi_line_decorator_is_skipped_to_reach_the_class(self):
        self.assertEqual(check_slice.following_code(["@unittest.skip(", "    'f',", ")", "@mock.patch('x')",
                                                     "# a note", "class T(unittest.TestCase):"], 1),
                         "class T(unittest.TestCase):")

    def test_an_unknown_following_line_reads_widest_when_added_and_narrowest_when_removed(self):
        added = check_slice.markers_of("@unittest.skip('f')", None, added=True)
        removed = check_slice.markers_of("@unittest.skip('f')", None, added=False)
        self.assertEqual((added[0].scope_name, removed[0].scope_name), ("suite", "test"))
        self.assertIsNone(check_slice.following_code(["@unittest.skip('f')"], 1))


class ClosingDirectiveTest(unittest.TestCase):
    """Item 2 fix 2: removing a closing directive extends its suppression; adding one only narrows it."""

    def assert_closer_removed(self, problems, directive):
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(f"a suppression got wider (its closing {directive} was removed) without a valid "
                      f"aidlc-exception", problems[0])

    def test_a_removed_eslint_enable_is_reported(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nconsole.log(2)\n"
        after = "/* eslint-disable no-console */\nconsole.log(1)\nconsole.log(2)\n"
        self.assert_closer_removed(edit_one("src/log.js", before, after), "eslint-enable")

    def test_a_removed_pragma_restore_is_reported(self):
        before = ("class A {\n#pragma warning disable CS0168\n    void F() { int x; }\n"
                  "#pragma warning restore CS0168\n    void G() { int y; }\n}\n")
        after = "class A {\n#pragma warning disable CS0168\n    void F() { int x; }\n    void G() { int y; }\n}\n"
        self.assert_closer_removed(edit_one("src/A.cs", before, after), "#pragma warning restore")

    def test_a_removed_pylint_enable_is_reported(self):
        before = "# pylint: disable=no-member\nx = a.b\n# pylint: enable=no-member\ny = c.d\n"
        after = "# pylint: disable=no-member\nx = a.b\ny = c.d\n"
        self.assert_closer_removed(edit_one("src/calc.py", before, after), "pylint: enable")

    def test_a_removed_c8_stop_is_reported(self):
        before = "/* c8 ignore start */\nfoo()\n/* c8 ignore stop */\nbar()\n"
        after = "/* c8 ignore start */\nfoo()\nbar()\n"
        self.assert_closer_removed(edit_one("src/run.js", before, after), "c8 ignore stop")

    def test_an_added_c8_stop_is_clean(self):
        self.assertEqual(edit_one("src/run.js", "/* c8 ignore start */\nfoo()\nbar()\n",
                                  "/* c8 ignore start */\nfoo()\n/* c8 ignore stop */\nbar()\n"), [])

    def test_removing_an_opener_with_its_closer_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nconsole.log(2)\n"
        self.assertEqual(edit_one("src/log.js", before, "console.log(1)\nconsole.log(2)\n"), [])

    def test_a_removed_closer_is_allowed_when_its_opener_carries_a_valid_exception(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nconsole.log(2)\n"
        after = ("// aidlc-exception: reason=legacy logger; owner=Bo; expires=2026-12-31\n"
                 "/* eslint-disable no-console */\nconsole.log(1)\nconsole.log(2)\n")
        self.assertEqual(edit_one("src/log.js", before, after), [])

    def test_a_closer_moved_within_the_file_is_reported_only_when_removed(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nconsole.log(2)\n"
        after = "/* eslint-disable no-console */\n/* eslint-enable no-console */\nconsole.log(1)\nconsole.log(2)\n"
        self.assertEqual(edit_one("src/log.js", before, after), [])


PAIR = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n"
VALID = "aidlc-exception: reason=legacy logger; owner=Bo; expires=2026-12-31"


class CloserPairTest(unittest.TestCase):
    """Item 2 fix round 2: a removed closer pairs with the nearest block-or-wider opener of its family above it in the
    base file; removing the pair is clean, and only that opener's exception (or the closer's own) excuses it."""

    def test_removing_a_pair_next_to_an_unrelated_opener_is_clean(self):
        before = "// eslint-disable-next-line no-alert\nalert(1)\n" + PAIR + "console.log(2)\n"
        after = "// eslint-disable-next-line no-alert\nalert(1)\nconsole.log(1)\nconsole.log(2)\n"
        self.assertEqual(edit_one("src/log.js", before, after), [])

    def test_removing_a_pylint_pair_next_to_a_trailing_disable_is_clean(self):
        before = ("x = 1  # pylint: disable=invalid-name\n# pylint: disable=no-member\ny = a.b\n"
                  "# pylint: enable=no-member\nz = c.d\n")
        after = "x = 1  # pylint: disable=invalid-name\ny = a.b\nz = c.d\n"
        self.assertEqual(edit_one("src/calc.py", before, after), [])

    def test_removing_only_the_closer_while_its_opener_stays_is_reported(self):
        before = "// eslint-disable-next-line no-alert\nalert(1)\n" + PAIR + "console.log(2)\n"
        after = before.replace("/* eslint-enable no-console */\n", "")
        problems = edit_one("src/log.js", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("its closing eslint-enable was removed", problems[0])

    def test_deleting_a_file_with_a_pair_is_clean_in_ci(self):
        r = Repo(bundle(), {"src/log.js": PAIR + "console.log(2)\n"})
        r.git("rm", "-q", "src/log.js")
        r.commit("drop")
        self.assertEqual(r.check(), ([], []))

    def test_deleting_a_file_with_a_pair_is_clean_in_the_hook(self):
        r = Repo(bundle(), {"src/log.js": PAIR + "console.log(2)\n"})
        (r.root / "src/log.js").unlink()
        self.assertEqual(run_main(r.root, ["--hook"], stdin="{}")[0], 0)

    def test_an_excepted_unrelated_opener_does_not_excuse_a_removed_closer(self):
        before = f"// eslint-disable-next-line no-alert -- {VALID}\nalert(1)\n" + PAIR + "console.log(2)\n"
        after = before.replace("/* eslint-enable no-console */\n", "")
        problems = edit_one("src/log.js", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("its closing eslint-enable was removed", problems[0])

    def test_an_exception_added_on_the_paired_opener_excuses_a_removed_closer(self):
        before = PAIR + "console.log(2)\n"
        after = f"/* eslint-disable no-console */ // {VALID}\nconsole.log(1)\nconsole.log(2)\n"
        self.assertEqual(edit_one("src/log.js", before, after), [])

    def test_an_edited_opener_without_an_exception_does_not_pair(self):
        before = PAIR + "console.log(2)\n"
        after = "/* eslint-disable  no-console */\nconsole.log(1)\nconsole.log(2)\n"
        problems = edit_one("src/log.js", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("its closing eslint-enable was removed", problems[0])

    def test_form_feeds_above_keep_line_numbers_in_step_with_git(self):
        methods = "".join(f"    def test_{i}(self, m):\n        pass\n\n" for i in range(4))
        top = "import unittest\nfrom unittest import mock\n" + "".join(f"x{i} = {i}\x0c\n" for i in range(6)) + "\n\n"
        before = (top + "@mock.patch('x')\nclass T(unittest.TestCase):\n" + methods
                  + "    @unittest.skip('f')\n    def test_a(self, m):\n        pass\n")
        after = (top + "@unittest.skip('f')\n@mock.patch('x')\nclass T(unittest.TestCase):\n" + methods
                 + "    def test_a(self, m):\n        pass\n")
        problems = edit_one("tests/test_patched.py", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("(skip, test, all rules → skip, suite, all rules)", problems[0])


TAIL = "".join(f"console.log({i})\n" for i in range(2, 6))
NESTED = ("/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-disable no-alert */\nalert(1)\n"
          "/* eslint-enable no-alert */\n/* eslint-enable no-console */\n" + TAIL)


class OpenInTheHeadTest(unittest.TestCase):
    """Item 2 fix round 3: a removed closer is judged by what is still open at its former place in the head file:
    every same-family block-or-wider opener still open there with overlapping rules needs its own valid exception in
    the head. Checked in both modes (CI on commits, the hook on the working tree)."""

    def both(self, path, before, after):
        ci, hook = Repo(bundle(), {path: before}), Repo(bundle(), {path: before})
        ci.commit("s1", {path: after})
        hook.write({path: after})
        return ci.check()[0], check_slice.check(hook.root, "main", "SHIP-7", None, worktree=True, today=TODAY)[0]

    def assert_reported(self, path, before, after):
        for mode, problems in zip(("ci", "hook"), self.both(path, before, after)):
            with self.subTest(mode=mode):
                self.assertEqual(len(problems), 1, problems)
                self.assertIn("its closing eslint-enable was removed" if path.endswith(".js")
                              else "its closing pylint: enable was removed", problems[0])

    def assert_clean(self, path, before, after):
        for mode, problems in zip(("ci", "hook"), self.both(path, before, after)):
            with self.subTest(mode=mode):
                self.assertEqual(problems, [])

    def test_a1_dropping_the_inner_opener_and_the_outer_closer_is_reported(self):
        after = "/* eslint-disable no-console */\nconsole.log(1)\nalert(1)\n/* eslint-enable no-alert */\n" + TAIL
        self.assert_reported("src/n.js", NESTED, after)

    def test_a1b_dropping_the_inner_pair_and_the_outer_closer_is_reported(self):
        self.assert_reported("src/n.js", NESTED, "/* eslint-disable no-console */\nconsole.log(1)\nalert(1)\n" + TAIL)

    def test_a2_a_pylint_module_disable_left_open_is_reported(self):
        before = ("# pylint: disable=no-member\nimport os\n\n\ndef f(x):\n    # pylint: disable=protected-access\n"
                  "    return x._y\n# pylint: enable=no-member\n\n\ndef g(a):\n    return a.b.c\n")
        after = ("# pylint: disable=no-member\nimport os\n\n\ndef f(x):\n    return x._y\n\n\n"
                 "def g(a):\n    return a.b.c\n")
        self.assert_reported("src/p.py", before, after)

    def test_a3_a_duplicate_opener_left_open_is_reported(self):
        before = ("/* eslint-disable no-console */\nconsole.log(0)\n/* eslint-disable no-console */\nconsole.log(1)\n"
                  "/* eslint-enable no-console */\n" + TAIL)
        self.assert_reported("src/d.js", before,
                             "/* eslint-disable no-console */\nconsole.log(0)\nconsole.log(1)\n" + TAIL)

    def test_s1_an_edited_opener_left_open_is_reported_even_when_another_equal_opener_goes(self):
        before = ("/* eslint-disable no-console */\nconsole.log(0)\n/* eslint-enable no-console */\nx()\n"
                  "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n" + TAIL)
        after = ("console.log(0)\n/* eslint-enable no-console */\nx()\n"
                 "/* eslint-disable no-console -- legacy */\nconsole.log(1)\n" + TAIL)
        self.assert_reported("src/s.js", before, after)

    def test_a4_removing_one_of_two_interleaved_pairs_is_clean(self):
        before = ("/* eslint-disable no-console */\n/* eslint-disable no-alert */\nconsole.log(1)\nalert(1)\n"
                  "/* eslint-enable no-console */\nalert(2)\n/* eslint-enable no-alert */\n" + TAIL)
        after = ("/* eslint-disable no-alert */\nconsole.log(1)\nalert(1)\nalert(2)\n/* eslint-enable no-alert */\n"
                 + TAIL)
        self.assert_clean("src/i.js", before, after)

    def test_n1_a_block_pair_narrowed_to_a_next_line_disable_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n" + TAIL
        self.assert_clean("src/r.js", before, "// eslint-disable-next-line no-console\nconsole.log(1)\n" + TAIL)

    def test_an_exception_on_the_still_open_opener_in_the_head_excuses(self):
        after = (f"/* eslint-disable no-console */ // {VALID}\nconsole.log(1)\nalert(1)\n"
                 "/* eslint-enable no-alert */\n" + TAIL)
        self.assert_clean("src/n.js", NESTED, after)

    def test_a_base_exception_above_the_closer_for_another_marker_does_not_excuse(self):
        before = ("/* eslint-disable no-console */\nconsole.log(1)\n"
                  f"alert(1) // eslint-disable-line no-alert -- {VALID}\n/* eslint-enable no-console */\n" + TAIL)
        self.assert_reported("src/b.js", before, before.replace("/* eslint-enable no-console */\n", ""))

    def test_a_closer_replaced_by_one_that_ends_the_same_rules_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n" + TAIL
        self.assert_clean("src/w.js", before, before.replace("/* eslint-enable no-console */", "/* eslint-enable */"))

    def test_a_closer_moved_down_is_reported(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n" + TAIL
        self.assert_reported("src/w.js", before, "/* eslint-disable no-console */\nconsole.log(1)\n" + TAIL
                             + "/* eslint-enable no-console */\n")

    def test_a_closer_whose_spacing_changes_in_place_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\n" + TAIL
        self.assert_clean("src/w.js", before, before.replace("/* eslint-enable", "/*  eslint-enable"))

    def test_a_lone_carriage_return_above_keeps_hook_line_numbers_in_step_with_git(self):
        methods = "".join(f"    def test_{i}(self, m):\n        pass\n\n" for i in range(4))

        def py(on):
            return ("import unittest\nfrom unittest import mock\n# a\rb\rc\rd\re\rf\rg\n\n\nX = 1\n\n\n"
                    + ("@unittest.skip('f')\n" if on else "") + "@mock.patch('x')\nclass T(unittest.TestCase):\n"
                    + methods + ("" if on else "    @unittest.skip('f')\n")
                    + "    def test_a(self, m):\n        pass\n")
        r = Repo(bundle(), {"tests/test_p.py": py(False)})
        r.write({"tests/test_p.py": py(True)})
        code, _, err = run_main(r.root, ["--hook"], stdin="{}")
        self.assertEqual(code, 2, err)
        self.assertIn("(skip, test, all rules → skip, suite, all rules)", err)


class WideningRanksTest(unittest.TestCase):
    """Item 2 fixes 3 to 5: "got wider" only when the added marker widens a removed one; ts and pylint ranks."""

    def test_an_unrelated_removed_marker_does_not_make_a_new_one_wider(self):
        problems = edit_one("src/calc.py", "x = 'long'  # noqa: E501\nimport os\n",
                            "x = 'long'\nimport os  # noqa: F401\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(NEW, problems[0])
        self.assertNotIn(WIDER, problems[0])

    def test_ts_expect_error_to_ts_ignore_is_wider(self):
        problems = edit_one("src/page.ts", "// @ts-expect-error\nexport const x: number = 'a'\n",
                            "// @ts-ignore\nexport const x: number = 'a'\n")
        self.assertEqual(len(problems), 1, problems)
        self.assertIn(WIDER, problems[0])

    def test_ts_ignore_to_ts_expect_error_is_clean(self):
        self.assertEqual(edit_one("src/page.ts", "// @ts-ignore\nexport const x: number = 'a'\n",
                                  "// @ts-expect-error\nexport const x: number = 'a'\n"), [])

    def test_a_pylint_disable_moved_onto_a_def_line_is_wider(self):
        before = "def total(a, b):\n    result = a + b  # pylint: disable=invalid-name\n    return result\n"
        after = "def total(a, b):  # pylint: disable=invalid-name\n    result = a + b\n    return result\n"
        problems = edit_one("src/calc.py", before, after)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("(pylint, line, invalid-name → pylint, block, invalid-name)", problems[0])


PYLINT_NESTED = ("# pylint: disable=no-member\nimport os\n# pylint: disable=protected-access\nX = os._exit\n"
                 "# pylint: enable=protected-access\nY = os.path.sep\n# pylint: enable=no-member\n"
                 "Z = os.environ.copy\n")


class HeadSimulationTest(unittest.TestCase):
    """Item 2 fix round 4: the head simulation reads a pylint closer's own rules, reads every directive on a line in
    the order written, keeps an opener it cannot read open, and finds a restyled closer past an edited next line.
    Checked in both modes (CI on commits, the hook on the working tree)."""

    def both(self, path, before, after):
        ci, hook = Repo(bundle(), {path: before}), Repo(bundle(), {path: before})
        ci.commit("s1", {path: after})
        hook.write({path: after})
        return ci.check()[0], check_slice.check(hook.root, "main", "SHIP-7", None, worktree=True, today=TODAY)[0]

    def assert_reported(self, path, before, after, directive):
        for mode, problems in zip(("ci", "hook"), self.both(path, before, after)):
            with self.subTest(mode=mode):
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(f"its closing {directive} was removed", problems[0])

    def assert_clean(self, path, before, after):
        for mode, problems in zip(("ci", "hook"), self.both(path, before, after)):
            with self.subTest(mode=mode):
                self.assertEqual(problems, [])

    def test_a_pylint_enable_ends_only_the_rules_it_names(self):
        closers = check_slice.read_closers("# pylint: enable=protected-access, too-many-locals")
        self.assertEqual([(c.family, c.rules) for c in closers],
                         [("pylint", frozenset({"protected-access", "too-many-locals"}))])
        self.assertIsNone(check_slice.read_closers("# pylint: enable=all")[0].rules)

    def test_p1_an_unrelated_pylint_enable_does_not_hide_a_removed_one(self):
        self.assert_reported("src/p.py", PYLINT_NESTED, PYLINT_NESTED.replace("# pylint: enable=no-member\n", ""),
                             "pylint: enable")

    def test_p2_a_pylint_pair_removed_beside_a_module_disable_of_another_rule_is_clean(self):
        before = ("# pylint: disable=invalid-name\nimport os\n# pylint: disable=no-member\nx = os.a\n"
                  "# pylint: enable=no-member\ny = 1\n")
        self.assert_clean("src/p.py", before, "# pylint: disable=invalid-name\nimport os\nx = os.a\ny = 1\n")

    def test_a_closer_restyled_in_place_with_the_next_line_edited_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nfoo(1)\nbar()\n"
        self.assert_clean("src/f.js", before, "/* eslint-disable no-console */\nconsole.log(1)\n"
                                              "// eslint-enable no-console\nfoo(2)\nbar()\n")

    def test_a_closer_restyled_in_place_with_the_next_line_unchanged_is_clean(self):
        before = "/* eslint-disable no-console */\nconsole.log(1)\n/* eslint-enable no-console */\nfoo(1)\nbar()\n"
        self.assert_clean("src/f.js", before, before.replace("/* eslint-enable no-console */",
                                                             "// eslint-enable no-console"))

    def test_an_opener_and_closer_on_one_line_close_in_the_order_written(self):
        top = "foo(); /* eslint-disable no-console */ console.log(0); /* eslint-enable no-console */\nx()\n"
        self.assert_clean("src/g.js", top + PAIR + TAIL, top + "console.log(1)\n" + TAIL)

    def test_a_closer_then_an_opener_on_one_line_leaves_it_open(self):
        top = "/* eslint-disable no-console */\n/* eslint-enable no-console */ x(); /* eslint-disable no-console */\n"
        before = top + "console.log(1)\n/* eslint-enable no-console */\n" + TAIL
        self.assert_reported("src/g.js", before, top + "console.log(1)\n" + TAIL, "eslint-enable")

    def test_every_closer_on_a_line_ends_its_rules(self):
        before = ("/* eslint-disable no-console, no-alert */\nalert(1)\n"
                  "/* eslint-enable no-alert */ /* eslint-enable no-console */\nx()\n" + PAIR + TAIL)
        after = ("/* eslint-disable no-console, no-alert */\nalert(1)\n"
                 "/* eslint-enable no-alert */ /* eslint-enable no-console */\nx()\nconsole.log(1)\n" + TAIL)
        self.assert_clean("src/h.js", before, after)

    def test_removing_a_line_of_two_closers_is_judged_on_each(self):
        before = ("/* eslint-disable no-console */\nconsole.log(1)\n"
                  "/* eslint-enable no-alert */ /* eslint-enable no-console */\n" + TAIL)
        self.assert_reported("src/h.js", before, "/* eslint-disable no-console */\nconsole.log(1)\n" + TAIL,
                             "eslint-enable")

    def test_an_opener_whose_details_cannot_be_read_stays_open(self):
        before = ("class A {\n#pragma warning disable CS0618 /* legacy */\n  void F() { Old(); }\n"
                  "#pragma warning restore CS0618\n  void G() { Old(); }\n}\n")
        self.assert_reported("src/A.cs", before, before.replace("#pragma warning restore CS0618\n", ""),
                             "#pragma warning restore")

    def test_a_numeric_pragma_code_is_its_cs_code(self):
        self.assertEqual(check_slice.parse_marker("#pragma warning disable 618, CA1062").rules,
                         frozenset({"CS0618", "CA1062"}))
        before = ("class A {\n#pragma warning disable 618\n  void F() { Old(); }\n#pragma warning restore CS0618\n"
                  "  void G() { Old(); }\n}\n")
        self.assert_reported("src/A.cs", before, before.replace("#pragma warning restore CS0618\n", ""),
                             "#pragma warning restore")


class HookOnAnyTurnTest(unittest.TestCase):
    """T1: the Stop hook runs on every turn; with nothing approved to check it notes it and lets the session stop."""

    def test_the_hook_lets_a_turn_with_no_bundle_stop(self):
        r = Repo(None)
        r.write({"src/app.py": "x = 1\n"})
        code, _, err = run_main(r.root, ["--hook"], stdin="{}")
        self.assertEqual(code, 0)
        self.assertIn("no bundle or brief found", err)

    def test_ci_still_fails_with_no_bundle(self):
        r = Repo(None)
        r.commit("s1", {"src/app.py": "x = 1\n"})
        self.assertEqual(run_main(r.root, ["--base", "main"])[0], 1)

    def test_the_block_message_speaks_to_any_role(self):
        r = Repo(bundle())
        r.write({"web/page.ts": "x\n"})
        code, _, err = run_main(r.root, ["--hook"], stdin="{}")
        self.assertEqual(code, 2)
        self.assertIn("check_slice: if you are building this slice, fix these or stop it (STATUS stopped); "
                      "otherwise report them.", err)


class ContractPinScopeTest(unittest.TestCase):
    """Plan 21 (F9): moving a vendored contract pin is planned work, inside a bundle whose MAY CHANGE names it."""

    PIN = {"contracts/orders-api/openapi.yaml": "openapi: 3.0.3\n", "contracts/orders-api/SOURCE": "tag: api-v1.1.0\n"}

    def test_a_pin_moved_outside_may_change_is_a_problem(self):
        r = Repo(bundle())
        r.commit("move the pin", self.PIN)
        self.assertEqual(r.check()[0], ["contracts/orders-api/SOURCE: outside every bundle's MAY CHANGE",
                                        "contracts/orders-api/openapi.yaml: outside every bundle's MAY CHANGE"])

    def test_a_pin_moved_in_its_own_slice_is_clean(self):
        r = Repo(bundle(may="src/**, tests/**, contracts/orders-api/**"))
        r.commit("move the pin", self.PIN)
        self.assertEqual(r.check(), ([], []))

    def test_a_pin_named_in_must_not_stays_out(self):
        r = Repo(bundle(may="**", must_not="AGENTS.md, contracts/**"))
        r.commit("move the pin", self.PIN)
        self.assertIn("contracts/orders-api/SOURCE: changed, but a bundle's MUST NOT names it", r.check()[0])


if __name__ == "__main__":
    unittest.main()
