"""aidlc new: create an artefact from a stage template."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..cli import command
from ..templates import TemplateError, list_templates, load_template, write_new


def _parse_sets(pairs: list[str]) -> dict[str, str]:
    values = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise TemplateError(f"--set expects KEY=VALUE, got '{pair}'")
        values[key] = value
    return values


def _run(args: argparse.Namespace) -> int:
    try:
        if args.list:
            for t in list_templates():
                print(f"{t.id:20} {t.stage:10} {t.title}  (fields: {', '.join(t.fields)})")
            return 0
        if not args.template or not args.out:
            print("aidlc new: give a template id and --out, or --list", file=sys.stderr)
            return 2
        path = write_new(load_template(args.template), _parse_sets(args.set), Path(args.out))
        print(f"created {path}")
        return 0
    except TemplateError as exc:
        print(f"aidlc new: {exc}", file=sys.stderr)
        return 1


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("new", help="create an artefact from a template")
    parser.add_argument("template", nargs="?", help="template id (see --list)")
    parser.add_argument("--out", help="file to create (never overwritten)")
    parser.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    parser.add_argument("--list", action="store_true", help="list templates")
    parser.set_defaults(func=_run)
