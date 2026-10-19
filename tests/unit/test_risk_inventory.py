import unittest

from aidlc.policy import load_policy, validate_all

ENFORCED = {"permission", "sandbox", "hook-pre", "hook-post", "ci", "branch-protection",
            "code-owners", "no-credential", "retry-limit", "budget", "gateway"}


class RiskInventoryTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_all(), [])

    def test_every_high_harm_has_two_enforced_controls(self):
        for risk in load_policy("risk-inventory")["risks"]:
            enforced = set(risk["controls"]) & ENFORCED
            with self.subTest(risk=risk["id"]):
                self.assertTrue(enforced, "every risk needs an enforced control")
                if risk["severity"] == "high":
                    self.assertGreaterEqual(len(enforced), 2, "serious harm needs two layers (guide 3.4)")

    def test_covers_the_guide_baseline(self):
        ids = {r["id"] for r in load_policy("risk-inventory")["risks"]}
        for required in ("read-secrets", "exfiltrate", "edit-ci", "edit-harness", "weaken-tests",
                         "edit-shared", "add-dependency", "destructive-git", "recursive-delete",
                         "log-personal-data", "tracker-write", "runaway-loop"):
            self.assertIn(required, ids)
