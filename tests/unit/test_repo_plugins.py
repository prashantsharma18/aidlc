# tests/unit/test_repo_plugins.py
import json
import unittest
from datetime import date

import yaml

from aidlc.adapters import get_adapter
from aidlc.repo import CONFIG, init_repo
from tests.helpers import TempRepo


class RepoPluginsTest(unittest.TestCase):
    def settings(self, harness):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            data = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
            data["harness"].update(harness)
            (root / CONFIG).write_text(yaml.safe_dump(data), encoding="utf-8")
            [f] = get_adapter("claude-code").render_permissions(root)
            return json.loads(f.content)

    def test_nothing_listed_changes_nothing(self):
        self.assertNotIn("enabledPlugins", self.settings({}))
        self.assertNotIn("extraKnownMarketplaces", self.settings({}))

    def test_an_approved_plugin_is_enabled_and_its_marketplace_registered(self):
        s = self.settings({"enable_plugins": ["aidlc-practice@aidlc"]})
        self.assertEqual(s["enabledPlugins"], {"aidlc-practice@aidlc": True})
        self.assertEqual(s["extraKnownMarketplaces"]["aidlc"]["source"]["repo"], "prashantsharma18/aidlc")

    def test_an_unapproved_marketplace_fails_render(self):
        with self.assertRaisesRegex(ValueError, "approved marketplace"):
            self.settings({"enable_plugins": ["evil@somewhere"]})

    def test_bad_names_fail_render(self):
        for value in ("aidlc-practice", ["x"], [""], ["a@b@c"]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.settings({"enable_plugins": value})

    def test_enable_and_disable_of_one_plugin_fails(self):
        with self.assertRaisesRegex(ValueError, "both enabled and disabled"):
            self.settings({"enable_plugins": ["aidlc-practice@aidlc"], "disable_user_plugins": ["aidlc-practice@aidlc"]})
