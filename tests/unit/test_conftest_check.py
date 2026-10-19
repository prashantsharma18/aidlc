import json
import os
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from aidlc.checks import conftest_check
from aidlc.checks.conftest_check import inputs, policy_data, run_conftest, verify_pack
from aidlc.repo import init_repo
from aidlc.tools import which_tool
from tests.helpers import TempRepo, run_cli


def fake(stdout="[]", code=0, stderr=""):
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, code, stdout, stderr)
    runner.calls = calls
    return runner


class Rendered:
    def __enter__(self):
        self.repo = TempRepo({"package.json": "{}\n"})
        self.root = self.repo.__enter__()
        init_repo(self.root, "svc", "team", "node", "purpose", date(2026, 10, 19))
        run_cli("render", "--tool", "claude-code", str(self.root))
        return self.root

    def __exit__(self, *exc):
        self.repo.__exit__(None, None, None)


class HermeticTest(unittest.TestCase):
    def test_inputs_and_data(self):
        with Rendered() as root:
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/v.yml").write_text("on: push\n")
            self.assertEqual(inputs(root), [("aidlc.settings", ".claude/settings.json"),
                                            ("aidlc.narrowing", ".aidlc/permissions.yaml"),
                                            ("aidlc.workflows", ".github/workflows/v.yml")])
            data = policy_data(root)["aidlc"]
            self.assertIn(".env", data["effective"]["secret_paths"])
            self.assertIn("./**/.env", data["sandbox_deny_read"])
            self.assertIn("git push*", data["baseline"]["deny"]["shell"])
            self.assertIn("~/.claude", data["refused_writes"])

    def test_a_namespace_that_evaluated_nothing_fails(self):
        with Rendered() as root:
            out = json.dumps([{"filename": "x", "namespace": "aidlc.settings", "successes": 0,
                               "failures": [], "warnings": []}])
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=fake(out))
            self.assertTrue(any(f.level == "FAIL" and "evaluated no rules" in f.message for f in findings))
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=fake("[]"))
            self.assertTrue(any(f.level == "FAIL" and "evaluated no rules" in f.message for f in findings))

    def test_failures_become_findings_and_command_is_well_formed(self):
        with Rendered() as root:
            out = json.dumps([{"filename": "x", "namespace": "aidlc.settings", "successes": 3,
                               "failures": [{"msg": "sandbox.enabled must be true"}], "warnings": []}])
            runner = fake(out, code=1)
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=runner)
            self.assertIn("FAIL .claude/settings.json sandbox.enabled must be true", [str(f) for f in findings])
            cmd = runner.calls[0]
            self.assertEqual(cmd[:3], ["/opt/conftest", "test", str(root / ".claude/settings.json")])
            self.assertEqual(cmd[cmd.index("--namespace") + 1], "aidlc.settings")
            self.assertEqual(cmd[cmd.index("--output") + 1], "json")

    def test_missing_binary_fails_closed(self):
        with Rendered() as root, mock.patch.object(conftest_check, "which_tool", return_value=None):
            [f] = run_conftest(root)
            self.assertEqual(f.level, "FAIL")
            self.assertIn("aidlc tools install conftest", f.message)

    def test_tool_errors_fail_closed(self):
        with Rendered() as root:
            for runner in (fake("", code=2, stderr="rego_parse_error"), fake("not json", code=0),
                           fake("[]", code=1), fake("[]", code=0)):
                with self.subTest(runner=runner):
                    findings = run_conftest(root, binary=Path("/opt/conftest"), runner=runner)
                    self.assertTrue(any(f.level == "FAIL" for f in findings))

    def test_missing_settings_fails(self):
        with TempRepo({"a": "a\n"}) as root:
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=fake())
            self.assertIn("FAIL .claude/settings.json .claude/settings.json is missing; run aidlc render",
                          [str(f) for f in findings])


@unittest.skipUnless(which_tool("conftest"), "conftest is not installed: run `aidlc tools install conftest` "
                     "(make policy-test runs these)")
class RealConftestTest(unittest.TestCase):
    def test_rego_pack_unit_tests_pass(self):
        code, out = verify_pack()
        self.assertEqual(code, 0, out)

    def test_rendered_settings_pass_and_weakened_settings_fail(self):
        with Rendered() as root:
            self.assertEqual([str(f) for f in run_conftest(root) if f.level == "FAIL"], [])
            path = root / ".claude/settings.json"
            settings = json.loads(path.read_text())
            settings["sandbox"]["enabled"] = False
            settings["permissions"]["deny"].remove("Read(.env)")
            path.write_text(json.dumps(settings))
            messages = [f.message for f in run_conftest(root) if f.level == "FAIL"]
            self.assertIn("sandbox.enabled must be true", messages)
            self.assertIn("secret path .env has no Read() deny rule", messages)

    def test_narrowing_that_reallows_a_deny_fails(self):
        with Rendered() as root:
            (root / ".aidlc/permissions.yaml").write_text(
                "allow_add: [{kind: shell, pattern: 'git push*', reason: release, owner: '@team'}]\n")
            messages = [f.message for f in run_conftest(root) if f.level == "FAIL"]
            self.assertIn("allow_add re-allows the baseline deny 'git push*' (shell)", messages)


class CiStepTest(unittest.TestCase):
    def test_config_policy_is_a_judge_step(self):
        from aidlc import ci
        self.assertEqual([n for n, _ in ci.JUDGE_STEPS][-1], "config-policy")
        self.assertEqual([n for n, _ in ci.AFTER_STEPS], ["skips", "protected-rerun"])
        self.assertEqual(ci.group_of("config-policy"), "scans")

    def test_ci_uses_the_pinned_conftest_only(self):
        from aidlc import ci
        with Rendered() as root, mock.patch.object(conftest_check, "which_tool", return_value=None) as which:
            step = ci.step_config_policy(type("Ctx", (), {"repo": root})())
            self.assertEqual(step.status, "FAIL")
            which.assert_called_with("conftest", pinned_only=True)

    def test_policy_commands(self):
        with Rendered() as root, mock.patch.object(conftest_check, "which_tool", return_value=None):
            code, out, _ = run_cli("policy", "conftest", "--repo", str(root))
            self.assertEqual(code, 1)
            self.assertIn("aidlc tools install conftest", out)
            code, out, err = run_cli("policy", "rego-test")
            self.assertEqual(code, 2)
        with Rendered() as root, mock.patch.object(conftest_check, "which_tool", return_value=Path("/opt/conftest")):
            (root / ".aidlc/permissions.yaml").write_text("deny_add: [not, a, mapping]\n")
            code, _, err = run_cli("policy", "conftest", "--repo", str(root))
            self.assertEqual(code, 2)                                  # a policy error is not a traceback
            self.assertIn("aidlc policy:", err)


class CommandHygieneTest(unittest.TestCase):
    """Controller rulings R1 to R3: conftest never reads change-chosen configuration."""

    def test_conftest_runs_in_an_empty_directory_with_a_minimal_environment(self):
        seen = []

        def runner(cmd, **kw):
            cwd = Path(kw["cwd"])
            seen.append((cmd, kw["cwd"], dict(kw["env"]), sorted(p.name for p in cwd.iterdir())))
            return subprocess.CompletedProcess(cmd, 0, json.dumps(
                [{"filename": cmd[2], "namespace": cmd[cmd.index("--namespace") + 1], "successes": 1,
                  "failures": [], "warnings": []}]), "")

        with Rendered() as root, mock.patch.dict("os.environ", {"CONFTEST_POLICY": "/permissive",
                                                                "CONFTEST_NAMESPACE": "x", "SECRET": "s"}):
            self.assertEqual(run_conftest(root, binary=Path("/opt/conftest"), runner=runner), [])
        self.assertTrue(seen)
        for cmd, cwd, env, listing in seen:
            self.assertNotEqual(Path(cwd).resolve(), root.resolve())
            self.assertEqual(listing, [])                                   # empty when conftest starts
            self.assertFalse([k for k in env if k.startswith("CONFTEST_")])
            self.assertNotIn("SECRET", env)
            self.assertEqual(set(env) - {"PATH", "HOME", "LANG"}, set())
            self.assertNotEqual(Path(env["HOME"]).resolve(), Path.home().resolve())
            self.assertNotIn("--update", cmd)
            self.assertFalse([c for c in cmd if "://" in c])
            self.assertTrue(Path(cmd[cmd.index("--policy") + 1]).is_absolute())
            self.assertEqual(Path(cmd[cmd.index("--policy") + 1]), conftest_check.rego_dir())

    def test_data_comes_from_the_data_repo_not_the_judged_repo(self):
        seen = []

        def runner(cmd, **kw):
            data = json.loads(Path(cmd[cmd.index("--data") + 1]).read_text())
            seen.append(data["aidlc"]["effective"]["secret_paths"])
            return subprocess.CompletedProcess(cmd, 0, json.dumps(
                [{"filename": "x", "namespace": cmd[cmd.index("--namespace") + 1], "successes": 1,
                  "failures": [], "warnings": []}]), "")

        with Rendered() as trusted, Rendered() as head:
            (trusted / ".aidlc/permissions.yaml").write_text("secret_paths_add: ['trusted-secret']\n")
            (head / ".aidlc/permissions.yaml").write_text("deny_add: [not, a, mapping]\n")   # invalid, ignored
            run_conftest(head, binary=Path("/opt/conftest"), runner=runner, data_repo=trusted)
        self.assertTrue(seen)
        self.assertTrue(all("trusted-secret" in s for s in seen))

    def test_symlinked_and_special_inputs_fail(self):
        with Rendered() as root, tempfile.TemporaryDirectory() as outside:
            real = Path(outside) / "settings.json"
            real.write_text("{}")
            (root / ".claude/settings.json").unlink()
            (root / ".claude/settings.json").symlink_to(real)
            (root / ".aidlc/permissions.yaml").unlink()
            os.mkfifo(root / ".aidlc/permissions.yaml")
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/v.yml").symlink_to("../../.claude/../README.md")
            runner = fake()
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=runner)
            text = [str(f) for f in findings]
            self.assertEqual(runner.calls, [])                    # nothing change-chosen reaches conftest
            self.assertTrue(any("settings.json" in t and "symlink" in t for t in text), text)
            self.assertTrue(any("permissions.yaml" in t and "regular file" in t for t in text), text)
            self.assertTrue(any("v.yml" in t and "symlink" in t for t in text), text)
            self.assertTrue(all(f.level == "FAIL" for f in findings))

    def test_a_symlinked_parent_directory_that_leaves_the_checkout_fails(self):
        with Rendered() as root, tempfile.TemporaryDirectory() as outside:
            (Path(outside) / "v.yml").write_text("on: push\n")
            (root / ".github").mkdir()
            (root / ".github/workflows").symlink_to(outside)
            runner = fake()
            findings = run_conftest(root, binary=Path("/opt/conftest"), runner=runner)
            self.assertTrue(any("v.yml" in str(f) and "outside" in str(f) for f in findings), findings)


@unittest.skipUnless(which_tool("conftest"), "conftest is not installed: run `aidlc tools install conftest` "
                     "(make policy-test runs these)")
class RealConftestHostileHeadTest(unittest.TestCase):
    def test_a_conftest_toml_in_the_head_does_not_change_the_verdict(self):
        with Rendered() as root:
            permissive = root / "permissive"
            permissive.mkdir()
            (permissive / "ok.rego").write_text("package main\n")
            for name in ("conftest.toml", ".conftest.toml"):
                (root / name).write_text('policy = ["permissive"]\nnamespace = ["main"]\n')
            path = root / ".claude/settings.json"
            settings = json.loads(path.read_text())
            settings["sandbox"]["enabled"] = False
            path.write_text(json.dumps(settings))
            messages = [f.message for f in run_conftest(root) if f.level == "FAIL"]
            self.assertIn("sandbox.enabled must be true", messages)

    def test_a_conftest_policy_variable_does_not_change_the_verdict(self):
        with Rendered() as root, tempfile.TemporaryDirectory() as permissive:
            (Path(permissive) / "ok.rego").write_text("package main\n")
            path = root / ".claude/settings.json"
            settings = json.loads(path.read_text())
            settings["sandbox"]["enabled"] = False
            path.write_text(json.dumps(settings))
            with mock.patch.dict("os.environ", {"CONFTEST_POLICY": permissive, "CONFTEST_NAMESPACE": "main"}):
                messages = [f.message for f in run_conftest(root) if f.level == "FAIL"]
            self.assertIn("sandbox.enabled must be true", messages)

    def test_a_head_that_loosens_its_own_data_does_not_pass(self):
        with Rendered() as trusted, Rendered() as head:
            (trusted / ".aidlc/permissions.yaml").write_text("secret_paths_add: ['vault/**']\n")
            findings = run_conftest(head, data_repo=trusted)       # the head renders without the extra secret
            messages = [f.message for f in findings if f.level == "FAIL"]
            self.assertIn("secret path vault/** has no Read() deny rule", messages)

    def test_an_unparsable_input_fails(self):
        with Rendered() as root:
            (root / ".claude/settings.json").write_text("{not json")
            self.assertTrue([f for f in run_conftest(root) if f.level == "FAIL"])
            (root / ".claude/settings.json").write_text("{}")
            (root / ".github/workflows").mkdir(parents=True)
            (root / ".github/workflows/v.yml").write_text("on: [unclosed\n")
            fails = [f for f in run_conftest(root) if f.level == "FAIL" and "v.yml" in f.file]
            self.assertTrue(fails)


class CiStepTrustTest(unittest.TestCase):
    def test_the_step_takes_its_data_from_the_trusted_checkout(self):
        from aidlc import ci
        ctx = type("Ctx", (), {"repo": Path("/head"), "trusted": Path("/base")})()
        with mock.patch.object(ci, "run_conftest", return_value=[]) as run:
            self.assertEqual(ci.step_config_policy(ctx).status, ci.OK)
        run.assert_called_once_with(Path("/head"), pinned_only=True, data_repo=Path("/base"))
