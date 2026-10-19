"""aidlc doctor: health check for the harness in a repository."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from ..checks.doctor import run_doctor
from ..checks.findings import report
from ..cli import command
from ..paths import find_repo_root
from ..repo import CONFIG


def _claude_version() -> str | None:
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout


def _run(args: argparse.Namespace) -> int:
    try:
        repo = find_repo_root(Path(args.path))
    except FileNotFoundError as exc:
        print(f"aidlc doctor: {exc}")
        return 2
    if not (repo / CONFIG).is_file():
        print(f"aidlc doctor: {repo} is not an installed repository; run aidlc init-repo")
        return 2
    return report(run_doctor(repo, claude_version=_claude_version()), "doctor")


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("doctor", help="check that the harness is intact and enforceable")
    parser.add_argument("path", nargs="?", default=".")
    parser.set_defaults(func=_run)
