"""aidlc scope: generate the read-only task scope from the bundle approved on the base branch."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ..cli import command
from ..policy import PolicyError
from ..repo import CONFIG, load_config
from ..scope import (ScopeError, ScopeUsageError, approved_ref, base_commit, bundle_at,
                     default_scope_path, parse_may_change, require_repository, write_scope)

DEFAULT_BASE = "main"   # approvals are read only from the base branch, never from the working branch
BRANCH_RE = re.compile(r"(?!-)[A-Za-z0-9._/-]+")


def base_branch(repo: Path) -> str:
    """harness.base_branch from .aidlc/config.yaml; main when the repository has no config."""
    if not (repo / CONFIG).is_file():
        return DEFAULT_BASE
    try:
        base = load_config(repo).harness.get("base_branch")
    except (OSError, ValueError, KeyError, TypeError, PolicyError) as exc:
        raise ScopeUsageError(f"{repo / CONFIG}: cannot read ({exc})") from exc
    if not isinstance(base, str) or not BRANCH_RE.fullmatch(base):
        raise ScopeUsageError(f"{repo / CONFIG}: harness.base_branch must be a branch name, got {base!r}")
    return base


def _run(args: argparse.Namespace) -> int:
    try:
        repo = require_repository(Path(args.repo).resolve())
        out = (Path(args.out) if args.out else default_scope_path(repo, args.branch)).resolve()
        if out.is_relative_to(repo):
            raise ScopeError(f"--out {out} is inside the repository; write the scope outside it")
        base = base_branch(repo)
        ref = approved_ref(repo, args.branch, base)
        patterns = parse_may_change(bundle_at(repo, ref))
        write_scope(patterns, out, base=base_commit(repo, base))
    except ScopeUsageError as exc:
        print(f"aidlc scope: {exc}", file=sys.stderr)
        return 2
    except ScopeError as exc:
        print(f"aidlc scope: {exc}; refusing to start", file=sys.stderr)
        return 1
    print(f"scope: {len(patterns)} pattern(s) from {ref} (base {base}) -> {out}")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("scope", help="generate a task scope from the bundle approved on the "
                            "base branch (harness.base_branch, default main)")
    parser.add_argument("--branch", required=True, help="the task branch, as recorded in "
                        "plans/approved-bundles.txt on the base branch")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", help="scope file; must be outside the repository "
                        "(default: where the guard looks, ~/.aidlc/scopes/<repo>/<branch>.scope)")
    parser.set_defaults(func=_run)
