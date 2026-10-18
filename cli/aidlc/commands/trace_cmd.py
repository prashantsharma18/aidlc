"""aidlc trace: generate traceability and tier docs; --check verifies them."""
from __future__ import annotations

import argparse

from ..cli import command
from ..paths import framework_root
from ..trace import check_links, collect, generated_docs


def _run(args: argparse.Namespace) -> int:
    root = framework_root()
    _, problems = collect(root)
    docs = generated_docs(root)
    if args.check:
        for path, text in docs.items():
            current = path.read_text(encoding="utf-8") if path.is_file() else ""
            if current != text:
                problems.append(f"{path.relative_to(root)}: out of date (run bin/aidlc trace)")
        problems += check_links(root)
    else:
        for path, text in docs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(root)}")
    for problem in problems:
        print(problem)
    print(f"trace: {len(problems)} problem(s)")
    return 1 if problems else 0


@command
def register(sub: argparse._SubParsersAction) -> None:
    parser = sub.add_parser("trace", help="guide traceability and generated docs")
    parser.add_argument("--check", action="store_true", help="fail if generated docs are stale")
    parser.set_defaults(func=_run)
