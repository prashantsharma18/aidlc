"""aidlc check <name>: deterministic checks. Plan 3 adds the one-command check (no name)."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ..checks.context_drift import check_context_drift
from ..checks.findings import report
from ..cli import command
from ..paths import find_repo_root

CHECKS = {}


def _repo(path: str) -> Path | None:
    try:
        return find_repo_root(Path(path))
    except FileNotFoundError as exc:
        print(f"aidlc check: {exc}")
        return None


def _context_drift(args: argparse.Namespace) -> int:
    repo = _repo(args.path)
    return 2 if repo is None else report(check_context_drift(repo, date.today()), "context-drift")


CHECKS["context-drift"] = _context_drift


def _list(_args: argparse.Namespace) -> int:
    print("available checks: " + ", ".join(sorted(CHECKS)))
    return 2


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("check", help="run deterministic checks")
    parser.set_defaults(func=_list)
    names = parser.add_subparsers(dest="check_name", metavar="<check>")
    for name, func in CHECKS.items():
        p = names.add_parser(name)
        p.add_argument("path", nargs="?", default=".")
        p.set_defaults(func=func)
