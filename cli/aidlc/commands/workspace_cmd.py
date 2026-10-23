"""aidlc workspace init: a workspace root with a read-only harness (never overwrites)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..cli import command
from ..policy import PolicyError
from ..workspace import init_workspace


def _run(args: argparse.Namespace) -> int:
    repos = []
    for spec in args.repo:
        name, sep, owner = spec.partition("=")
        if not sep:
            print(f"aidlc workspace init: --repo takes NAME=OWNER, got '{spec}'", file=sys.stderr)
            return 2
        repos.append((name.strip(), owner.strip()))
    try:
        report = init_workspace(Path(args.path).resolve(), args.key, args.title, repos, args.disable_plugin)
    except (ValueError, PolicyError) as exc:
        print(f"aidlc workspace init: {exc}", file=sys.stderr)
        return 2
    for rel, status in report:
        print(f"{status:18} {rel}")
    print("next: fill in WORKSPACE.md (each repository's slice and role) and commit it")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("workspace", help="set up a workspace root (read-only harness)")
    wsub = parser.add_subparsers(dest="workspace_command", metavar="<action>", required=True)
    init = wsub.add_parser("init", help="write WORKSPACE.md, CLAUDE.md and the read-only harness")
    init.add_argument("path", nargs="?", default=".")
    init.add_argument("--key", required=True, help="the work item, e.g. SHIP-1")
    init.add_argument("--title", required=True)
    init.add_argument("--repo", action="append", required=True, metavar="NAME=OWNER")
    init.add_argument("--disable-plugin", action="append", default=[], metavar="PLUGIN@MARKETPLACE")
    init.set_defaults(func=_run)
