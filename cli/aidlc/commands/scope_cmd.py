"""aidlc scope: generate the read-only task scope from an approved bundle."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..cli import command
from ..scope import ScopeError, approved_ref, bundle_at, parse_may_change, write_scope


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    try:
        ref = args.bundle or approved_ref(repo, args.branch, args.approvals_ref)
        patterns = parse_may_change(bundle_at(repo, ref))
        write_scope(patterns, Path(args.out))
    except ScopeError as exc:
        print(f"aidlc scope: {exc}; refusing to start")
        return 1
    print(f"scope: {len(patterns)} pattern(s) from {ref} -> {args.out}")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("scope", help="generate a task scope from an approved bundle")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--bundle", help="<commit>:<path> of the approved bundle")
    which.add_argument("--branch", help="look the bundle up in plans/approved-bundles.txt")
    parser.add_argument("--approvals-ref", default="main")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", required=True)
    parser.set_defaults(func=_run)
