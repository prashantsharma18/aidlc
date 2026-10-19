import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc.checks.doctor import check_d13, run_doctor
from tests.unit.test_doctor import ready_repo


class _Base(unittest.TestCase):
    def setUp(self):
        self.repo, self.root = ready_repo()
        self.tmp = Path(tempfile.mkdtemp())
        self.user, self.managed = self.tmp / "user.json", self.tmp / "managed.json"
        self.env = mock.patch.dict(os.environ, {"AIDLC_USER_SETTINGS": str(self.user),
                                                "AIDLC_MANAGED_SETTINGS": str(self.managed)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.repo.__exit__(None, None, None)

    def d13(self):
        return [str(f) for f in check_d13(self.root)]

    def write(self, path, data):
        path.write_text(json.dumps(data) if not isinstance(data, str) else data)


class OverrideTest(_Base):
    def test_no_override_files_no_findings(self):
        self.assertEqual(self.d13(), [])

    def test_local_file_disabling_the_sandbox_fails(self):
        self.write(self.root / ".claude/settings.local.json", {"sandbox": {"enabled": False}})
        self.assertTrue(any(m.startswith("FAIL") and "sandbox.enabled: false" in m for m in self.d13()))

    def test_managed_file_allowing_unsandboxed_fails(self):
        self.write(self.managed, {"sandbox": {"allowUnsandboxedCommands": True}})
        self.assertTrue(any(m.startswith("FAIL") and "allowUnsandboxedCommands" in m for m in self.d13()))

    def test_user_file_cannot_beat_project_set_keys(self):
        self.write(self.user, {"sandbox": {"enabled": False}})
        self.assertEqual([m for m in self.d13() if m.startswith("FAIL")], [])

    def test_disable_all_hooks_fails_from_any_file(self):
        for path in (self.user, self.managed, self.root / ".claude/settings.local.json"):
            with self.subTest(path=path.name):
                self.write(path, {"disableAllHooks": True})
                self.assertTrue(any(m.startswith("FAIL") and "disableAllHooks" in m for m in self.d13()))
                path.unlink()

    def test_bypass_default_mode_fails(self):
        self.write(self.user, {"permissions": {"defaultMode": "bypassPermissions"}})
        self.assertTrue(any(m.startswith("FAIL") and "bypassPermissions" in m for m in self.d13()))

    def test_bare_allow_and_own_hooks_warn(self):
        self.write(self.root / ".claude/settings.local.json",
                   {"permissions": {"allow": ["Bash", "Bash(npm run lint)", "Read"]},
                    "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "true"}]}]}})
        msgs = self.d13()
        self.assertTrue(any(m.startswith("WARN") and "'Bash'" in m for m in msgs))
        self.assertFalse(any("npm run lint" in m for m in msgs))
        self.assertTrue(any(m.startswith("WARN") and "defines its own hooks (Stop)" in m for m in msgs))

    def test_env_overrides_of_the_harness_fail(self):
        for env in ({"AIDLC_HARNESS_FILE": "/tmp/h.json"}, {"AIDLC_HOME_DIR": "/tmp/x"}, {"AIDLC_SCOPE": "off"},
                    {"AIDLC_LOG_DIR": "/tmp/logs"},
                    {"AIDLC_SCOPE_FILE": "/tmp/s"}, {"AIDLC_BASE_REF": "HEAD"}, {"CHECK_SCOPE": "skip"}):
            with self.subTest(env=env):
                self.write(self.user, {"env": env})
                self.assertTrue(any(m.startswith("FAIL") and next(iter(env)) in m for m in self.d13()))
        self.write(self.user, {"env": {"AIDLC_SCOPE": "on", "OTEL_SERVICE_NAME": "x"}})
        self.assertEqual([m for m in self.d13() if m.startswith("FAIL")], [])

    def test_excluded_commands_fail(self):
        self.write(self.root / ".claude/settings.local.json", {"sandbox": {"excludedCommands": ["docker"]}})
        self.assertTrue(any(m.startswith("FAIL") and "excludedCommands" in m for m in self.d13()))

    def test_write_grants_to_the_harness_fail_even_from_user_settings(self):
        home = str(Path.home())
        for grant in ("~/.aidlc", "~/.aidlc/attempts", "./.aidlc", ".claude", f"{home}/.aidlc", home, "/",
                      str(self.root)):
            with self.subTest(grant=grant):
                self.write(self.user, {"sandbox": {"filesystem": {"allowWrite": [grant]}}})
                self.assertTrue(any(m.startswith("FAIL") and "allowWrite" in m for m in self.d13()))
        self.write(self.user, {"sandbox": {"filesystem": {"allowWrite": ["~/.npm", "./node_modules"]}}})
        self.assertEqual([m for m in self.d13() if "allowWrite" in m], [])

    def test_unreadable_file_warns(self):
        self.write(self.managed, "{not json")
        self.assertTrue(any(m.startswith("WARN") and "cannot read managed settings" in m for m in self.d13()))

    def test_run_doctor_includes_d13(self):
        self.write(self.user, {"disableAllHooks": True})
        msgs = [str(f) for f in run_doctor(self.root, which=lambda n: "/usr/bin/x", claude_version="2.1.296")]
        self.assertTrue(any("D13" in m for m in msgs))


class EntryAndReadTest(_Base):
    """R1 (framework entry), R2 (more env names), R3 (how override files are read)."""

    def setUp(self):
        super().setUp()
        from tests.helpers import _CLI_HOME  # where ready_repo's render recorded the entry
        home = mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": _CLI_HOME.name})
        home.start()
        self.addCleanup(home.stop)

    def entry_dir(self):
        from aidlc.hookbridge import hooks
        entry = hooks().guard.recorded_entry(self.root)
        self.assertTrue(entry, "ready_repo must have a recorded entry")
        return Path(entry).parent

    def test_write_grants_reaching_the_framework_entry_fail(self):
        entry_dir = self.entry_dir()
        for key_path, grant in (("allowWrite", str(entry_dir)), ("allowWrite", str(entry_dir.parent)),
                                ("allowWrite", "/"),
                                ("additionalDirectories", str(entry_dir)),
                                ("additionalDirectories", str(entry_dir.parent))):
            with self.subTest(key=key_path, grant=grant):
                if key_path == "allowWrite":
                    data = {"sandbox": {"filesystem": {"allowWrite": [grant]}}}
                else:
                    data = {"permissions": {"additionalDirectories": [grant]}}
                self.write(self.user, data)
                msgs = self.d13()
                self.assertTrue(any(m.startswith("FAIL") and "lets the agent write the aidlc framework" in m
                                    and f"({entry_dir})" in m and f"'{grant}'" in m for m in msgs), msgs)

    def test_tilde_grant_is_expanded_for_the_entry_row(self):
        entry_dir = self.entry_dir()
        with mock.patch.dict(os.environ, {"HOME": str(entry_dir.parent)}):
            self.write(self.user, {"sandbox": {"filesystem": {"allowWrite": ["~"]}}})
            self.assertTrue(any("lets the agent write the aidlc framework" in m for m in self.d13()))

    def test_unrelated_grants_do_not_reach_the_framework(self):
        self.write(self.user, {"sandbox": {"filesystem": {"allowWrite": ["~/.npm"]}},
                               "permissions": {"additionalDirectories": ["/nonexistent/other"]}})
        self.assertFalse(any("aidlc framework" in m for m in self.d13()))

    def test_no_recorded_entry_skips_the_entry_row(self):
        empty = tempfile.mkdtemp()
        with mock.patch.dict(os.environ, {"AIDLC_HOME_DIR": empty}):
            self.write(self.user, {"permissions": {"additionalDirectories": ["/"]}})
            self.assertFalse(any("aidlc framework" in m for m in self.d13()))

    def test_more_env_names_fail(self):
        for name in ("AIDLC_TOOLS_DIR", "AIDLC_USER_SETTINGS", "AIDLC_MANAGED_SETTINGS", "AIDLC_HARNESS_FILE"):
            with self.subTest(name=name):
                self.write(self.user, {"env": {name: "/x"}})
                self.assertTrue(any(m.startswith("FAIL") and name in m for m in self.d13()))

    def test_symlinked_user_file_is_followed(self):
        real = self.tmp / "real.json"
        self.write(real, {"disableAllHooks": True})
        self.user.symlink_to(real)
        self.assertTrue(any(m.startswith("FAIL") and "disableAllHooks" in m for m in self.d13()))

    def test_oversized_file_warns(self):
        self.write(self.user, json.dumps({"x": "a" * (1024 * 1024 + 10)}))
        self.assertTrue(any(m.startswith("WARN") and "cannot read user settings" in m for m in self.d13()))

    def test_file_at_the_cap_is_read(self):
        body = json.dumps({"disableAllHooks": True})
        self.write(self.user, body + " " * (1024 * 1024 - len(body)))
        self.assertTrue(any(m.startswith("FAIL") and "disableAllHooks" in m for m in self.d13()))

    def test_fifo_warns_without_blocking(self):
        os.mkfifo(self.user)
        self.assertTrue(any(m.startswith("WARN") and "cannot read user settings" in m for m in self.d13()))

    def test_directory_warns(self):
        self.user.mkdir()
        self.assertTrue(any(m.startswith("WARN") and "cannot read user settings" in m for m in self.d13()))

    def test_missing_file_is_silent(self):
        self.assertEqual(self.d13(), [])

