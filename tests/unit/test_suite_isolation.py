# tests/unit/test_suite_isolation.py
import os
import unittest
from pathlib import Path


class SuiteIsolationTest(unittest.TestCase):
    def test_the_suite_uses_its_own_decision_log(self):
        log_dir = Path(os.environ["AIDLC_LOG_DIR"])
        self.assertNotEqual(log_dir.resolve(), (Path.home() / ".aidlc" / "logs").resolve())
        self.assertTrue(log_dir.name.startswith("aidlc-test-logs-"))
