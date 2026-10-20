"""aidlc ci: the gates against a task branch. GitHub mode is the trusted CI (ADR 0002); local mode is a preview."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ..checks.onecheck import CheckError
from ..ci import GITHUB_LABEL, GROUPS, LOCAL_LABEL, SANDBOX_MODES, CiError, ci_checkouts, ci_local
from ..cli import command
from ..harness import HarnessError
from ..policy import PolicyError
from ..repo import CONFIG
from ..sandbox import SandboxError
from ..scope import ScopeError, require_repository


def _run(args: argparse.Namespace) -> int:
    try:
        if args.trusted or args.head:
            if not (args.trusted and args.head and args.branch and args.head_sha and args.records):
                raise CiError("GitHub mode needs --trusted, --head, --branch, --head-sha and --records together")
            result, record, path = ci_checkouts(Path(args.trusted).resolve(), Path(args.head).resolve(),
                                                args.branch, args.head_sha, Path(args.records), args.group,
                                                args.sandbox)
        else:
            if args.sandbox != "require":
                raise CiError("--sandbox auto is for GitHub mode only; local mode always requires the sandbox")
            repo = require_repository(Path(args.repo).resolve())
            if not (repo / CONFIG).is_file():
                raise CiError(f"{repo} is not an installed repository; run aidlc init-repo")
            result, record, path = ci_local(repo, args.branch, args.group)
    except (CiError, CheckError, HarnessError, PolicyError, SandboxError, ScopeError, ValueError,
            KeyError, TypeError, AttributeError, OSError, subprocess.SubprocessError) as exc:
        print(f"aidlc ci: {exc}", file=sys.stderr)
        return 2
    if record["label"] == LOCAL_LABEL:
        print(f"ci  record {path}  (local preview: not evidence; trusted CI is GitHub Actions)")
    else:
        print(f"ci  record {path}  ({GITHUB_LABEL})")
    return 0 if result.passed else 1


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("ci", help="the gates against a task branch: GitHub mode is the trusted CI, local mode a preview",
                            allow_abbrev=False)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch")
    parser.add_argument("--group", choices=GROUPS)
    parser.add_argument("--trusted", help="GitHub mode: checkout of the base branch")
    parser.add_argument("--head", help="GitHub mode: checkout of the pull request head")
    parser.add_argument("--head-sha", help="GitHub mode: the pull request head commit")
    parser.add_argument("--records", help="GitHub mode: a directory that does not exist yet")
    parser.add_argument("--sandbox", choices=SANDBOX_MODES, default="require",
                        help="GitHub mode: auto runs without bubblewrap where it cannot start (--group scans only)")
    parser.set_defaults(func=_run)
