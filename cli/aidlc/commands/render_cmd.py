"""aidlc render: generate tool-specific files from AGENTS.md and .aidlc/ sources."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..adapters import adapter_names, get_adapter
from ..adapters.base import AdapterNotImplemented, write_rendered
from ..cli import command


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    adapter = get_adapter(args.tool)
    try:
        files = adapter.render_rules(repo) + adapter.render_folder_rules(repo)
    except AdapterNotImplemented as exc:
        print(f"aidlc render: {exc}")
        return 2
    except ValueError as exc:
        print(f"aidlc render: {exc}")
        return 1
    problems = write_rendered(repo, files, check=args.check)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"render ({adapter.name}): {len(files)} file(s) {'current' if args.check else 'written'}")
    return 1 if problems else 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("render", help="render tool-specific config from sources")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--tool", required=True, choices=adapter_names())
    parser.add_argument("--check", action="store_true", help="report stale files; write nothing")
    parser.set_defaults(func=_run)
