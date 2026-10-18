import unittest

from aidlc.policy import load_policy, validate_all

NAMES = ["data-classes", "model-routes", "routing", "dependency-policy", "memory-policy",
         "branch-protection", "tool-register", "context-classes"]


class GovernancePolicyTest(unittest.TestCase):
    def test_all_valid(self):
        self.assertEqual(validate_all(), [])

    def test_each_loads(self):
        for name in NAMES:
            with self.subTest(name=name):
                self.assertEqual(load_policy(name)["meta"]["id"], f"policy-{name}")

    def test_routes_never_exceed_internal_for_this_demo(self):
        for route in load_policy("model-routes")["routes"]:
            self.assertIn(route["max_data_class"], {"public", "internal"})

    def test_routing_tier3_always_capable(self):
        self.assertEqual(load_policy("routing")["choose"]["tier3"], "capable")

    def test_branch_protection_excludes_authors(self):
        excluded = load_policy("branch-protection")["approvals"]["excluded_identities"]
        self.assertEqual(set(excluded), {"pr_author", "commit_pushers"})

    def test_context_classes_eight_in_order(self):
        classes = load_policy("context-classes")["classes"]
        self.assertEqual([c["n"] for c in classes], list(range(1, 9)))
        self.assertEqual(classes[7]["trust"], "never authoritative")

    def test_every_register_entry_has_owner_and_review(self):
        for tool in load_policy("tool-register")["tools"]:
            self.assertTrue(tool["owner"] and tool["review_by"])
