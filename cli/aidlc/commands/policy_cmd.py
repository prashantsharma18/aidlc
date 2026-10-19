"""aidlc policy: validate the policies; judge a repository with the Rego pack (ADR 0001)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..checks.conftest_check import run_conftest, verify_pack
from ..checks.findings import report
from ..cli import command
from ..harness import HarnessError
from ..paths import find_repo_root
from ..policy import PolicyError, validate_all


def _validate(_args: argparse.Namespace) -> int:
    problems = validate_all()
    for problem in problems:
        print(problem)
    if problems:
        print(f"policy: {len(problems)} problem(s)")
        return 1
    print("policy: all policies valid")
    return 0


def _conftest(args: argparse.Namespace) -> int:
    try:
        repo = find_repo_root(Path(args.repo))
        findings = run_conftest(repo)
    except (FileNotFoundError, HarnessError, PolicyError, ValueError) as exc:
        print(f"aidlc policy: {exc}", file=sys.stderr)
        return 2
    return report(findings, "conftest")


def _rego_test(_args: argparse.Namespace) -> int:
    code, output = verify_pack()
    print(output)
    return 2 if code == 2 and "not installed" in output else (0 if code == 0 else 1)


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("policy", help="work with framework policies")
    actions = parser.add_subparsers(dest="action", metavar="<action>", required=True)
    actions.add_parser("validate", help="validate every policy").set_defaults(func=_validate)
    conftest = actions.add_parser("conftest", help="judge settings, narrowing and workflows with the Rego pack")
    conftest.add_argument("--repo", default=".", help="repository to judge (default: .)")
    conftest.set_defaults(func=_conftest)
    actions.add_parser("rego-test", help="run the Rego pack's own unit tests").set_defaults(func=_rego_test)
