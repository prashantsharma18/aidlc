"""aidlc tools: install and inspect the pinned policy tools (opa, conftest)."""
from __future__ import annotations

import argparse
import sys
import urllib.error
from pathlib import Path

from ..cli import command
from ..policy import load_policy
from ..tools import ToolError, install, tools_dir, which_tool


def _pinned() -> list[dict]:
    return [t for t in load_policy("tool-register")["tools"] if t.get("artifacts")]


def _install(args: argparse.Namespace) -> int:
    names = args.names or [t["id"] for t in _pinned()]
    dest = Path(args.dir).expanduser() if args.dir else None
    failed = 0
    for name in names:
        try:
            path = install(name, dest)
            print(f"tools: {name} installed and verified -> {path}")
        except (ToolError, urllib.error.URLError, OSError) as exc:
            failed += 1
            print(f"aidlc tools: {name}: {exc}", file=sys.stderr)
    return 1 if failed else 0


def _status(_args: argparse.Namespace) -> int:
    for tool in _pinned():
        found = which_tool(tool["id"])
        where = f"{found}" if found else f"not installed (run: aidlc tools install {tool['id']})"
        print(f"tools: {tool['id']} {tool['version']} pinned; {where}")
    print(f"tools: install directory {tools_dir()}")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("tools", help="install or inspect the pinned policy tools")
    actions = parser.add_subparsers(dest="tools_action", metavar="<action>", required=True)
    p = actions.add_parser("install", help="download, verify and install pinned tools")
    p.add_argument("names", nargs="*")
    p.add_argument("--dir")
    p.set_defaults(func=_install)
    s = actions.add_parser("status", help="show where each pinned tool is installed")
    s.set_defaults(func=_status)
