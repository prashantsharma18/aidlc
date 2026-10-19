"""A check finding and the shared report format."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Finding:
    level: Literal["FAIL", "WARN"]
    file: str
    line: int
    message: str

    def __str__(self) -> str:
        where = f"{self.file}:{self.line}" if self.line else self.file
        return f"{self.level} {where} {self.message}"


def report(findings: list[Finding], name: str) -> int:
    for f in findings:
        print(f)
    fails = sum(f.level == "FAIL" for f in findings)
    print(f"{name}: {fails} fail, {len(findings) - fails} warn")
    return 1 if fails else 0
