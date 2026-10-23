# cli/aidlc/baseline.py
"""The adoption baseline (ADR 0007): `.aidlc/baseline.yaml` lists the debt a repository accepted when it
adopted aidlc. Each entry has an owner, a review date and a reason. Two kinds:

    report_only:                         # a command step that runs but does not fail the check yet
      - {step: lint, owner: "@team", review_by: "2027-01-31", reason: "1,240 existing lint errors"}
    skips:                               # a test that may be skipped until its date
      - {test: "pkg.A slow", owner: "@team", review_by: "2027-01-31", reason: "needs the carrier sandbox"}

Trusted CI reads the base branch's copy, so a change cannot widen its own allowance, and the `baseline`
judge step lets the file only shrink. `test`, `build`, `install` and `restore` can never be report-only,
and secrets are never baselined: they are fixed before adoption."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

import yaml

BASELINE = ".aidlc/baseline.yaml"
NEVER_REPORT_ONLY = frozenset({"test", "build", "compile", "install", "restore"})
STEP_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")      # the same rule as onecheck.STEP_NAME
PLAIN_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_KEY = {"report_only": "step", "skips": "test"}


class BaselineError(ValueError):
    pass


@dataclass(frozen=True)
class Entry:
    kind: str            # "report_only" or "skips"
    key: str             # the step name, or the test name as the test report gives it
    owner: str
    review_by: date
    reason: str


def _date(value: object, label: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str) and PLAIN_DATE.fullmatch(value.strip()):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise BaselineError(f"{label}: review_by must be a date such as 2027-01-31, got {value!r}")


def parse(text: str, label: str = BASELINE) -> list[Entry]:
    if not text.strip():
        return []
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BaselineError(f"{label}: not valid YAML ({type(exc).__name__})") from None
    if not isinstance(data, dict) or set(data) - set(_KEY):
        raise BaselineError(f"{label}: only the lists 'report_only' and 'skips' are allowed")
    out: list[Entry] = []
    for kind, field in _KEY.items():
        items = data.get(kind) or []
        if not isinstance(items, list):
            raise BaselineError(f"{label}: '{kind}' must be a list")
        for item in items:
            if not isinstance(item, dict) or set(item) != {field, "owner", "review_by", "reason"}:
                raise BaselineError(f"{label}: every {kind} entry has exactly {field}, owner, review_by and reason")
            key, owner, reason = item[field], item["owner"], item["reason"]
            if not all(isinstance(v, str) and v.strip() for v in (key, owner, reason)):
                raise BaselineError(f"{label}: {kind} entries need a non-empty {field}, owner and reason")
            key = key.strip()                     # checked after stripping: " test" is "test"
            if kind == "report_only" and not STEP_NAME.fullmatch(key):
                raise BaselineError(f"{label}: '{key}' is not a step name (lower case, digits and dashes)")
            if kind == "report_only" and key in NEVER_REPORT_ONLY:
                raise BaselineError(f"{label}: '{key}' can never be report-only; a failing {key} is a broken repository")
            out.append(Entry(kind, key, owner.strip(), _date(item["review_by"], label), reason.strip()))
    seen: set[tuple[str, str]] = set()
    for e in out:
        if (e.kind, e.key) in seen:
            raise BaselineError(f"{label}: {e.kind} '{e.key}' is listed twice")
        seen.add((e.kind, e.key))
    return out


def active(entries: list[Entry], kind: str, today: date | None = None) -> dict[str, Entry]:
    """The entries of one kind still before their review date."""
    today = today or date.today()
    return {e.key: e for e in entries if e.kind == kind and e.review_by >= today}
