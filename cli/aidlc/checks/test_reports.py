"""Test-report parsers for the skip check (guide 9.7): Vitest/Jest JSON, .NET TRX, JUnit XML.
Each returns (full test name, status) pairs. The status is "passed", "failed" or "notrun"
(skipped, pending, todo, NotExecuted, or any status not recognised: anything that did not run).
A report is untrusted input written by the change's own test run: any malformed content raises
ReportError and is never read as a pass."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

PASSED, FAILED, NOTRUN = "passed", "failed", "notrun"
TRX_NS = "{http://microsoft.com/schemas/VisualStudio/TeamTest/2010}"
TRX_FAILED = {"Failed", "Error", "Timeout", "Aborted"}


class ReportError(Exception):
    """A report that cannot be read. The skip step turns it into a failure."""


def parse_report(path: Path) -> list[tuple[str, str]]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            return _jest_json(path)
        if suffix == ".trx":
            return _trx(path)
        if suffix == ".xml":
            return _junit(path)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, ET.ParseError) as exc:
        raise ReportError(f"{path.name}: unreadable test report ({type(exc).__name__}: {exc})") from exc
    raise ReportError(f"{path.name}: unknown report format (use .json, .trx or .xml)")


def _jest_json(path: Path) -> list[tuple[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for suite in data["testResults"]:
        for test in suite.get("assertionResults", []):
            name = test.get("fullName") or " ".join([*test.get("ancestorTitles", []), test.get("title", "")]).strip()
            status = test.get("status")
            out.append((name, PASSED if status == "passed" else FAILED if status == "failed" else NOTRUN))
    return out


def _trx(path: Path) -> list[tuple[str, str]]:
    out = []
    for result in ET.parse(path).getroot().iter(f"{TRX_NS}UnitTestResult"):
        outcome = result.get("outcome", "")
        status = PASSED if outcome == "Passed" else FAILED if outcome in TRX_FAILED else NOTRUN
        out.append((result.get("testName", ""), status))
    return out


def _junit(path: Path) -> list[tuple[str, str]]:
    out = []
    for case in ET.parse(path).getroot().iter("testcase"):
        name = " ".join(part for part in (case.get("classname", ""), case.get("name", "")) if part)
        if case.find("skipped") is not None:
            status = NOTRUN
        elif case.find("failure") is not None or case.find("error") is not None:
            status = FAILED
        else:
            status = PASSED
        out.append((name, status))
    return out
