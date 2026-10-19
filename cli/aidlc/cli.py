"""Command-line entry point. Subcommand modules register themselves with @command."""
from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from . import __version__

Registrar = Callable[[argparse._SubParsersAction], None]
_REGISTRARS: list[Registrar] = []


def command(fn: Registrar) -> Registrar:
    """Register a function that adds one subcommand to the parser."""
    _REGISTRARS.append(fn)
    return fn


def build_parser() -> argparse.ArgumentParser:
    from . import commands  # noqa: F401  importing registers every subcommand

    parser = argparse.ArgumentParser(
        prog="aidlc", description="AI-native SDLC framework (From Intent to Verified Change)")
    parser.add_argument("--version", action="version", version=f"aidlc {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    for register in _REGISTRARS:
        register(sub)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    return int(func(args) or 0)
