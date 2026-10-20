# tests/unit/test_test_reports.py
import tempfile
import unittest
from pathlib import Path

from aidlc.checks.test_reports import ReportError, parse_report

JEST = """{"testResults": [{"assertionResults": [
  {"fullName": "auth resets AC1", "status": "passed"},
  {"fullName": "auth resets AC2", "status": "failed"},
  {"fullName": "auth resets E2", "status": "skipped"},
  {"ancestorTitles": ["auth"], "title": "todo one", "status": "todo"}]}]}"""
TRX = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>
  <UnitTestResult testName="Api.Tests.Window.Maps" outcome="Passed" />
  <UnitTestResult testName="Api.Tests.Window.Drops" outcome="Failed" />
  <UnitTestResult testName="Api.Tests.Window.Redis" outcome="NotExecuted" />
</Results></TestRun>"""
JUNIT = """<testsuites><testsuite name="s">
  <testcase classname="pkg.A" name="ok"/>
  <testcase classname="pkg.A" name="bad"><failure message="x"/></testcase>
  <testcase classname="pkg.A" name="err"><error message="x"/></testcase>
  <testcase classname="pkg.A" name="skip"><skipped/></testcase>
</testsuite></testsuites>"""


def write(name, text):
    d = Path(tempfile.mkdtemp())
    (d / name).write_text(text, encoding="utf-8")
    return d / name


class ParseReportTest(unittest.TestCase):
    def test_jest_vitest_json(self):
        self.assertEqual(parse_report(write("r.json", JEST)),
                         [("auth resets AC1", "passed"), ("auth resets AC2", "failed"),
                          ("auth resets E2", "notrun"), ("auth todo one", "notrun")])

    def test_trx(self):
        self.assertEqual(parse_report(write("r.trx", TRX)),
                         [("Api.Tests.Window.Maps", "passed"), ("Api.Tests.Window.Drops", "failed"),
                          ("Api.Tests.Window.Redis", "notrun")])

    def test_junit(self):
        self.assertEqual(parse_report(write("r.xml", JUNIT)),
                         [("pkg.A ok", "passed"), ("pkg.A bad", "failed"), ("pkg.A err", "failed"),
                          ("pkg.A skip", "notrun")])

    def test_unreadable_or_unknown_raises(self):
        for name, text in (("r.json", "{not json"), ("r.json", "[]"), ("r.trx", "<oops"), ("r.txt", "x")):
            with self.subTest(name=name, text=text), self.assertRaises(ReportError):
                parse_report(write(name, text))

    def test_wrong_shapes_raise(self):
        for name, text in (("r.json", '{"testResults": 5}'), ("r.json", '{"testResults": ["x"]}'),
                           ("r.json", '{"testResults": [{"assertionResults": 3}]}'),
                           ("r.json", '{}'), ("r.xml", ""), ("r.json", "\xff")):
            with self.subTest(name=name, text=text), self.assertRaises(ReportError):
                parse_report(write(name, text))

    def test_unrecognised_status_is_not_run(self):
        text = '{"testResults": [{"assertionResults": [{"fullName": "a", "status": "weird"}, {"fullName": "b"}]}]}'
        self.assertEqual(parse_report(write("r.json", text)), [("a", "notrun"), ("b", "notrun")])

    def test_missing_file_raises(self):
        with self.assertRaises(ReportError):
            parse_report(Path(tempfile.mkdtemp()) / "none.json")

    def test_oversized_report_raises(self):
        from unittest import mock
        from aidlc.checks import test_reports
        path = write("r.json", JEST)
        with mock.patch.object(test_reports, "MAX_REPORT_BYTES", 10), self.assertRaises(ReportError):
            parse_report(path)
