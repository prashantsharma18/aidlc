import re
import unittest

from tests.helpers import run_cli


class CliTest(unittest.TestCase):
    def test_version(self):
        code, out, _ = run_cli("--version")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"^aidlc \d+\.\d+\.\d+")

    def test_no_command_prints_help_and_returns_2(self):
        code, out, _ = run_cli()
        self.assertEqual(code, 2)
        self.assertIn("usage: aidlc", out)

    def test_unknown_command_is_usage_error(self):
        code, _, err = run_cli("no-such-command")
        self.assertEqual(code, 2)
        self.assertTrue(re.search(r"invalid choice", err))
