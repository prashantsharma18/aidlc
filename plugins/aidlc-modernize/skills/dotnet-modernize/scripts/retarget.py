#!/usr/bin/env python3
"""A deterministic recipe: changes the target framework of SDK-style .NET projects and removes the .NET Framework
reference-assemblies package, which a modern target does not need. Same input, same output; a second run changes
nothing. Line endings and a byte-order mark are kept.

    python3 retarget.py --from net48 --to net10.0 <project.csproj>...

Fails with exit 1, writing no file, when any project is not SDK-style or targets neither framework.
Standard library only; part of aidlc-modernize (dotnet-modernize). Commit trailer: Recipe: aidlc-retarget@1.0.0"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION = "1.0.0"
BOM = b"\xef\xbb\xbf"
TFM = re.compile(r"(<TargetFrameworks?>)([^<]*)(</TargetFrameworks?>)")
REF_ASSEMBLIES = re.compile(r'[ \t]*<PackageReference Include="Microsoft\.NETFramework\.ReferenceAssemblies"'
                            r'[^>]*?(?:/>|>.*?</PackageReference>)[ \t]*\r?\n', re.DOTALL)
EMPTY_ITEM_GROUP = re.compile(r"[ \t]*<ItemGroup>\s*</ItemGroup>[ \t]*\r?\n")


def retarget(text: str, old: str, new: str) -> str:
    if "<Project Sdk=" not in text:
        raise ValueError("not an SDK-style project; convert it first (this recipe does not)")
    targets: list[str] = []

    def swap(m: re.Match) -> str:
        frameworks = [f.strip() for f in m.group(2).split(";") if f.strip()]
        targets.extend(frameworks)
        return m.group(1) + ";".join(new if f == old else f for f in frameworks) + m.group(3)

    text = TFM.sub(swap, text)
    if old not in targets and new not in targets:
        raise ValueError(f"targets neither {old} nor {new}")
    return EMPTY_ITEM_GROUP.sub("", REF_ASSEMBLIES.sub("", text))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="old")
    parser.add_argument("--to", dest="new")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("projects", nargs="*", type=Path)
    args = parser.parse_args(argv[1:])
    if args.version:
        print(VERSION)
        return 0
    if not (args.old and args.new and args.projects):
        parser.error("--from, --to and at least one project are required")
    results, errors = {}, []
    for path in args.projects:
        raw = path.read_bytes()
        bom = raw.startswith(BOM)
        try:
            results[path] = (bom, raw, retarget(raw[len(BOM) if bom else 0:].decode("utf-8"), args.old, args.new))
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        print("\n".join(errors))
        return 1
    changed = 0
    for path, (bom, raw, text) in results.items():
        data = (BOM if bom else b"") + text.encode("utf-8")
        if data != raw:
            path.write_bytes(data)
            changed += 1
    print(f"retarget {VERSION}: {changed} project(s) changed, {len(results) - changed} already on {args.new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
