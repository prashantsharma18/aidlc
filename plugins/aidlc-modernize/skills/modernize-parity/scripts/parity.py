#!/usr/bin/env python3
"""Runs the old and the new version of a program on the same inputs and reports every difference.

    python3 parity.py --old "<command>" --new "<command>" --inputs <folder> --out <report.md> [--ignore <regex>]...

Each command contains {input}, replaced by the input file's path. The old version runs twice per input: a difference
between its own two runs is noise, reported as NOISY until an --ignore pattern removes it, so noise is never mistaken
for parity. Output is compared after line endings are normalised (a Windows program prints CRLF) and every --ignore
match is replaced. Exit 0 only when every input gives the same exit code and output; 1 otherwise; 2 when there is no
input. Standard library only; part of aidlc-modernize."""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


def run(template: str, path: Path) -> tuple[int, str]:
    command = template.replace("{input}", shlex.quote(str(path)))
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def normalise(text: str, ignore: list[re.Pattern]) -> str:
    text = text.replace("\r\n", "\n")
    for pattern in ignore:
        text = pattern.sub("<ignored>", text)
    return text


def first_difference(a: str, b: str) -> str:
    for number, (x, y) in enumerate(zip(a.split("\n"), b.split("\n")), start=1):
        if x != y:
            return f"line {number}: old `{x}` new `{y}`"
    return "the outputs have a different number of lines"


def compare(old: str, new: str, inputs: Path, ignore: list[str]) -> list[tuple[str, str, str]]:
    """(input, verdict, detail) for each input file, sorted by name; verdict SAME, DIFFERENT or NOISY."""
    patterns = [re.compile(p) for p in ignore]
    rows = []
    for path in sorted(p for p in inputs.iterdir() if p.is_file()):
        (c1, o1), (c2, o2), (c3, o3) = run(old, path), run(old, path), run(new, path)
        o1, o2, o3 = (normalise(t, patterns) for t in (o1, o2, o3))
        if (c1, o1) != (c2, o2):
            rows.append((path.name, "NOISY", first_difference(o1, o2) if o1 != o2 else f"exit {c1} vs {c2}"))
        elif (c1, o1) != (c3, o3):
            rows.append((path.name, "DIFFERENT", f"exit {c1} vs {c3}" if c1 != c3 else first_difference(o1, o3)))
        else:
            rows.append((path.name, "SAME", ""))
    return rows


def report(rows: list[tuple[str, str, str]], old: str, new: str, ignore: list[str]) -> str:
    lines = ["# Parity report", "", f"- Old: `{old}`", f"- New: `{new}`",
             f"- Ignored patterns: {', '.join(f'`{p}`' for p in ignore) or 'none'}",
             f"- Result: {sum(v == 'SAME' for _, v, _ in rows)} of {len(rows)} inputs the same", "",
             "| Input | Verdict | First difference |", "|---|---|---|"]
    lines += [f"| {name} | {verdict} | {detail.replace('|', '/')} |" for name, verdict, detail in rows]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ignore", action="append", default=[])
    args = parser.parse_args(argv[1:])
    if not args.inputs.is_dir() or not any(p.is_file() for p in args.inputs.iterdir()):
        print(f"parity: no input files in {args.inputs}")
        return 2
    rows = compare(args.old, args.new, args.inputs, args.ignore)
    args.out.write_text(report(rows, args.old, args.new, args.ignore), encoding="utf-8")
    same = sum(v == "SAME" for _, v, _ in rows)
    print(f"parity: {same} of {len(rows)} inputs the same; report {args.out}")
    return 0 if same == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
