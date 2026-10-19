import os
import tempfile
import unittest
from pathlib import Path

from aidlc.paths import find_repo_root, framework_root
from tests.helpers import TempRepo


class PathsTest(unittest.TestCase):
    def test_framework_root_contains_cli(self):
        self.assertTrue((framework_root() / "cli" / "aidlc" / "cli.py").is_file())

    def test_framework_root_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AIDLC_HOME"] = tmp
            try:
                self.assertEqual(framework_root(), Path(tmp).resolve())
            finally:
                del os.environ["AIDLC_HOME"]

    def test_find_repo_root_from_subdirectory(self):
        with TempRepo({"src/app/x.txt": "x\n"}) as root:
            self.assertEqual(find_repo_root(root / "src" / "app"), root.resolve())

    def test_find_repo_root_outside_repo_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                find_repo_root(Path(tmp))
