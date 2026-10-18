import json
import shutil
import tempfile
import unittest
from pathlib import Path

from aidlc.paths import framework_root
from aidlc.policy import PolicyError, load_policy, validate_all
from tests.helpers import run_cli


def scratch_framework() -> Path:
    """A copy of core/ in a temp dir, so tests can break policies safely."""
    tmp = Path(tempfile.mkdtemp(prefix="aidlc-fw-"))
    shutil.copytree(framework_root() / "core", tmp / "core")
    return tmp


class PolicyTest(unittest.TestCase):
    def test_real_policies_are_valid(self):
        self.assertEqual(validate_all(), [])

    def test_tiers_has_three_tiers_in_order(self):
        tiers = load_policy("tiers")["tiers"]
        self.assertEqual([t["id"] for t in tiers], [1, 2, 3])

    def test_permissions_secret_paths_are_denied_for_read(self):
        perms = load_policy("permissions")
        for path in perms["secret_paths"]:
            self.assertIn(path, perms["deny"]["read"])

    def test_missing_meta_field_is_reported_with_path(self):
        root = scratch_framework()
        try:
            policy = root / "core" / "policy" / "tiers.yaml"
            text = policy.read_text(encoding="utf-8").replace("  owner:", "  ownerx:", 1)
            policy.write_text(text, encoding="utf-8")
            problems = validate_all(root)
            self.assertTrue(any("tiers.yaml" in p and "owner" in p for p in problems), problems)
        finally:
            shutil.rmtree(root)

    def test_policy_without_schema_is_an_error(self):
        root = scratch_framework()
        try:
            (root / "core" / "policy" / "orphan.yaml").write_text(
                "meta: {id: orphan, owner: x, review_by: '2027-01-01', guide: ['1']}\n",
                encoding="utf-8")
            self.assertTrue(any("orphan" in p and "no schema" in p for p in validate_all(root)))
        finally:
            shutil.rmtree(root)

    def test_empty_policy_raises(self):
        root = scratch_framework()
        try:
            (root / "core" / "policy" / "tiers.yaml").write_text("", encoding="utf-8")
            with self.assertRaises(PolicyError):
                load_policy("tiers", root)
        finally:
            shutil.rmtree(root)

    def test_cli_validate(self):
        code, out, _ = run_cli("policy", "validate")
        self.assertEqual(code, 0, out)
        self.assertIn("policies valid", out)

    def test_schemas_are_valid_json(self):
        for path in (framework_root() / "core" / "schemas").glob("*.json"):
            json.loads(path.read_text(encoding="utf-8"))
