"""aidlc ci: the local trusted-CI runner. Results are labelled simulated-ci."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from ..checks.onecheck import CheckError
from ..ci import GROUPS, LABEL, SANDBOX_MODES, CiError, ci_checkouts, ci_local
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
    print(f"ci  merge-ready {'yes' if record['merge_ready'] else 'no'}  ({record['merge_ready_reason']})")
    print(f"ci  record {path}  ({LABEL}, sandbox {record['sandbox']}: local evidence of the trusted gates, "
          "not a Git-host CI run)")
    return 0 if result.passed else 1


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("ci", help="run the trusted gates from the base branch against a task branch",
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
