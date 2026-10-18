"""aidlc scope: generate the read-only task scope from the bundle approved on main."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..cli import command
from ..scope import ScopeError, approved_ref, bundle_at, parse_may_change, write_scope

PROTECTED_BRANCH = "main"   # approvals are read only from here, never from the working branch


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.repo).resolve()
    out = Path(args.out).resolve()
    try:
        if out.is_relative_to(repo):
            raise ScopeError(f"--out {out} is inside the repository; write the scope outside it")
        ref = approved_ref(repo, args.branch, PROTECTED_BRANCH)
        patterns = parse_may_change(bundle_at(repo, ref))
        write_scope(patterns, out)
    except ScopeError as exc:
        print(f"aidlc scope: {exc}; refusing to start")
        return 1
    print(f"scope: {len(patterns)} pattern(s) from {ref} -> {out}")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("scope", help="generate a task scope from the bundle approved on main")
    parser.add_argument("--branch", required=True, help="the task branch, as recorded in "
                        "plans/approved-bundles.txt on main")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", required=True, help="scope file; must be outside the repository")
    parser.set_defaults(func=_run)
