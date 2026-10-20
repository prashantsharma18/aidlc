# tests/unit/test_hookbridge.py
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc.hookbridge import hooks
from aidlc.paths import framework_root


class HookBridgeTest(unittest.TestCase):
    def tearDown(self):
        hooks.cache_clear()                                  # the next caller loads the real framework

    def test_loads_guard_and_post_check_without_side_effects(self):
        # Load from a fresh copy of core/hooks, so no other test's bytecode can be in the way.
        tmp = Path(tempfile.mkdtemp())
        shutil.copytree(framework_root() / "core" / "hooks", tmp / "core" / "hooks",
                        ignore=shutil.ignore_patterns("__pycache__"))
        path_before = list(sys.path)
        had_guard = "guard" in sys.modules
        with mock.patch.dict(os.environ, {"AIDLC_HOME": str(tmp)}):
            hooks.cache_clear()
            h = hooks()
        self.assertEqual(Path(h.guard.__file__).resolve(), (tmp / "core/hooks/guard.py").resolve())
        self.assertTrue(callable(h.guard.matches))
        self.assertTrue(hasattr(h.post_check, "TEST_FILE_RE"))
        self.assertIs(h.post_check.guard, h.guard)          # post_check uses the same guard
        self.assertEqual(sys.path, path_before)
        self.assertEqual("guard" in sys.modules, had_guard)
        self.assertFalse((tmp / "core" / "hooks" / "__pycache__").exists())

    def test_cached(self):
        hooks.cache_clear()
        self.assertIs(hooks(), hooks())
