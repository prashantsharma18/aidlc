# tests/unit/test_legacy_paths.py
import unittest
from datetime import date

import yaml

from aidlc.repo import CONFIG, init_repo, load_config
from tests.helpers import TempRepo


class LegacyPathsTest(unittest.TestCase):
    def config(self, value):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            data = yaml.safe_load((root / CONFIG).read_text(encoding="utf-8"))
            data["legacy_paths"] = value
            (root / CONFIG).write_text(yaml.safe_dump(data), encoding="utf-8")
            return load_config(root)

    def test_default_is_none(self):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            self.assertEqual(load_config(root).legacy_paths, [])

    def test_globs_are_kept(self):
        self.assertEqual(self.config(["src/billing/**", "lib/old_*.py"]).legacy_paths,
                         ["src/billing/**", "lib/old_*.py"])

    def test_bad_values_fail_closed(self):
        for value in ("src/**", [1], ["/etc/x"], ["../up/**"], [""]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.config(value)
