"""aidlc scope: generate the read-only task scope from the bundle approved on the base branch."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from ..cli import command
from ..policy import PolicyError
from ..repo import CONFIG, load_config
from ..hookbridge import hooks
from ..scope import (FULL_SHA, ScopeError, ScopeUsageError, approved_ref, base_commit, base_moves, bundle_at,
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


def _confirmed_base(repo: Path, out: Path, branch: str, base: str, accepted: str | None) -> str:
    """The live base commit, once it may be pinned. A first scope pins it as before. When a scope
    already pins another base, the base moved: an agent shell can move it with one redirect into
    .git/refs, so every commit since the pinned base is listed (evidence-touching ones flagged) and
    a person must name the live commit with --accept-base. Any other value is refused."""
    live = base_commit(repo, base)
    if accepted is not None and accepted != live:
        raise ScopeUsageError(f"--accept-base {accepted} is not the live base commit of {base} ({live}); "
                              "nothing was written")
    try:
        previous = hooks().guard.read_scope_file(out, repo) if out.is_file() else None
    except (OSError, ValueError):
        previous = None                       # unreadable or not UTF-8: nothing pinned to compare
    pinned = previous[1] if previous else None
    if pinned and pinned != live and accepted != live:
        print(f"aidlc scope: the scope for {branch} pins base {pinned}; {base} is now {live}. "
              "Commits since the pinned base (! = touches approvals, skips, exceptions or configuration):",
              file=sys.stderr)
        for line in base_moves(repo, pinned, live, base):
            print(f"  {line}", file=sys.stderr)
        raise ScopeUsageError(f"the base moved since the last scope; review the commits above, then run "
                              f"aidlc scope --branch {branch} --accept-base {live}")
    return live


def _run(args: argparse.Namespace) -> int:
    try:
        repo = require_repository(Path(args.repo).resolve())
        out = (Path(args.out) if args.out else default_scope_path(repo, args.branch)).resolve()
        if out.is_relative_to(repo):
            raise ScopeError(f"--out {out} is inside the repository; write the scope outside it")
        base = base_branch(repo)
        live = _confirmed_base(repo, out, args.branch, base, args.accept_base)
        ref = approved_ref(repo, args.branch, base)
        pinned = ref.split(":", 1)[0]
        if not FULL_SHA.fullmatch(pinned):
            print(f"aidlc scope: warning: the approval pins the short commit '{pinned}'; aidlc ci requires the "
                  "full SHA, so ask the approver to write all of it", file=sys.stderr)
        patterns = parse_may_change(bundle_at(repo, ref))
        write_scope(patterns, out, base=live)
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
                            "base branch (harness.base_branch, default main)", allow_abbrev=False)
    parser.add_argument("--branch", required=True, help="the task branch, as recorded in "
                        "plans/approved-bundles.txt on the base branch")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", help="scope file; must be outside the repository "
                        "(default: where the guard looks, ~/.aidlc/scopes/<repo>/<branch>.scope)")
    parser.add_argument("--accept-base", metavar="SHA", help="after the base branch moved: the full live base "
                        "commit, which you reviewed; any other value is refused (a person's step, never an agent's)")
    parser.set_defaults(func=_run)
