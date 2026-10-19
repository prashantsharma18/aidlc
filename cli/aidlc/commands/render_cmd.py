"""aidlc render: generate tool-specific files from AGENTS.md and .aidlc/ sources."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..adapters import adapter_names, get_adapter
from ..adapters.base import AdapterNotImplemented, write_rendered
from ..cli import command
from ..cliinfo import record_base, record_entry, recorded_base
from ..harness import BRANCH_RE, HarnessError, base_branch
from ..hookbridge import hooks
from ..paths import find_repo_root
from ..repo import CONFIG


def _allow_write(files) -> list[str]:
    """The sandbox allowWrite paths this render put into .claude/settings.json."""
    for f in files:
        if f.path == ".claude/settings.json":
            paths = json.loads(f.content).get("sandbox", {}).get("filesystem", {}).get("allowWrite", [])
            return [p for p in paths if isinstance(p, str)]
    return []


def _trusted_base(repo: Path, explicit: str | None) -> None:
    """The base branch `aidlc ci` trusts ($AIDLC_HOME_DIR/entry/<repo>-<hash8>.base.json). The working
    copy's configuration is the checked-out branch's own file, so it may set the record only from the
    base branch itself: when no record exists yet, or with an explicit --trusted-base on that branch
    (checked by the caller). A task branch never moves it."""
    if explicit is not None:
        record_base(repo, explicit)
        return
    if not (repo / CONFIG).is_file():                 # aidlc ci runs only in installed repositories
        return
    existing, configured = recorded_base(repo), base_branch(repo)
    if existing is None:
        if hooks().guard.current_branch(repo) == configured:
            record_base(repo, configured)
        else:
            print("aidlc render: warning: no trusted base recorded; check out the base branch and run aidlc render",
                  file=sys.stderr)
    elif existing != configured:
        print(f"aidlc render: warning: trusted base stays '{existing}'; to change it, check out the new base "
              "and run aidlc render --trusted-base NAME", file=sys.stderr)


def _run(args: argparse.Namespace) -> int:
    try:
        repo = find_repo_root(Path(args.path))
    except FileNotFoundError as exc:
        print(f"aidlc render: {exc}", file=sys.stderr)
        return 2
    if args.trusted_base is not None:
        name, current = args.trusted_base, hooks().guard.current_branch(repo)
        if args.check:
            print("aidlc render: --trusted-base writes the trusted record; it cannot be used with --check",
                  file=sys.stderr)
            return 2
        if not BRANCH_RE.fullmatch(name) or ".." in name:
            print(f"aidlc render: --trusted-base '{name}' is not a branch name", file=sys.stderr)
            return 2
        if current != name:
            print(f"aidlc render: --trusted-base {name} needs '{name}' checked out (now: "
                  f"{current or 'a detached HEAD'}); check it out and run this again", file=sys.stderr)
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
            status, entry = record_entry(repo, _allow_write(files))
        except OSError as exc:
            print(f"aidlc render: cannot record the aidlc entry point ({exc}); a passing check "
                  "will not reset the retry counter")
            return 1
        if status == "missing":
            print("aidlc render: warning: framework entry point not found; the retry limit will "
                  "never credit a PASS", file=sys.stderr)
        elif status == "refused":
            print(f"aidlc render: warning: framework entry point {entry} is in a location the agent "
                  "can write; the retry limit will never credit a PASS", file=sys.stderr)
    if not problems and not args.check:
        try:
            _trusted_base(repo, args.trusted_base)
        except (OSError, HarnessError, ValueError) as exc:
            print(f"aidlc render: cannot record the trusted base branch ({exc}); aidlc ci will refuse to run")
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
    parser.add_argument("--trusted-base", metavar="NAME",
                        help="record NAME as the base branch aidlc ci trusts; NAME must be checked out")
    parser.set_defaults(func=_run)
