# tests/unit/test_onecheck_integrity.py
import unittest

from aidlc.checks import onecheck
from aidlc.checks.onecheck import FAIL, OK, local_context, protected_test_changes, run_check
from aidlc.repo import load_config
from tests.helpers import git
from tests.unit.test_guard import GuardEnv
from tests.unit.test_onecheck import installed

TEST = "test/app.test.ts"
BASE_TEST = "it('a', () => { expect(f()).toBe(1); });\n"


class IntegrityStepsTest(unittest.TestCase):
    def setUp(self):
        self.env = GuardEnv().__enter__()
        self.repo, self.root = installed({}, [], files={TEST: BASE_TEST,
                                                         "test/protected-exceptions.txt": "# exceptions\n"})
        self.env.write_scope(self.root, ["**"])

    def tearDown(self):
        self.repo.__exit__(None, None, None)
        self.env.__exit__(None, None, None)

    def step(self, name):
        ctx = local_context(self.root, load_config(self.root))
        fn = dict(onecheck.BUILTINS)[name]
        return run_check(ctx, builtins=[(name, fn)]).steps[-1]

    def test_builtins_order(self):
        names = [n for n, _ in onecheck.BUILTINS]
        self.assertEqual(names[:2], ["scope", "protected-tests"])
        self.assertEqual(names[-2:], ["context-drift", "secrets"])

    def test_added_test_lines_pass(self):
        (self.root / TEST).write_text(BASE_TEST + "it('b', () => { expect(g()).toBe(2); });\n")
        self.assertEqual(self.step("protected-tests").status, OK)

    def test_changed_line_fails(self):
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")
        step = self.step("protected-tests")
        self.assertEqual(step.status, FAIL)
        self.assertIn(f"1 existing line(s) changed or removed: {TEST}", step.detail)

    def test_deleted_test_fails(self):
        (self.root / TEST).unlink()
        step = self.step("protected-tests")
        self.assertEqual(step.status, FAIL)
        self.assertIn(f"deleted or renamed: {TEST}", step.detail)

    def test_renamed_test_fails(self):
        git(self.root, "mv", TEST, "test/b.test.ts")
        self.assertIn(f"deleted or renamed: {TEST}", self.step("protected-tests").detail)

    def test_committed_weakening_on_the_branch_still_fails(self):
        (self.root / TEST).write_text("it('a', () => { expect(true).toBe(true); });\n")
        git(self.root, "commit", "-qam", "weaken")
        self.assertEqual(self.step("protected-tests").status, FAIL)

    def test_exception_added_by_this_change_excuses_the_file(self):
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")
        with (self.root / "test/protected-exceptions.txt").open("a") as fh:
            fh.write(f"{TEST} spec:1.7.0 AC4 changed by the approved spec\n")
        self.assertEqual(self.step("protected-tests").status, OK)

    def test_exception_already_on_the_base_excuses_nothing(self):
        git(self.root, "checkout", "-q", "main")
        with (self.root / "test/protected-exceptions.txt").open("a") as fh:
            fh.write(f"{TEST} test-quality old reason\n")
        git(self.root, "commit", "-qam", "old exception")
        git(self.root, "checkout", "-q", "feat/SHIP-1-x")
        git(self.root, "merge", "-q", "main")
        self.env.write_scope(self.root, ["**"])
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")
        self.assertEqual(self.step("protected-tests").status, FAIL)

    def test_malformed_exception_line_excuses_nothing(self):
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")
        with (self.root / "test/protected-exceptions.txt").open("a") as fh:
            fh.write(f"{TEST} because\n")
        self.assertEqual(self.step("protected-tests").status, FAIL)

    def test_protected_test_changes_lists_changed_existing_files(self):
        (self.root / TEST).write_text(BASE_TEST + "it('b', () => {});\n")
        problems, changed = protected_test_changes(self.root, git(self.root, "merge-base", "main", "HEAD"))
        self.assertEqual((problems, changed), ([], [TEST]))

    def test_test_file_replaced_by_a_symlink_fails(self):
        (self.root / TEST).unlink()
        (self.root / TEST).symlink_to("../src/app.txt")
        step = self.step("protected-tests")
        self.assertEqual(step.status, FAIL)
        self.assertIn(f"deleted or replaced: {TEST}", step.detail)

    def test_steering_files_are_not_judged_as_tests(self):
        git(self.root, "checkout", "-q", "main")                 # the file must exist at the base
        (self.root / onecheck.ALLOWED_SKIPS).write_text("a skip # reason\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "allow")
        git(self.root, "checkout", "-q", "feat/SHIP-1-x")
        git(self.root, "merge", "-q", "main")
        self.env.write_scope(self.root, ["**"])
        (self.root / onecheck.ALLOWED_SKIPS).write_text("")      # an existing line removed: status M
        self.assertEqual(self.step("protected-tests").status, OK)

    def test_parser_is_not_blinded_by_a_plus_plus_line(self):
        patch = ("diff --git a/src/x.py b/src/x.py\n--- a/src/x.py\n+++ b/src/x.py\n@@ -0,0 +1,2 @@\n"
                 "+++ hide the rest\n+AKIAABCDEFGHIJKLMNOP\n")
        self.assertEqual(onecheck.added_lines_by_file(patch),
                         {"src/x.py": ["++ hide the rest", "AKIAABCDEFGHIJKLMNOP"]})

    def test_parser_strips_the_tab_git_adds_to_names_with_spaces(self):
        patch = "diff --git a/a b.txt b/a b.txt\n--- a/a b.txt\t\n+++ b/a b.txt\t\n@@ -0,0 +1 @@\n+x\n"
        self.assertEqual(onecheck.added_lines_by_file(patch), {"a b.txt": ["x"]})

    def test_secret_after_a_plus_plus_line_is_found(self):
        (self.root / "src/app.txt").write_text("a\n++ hide\nAKIAABCDEFGHIJKLMNOP\n")
        self.assertEqual(self.step("secrets").status, FAIL)

    def test_objects_mode_finds_a_secret_added_then_removed(self):
        (self.root / "src/app.txt").write_text("a\nAKIAABCDEFGHIJKLMNOP\n")
        git(self.root, "commit", "-qam", "oops")
        (self.root / "src/app.txt").write_text("a\n")
        git(self.root, "commit", "-qam", "remove it again")
        ctx = local_context(self.root, load_config(self.root))
        ctx.head = git(self.root, "rev-parse", "HEAD")
        step = run_check(ctx, builtins=[("secrets", onecheck.step_secrets)]).steps[-1]
        self.assertEqual(step.status, FAIL)
        self.assertIn("src/app.txt", step.detail)

    def test_objects_mode_protected_tests_ignore_the_working_tree(self):
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")   # uncommitted
        ctx = local_context(self.root, load_config(self.root))
        ctx.head = git(self.root, "rev-parse", "HEAD")
        step = run_check(ctx, builtins=[("protected-tests", onecheck.step_protected_tests)]).steps[-1]
        self.assertEqual(step.status, OK)

    def test_secret_in_added_line_fails_without_printing_it(self):
        (self.root / "src/app.txt").write_text("a\napi_key = \"sk9f8a7d6s5a4f3d2s1a\"\n")
        step = self.step("secrets")
        self.assertEqual(step.status, FAIL)
        self.assertIn("src/app.txt", step.detail)
        self.assertNotIn("sk9f8a7d6s5a4f3d2s1a", step.detail)

    def test_secret_in_untracked_file_fails(self):
        (self.root / "src/new.env.txt").write_text("AKIAABCDEFGHIJKLMNOP\n")
        self.assertIn("src/new.env.txt", self.step("secrets").detail)

    def test_ordinary_code_passes(self):
        (self.root / "src/app.txt").write_text("a\nconst token = getToken();\npassword: string;\n")
        self.assertEqual(self.step("secrets").status, OK)

    def test_binary_untracked_file_is_not_scanned(self):
        (self.root / "src/logo.bin").write_bytes(b"\x00\x01AKIAABCDEFGHIJKLMNOP")
        self.assertEqual(self.step("secrets").status, OK)

    def test_large_untracked_file_fails_closed(self):
        (self.root / "src/big.txt").write_text("x" * (onecheck.MAX_SCAN_BYTES + 1))
        step = self.step("secrets")
        self.assertEqual(step.status, FAIL)
        self.assertIn("too large to scan", step.detail)


KEY = "AKIAABCDEFGHIJKLMNOP"


class IntegrityBypassTest(IntegrityStepsTest):
    """Fix round 1: bypasses found in review. Inherits setUp and step(); its tests re-run harmlessly."""

    def objects_secrets(self):
        ctx = local_context(self.root, load_config(self.root))
        ctx.head = git(self.root, "rev-parse", "HEAD")
        return run_check(ctx, builtins=[("secrets", onecheck.step_secrets)]).steps[-1]

    def test_parser_splits_on_newline_only(self):
        for sep in ("\f", "\v", "\x1c", "\x85", " ", " ", "\r"):
            patch = (f"diff --git a/s.txt b/s.txt\n--- a/s.txt\n+++ b/s.txt\n@@ -0,0 +1,2 @@\n"
                     f"+x{sep}diff --git a/z b/z\n+{KEY}\n")
            self.assertEqual(onecheck.added_lines_by_file(patch),
                             {"s.txt": [f"x{sep}diff --git a/z b/z", KEY]}, repr(sep))

    def test_separator_characters_do_not_hide_a_secret(self):
        for sep in ("\f", " ", "\r"):
            (self.root / "src/app.txt").write_text(f"a\nx{sep}diff --git a/z b/z\n{KEY}\n", encoding="utf-8", newline="")
            self.assertEqual(self.step("secrets").status, FAIL, repr(sep))

    def test_diff_attribute_does_not_hide_a_secret(self):
        (self.root / ".gitattributes").write_text("g.txt -diff\n")
        (self.root / "g.txt").write_text(KEY + "\n")
        git(self.root, "add", "-A")
        self.assertIn("g.txt", self.step("secrets").detail)
        git(self.root, "commit", "-qm", "attr")
        step = self.objects_secrets()
        self.assertEqual(step.status, FAIL)
        self.assertIn("g.txt", step.detail)

    def test_evil_merge_secret_is_found_in_objects_mode(self):
        git(self.root, "checkout", "-q", "-b", "side")
        (self.root / "m.txt").write_text("side\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "side")
        git(self.root, "checkout", "-q", "feat/SHIP-1-x")
        (self.root / "m.txt").write_text("mine\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "mine")
        subprocess_merge = __import__("subprocess").run(["git", "merge", "-q", "side"], cwd=self.root,
                                                        capture_output=True)
        self.assertNotEqual(subprocess_merge.returncode, 0)
        (self.root / "m.txt").write_text(KEY + "\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "merge")
        step = self.objects_secrets()
        self.assertEqual(step.status, FAIL)
        self.assertIn("m.txt", step.detail)

    def test_combined_diff_headers_are_sections(self):
        patch = "diff --cc m.txt\nindex 1,2..3\n--- a/m.txt\n+++ b/m.txt\n@@@ -1,1 -1,1 +1,1 @@@\n++" + KEY + "\n"
        self.assertEqual(onecheck.added_lines_by_file(patch), {"m.txt": ["+" + KEY]})   # new against both parents

    def test_noprefix_config_does_not_break_exceptions(self):
        git(self.root, "config", "diff.noprefix", "true")
        (self.root / TEST).write_text("it('a', () => { expect(f()).toBe(2); });\n")
        with (self.root / "test/protected-exceptions.txt").open("a") as fh:
            fh.write(f"{TEST} spec:1.7.0 AC4 changed by the approved spec\n")
        self.assertEqual(self.step("protected-tests").status, OK)

    def test_binary_test_file_change_is_named_as_binary(self):
        git(self.root, "checkout", "-q", "main")
        (self.root / "test/img.test.bin").write_bytes(b"\x00\x01")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-qm", "bin")
        git(self.root, "checkout", "-q", "feat/SHIP-1-x")
        git(self.root, "merge", "-q", "main")
        self.env.write_scope(self.root, ["**"])
        (self.root / "test/img.test.bin").write_bytes(b"\x00\x02")
        detail = self.step("protected-tests").detail
        self.assertIn("binary test file changed: test/img.test.bin", detail)
