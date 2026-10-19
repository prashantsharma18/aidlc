"""aidlc attempts: the retry counter for a branch (guide 8.8). The post-tool hooks count failing
one-command checks; at the limit the guard stops edits and shell calls. Only a person resets it:
agent shells cannot (sandbox denyWrite on ~/.aidlc, and a shell deny rule)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..cli import command
from ..hookbridge import hooks
from ..paths import find_repo_root
from ..policy import load_policy


def _run(args: argparse.Namespace) -> int:
    try:
        repo = find_repo_root(Path(args.repo))
    except FileNotFoundError as exc:
        print(f"aidlc attempts: {exc}", file=sys.stderr)
        return 2
    guard = hooks().guard
    branch = args.branch or guard.current_branch(repo)      # None: the detached key
    path = guard.attempts_file(repo, branch)
    branch = branch or guard.DETACHED
    if args.reset:
        path.unlink(missing_ok=True)
        print(f"attempts: reset for {branch}")
        return 0
    cap = load_policy("routing")["retry_cap"]
    failures = guard.read_failures(repo, None if branch == guard.DETACHED else branch)
    if failures is None:
        print(f"attempts: the record {path} is unreadable; inspect it, then run aidlc attempts --reset")
        return 1
    print(f"attempts: {failures} failing check(s) in a row on {branch} (limit {cap})")
    return 1 if failures >= cap else 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("attempts", help="show or reset the retry counter for a branch",
                            allow_abbrev=False)          # `--rese` must not slip past the deny rule
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch")
    parser.add_argument("--reset", action="store_true", help="reset the counter (a person, after review)")
    parser.set_defaults(func=_run)
