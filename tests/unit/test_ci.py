import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest import mock

import yaml

from aidlc import ci, sandbox
from aidlc.repo import init_repo
from tests.helpers import TempRepo, git, run_cli

PY = sys.executable
APP = "def value():\n    return 1\n"
TEST_APP = ("import unittest\nfrom app import value\n\n\nclass AppTest(unittest.TestCase):\n"
            "    def test_value(self):\n        self.assertEqual(value(), 1)\n")
# A tiny test runner that writes a JUnit report, as a real runner's reporter would.
RUNNER = '''import sys, unittest
from pathlib import Path
from xml.sax.saxutils import quoteattr
sys.path.insert(0, "src")
cases = []
class R(unittest.TextTestResult):
    def addSuccess(self, t): super().addSuccess(t); cases.append((t.id(), ""))
    def addFailure(self, t, e): super().addFailure(t, e); cases.append((t.id(), "<failure/>"))
    def addError(self, t, e): super().addError(t, e); cases.append((t.id(), "<error/>"))
    def addSkip(self, t, r): super().addSkip(t, r); cases.append((t.id(), "<skipped/>"))
suite = unittest.defaultTestLoader.discover("test", pattern="test_*.py", top_level_dir="test")
result = unittest.TextTestRunner(resultclass=R, verbosity=0).run(suite)
Path(".check").mkdir(exist_ok=True)
body = "".join(f"<testcase name={quoteattr(n)}>{x}</testcase>" for n, x in cases)
Path(".check/junit.xml").write_text(f"<testsuite>{body}</testsuite>")
sys.exit(0 if result.wasSuccessful() else 1)
'''
BRANCH = "feat/SHIP-1-x"
NEEDS_SANDBOX = unittest.skipUnless(sandbox.available(), "bubblewrap cannot start a sandbox here")


def stub_conftest(directory: Path) -> None:
    """A conftest stand-in: one passing result for the namespace it is asked about (Task 8 adds the
    config-policy step, which requires that each namespace evaluated rules)."""
    path = directory / "conftest"
    path.write_text(f"#!{PY}\nimport json, sys\nns = sys.argv[sys.argv.index('--namespace') + 1]\n"
                    "print(json.dumps([{'filename': sys.argv[2], 'namespace': ns, 'successes': 1, "
                    "'failures': [], 'warnings': []}]))\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class CiRepo:
    """An installed, rendered repository: tests on main, an approved bundle, and a task branch."""

    def __enter__(self):
        self.tools = tempfile.TemporaryDirectory()
        stub_conftest(Path(self.tools.name))
        self.home = tempfile.TemporaryDirectory()          # render records the trusted base here
        self.env = mock.patch.dict(os.environ, {"AIDLC_TOOLS_DIR": self.tools.name,
                                                "AIDLC_HOME_DIR": self.home.name})
        self.env.start()
        self.repo = TempRepo({"src/app.py": APP, "test/test_app.py": TEST_APP, "test/run.py": RUNNER,
                              "plans/b.md": "# bundle\nMAY CHANGE: src/**, test/**\n"})
        root = self.root = self.repo.__enter__()
        init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 19))
        cfg_path = root / ".aidlc/config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())
        cfg.update({"commands": {"test": f'"{PY}" test/run.py'}, "check_steps": ["test"],
                    "test_reports": [".check/junit.xml"]})
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        code, out, _ = run_cli("render", "--tool", "claude-code", str(root))   # Task 8's policy step reads it
        assert code == 0, out
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "install")
        # The codebase map's "Last verified ... against commit `<sha>`" must name a real commit,
        # or context drift fails (as tests/integration/test_procedure_a.py does).
        cmap = root / "docs/codebase-map.md"
        cmap.write_text(cmap.read_text().replace("<sha>", git(root, "rev-parse", "--short", "HEAD")))
        git(root, "commit", "-qam", "verify the map")
        bundle_commit = git(root, "rev-parse", "HEAD")
        with (root / "plans/approved-bundles.txt").open("a") as fh:
            fh.write(f"{BRANCH} {bundle_commit}:plans/b.md lead 2026-10-19\n")
        git(root, "commit", "-qam", "approve bundle")
        git(root, "checkout", "-q", "-b", BRANCH)
        # A person generates the scope; local aidlc ci judges against the base it pins (final review C1).
        code, out, err = run_cli("scope", "--branch", BRANCH, "--repo", str(root))
        assert code == 0, out + err
        return self

    def rescope(self, branch=BRANCH):
        """A person re-runs aidlc scope after the base branch moved: the scope file, written as aidlc
        scope writes it (some tests break the working tree's config, which aidlc scope reads)."""
        from aidlc.scope import default_scope_path, write_scope
        write_scope(["src/**", "test/**"], default_scope_path(self.root, branch), base=git(self.root, "rev-parse", "main"))

    def __exit__(self, *exc):
        self.repo.__exit__(None, None, None)
        self.env.stop()
        self.tools.cleanup()
        self.home.cleanup()

    def commit(self, files: dict[str, str], message="change"):
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", message)

    def records(self):
        """Records, oldest first, by the time and sequence written inside them."""
        d = self.root / ci.RECORDS
        found = [(json.loads(p.read_text()), p) for p in d.glob("*.json")] if d.is_dir() else []
        return [p for _, p in sorted(found, key=lambda rp: (rp[0]["time"], rp[1].name))]

    def worktrees(self):
        return [l for l in git(self.root, "worktree", "list", "--porcelain").splitlines() if l.startswith("worktree ")]


def steps(record):
    return {s["name"]: s for s in record["steps"]}


def last(r):
    return json.loads(r.records()[-1].read_text())


@NEEDS_SANDBOX
class CiTest(unittest.TestCase):
    def test_passing_branch_records_simulated_ci_and_cleans_up(self):
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n"})
            status_before = git(r.root, "status", "--porcelain")
            code, out, _ = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 0, out)
            record = last(r)
            self.assertEqual((record["label"], record["result"], record["branch"], record["sandbox"]),
                             ("simulated-ci", "PASS", BRANCH, "bwrap"))
            self.assertTrue(ci.verify_record(record))
            self.assertFalse(record["merge_ready"])
            self.assertIn("no approval record", record["merge_ready_reason"])
            self.assertEqual(len(r.worktrees()), 1)
            self.assertEqual(git(r.root, "status", "--porcelain"), status_before)
            self.assertIn("ci  merge-ready no", out)
            self.assertIn("simulated-ci", out)

    def test_judges_run_before_the_change_code(self):
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n"})
            run_cli("ci", "--repo", str(r.root))
            names = [s["name"] for s in last(r)["steps"]]
            self.assertLess(max(names.index(n) for n in ("scope", "protected-tests", "secrets", "context-drift")),
                            names.index("test"))
            self.assertEqual(names[-2:], ["skips", "protected-rerun"])

    def test_tests_that_try_to_rewrite_their_judges_change_nothing(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as scratch_home, \
                mock.patch.dict(os.environ, {"HOME": scratch_home}):            # never the real home
            (Path(scratch_home) / ".aidlc").mkdir()                             # a target that exists on the host
            marker = f"aidlc-ci-hostile-{uuid.uuid4().hex}"
            # The hostile code reports each attempt, then fails the run so the tail of its log, with the
            # report, is printed: proof that it ran (minor 8), whatever it managed to write.
            hostile = TEST_APP + ("\nimport pathlib, os, sys\nseen = []\n"
                                  f"for label, p in [('home', os.path.expanduser('~/.aidlc/{marker}')),\n"
                                  "                 ('trusted', '../trusted/plans/approved-merges.txt'),\n"
                                  f"                 ('records', '{r.root}/.aidlc/ci-records/forged.json')]:\n"
                                  "    try:\n        pathlib.Path(p).write_text('forged')\n        seen.append(label + ':wrote')\n"
                                  "    except OSError:\n        seen.append(label + ':denied')\n"
                                  f"print('HOSTILE-RAN {marker} ' + ' '.join(seen), flush=True)\nos._exit(3)\n")
            r.commit({"test/test_app.py": hostile})
            _, out, _ = run_cli("ci", "--repo", str(r.root))
            self.assertIn(f"HOSTILE-RAN {marker} home:denied trusted:denied records:denied", out)
            self.assertEqual(steps(last(r))["test"]["status"], "FAIL")
            self.assertFalse(Path(os.path.expanduser(f"~/.aidlc/{marker}")).exists())
            self.assertFalse((r.root / ci.RECORDS / "forged.json").exists())
            self.assertFalse(last(r)["merge_ready"])

    def test_a_tracked_check_dir_is_refused(self):
        with CiRepo() as r:
            victim = r.root.parent / "victim.txt"
            victim.write_text("precious\n")
            (r.root / ".check").mkdir(exist_ok=True)
            (r.root / ".check" / ".gitignore").unlink(missing_ok=True)
            (r.root / ".check" / ".gitignore").symlink_to(victim)
            git(r.root, "add", "-f", ".check/.gitignore")
            git(r.root, "commit", "-qm", "plant")
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("under .check/", err)
            self.assertEqual(victim.read_text(), "precious\n")
            self.assertEqual(len(r.worktrees()), 1)

    def test_tampered_record_fails_verification(self):
        with CiRepo() as r:
            run_cli("ci", "--repo", str(r.root))
            record = last(r)
            record["result"] = "PASS" if record["result"] == "FAIL" else "FAIL"
            self.assertFalse(ci.verify_record(record))

    def test_merge_ready_needs_an_approval_for_this_exact_head(self):
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n"})
            head = git(r.root, "rev-parse", "HEAD")
            git(r.root, "checkout", "-q", "main")
            with (r.root / ci.MERGES).open("a") as fh:
                fh.write(f"{BRANCH} {head} lead 2026-10-19\n")
            git(r.root, "add", "-A")
            git(r.root, "commit", "-q", "-m", "approve merge")
            git(r.root, "checkout", "-q", BRANCH)
            r.rescope()                                   # main moved: a person re-scopes
            run_cli("ci", "--repo", str(r.root))
            self.assertTrue(last(r)["merge_ready"])
            r.commit({"src/extra.py": "X = 2\n"}, "new commit after approval")
            run_cli("ci", "--repo", str(r.root))
            self.assertFalse(last(r)["merge_ready"])

    def test_the_base_branch_configuration_judges_the_change(self):
        with CiRepo() as r:
            cfg_path = r.root / ".aidlc/config.yaml"
            cfg = yaml.safe_load(cfg_path.read_text())
            cfg["commands"]["test"] = "true"                       # the branch tries to neuter its tests
            r.commit({".aidlc/config.yaml": yaml.safe_dump(cfg), "src/app.py": "def value():\n    return 2\n"})
            code, _, _ = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 1)
            self.assertEqual(steps(last(r))["test"]["status"], "FAIL")

    def test_weakened_existing_test_fails(self):
        with CiRepo() as r:
            r.commit({"test/test_app.py": TEST_APP.replace("assertEqual(value(), 1)", "assertTrue(True)")})
            run_cli("ci", "--repo", str(r.root))
            self.assertEqual(steps(last(r))["protected-tests"]["status"], "FAIL")

    def test_added_line_that_hides_a_regression_is_caught_by_the_rerun(self):
        with CiRepo() as r:
            hidden = TEST_APP.replace("from app import value\n", "from app import value\nvalue = lambda: 1\n")
            r.commit({"src/app.py": "def value():\n    return 2\n", "test/test_app.py": hidden})
            code, _, _ = run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual(code, 1)
            self.assertEqual(s["protected-tests"]["status"], "ok")      # only lines were added
            self.assertEqual(s["protected-rerun"]["status"], "FAIL")    # main's test fails on the new code

    def test_the_change_cannot_declare_its_own_skips(self):
        with CiRepo() as r:
            skipping = TEST_APP.replace("    def test_value", "    @unittest.skip('later')\n    def test_value")
            r.commit({"test/test_app.py": skipping,
                      "test/allowed-skips.txt": "test_app.AppTest.test_value # the change says so\n"})
            run_cli("ci", "--repo", str(r.root))
            self.assertEqual(steps(last(r))["skips"]["status"], "FAIL")

    def test_unapproved_branch_fails_scope(self):
        with CiRepo() as r:
            git(r.root, "checkout", "-q", "-b", "feat/SHIP-2-other")
            # A scope written before the approval was withdrawn: CI reads approvals from the base.
            from aidlc.scope import default_scope_path, write_scope
            write_scope(["src/**"], default_scope_path(r.root, "feat/SHIP-2-other"), base=git(r.root, "rev-parse", "main"))
            run_cli("ci", "--repo", str(r.root))
            scope = steps(last(r))["scope"]
            self.assertEqual(scope["status"], "FAIL")
            self.assertIn("no approved bundle", scope["detail"])

    def test_worktrees_are_removed_when_a_gate_raises(self):
        with CiRepo() as r:
            with mock.patch("aidlc.ci._run_phases", side_effect=RuntimeError("boom")):
                with self.assertRaises(RuntimeError):
                    ci.ci_local(r.root, BRANCH, None)
            self.assertEqual(len(r.worktrees()), 1)
            self.assertEqual(r.records(), [])

    def test_groups(self):
        with CiRepo() as r:
            run_cli("ci", "--repo", str(r.root), "--group", "scans")
            record = last(r)
            self.assertEqual(record["group"], "scans")
            self.assertEqual({s["name"] for s in record["steps"]} - {"config-policy"}, {"secrets"})
            self.assertFalse(record["merge_ready"])
            self.assertEqual([ci.group_of(s) for s in ("install", "build", "test", "scope", "secrets", "skips")],
                             ["compile", "compile", "check", "check", "scans", "check"])

    def test_github_mode(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as tmp:
            r.commit({"src/extra.py": "X = 1\n"})
            head_sha = git(r.root, "rev-parse", "HEAD")
            trusted, head, records = Path(tmp, "trusted"), Path(tmp, "pr"), Path(tmp, "records")
            git(r.root, "worktree", "add", "--detach", str(trusted), "main")
            git(r.root, "worktree", "add", "--detach", str(head), BRANCH)
            args = ["ci", "--trusted", str(trusted), "--head", str(head), "--branch", BRANCH,
                    "--head-sha", head_sha, "--records", str(records)]
            try:
                with mock.patch.dict(os.environ):
                    os.environ.pop("GITHUB_ACTIONS", None)
                    code, _, err = run_cli(*args)
                self.assertEqual(code, 2)
                self.assertIn("GITHUB_ACTIONS", err)                     # refused outside GitHub Actions
                with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
                    code, out, _ = run_cli(*args)
                    self.assertEqual(code, 0, out)
                    [path] = list(records.glob("*.json"))
                    self.assertEqual(json.loads(path.read_text())["label"], "simulated-ci")
                    code, _, err = run_cli(*args)                       # the records dir now exists
                    self.assertEqual(code, 2)
                    self.assertIn("must not exist", err)
                    code, _, err = run_cli(*args[:-4], "--head-sha", "a" * 40, "--records", str(Path(tmp, "r2")))
                    self.assertEqual(code, 2)
                    self.assertIn("is not the commit checked out", err)
            finally:
                git(r.root, "worktree", "remove", "--force", str(trusted))
                git(r.root, "worktree", "remove", "--force", str(head))


class CiWithoutSandboxTest(unittest.TestCase):
    def test_local_mode_requires_the_sandbox(self):
        with CiRepo() as r, mock.patch("aidlc.ci.available", return_value=False):
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("bubblewrap", err)
            self.assertEqual(len(r.worktrees()), 1)

    def test_usage_errors_exit_2(self):
        with CiRepo() as r:
            git(r.root, "checkout", "-q", "main")
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("not the base branch", err)
        with TempRepo({"a": "a\n"}) as root:
            code, _, err = run_cli("ci", "--repo", str(root))
            self.assertEqual(code, 2)
            self.assertIn("not an installed repository", err)

    def test_record_file_name_is_safe_and_unique(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        rec = {"branch": "feat/SHIP-1.x y", "head": "a" * 40, "time": "2026-10-19T10:00:00.123456+00:00"}
        first, second = ci.write_ci_record(d, rec), ci.write_ci_record(d, rec)
        self.assertRegex(first.name, r"^\d{8}T\d{12}Z-feat__SHIP-1\.x_y-a{12}(-\d+)?\.json$")
        self.assertNotEqual(first, second)
        self.assertEqual((d / ".gitignore").read_text(), "*\n")
        with self.assertRaises(FileExistsError):
            ci.write_ci_record(d, rec, fresh=True)


@NEEDS_SANDBOX
class CiOrderAndCleanupTest(unittest.TestCase):
    """Beyond the brief: the ordering rule pinned directly, and cleanup that survives a hostile change."""

    def test_no_git_reads_the_checkout_after_the_change_code_ran(self):
        import contextlib
        import io

        from aidlc.checks import onecheck
        with CiRepo() as r:
            r.commit({"src/app.py": "def value():\n    return 1  # extended\n",
                      "test/test_app.py": TEST_APP + "\n# one more line\n"})       # protected re-run is exercised
            calls, ran = [], []
            real_git, real_blob, real_run = onecheck.git, ci._blob, ci.run_command

            def spy_git(repo, *args):
                calls.append((Path(repo), bool(ran), args[0]))
                return real_git(repo, *args)

            def spy_blob(repo, *args):
                calls.append((Path(repo), bool(ran), "cat-file"))
                return real_blob(repo, *args)

            def spy_run(*args, **kwargs):
                ran.append(True)
                return real_run(*args, **kwargs)

            with mock.patch.object(onecheck, "git", spy_git), mock.patch.object(ci, "git", spy_git), \
                    mock.patch.object(ci, "_blob", spy_blob), mock.patch.object(ci, "run_command", spy_run), \
                    contextlib.redirect_stdout(io.StringIO()):
                ci.ci_local(r.root, BRANCH, None)
            self.assertTrue(ran)
            self.assertIn("cat-file", [name for _, _, name in calls])                # base versions were read
            work = {repo for repo, _, _ in calls if repo.name in ("head", "rerun")}
            self.assertEqual(len(work), 1)                                       # git never needs cwd=rerun
            self.assertEqual([c for c in calls if c[0] in work and c[1]], [])        # nothing after the code ran
            self.assertEqual(steps(last(r))["protected-rerun"]["status"], "ok")

    def test_a_change_that_locks_its_directories_is_still_cleaned_up(self):
        with CiRepo() as r:
            hostile = TEST_APP + ("\nimport os\nos.makedirs('locked/inner', exist_ok=True)\n"
                                  "open('locked/inner/f', 'w').close()\nos.chmod('locked/inner', 0)\n"
                                  "os.chmod('locked', 0o500)\n")
            r.commit({"test/test_app.py": hostile})
            run_cli("ci", "--repo", str(r.root))
            self.assertEqual(len(r.worktrees()), 1)
            self.assertEqual(len(r.records()), 1)

    def test_github_mode_refuses_records_inside_the_pull_request_checkout(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as tmp:
            head_sha = git(r.root, "rev-parse", "HEAD")
            trusted, head = Path(tmp, "trusted"), Path(tmp, "pr")
            git(r.root, "worktree", "add", "--detach", str(trusted), "main")
            git(r.root, "worktree", "add", "--detach", str(head), BRANCH)
            try:
                with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
                    code, _, err = run_cli("ci", "--trusted", str(trusted), "--head", str(head), "--branch", BRANCH,
                                           "--head-sha", head_sha, "--records", str(head / "records"))
                self.assertEqual(code, 2)
                self.assertIn("outside the pull request checkout", err)
            finally:
                git(r.root, "worktree", "remove", "--force", str(trusted))
                git(r.root, "worktree", "remove", "--force", str(head))


class CiSandboxModeTest(unittest.TestCase):
    def test_auto_never_runs_the_change_code_unsandboxed(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as tmp:
            head_sha = git(r.root, "rev-parse", "HEAD")
            trusted, head = Path(tmp, "trusted"), Path(tmp, "pr")
            git(r.root, "worktree", "add", "--detach", str(trusted), "main")
            git(r.root, "worktree", "add", "--detach", str(head), BRANCH)
            args = ["ci", "--trusted", str(trusted), "--head", str(head), "--branch", BRANCH,
                    "--head-sha", head_sha, "--sandbox", "auto"]
            try:
                with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}), \
                        mock.patch("aidlc.ci.available", return_value=False):
                    code, _, err = run_cli(*args, "--group", "check", "--records", str(Path(tmp, "r1")))
                    self.assertEqual(code, 2)
                    self.assertIn("only for --group scans", err)
                    self.assertFalse(Path(tmp, "r1").exists())
                    code, out, _ = run_cli(*args, "--group", "scans", "--records", str(Path(tmp, "r2")))
                    self.assertEqual(code, 0, out)
                    [path] = list(Path(tmp, "r2").glob("*.json"))
                    self.assertEqual(json.loads(path.read_text())["sandbox"], "none")
            finally:
                git(r.root, "worktree", "remove", "--force", str(trusted))
                git(r.root, "worktree", "remove", "--force", str(head))

    def test_local_mode_refuses_sandbox_auto(self):
        with CiRepo() as r:
            code, _, err = run_cli("ci", "--repo", str(r.root), "--sandbox", "auto")
            self.assertEqual(code, 2)
            self.assertIn("GitHub mode only", err)


class CiRecordFileTest(unittest.TestCase):
    def test_a_planted_symlink_at_the_record_name_is_never_written_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            d, victim = Path(tmp, "records"), Path(tmp, "victim.txt")
            d.mkdir()
            victim.write_text("precious\n")
            rec = {"branch": "feat/x", "head": "b" * 40, "time": "2026-10-19T10:00:00.000001+00:00"}
            (d / "20261019T100000000001Z-feat__x-bbbbbbbbbbbb.json").symlink_to(victim)
            (d / ".gitignore").symlink_to(victim)
            with self.assertRaises(OSError):
                ci.write_ci_record(d, rec)
            (d / ".gitignore").unlink()
            path = ci.write_ci_record(d, rec)
            self.assertFalse(path.is_symlink())
            self.assertEqual(victim.read_text(), "precious\n")

    def test_a_symlinked_records_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            real, link = Path(tmp, "real"), Path(tmp, "link")
            real.mkdir()
            link.symlink_to(real)
            with self.assertRaises(ci.CiError):
                ci.write_ci_record(link, {"branch": "b", "head": "c" * 40, "time": "t"})
            self.assertEqual(list(real.iterdir()), [])


class ParseApprovalsTest(unittest.TestCase):
    def test_messages_and_line_rules(self):
        from aidlc.scope import ScopeError, ScopeUsageError, parse_approvals
        text = "# feat/a abc123:plans/x.md\nfeat/a abc123:plans/a.md lead 2026-10-19\nfeat/a def456:plans/b.md\n"
        self.assertEqual(parse_approvals(text, "feat/a", "main:plans/approved-bundles.txt"), "def456:plans/b.md")
        with self.assertRaises(ScopeError) as cm:
            parse_approvals(text, "feat/b", "main:plans/approved-bundles.txt")
        self.assertEqual(str(cm.exception), "no approved bundle for branch 'feat/b' in main:plans/approved-bundles.txt")
        with self.assertRaises(ScopeUsageError):
            parse_approvals("feat/a main:plans/a.md\n", "feat/a", "s")
        with self.assertRaises(ScopeError):                  # \f never starts a new line: still a comment
            parse_approvals("# note\ffeat/a abc123:plans/a.md\n", "feat/a", "s")


# ---- Task 6 fix round 1 ------------------------------------------------------------------------

def base_update(r, fn, files=None):
    """Change main's configuration (and files) and move the task branch onto it."""
    git(r.root, "checkout", "-q", "main")
    cfg_path = r.root / ".aidlc/config.yaml"
    cfg = yaml.safe_load(cfg_path.read_text())
    fn(cfg)
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    for rel, (text, mode) in (files or {}).items():
        (r.root / rel).write_text(text)
        (r.root / rel).chmod(mode)
    git(r.root, "add", "-A")
    git(r.root, "commit", "-qm", "base update")
    git(r.root, "branch", "-f", BRANCH, "main")
    git(r.root, "checkout", "-q", BRANCH)
    r.rescope()                                       # main moved: a person re-scopes


AKIA = "AKIA" + "ABCDEFGHIJKLMNOP"


class PinnedBaseTest(unittest.TestCase):
    def test_a_missing_base_record_exits_2(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            cliinfo.base_file(r.root).unlink()
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("the trusted record has no base branch for this repository; check out the base branch "
                          "and run aidlc render --trusted-base", err)
            self.assertEqual(len(r.worktrees()), 1)

    def test_a_malformed_base_record_exits_2(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            for body in ('{"base_branch": 5}', "{nope", "[]"):
                cliinfo.base_file(r.root).write_text(body)
                code, _, err = run_cli("ci", "--repo", str(r.root))
                self.assertEqual(code, 2, body)
                self.assertIn("aidlc render --trusted-base", err)

    def test_a_symlinked_base_record_is_neither_trusted_nor_written_through(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            victim = r.root.parent / f"victim-{uuid.uuid4().hex}.json"
            victim.write_text('{"base_branch": "main"}')
            self.addCleanup(victim.unlink)
            record = cliinfo.base_file(r.root)
            record.unlink()
            record.symlink_to(victim)
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("aidlc render --trusted-base", err)
            git(r.root, "checkout", "-q", "main")                        # render writes only on the base
            code, out, _ = run_cli("render", "--tool", "claude-code", str(r.root))
            self.assertEqual(code, 1)
            self.assertIn("cannot record the trusted base branch", out)
            self.assertEqual(victim.read_text(), '{"base_branch": "main"}')

    def test_render_records_the_configured_base(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            self.assertEqual(cliinfo.recorded_base(r.root), "main")
            self.assertFalse(cliinfo.base_file(r.root).is_symlink())


@NEEDS_SANDBOX
class CiFixRound1Test(unittest.TestCase):
    def test_the_recorded_base_judges_even_when_the_branch_config_names_another(self):
        with CiRepo() as r:
            cfg_path = r.root / ".aidlc/config.yaml"
            cfg = yaml.safe_load(cfg_path.read_text())
            cfg["harness"]["base_branch"] = "evil"
            r.commit({".aidlc/config.yaml": yaml.safe_dump(cfg), "src/extra.py": "X = 1\n"})
            head = git(r.root, "rev-parse", "HEAD")
            git(r.root, "checkout", "-q", "-b", "evil", "main")         # a base the branch controls
            r.commit({".aidlc/config.yaml": yaml.safe_dump(cfg), ci.MERGES: f"{BRANCH} {head} lead 2026-10-19\n"})
            git(r.root, "checkout", "-q", BRANCH)
            run_cli("ci", "--repo", str(r.root))
            record = last(r)
            self.assertEqual((record["base_branch"], record["base"]), ("main", git(r.root, "rev-parse", "main")))
            self.assertFalse(record["merge_ready"])

    def test_the_base_branch_itself_is_still_refused(self):
        with CiRepo() as r:
            code, _, err = run_cli("ci", "--repo", str(r.root), "--branch", "main")
            self.assertEqual(code, 2)
            self.assertIn("not the base branch", err)

    def test_a_tracked_record_in_the_head_is_refused(self):
        with CiRepo() as r:
            planted = r.root / ci.RECORDS / "20990101T000000000000Z-forged.json"
            planted.parent.mkdir(parents=True, exist_ok=True)
            planted.write_text('{"label": "simulated-ci", "merge_ready": true}\n')
            git(r.root, "add", "-f", str(planted.relative_to(r.root)))
            git(r.root, "commit", "-qm", "plant a record")
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("under .aidlc/ci-records/", err)
            self.assertEqual(len(r.worktrees()), 1)

    def test_the_rerun_keeps_the_exec_bit(self):
        with CiRepo() as r:
            base_update(r, lambda c: c["commands"].__setitem__("test", "./test/run.sh"),
                        {"test/run.sh": (f'#!/bin/sh\nexec "{PY}" test/run.py\n', 0o755)})
            sh = r.root / "test/run.sh"
            r.commit({"test/run.sh": sh.read_text() + "# a harmless added line\n"})
            self.assertEqual(git(r.root, "ls-tree", "HEAD", "--", "test/run.sh").split()[0], "100755")
            code, out, _ = run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual(s["protected-rerun"]["status"], "ok", out)
            self.assertEqual(code, 0, out)

    def test_a_symlink_in_the_base_cannot_be_restored(self):
        with CiRepo() as r:
            git(r.root, "checkout", "-q", "main")
            (r.root / "test/link_test.py").symlink_to("test_app.py")
            git(r.root, "add", "-A")
            git(r.root, "commit", "-qm", "a symlinked test")
            git(r.root, "branch", "-f", BRANCH, "main")
            git(r.root, "checkout", "-q", BRANCH)
            r.rescope()
            (r.root / "test/link_test.py").unlink()
            r.commit({"test/link_test.py": TEST_APP})              # T: a link becomes a file
            run_cli("ci", "--repo", str(r.root))
            rerun = steps(last(r))["protected-rerun"]
            self.assertEqual(rerun["status"], "FAIL")
            self.assertIn("test/link_test.py (mode 120000)", rerun["detail"])

    def test_an_added_test_that_monkeypatches_the_app_is_removed_for_the_rerun(self):
        with CiRepo() as r:
            r.commit({"src/app.py": "def value():\n    return 2\n",
                      "test/test_aaa.py": "import app\napp.value = lambda: 1\n"})
            code, _, _ = run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual((s["protected-tests"]["status"], s["test"]["status"]), ("ok", "ok"))
            self.assertEqual(s["protected-rerun"]["status"], "FAIL")
            self.assertIn("test/test_aaa.py", s["protected-rerun"]["detail"])
            self.assertEqual(code, 1)

    def test_a_deleted_base_test_is_restored_for_the_rerun(self):
        with CiRepo() as r:
            (r.root / "test/test_app.py").unlink()
            r.commit({"src/app.py": "def value():\n    return 2\n"})
            run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual(s["protected-tests"]["status"], "FAIL")
            self.assertEqual(s["protected-rerun"]["status"], "FAIL")      # main's test is back, and fails
            self.assertIn("test/test_app.py", s["protected-rerun"]["detail"])

    def test_an_honest_change_that_adds_a_passing_test_passes(self):
        with CiRepo() as r:
            more = "import unittest\nfrom app import value\n\n\nclass More(unittest.TestCase):\n" \
                   "    def test_more(self):\n        self.assertEqual(value() + 1, 2)\n"
            r.commit({"src/extra.py": "X = 1\n", "test/test_more.py": more})
            code, out, _ = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 0, out)
            self.assertEqual(steps(last(r))["protected-rerun"]["status"], "ok")

    def test_what_the_first_run_leaves_behind_does_not_reach_the_rerun(self):
        with CiRepo() as r:
            hostile = TEST_APP + "\nimport os\nos.makedirs('test/locked', exist_ok=True)\nos.chmod('test/locked', 0)\n"
            r.commit({"test/test_app.py": hostile})
            run_cli("ci", "--repo", str(r.root))
            self.assertEqual(steps(last(r))["protected-rerun"]["status"], "ok")

    def test_a_malformed_trusted_config_exits_2(self):
        for label, fn in (("check_steps", lambda c: c.__setitem__("check_steps", 5)),
                          ("profile", lambda c: c.__setitem__("profile", ["x"]))):
            with CiRepo() as r:
                base_update(r, fn)
                code, _, err = run_cli("ci", "--repo", str(r.root))
                self.assertEqual(code, 2, label)
                self.assertIn(label, err)
                self.assertEqual(len(r.worktrees()), 1)


class TextconvTest(unittest.TestCase):
    """A branch's .gitattributes picks a diff driver; the judges must read the real bytes."""

    def repo(self, files):
        from aidlc.repo import RepoConfig
        tmp = TempRepo({"src/a.py": "A = 1\n", "test/test_a.py": "assert 1 == 1\n"})
        root = tmp.__enter__()
        self.addCleanup(tmp.__exit__, None, None, None)
        git(root, "config", "diff.blind.textconv", "true")         # repo-local: prints nothing
        base = git(root, "rev-parse", "HEAD")
        git(root, "checkout", "-q", "-b", BRANCH)
        for rel, text in files.items():
            (root / rel).write_text(text)
        git(root, "add", "-A")
        git(root, "commit", "-qm", "change")
        config = RepoConfig("svc", "team", "generic", "purpose", {}, [], {}, harness={}, tool_names={})
        return root, base, git(root, "rev-parse", "HEAD"), config

    def test_secrets_are_found_in_both_modes(self):
        from aidlc.checks.onecheck import FAIL, CheckContext, step_secrets
        root, base, head, config = self.repo({"src/key.py": f'K = "{AKIA}"\n', ".gitattributes": "*.py diff=blind\n"})
        for mode_head in (None, head):
            ctx = CheckContext(repo=root, config=config, branch=BRANCH, base=base, scope=None, head=mode_head)
            self.assertEqual(step_secrets(ctx).status, FAIL, mode_head)

    def test_removed_test_lines_are_found_in_both_modes(self):
        from aidlc.checks.onecheck import protected_test_changes
        root, base, head, _ = self.repo({"test/test_a.py": "pass\n", ".gitattributes": "*.py diff=blind\n"})
        for mode_head in (None, head):
            problems, _ = protected_test_changes(root, base, mode_head)
            self.assertTrue(any("test/test_a.py" in p for p in problems), (mode_head, problems))


class PrintResultTest(unittest.TestCase):
    def test_control_characters_are_stripped(self):
        import contextlib
        import io

        from aidlc.checks.onecheck import FAIL, CheckResult, StepResult, print_result
        out = io.StringIO()
        step = StepResult("test", FAIL, "bad\x1b]0;title\x07 \x9b2J", ".check/test.log", ["\x1b[8mhidden\tok\x7f"])
        with contextlib.redirect_stdout(out):
            print_result(CheckResult([step]), Path("."))
        text = out.getvalue()
        for ch in ("\x1b", "\x07", "\x9b", "\x7f"):
            self.assertNotIn(ch, text)
        self.assertIn("hidden\tok", text)


class LiteralPathspecTest(unittest.TestCase):
    def test_a_test_file_named_like_a_glob_is_judged_by_its_own_lines(self):
        from aidlc.checks.onecheck import protected_test_changes
        with TempRepo({"test/X_test.py": "assert 1\n", "test/[X]_test.py": "assert 2\nassert 3\n"}) as root:
            base = git(root, "rev-parse", "HEAD")
            (root / "test/X_test.py").write_text("assert 1\nassert 4\n")         # only gains a line
            (root / "test/[X]_test.py").write_text("assert 2\n")                 # loses one
            git(root, "commit", "-qam", "change")
            problems, _ = protected_test_changes(root, base, git(root, "rev-parse", "HEAD"))
            self.assertIn("1 existing line(s) changed or removed: test/[X]_test.py", problems)


# ---- Task 6 fix round 2 ------------------------------------------------------------------------

def render(root, *extra):
    return run_cli("render", "--tool", "claude-code", *extra, str(root))


@NEEDS_SANDBOX
class RerunCheckoutTest(unittest.TestCase):
    def test_an_untracked_test_written_by_the_first_run_does_not_reach_the_rerun(self):     # review g1
        with CiRepo() as r:
            gen = ("import pathlib\npathlib.Path('test/test_aab.py').write_text('import app\\napp.value = lambda: 1\\n')\n"
                   "import app\napp.value = lambda: 1\n")
            r.commit({"src/app.py": "def value():\n    return 2\n", "test/test_aaa.py": gen})
            code, _, _ = run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual(s["test"]["status"], "ok")
            self.assertEqual(s["protected-rerun"]["status"], "FAIL")
            self.assertEqual(code, 1)

    def test_a_base_test_rewritten_by_the_first_run_does_not_reach_the_rerun(self):     # review g2
        with CiRepo() as r:
            neuter = ("import pathlib\npathlib.Path('test/test_app.py').write_text('import unittest\\n"
                      "class AppTest(unittest.TestCase):\\n    def test_value(self):\\n        pass\\n')\n")
            r.commit({"src/app.py": "def value():\n    return 2\n", "test/test_aaa.py": neuter})
            code, _, _ = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(steps(last(r))["protected-rerun"]["status"], "FAIL")
            self.assertEqual(code, 1)

    def test_no_test_change_means_no_rerun(self):                                       # review g3
        with CiRepo() as r:
            app = ("import pathlib\n_p = pathlib.Path('test/test_app.py')\n"
                   "_p.write_text('import unittest\\nclass AppTest(unittest.TestCase):\\n    def test_value(self):\\n"
                   "        pass\\n')\ndef value():\n    return 1\n")
            r.commit({"src/app.py": app})
            run_cli("ci", "--repo", str(r.root))
            rerun = steps(last(r))["protected-rerun"]
            self.assertEqual((rerun["status"], rerun["detail"]), ("ok", "no existing test file changed"))

    def test_a_rename_restores_the_base_name(self):
        with CiRepo() as r:
            git(r.root, "mv", "test/test_app.py", "test/test_app2.py")
            git(r.root, "commit", "-qm", "rename")
            run_cli("ci", "--repo", str(r.root))
            s = steps(last(r))
            self.assertEqual(s["protected-tests"]["status"], "FAIL")
            self.assertEqual((s["protected-rerun"]["status"], s["protected-rerun"]["detail"]), ("ok", ""))

    def test_a_committed_symlinked_parent_is_refused_and_nothing_is_written_through_it(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as victim:
            git(r.root, "checkout", "-q", "main")
            r.commit({"test/sub/test_sub.py": "X = 1\n"})
            git(r.root, "branch", "-f", BRANCH, "main")
            git(r.root, "checkout", "-q", BRANCH)
            r.rescope()
            git(r.root, "rm", "-q", "-r", "test/sub")
            (r.root / "test/sub").symlink_to(victim)
            git(r.root, "add", "test/sub")
            git(r.root, "commit", "-qm", "a dir becomes a link")
            run_cli("ci", "--repo", str(r.root))
            rerun = steps(last(r))["protected-rerun"]
            self.assertEqual(rerun["status"], "FAIL")
            self.assertIn("symlink", rerun["detail"])
            self.assertEqual(os.listdir(victim), [])

    def test_the_rerun_is_prepared_before_the_first_sandbox_and_never_shared(self):
        import contextlib
        import io
        import subprocess
        import types

        from aidlc.checks import onecheck
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n", "test/test_app.py": TEST_APP + "\n# one more line\n"})
            events = []
            real_prepare = ci._prepare_rerun

            def spy_prepare(*args, **kwargs):
                out = real_prepare(*args, **kwargs)
                events.append(("prepared", str(out.path)))
                return out

            def spy_popen(argv, *args, **kwargs):
                if isinstance(argv, list) and argv and argv[0].endswith("bwrap"):
                    events.append(("BWRAP-START", argv))
                return subprocess.Popen(argv, *args, **kwargs)

            fake = types.SimpleNamespace(**{k: getattr(subprocess, k) for k in dir(subprocess) if not k.startswith("__")})
            fake.Popen = spy_popen
            with mock.patch.object(ci, "_prepare_rerun", spy_prepare), mock.patch.object(onecheck, "subprocess", fake), \
                    contextlib.redirect_stdout(io.StringIO()):
                ci.ci_local(r.root, BRANCH, None)
            self.assertEqual(steps(last(r))["protected-rerun"]["status"], "ok")
            kinds = [e[0] for e in events]
            self.assertEqual(kinds[0], "prepared")
            rerun_path = events[0][1]
            starts = [argv for kind, argv in events if kind == "BWRAP-START"]
            first, rerun = starts[0], starts[-1]
            self.assertNotIn(rerun_path, " ".join(first))                    # the first run never sees rerun/
            self.assertIn(rerun_path, " ".join(rerun))
            chdir = lambda argv: argv[argv.index("--chdir") + 1]             # noqa: E731
            self.assertNotIn(chdir(first), " ".join(rerun))                  # nor the re-run the first run's tree
            homes = [argv[argv.index("--bind") + 1] for argv in (first, rerun)]
            self.assertNotEqual(homes[0], homes[1])                          # a fresh private home
            self.assertEqual(len(r.worktrees()), 1)


class TrustedBaseRenderTest(unittest.TestCase):
    def test_render_on_a_task_branch_never_repins_the_base(self):          # review probe13
        from aidlc import cliinfo
        with CiRepo() as r:
            cfg_path = r.root / ".aidlc/config.yaml"
            cfg = yaml.safe_load(cfg_path.read_text())
            cfg["harness"]["base_branch"] = "evil"
            r.commit({".aidlc/config.yaml": yaml.safe_dump(cfg)})
            git(r.root, "branch", "evil", "main")
            code, _, err = render(r.root)
            self.assertEqual(code, 0)
            self.assertEqual(cliinfo.recorded_base(r.root), "main")
            self.assertIn("aidlc render: warning: trusted base stays 'main'; to change it, check out the new base "
                          "and run aidlc render --trusted-base NAME", err)

    def test_a_first_render_on_a_task_branch_writes_no_record(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            cliinfo.base_file(r.root).unlink()
            code, _, err = render(r.root)
            self.assertEqual(code, 0)
            self.assertIsNone(cliinfo.recorded_base(r.root))
            self.assertIn("aidlc render: warning: no trusted base recorded; check out the base branch and run "
                          "aidlc render", err)

    def test_trusted_base_needs_that_branch_checked_out(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            git(r.root, "branch", "trunk", "main")
            code, _, err = render(r.root, "--trusted-base", "trunk")
            self.assertEqual(code, 2)
            self.assertIn("trunk", err)
            self.assertEqual(cliinfo.recorded_base(r.root), "main")

    def test_trusted_base_on_that_branch_updates_the_record(self):
        from aidlc import cliinfo
        with CiRepo() as r:
            git(r.root, "checkout", "-q", "-b", "trunk", "main")
            code, out, err = render(r.root, "--trusted-base", "trunk")
            self.assertEqual(code, 0, out + err)
            self.assertEqual(cliinfo.recorded_base(r.root), "trunk")

    def test_a_base_changed_on_the_base_branch_names_the_command(self):    # review probe13, case 1
        with CiRepo() as r:
            base_update(r, lambda c: c["harness"].__setitem__("base_branch", "trunk"))
            git(r.root, "branch", "trunk", "main")
            with mock.patch("aidlc.ci.available", return_value=True):
                code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn("check out 'trunk' and run aidlc render --trusted-base trunk", err)
            self.assertEqual(len(r.worktrees()), 1)


# ---- Final review fix wave ---------------------------------------------------------------------

def forge_base(r, merge_line: str) -> str:
    """What an agent shell can do with plumbing and one redirect (review probe p6): a commit on main
    that approves the merge, written straight to .git/refs/heads/main. No git command the guard denies."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    index = {**env, "GIT_INDEX_FILE": str(r.root.parent / f"agent-index-{uuid.uuid4().hex}")}

    def run(*args, env=env, stdin=None):
        import subprocess
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=agent", "-c",
                               "user.email=a@b", *args], cwd=r.root, env=env, input=stdin, capture_output=True,
                              text=True, check=True).stdout.strip()

    run("read-tree", "main", env=index)
    blob = run("hash-object", "-w", "--stdin", stdin=merge_line)
    run("update-index", "--add", "--cacheinfo", f"100644,{blob},{ci.MERGES}", env=index)
    forged = run("commit-tree", run("write-tree", env=index), "-p", "main", "-m", "approve")
    (r.root / ".git/refs/heads/main").write_text(forged + "\n")
    return forged


class CiPinnedScopeBaseTest(unittest.TestCase):
    """C1: local aidlc ci judges against the base commit pinned in the scope file, never the live ref."""

    def test_a_base_ref_moved_by_a_shell_write_exits_2_and_records_nothing(self):
        with CiRepo() as r, mock.patch("aidlc.ci.available", return_value=True):
            r.commit({"src/extra.py": "X = 1\n"})
            pinned = git(r.root, "rev-parse", "main")
            forged = forge_base(r, f"{BRANCH} {git(r.root, 'rev-parse', 'HEAD')} agent-forged 2026-10-20\n")
            code, out, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2, out + err)
            self.assertIn(f"the base branch moved since the scope was generated (scope base {pinned[:12]}, "
                          f"main now {forged[:12]}); a person must re-run aidlc scope", err)
            self.assertNotIn("merge-ready yes", out)
            self.assertEqual(r.records(), [])
            self.assertEqual(len(r.worktrees()), 1)

    def test_a_missing_scope_exits_2(self):
        from aidlc.scope import default_scope_path
        with CiRepo() as r, mock.patch("aidlc.ci.available", return_value=True):
            path = default_scope_path(r.root, BRANCH)
            path.chmod(0o644)
            path.unlink()
            code, _, err = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 2)
            self.assertIn(f"a person must run aidlc scope --branch {BRANCH}", err)
            self.assertEqual(r.records(), [])

    def test_a_scope_without_a_pinned_base_or_unreadable_exits_2(self):
        from aidlc.scope import default_scope_path
        with CiRepo() as r, mock.patch("aidlc.ci.available", return_value=True):
            path = default_scope_path(r.root, BRANCH)
            path.chmod(0o644)
            for body in (b"src/**\n", b"base: nope\nsrc/**\n", b"\xff\xfe base: x\n"):
                path.write_bytes(body)
                code, _, err = run_cli("ci", "--repo", str(r.root))
                self.assertEqual(code, 2, body)
                self.assertIn("aidlc scope --branch", err)
            self.assertEqual(r.records(), [])

    @NEEDS_SANDBOX
    def test_an_unmoved_base_runs_against_the_pinned_commit(self):
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n"})
            code, out, _ = run_cli("ci", "--repo", str(r.root))
            self.assertEqual(code, 0, out)
            self.assertEqual(last(r)["base"], git(r.root, "rev-parse", "main"))


class ApprovalRefTest(unittest.TestCase):
    """I1: in CI an approval must pin a full commit SHA that resolves to itself in the object store
    the change controls; a short one can be matched by a commit the change wrote (review probe p2)."""

    def test_only_a_full_sha_that_resolves_to_itself_is_accepted(self):
        from aidlc.scope import ScopeError
        with TempRepo({"plans/b.md": "MAY CHANGE: src/**\n"}) as root:
            sha = git(root, "rev-parse", "HEAD")
            git(root, "tag", "-a", "-m", "t", "approved")
            tag = git(root, "rev-parse", "approved")                 # a tag object, not the commit
            self.assertEqual(ci.verified_approval(root, f"{sha}:plans/b.md"), f"{sha}:plans/b.md")
            for ref, why in ((f"{sha[:6]}:plans/b.md", "not a full commit SHA"),
                             (f"{sha[:39]}:plans/b.md", "not a full commit SHA"),
                             (f"{'0' * 40}:plans/b.md", "does not resolve to that commit"),
                             (f"{'a' * 64}:plans/b.md", "does not resolve to that commit"),
                             (f"{tag}:plans/b.md", "does not resolve to that commit")):
                with self.assertRaises(ScopeError, msg=ref) as cm:
                    ci.verified_approval(root, ref)
                self.assertIn(why, str(cm.exception))

    @NEEDS_SANDBOX
    def test_a_short_approval_ref_fails_scope_in_ci_and_a_full_one_passes(self):
        with CiRepo() as r:
            r.commit({"src/extra.py": "X = 1\n"})
            run_cli("ci", "--repo", str(r.root))
            self.assertEqual(steps(last(r))["scope"]["status"], "ok")          # the fixture pins a full SHA
            git(r.root, "checkout", "-q", "main")
            approvals = r.root / ci.APPROVALS
            line = [l for l in approvals.read_text().splitlines() if l.startswith(BRANCH)][-1]
            sha = line.split()[1].split(":")[0]
            approvals.write_text(approvals.read_text().replace(line, line.replace(sha, sha[:7])))
            git(r.root, "commit", "-qam", "a short approval ref")
            git(r.root, "checkout", "-q", BRANCH)
            r.rescope()
            run_cli("ci", "--repo", str(r.root))
            scope = steps(last(r))["scope"]
            self.assertEqual(scope["status"], "FAIL")
            self.assertIn(f"the approval pins '{sha[:7]}', which is not a full commit SHA", scope["detail"])

    def test_local_scope_warns_on_a_short_ref(self):
        with TempRepo({"plans/b.md": "MAY CHANGE: src/**\n"}) as root, tempfile.TemporaryDirectory() as home:
            sha = git(root, "rev-parse", "HEAD")
            (root / "plans/approved-bundles.txt").write_text(f"feat/x {sha[:8]}:plans/b.md lead 2026-10-20\n")
            git(root, "add", "-A")
            git(root, "commit", "-qm", "approve")
            out_file = Path(home) / "x.scope"
            code, out, err = run_cli("scope", "--branch", "feat/x", "--repo", str(root), "--out", str(out_file))
            self.assertEqual(code, 0, out + err)
            self.assertIn(f"aidlc scope: warning: the approval pins the short commit '{sha[:8]}'; aidlc ci "
                          "requires the full SHA", err)
            code, out, err = run_cli("scope", "--branch", "feat/y", "--repo", str(root), "--out", str(out_file))
            self.assertNotIn("warning", err)


class ContextDriftLinksTest(unittest.TestCase):
    """I2b: context drift never reads a head file through a symlink or a non-regular file; review
    probe p3 put an excerpt of a host secret into a CI record that way."""

    SECRET = f"aidlc-host-secret-{uuid.uuid4().hex}"

    def drift(self, plant):
        from aidlc.checks.context_drift import check_context_drift
        from tests.unit.test_context_drift import TODAY, files, with_real_commit
        with TempRepo(files()) as root, tempfile.TemporaryDirectory() as host:
            with_real_commit(root)
            secret = Path(host) / "secret.md"
            secret.write_text(f"# {self.SECRET}\nOwner: x · Last verified: 2026-10-10, against commit abc1234\n"
                              f"`{self.SECRET}.md` `npm run {self.SECRET}` `make {self.SECRET}`\n"
                              f"{{\"scripts\": {{\"{self.SECRET}\": 1}}}}\n")
            (Path(host) / "dir").mkdir()
            (Path(host) / "dir" / "codebase-map.md").write_text(secret.read_text())
            (Path(host) / "dir" / "x.md").write_text(secret.read_text())
            plant(root, Path(host))
            return [str(f) for f in check_context_drift(root, TODAY)]

    def link(self, root, rel, target):
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if os.path.lexists(path):
            path.unlink() if not path.is_dir() or path.is_symlink() else shutil.rmtree(path)
        path.symlink_to(target)

    def test_every_file_the_judge_reads_is_refused_through_a_symlink(self):
        cases = {
            ".aidlc/config.yaml": lambda root, host: self.link(root, ".aidlc/config.yaml", host / "secret.md"),
            ".aidlc": lambda root, host: self.link(root, ".aidlc", host / "dir"),
            "AGENTS.md": lambda root, host: self.link(root, "AGENTS.md", host / "secret.md"),
            "CLAUDE.md": lambda root, host: self.link(root, "CLAUDE.md", host / "secret.md"),
            "docs/codebase-map.md": lambda root, host: self.link(root, "docs/codebase-map.md", host / "secret.md"),
            "docs": lambda root, host: self.link(root, "docs", host / "dir"),
            ".aidlc/rules/x.md": lambda root, host: self.link(root, ".aidlc/rules/x.md", host / "secret.md"),
            ".aidlc/rules": lambda root, host: self.link(root, ".aidlc/rules", host / "dir"),
            "package.json": lambda root, host: self.link(root, "package.json", host / "secret.md"),
            "Makefile": lambda root, host: self.link(root, "Makefile", host / "secret.md"),
        }
        for rel, plant in cases.items():
            with self.subTest(rel=rel):
                msgs = self.drift(plant)
                self.assertTrue(any(m.startswith(f"FAIL {rel}") and f"{rel} is a symlink" in m
                                    and "not follow" in m for m in msgs), msgs)
                self.assertFalse(any(self.SECRET in m for m in msgs), msgs)

    def test_a_fifo_is_not_a_regular_file_and_never_blocks(self):
        def plant(root, host):
            (root / "CLAUDE.md").unlink(missing_ok=True)
            os.mkfifo(root / "CLAUDE.md")
        msgs = self.drift(plant)
        self.assertTrue(any(m.startswith("FAIL CLAUDE.md") and "not a regular file" in m for m in msgs), msgs)

    @NEEDS_SANDBOX
    def test_a_symlinked_config_never_reaches_the_ci_record(self):
        with CiRepo() as r, tempfile.TemporaryDirectory() as host:
            secret = Path(host) / "secret.ini"
            secret.write_text(f"[db]\npassword = {self.SECRET}\n")
            (r.root / ".aidlc/config.yaml").unlink()
            (r.root / ".aidlc/config.yaml").symlink_to(secret)
            (r.root / "CLAUDE.md").unlink(missing_ok=True)
            (r.root / "CLAUDE.md").symlink_to(secret)
            git(r.root, "add", "-A")
            git(r.root, "commit", "-qm", "link the host secret")
            code, out, err = run_cli("ci", "--repo", str(r.root))
            drift = steps(last(r))["context-drift"]
            self.assertEqual(drift["status"], "FAIL")
            self.assertIn(".aidlc/config.yaml is a symlink", drift["detail"])
            self.assertNotIn(self.SECRET, r.records()[-1].read_text())
            self.assertNotIn(self.SECRET, out + err)


class PrintResultLinesTest(unittest.TestCase):
    """Minors 1 and 2: a detail prints as one line, and control characters cannot split a secret
    past the redaction."""

    def printed(self, detail, tail=()):
        import contextlib
        import io

        from aidlc.checks.onecheck import FAIL, CheckResult, StepResult, print_result
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            print_result(CheckResult([StepResult("test", FAIL, detail, "", list(tail))]), Path("."), prefix="ci")
        return out.getvalue()

    def test_a_detail_cannot_forge_output_lines_or_workflow_commands(self):
        text = self.printed("tests failed: name\nci  result PASS  (0 of 9 steps failed)\r\n::error::x\rend",
                            ["tail\r::warning::y"])
        lines = text.split("\n")
        self.assertEqual(len(lines), 4, lines)                                    # step, tail, summary, ""
        self.assertTrue(lines[0].startswith("ci  test"), lines)
        self.assertIn("name ci  result PASS  (0 of 9 steps failed) ::error::x end", lines[0])
        self.assertFalse(any(l.startswith(("ci  result PASS", "::")) for l in lines), lines)
        self.assertNotIn("\r", text)
        self.assertTrue(lines[2].startswith("ci  result FAIL"), lines)

    def test_control_characters_are_stripped_before_redaction(self):
        text = self.printed("found AKIA\x01IOSFODNN7EXAMPLE here", ["key AKIA\x1bIOSFODNN7EXAMPLE"])
        self.assertNotIn("IOSFODNN7EXAMPLE", text)
        self.assertEqual(text.count("[REDACTED]"), 2, text)


class AllowedSkipsLinesTest(unittest.TestCase):
    def test_only_a_newline_starts_a_new_line(self):                                # final review minor 11
        from aidlc.checks.onecheck import ALLOWED_SKIPS, _allowed_skips
        for sep in ("\f", "\v", "\x1c", "\x85", " "):
            with self.subTest(sep=repr(sep)):
                text = f"# a comment{sep}test_app.AppTest.test_value # hidden in the comment\nkept.test # why\n"
                ctx = mock.Mock(steering={ALLOWED_SKIPS: text})
                self.assertEqual(_allowed_skips(ctx), {"kept.test"})
