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
        r = Repo(bundle())
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


if __name__ == "__main__":
    unittest.main()
