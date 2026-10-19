"""aidlc render: generate tool-specific files from AGENTS.md and .aidlc/ sources."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..adapters import adapter_names, get_adapter
from ..adapters.base import AdapterNotImplemented, write_rendered
from ..cli import command
from ..cliinfo import write_cli_entry
from ..harness import HarnessError
from ..paths import find_repo_root


def _run(args: argparse.Namespace) -> int:
    try:
        repo = find_repo_root(Path(args.path))
    except FileNotFoundError as exc:
        print(f"aidlc render: {exc}", file=sys.stderr)
        return 2
    adapter = get_adapter(args.tool)
    try:
        files = (adapter.render_rules(repo) + adapter.render_folder_rules(repo)
                 + adapter.render_permissions(repo) + adapter.render_hooks(repo))
    except AdapterNotImplemented as exc:
        print(f"aidlc render: {exc}", file=sys.stderr)
        return 2
    except (ValueError, HarnessError) as exc:
        print(f"aidlc render: {exc}")  # existing test asserts stdout
        return 1
    problems = write_rendered(repo, files, check=args.check,
                              managed_dirs=adapter.managed_dirs)
    for problem in problems:
        print(problem)
    if not problems and not args.check and args.tool == "claude-code":
        try:
            if write_cli_entry() is None:
                print("aidlc render: warning: framework entry point not found; the retry limit will "
                      "never credit a PASS", file=sys.stderr)
            # next to harness.json: the hooks trust a PASS only from this entry point
        except OSError as exc:
            print(f"aidlc render: cannot record the aidlc entry point ({exc}); a passing check "
                  "will not reset the retry counter")
            return 1
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
