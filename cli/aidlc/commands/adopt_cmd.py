"""aidlc adopt: survey an existing repository (read-only), or print the import patch (ADR 0007)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .. import adopt
from ..cli import command


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not (repo / ".git").exists():
        print(f"aidlc adopt: {repo} is not the root of a git repository", file=sys.stderr)
        return 2
    try:
        if args.import_patch:
            patch, problems = adopt.import_patch(repo)
            for problem in problems:
                print(f"aidlc adopt: {problem}", file=sys.stderr)
            sys.stdout.write(patch)
            return 0
        s = adopt.survey(repo)
    except adopt.AdoptError as exc:
        print(f"aidlc adopt: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(adopt.report(s))
    return 1 if s.secrets else 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("adopt", help="survey an existing repository, or print the import patch")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--import", dest="import_patch", action="store_true",
                        help="print a patch moving other tools' rule files into AGENTS.md and .aidlc/rules/")
    parser.set_defaults(func=_run)
