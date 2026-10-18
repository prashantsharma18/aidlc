"""aidlc policy validate: check every policy against its schema."""
from __future__ import annotations

import argparse

from ..cli import command
from ..policy import validate_all


def _validate(_args: argparse.Namespace) -> int:
    problems = validate_all()
    for problem in problems:
        print(problem)
    if problems:
        print(f"policy: {len(problems)} problem(s)")
        return 1
    print("policy: all policies valid")
    return 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("policy", help="work with framework policies")
    actions = parser.add_subparsers(dest="action", metavar="<action>", required=True)
    actions.add_parser("validate", help="validate every policy").set_defaults(func=_validate)
