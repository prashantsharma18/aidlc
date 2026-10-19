"""aidlc init-repo: scaffold repository context and harness config (never overwrites)."""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from ..cli import command
from ..paths import framework_root
from ..policy import PolicyError, load_yaml
from ..repo import init_repo


def _run(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    if not (repo / ".git").exists():
        print(f"aidlc init-repo: {repo} is not the root of a git repository")  # existing test asserts stdout
        return 2
    try:
        report = init_repo(repo, args.name, args.owner, args.profile, args.purpose, date.today())
    except ValueError as exc:
        print(f"aidlc init-repo: {exc}", file=sys.stderr)
        return 2
    for rel, status in report:
        print(f"{status:18} {rel}")
    print("next: fill in AGENTS.md and docs/codebase-map.md, then run "
          "`aidlc render --tool claude-code` and `aidlc check context-drift`")
    return 0


def _profiles() -> list[str]:
    try:
        return sorted(load_yaml(framework_root() / "core" / "context" / "profiles.yaml"))
    except PolicyError as exc:
        raise SystemExit(f"aidlc init-repo: {exc}") from exc


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("init-repo", help="scaffold Procedure A context for a repository")
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--name", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--profile", required=True, choices=_profiles())
    parser.add_argument("--purpose", required=True)
    parser.set_defaults(func=_run)
