"""aidlc check: the one-command check (no name), or a named deterministic check."""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from ..checks.context_drift import check_context_drift
from ..checks.findings import report
from ..checks.onecheck import CheckError, context_line, local_context, print_result, run_check, write_record
from ..checks.openwiki_block import check_openwiki
from ..cli import command
from ..harness import HarnessError
from ..paths import find_repo_root
from ..policy import PolicyError
from ..repo import CONFIG, load_config

CHECKS = {}


def _repo(path: str) -> Path | None:
    try:
        return find_repo_root(Path(path))
    except FileNotFoundError as exc:
        print(f"aidlc check: {exc}", file=sys.stderr)
        return None


def _context_drift(args: argparse.Namespace) -> int:
    repo = _repo(args.path)
    return 2 if repo is None else report(check_context_drift(repo, date.today()), "context-drift")


CHECKS["context-drift"] = _context_drift


def _openwiki(args: argparse.Namespace) -> int:
    repo = _repo(args.path)
    return 2 if repo is None else report(check_openwiki(repo), "openwiki")


CHECKS["openwiki"] = _openwiki


def _one(args: argparse.Namespace) -> int:
    repo = _repo(args.repo)
    if repo is None:
        return 2
    if not (repo / CONFIG).is_file():
        print(f"aidlc check: {repo} is not an installed repository; run aidlc init-repo", file=sys.stderr)
        return 2
    try:
        ctx = local_context(repo, load_config(repo))
    except (CheckError, HarnessError, PolicyError, ValueError, KeyError, OSError,
            subprocess.SubprocessError) as exc:
        print(f"aidlc check: {exc}", file=sys.stderr)
        return 2
    print(context_line(ctx))
    try:
        result = run_check(ctx)
        print_result(result, repo)
        write_record(repo, result.record(ctx))
    except (CheckError, ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"aidlc check: {exc}", file=sys.stderr)
        return 2
    return 0 if result.passed else 1


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("check", help="the one-command check, or a named deterministic check")
    parser.add_argument("--repo", default=".", help="repository to check (default: current directory)")
    parser.set_defaults(func=_one)
    names = parser.add_subparsers(dest="check_name", metavar="<check>")
    for name, func in CHECKS.items():
        p = names.add_parser(name)
        p.add_argument("path", nargs="?", default=".")
        p.set_defaults(func=func)
