#!/usr/bin/env python3
"""Shows where every part of a story stands, read from each repository's own index, so the workspace root tracks
the story without any session writing into another repository.

    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release]

Reads stories/<KEY>/README.md (the story index: its CURRENT versions and UNAFFECTED records) and
stories/<KEY>/coordination-plan.md (its PARTS rows), then <repository>/plans/<KEY>/README.md for each part (the part
index: its PINS line and its stage rows). Prints a table. --write also saves it to stories/<KEY>/status.md.
--check-release exits 1 unless every part is merged at the current versions. Exits 2 when the story's index or
coordination plan is missing. Standard library only."""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

STAGES = ("aidlc-plan", "aidlc-build", "aidlc-verify", "aidlc-review", "merged")
HEADER = re.compile(r"^[A-Z][A-Z-]+\b")
PART_ROW = re.compile(r"^\s+(\d+)\s+([A-Za-z0-9._-]+)\s")
VERSION = re.compile(r"^(.*?)\s+v(\d+)$")
STAGE_ROW = re.compile(r"^\|\s*([a-z-]+)\s*\|[^|]*\|\s*([^|]+?)\s*\|$")
UNAFFECTED = re.compile(r"^UNAFFECTED\s+([A-Za-z0-9._-]+)\s+spec\s+v(\d+)\s*:", re.I)


@dataclass
class PartStatus:
    number: int
    repository: str
    reached: str
    pins: str
    needs: list[str] = field(default_factory=list)

    @property
    def merged(self) -> bool:
        return self.reached == "merged"


def parse_versions(text: str) -> dict[str, int]:
    """'spec v2 · contract orders-api v1' -> {'spec': 2, 'contract orders-api': 1}; 'none' or '' -> {}."""
    versions = {}
    for item in re.split(r"[·,]", text):
        m = VERSION.match(" ".join(item.split()).lower())
        if m:
            versions[m.group(1)] = int(m.group(2))
    return versions


def field_line(text: str, name: str) -> str:
    """The value of a 'NAME   value   (comment)' line, without the comment; '' when there is none."""
    for line in text.splitlines():
        if re.match(rf"^{name}\s", line, re.I):
            return line[len(name):].split("(")[0].strip()
    return ""


def stage_rows(text: str) -> dict[str, str]:
    rows = {}
    for line in text.splitlines():
        m = STAGE_ROW.match(line.strip())
        if m and m.group(1) in STAGES:
            rows[m.group(1)] = " ".join(m.group(2).split()).lower()
    return rows


def parts(plan: str) -> list[tuple[int, str]]:
    """The (number, repository) of each real PARTS row; template rows with <placeholders> are skipped."""
    found, inside = [], False
    for line in plan.splitlines():
        if HEADER.match(line):
            inside = line.startswith("PARTS")
            continue
        m = PART_ROW.match(line) if inside else None
        if m:
            found.append((int(m.group(1)), m.group(2)))
    return found


def part_status(workspace: Path, key: str, number: int, repository: str, current: dict[str, int],
                unaffected: dict[str, int]) -> PartStatus:
    folder = workspace / repository
    if not folder.is_dir():
        return PartStatus(number, repository, "missing", "-", [f"{repository} is not in the workspace"])
    index = folder / "plans" / key / "README.md"
    if not index.is_file():
        return PartStatus(number, repository, "waiting", "-", [])
    text = index.read_text(encoding="utf-8")
    rows, reached, needs = stage_rows(text), "waiting", []
    for stage in STAGES:
        status = rows.get(stage, "to do")
        if status.startswith("stopped"):
            needs.append(f"{stage} {status}")
            break
        if status == "done":
            reached = stage
    pins_text = field_line(text, "PINS")
    pins = parse_versions(pins_text)
    if not pins:
        needs.append("no PINS line")
    for name, version in current.items():
        pinned = pins.get(name)
        if pinned is None or pinned >= version:
            continue
        if name == "spec" and unaffected.get(repository, 0) >= version:
            continue
        needs.append(f"re-plan: {name} v{pinned} < v{version}")
    for name in pins:
        if name not in ("spec", "plan") and name not in current:
            needs.append(f"pins {name}, which the story no longer lists")
    return PartStatus(number, repository, reached, pins_text or "-", needs)


def story_status(workspace: Path, key: str) -> list[PartStatus]:
    story = workspace / "stories" / key
    index = (story / "README.md").read_text(encoding="utf-8")
    current = parse_versions(field_line(index, "CURRENT"))
    unaffected: dict[str, int] = {}
    for line in index.splitlines():
        m = UNAFFECTED.match(line.strip())
        if m:
            unaffected[m.group(1)] = max(unaffected.get(m.group(1), 0), int(m.group(2)))
    plan = (story / "coordination-plan.md").read_text(encoding="utf-8")
    return [part_status(workspace, key, n, repo, current, unaffected) for n, repo in parts(plan)]


def release_ready(rows: list[PartStatus]) -> bool:
    return bool(rows) and all(r.merged and not r.needs for r in rows)


def render(key: str, rows: list[PartStatus]) -> str:
    lines = [f"# {key} · status (generated by scripts/story_status.py; do not edit)", "",
             "| Part | Repository | Reached | Pins | Needs |", "|---|---|---|---|---|"]
    lines += [f"| {r.number} | {r.repository} | {r.reached} | {r.pins} | {'; '.join(r.needs) or '-'} |" for r in rows]
    lines += ["", f"Release: {'ready' if release_ready(rows) else 'not ready'}", ""]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Where every part of a story stands.")
    parser.add_argument("key")
    parser.add_argument("--root", default=".")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check-release", action="store_true")
    args = parser.parse_args(argv)
    workspace = Path(args.root)
    story = workspace / "stories" / args.key
    for name in ("README.md", "coordination-plan.md"):
        if not (story / name).is_file():
            print(f"story_status: {(story / name).as_posix()} not found", file=sys.stderr)
            return 2
    rows = story_status(workspace, args.key)
    text = render(args.key, rows)
    print(text)
    if args.write:
        (story / "status.md").write_text(text, encoding="utf-8")
    return 1 if args.check_release and not release_ready(rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
