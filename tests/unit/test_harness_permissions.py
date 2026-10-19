# tests/unit/test_harness_permissions.py
import unittest
from datetime import date

from aidlc.harness import HarnessError, effective_permissions, harness_data, map_tools
from aidlc.repo import init_repo, load_config
from tests.helpers import TempRepo


def scaffold(root, profile="node"):
    init_repo(root, "svc", "team", profile, "purpose", date(2026, 10, 19))


class EffectivePermissionsTest(unittest.TestCase):
    def test_baseline_without_narrowing(self):
        with TempRepo() as root:
            scaffold(root)
            eff = effective_permissions(root)
            self.assertIn("git push*", eff["deny"]["shell"])
            self.assertIn("rm -fr*", eff["deny"]["shell"])
            self.assertIn("~/.aidlc/**", eff["protected_paths"])
            self.assertEqual(eff["allow_added"], [])

    def test_narrowing_only_adds_denies_and_removes_allows(self):
        with TempRepo() as root:
            scaffold(root)
            (root / ".aidlc/permissions.yaml").write_text(
                "deny_add: {shell: ['docker *']}\nallow_remove: {shell: ['npm test*']}\n"
                "secret_paths_add: ['config/prod/**']\nprotected_paths_add: ['db/migrations/**']\n",
                encoding="utf-8")
            eff = effective_permissions(root)
            self.assertIn("docker *", eff["deny"]["shell"])
            self.assertNotIn("npm test*", eff["allow"]["shell"])
            self.assertIn("config/prod/**", eff["secret_paths"])
            self.assertIn("config/prod/**", eff["deny"]["read"])
            self.assertIn("db/migrations/**", eff["deny"]["edit"])

    def test_allow_add_requires_reason_and_owner(self):
        with TempRepo() as root:
            scaffold(root)
            (root / ".aidlc/permissions.yaml").write_text(
                "allow_add: [{kind: shell, pattern: 'docker build*'}]\n", encoding="utf-8")
            with self.assertRaises(HarnessError):
                effective_permissions(root)

    def test_allow_add_cannot_remove_a_deny(self):
        with TempRepo() as root:
            scaffold(root)
            (root / ".aidlc/permissions.yaml").write_text(
                "allow_add: [{kind: shell, pattern: 'git push*', reason: r, owner: o}]\n", encoding="utf-8")
            eff = effective_permissions(root)
            self.assertIn("git push*", eff["deny"]["shell"])          # deny still wins (deny > allow)
            self.assertEqual(eff["allow_added"][0]["pattern"], "git push*")

    def test_unknown_narrowing_key_is_an_error(self):
        with TempRepo() as root:
            scaffold(root)
            (root / ".aidlc/permissions.yaml").write_text("allow: {shell: ['*']}\n", encoding="utf-8")
            with self.assertRaises(HarnessError):
                effective_permissions(root)

    def test_map_tools(self):
        mapped, unmapped = map_tools(["tracker.transition_issue", "tracker.delete_*"],
                                     {"tracker.transition_issue": "mcp__lab-jira__atlassian-rovo-transitionjiraissue"})
        self.assertEqual(mapped, ["mcp__lab-jira__atlassian-rovo-transitionjiraissue"])
        self.assertEqual(unmapped, ["tracker.delete_*"])

    def test_harness_data_version_is_deterministic(self):
        with TempRepo() as root:
            scaffold(root)
            self.assertEqual(harness_data(root), harness_data(root))
            self.assertRegex(harness_data(root)["version"], r"^\d+\.\d+\.\d+\+[0-9a-f]{12}$")

    def test_config_has_harness_defaults(self):
        with TempRepo() as root:
            scaffold(root, "dotnet")
            cfg = load_config(root)
            self.assertEqual(cfg.harness["auto_memory"], False)
            self.assertEqual(cfg.harness["base_branch"], "main")
            self.assertEqual(cfg.tool_names, {})
