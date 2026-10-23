# cli/aidlc/commands/plugin_cmd.py
"""aidlc plugin build: generate the Claude Code plugin from core/skills and core/agents (ADR 0005)."""
from __future__ import annotations

import argparse
import sys

from ..cli import command
from ..paths import framework_root
from ..adapters.claude_plugin import PluginError, build, check, write_files
from ..policy import PolicyError


def _run(args: argparse.Namespace) -> int:
    root = framework_root()
    try:
        if args.check:
            problems = check(root)
            for problem in problems:
                print(problem)
            print(f"plugin: {len(problems)} problem(s)" + (" (run bin/aidlc plugin build)" if problems else ""))
            return 1 if problems else 0
        files = build(root)
        for rel in write_files(root, files):
            print(f"removed {rel} (no longer generated)")
        print(f"plugin: wrote {len(files)} file(s) to plugins/aidlc, plugins/aidlc-practice and "
              ".claude-plugin/marketplace.json")
        return 0
    except (PluginError, PolicyError) as exc:
        print(f"aidlc plugin: {exc}", file=sys.stderr)
        return 2


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("plugin", help="build the Claude Code plugin from core/skills and core/agents")
    parser.add_argument("action", choices=("build",))
    parser.add_argument("--check", action="store_true", help="fail if the committed plugin is out of date")
    parser.set_defaults(func=_run)
