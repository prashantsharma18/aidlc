#!/usr/bin/env python3
"""Shows where every part of a story stands, read from each repository's own index, so the workspace root tracks
the story without any session writing into another repository.

    python3 scripts/story_status.py <KEY> [--root <workspace>] [--write] [--check-release]

Reads stories/<KEY>/README.md (the story index: its CURRENT versions and UNAFFECTED records) and
stories/<KEY>/coordination-plan.md (its PARTS rows), then, for each part, its index in the repository:
<repository>/plans/<KEY>/part-<n>/README.md when that folder exists (a repository holding more than one part),
otherwise <repository>/plans/<KEY>/README.md. Prints a table. --write also saves it to stories/<KEY>/status.md.
--check-release exits 1 unless the story is release-ready: every part merged at the current versions, nothing it
could not read, and every repository checked out on its default branch (run `git pull` in each first; a part's index
reaches the default branch only through its merge). Anything the script cannot read is reported, never skipped.
Exits 2 when the story's index or coordination plan is missing. Standard library only."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

STAGES = ("aidlc-plan", "aidlc-build", "aidlc-verify", "aidlc-review", "merged")
HEADER = re.compile(r"^[A-Z][A-Z-]+\b")
PART_ROW = re.compile(r"^\s+(\d+)\.?\s+([A-Za-z0-9._/-]+)(?:\s|$)")
VERSION = re.compile(r"^(.*?)\s+v(\d+(?:\.\d+)*)$")
STAGE_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|[^|]*\|\s*([^|]+?)\s*\|?$")
UNAFFECTED = re.compile(r"^UNAFFECTED\s+([A-Za-z0-9._/-]+)\s+spec\s+v(\d+)\s*:", re.I)

Version = int | tuple[int, ...]


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


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def as_tuple(v: Version) -> tuple[int, ...]:
    return v if isinstance(v, tuple) else (v,)


def show(v: Version) -> str:
    return ".".join(map(str, as_tuple(v)))


def items(text: str) -> list[str]:
    """The non-placeholder items of a versions line: 'spec v2 · contract x v1' -> ['spec v2', 'contract x v1']."""
    found = []
    for item in re.split(r"[·,]", text):
        item = " ".join(item.split())
        if item and item.lower() != "none" and "<" not in item and "{{" not in item:
            found.append(item)
    return found


def parse_versions(text: str) -> dict[str, Version]:
    """'spec v2 · contract orders-api v2.1.0' -> {'spec': 2, 'contract orders-api': (2, 1, 0)}; 'none' or '' -> {}."""
    versions: dict[str, Version] = {}
    for item in items(text):
        m = VERSION.match(item.lower())
        if m:
            parts = tuple(int(n) for n in m.group(2).split("."))
            versions[m.group(1)] = parts[0] if len(parts) == 1 else parts
    return versions


def unread_items(text: str) -> list[str]:
    return [item for item in items(text) if not VERSION.match(item.lower())]


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
        if m:
            name = m.group(1).strip("` ").lower()
            if name in STAGES:
                rows[name] = " ".join(m.group(2).split()).lower()
    return rows


def read_parts(plan: str) -> tuple[list[tuple[int, str]], list[str]]:
    """The (number, repository) of each real PARTS row, and every other PARTS line that could not be read.
    Template rows holding <placeholders> and notes in parentheses are skipped."""
    found, unread, inside = [], [], False
    for line in plan.splitlines():
        if HEADER.match(line):
            inside = line.startswith("PARTS")
            continue
        if line.strip().startswith("```"):
            inside = False
            continue
        if not inside or not line.strip() or "<" in line or "{{" in line or line.strip().startswith("("):
            continue
        m = PART_ROW.match(line)
        if m:
            found.append((int(m.group(1)), m.group(2)))
        else:
            unread.append(line.strip())
    return found, unread


def parts(plan: str) -> list[tuple[int, str]]:
    return read_parts(plan)[0]


def part_index(workspace: Path, key: str, number: int, repository: str) -> Path:
    own = workspace / repository / "plans" / key / f"part-{number}" / "README.md"
    return own if own.is_file() else workspace / repository / "plans" / key / "README.md"


def part_status(workspace: Path, key: str, number: int, repository: str, current: dict[str, Version],
                unaffected: dict[str, int]) -> PartStatus:
    if not (workspace / repository).is_dir():
        return PartStatus(number, repository, "missing", "-", [f"{repository} is not in the workspace"])
    index = part_index(workspace, key, number, repository)
    if not index.is_file():
        return PartStatus(number, repository, "waiting", "-", [])
    text = read(index)
    rows, reached, needs = stage_rows(text), "waiting", []
    if not rows:
        needs.append("no stage rows recognised in the part index")
    for stage in STAGES:
        status = rows.get(stage, "to do")
        if status.startswith("stopped"):
            needs.append(f"{stage} {status}")
            break
        if status == "done":
            reached = stage
    pins_text = field_line(text, "PINS")
    pins = parse_versions(pins_text)
    needs += [f"PINS item not understood: {item}" for item in unread_items(pins_text)]
    if not pins:
        needs.append("no PINS line")
    elif "spec" in current and "spec" not in pins:
        needs.append("no spec pin")
    for name, version in current.items():
        pinned = pins.get(name)
        if pinned is None or as_tuple(pinned) >= as_tuple(version):
            continue
        if name == "spec" and unaffected.get(repository, 0) >= as_tuple(version)[0]:
            continue
        needs.append(f"re-plan: {name} v{show(pinned)} < v{show(version)}")
    for name in pins:
        if name not in ("spec", "plan") and name not in current:
            needs.append(f"pins {name}, which the story no longer lists")
    return PartStatus(number, repository, reached, pins_text or "-", needs)


def story_current(workspace: Path, key: str) -> tuple[dict[str, Version], dict[str, int], str]:
    index = read(workspace / "stories" / key / "README.md")
    current_text = field_line(index, "CURRENT")
    unaffected: dict[str, int] = {}
    for line in index.splitlines():
        m = UNAFFECTED.match(line.strip())
        if m:
            unaffected[m.group(1)] = max(unaffected.get(m.group(1), 0), int(m.group(2)))
    return parse_versions(current_text), unaffected, current_text


def story_status(workspace: Path, key: str) -> list[PartStatus]:
    current, unaffected, _ = story_current(workspace, key)
    plan = read(workspace / "stories" / key / "coordination-plan.md")
    return [part_status(workspace, key, n, repo, current, unaffected) for n, repo in parts(plan)]


def story_problems(workspace: Path, key: str) -> list[str]:
    """What stops the whole story from being judged: a missing CURRENT spec, and lines the script could not read."""
    current, _, current_text = story_current(workspace, key)
    found, unread = read_parts(read(workspace / "stories" / key / "coordination-plan.md"))
    problems = [] if "spec" in current else ["the story index has no CURRENT spec version"]
    problems += [f"CURRENT item not understood: {item}" for item in unread_items(current_text)]
    problems += [f"PARTS row not understood: {line}" for line in unread]
    if not found:
        problems.append("no parts found in the coordination plan")
    return problems


def git(folder: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def branch_problem(folder: Path, repository: str) -> str | None:
    """Why this checkout cannot stand for the merged state, or None when it is on its default branch."""
    if git(folder, "rev-parse", "--is-inside-work-tree") != "true":
        return f"{repository}: not a git repository"
    current = git(folder, "branch", "--show-current") or "a detached HEAD"
    remote = git(folder, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    default = remote.split("/", 1)[1] if remote else next(
        (b for b in ("main", "master") if git(folder, "rev-parse", "--verify", "--quiet", f"refs/heads/{b}")), None)
    if default is None:
        return f"{repository}: its default branch cannot be found"
    return None if current == default else f"{repository}: on branch {current}, not its default branch {default}"


def release_ready(rows: list[PartStatus], problems: list[str] | tuple[str, ...] = ()) -> bool:
    return bool(rows) and not problems and all(r.merged and not r.needs for r in rows)


def render(key: str, rows: list[PartStatus], problems: list[str] | tuple[str, ...] = ()) -> str:
    lines = [f"# {key} · status (generated by scripts/story_status.py; do not edit)", "",
             "| Part | Repository | Reached | Pins | Needs |", "|---|---|---|---|---|"]
    lines += [f"| {r.number} | {r.repository} | {r.reached} | {r.pins} | {'; '.join(r.needs) or '-'} |" for r in rows]
    lines += [""] + [f"Story needs: {p}" for p in problems]
    lines += [f"Release: {'ready' if release_ready(rows, problems) else 'not ready'}", ""]
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
    problems = story_problems(workspace, args.key)
    if args.check_release:
        for repository in dict.fromkeys(r.repository for r in rows if r.reached != "missing"):
            problem = branch_problem(workspace / repository, repository)
            if problem:
                problems.append(problem)
    text = render(args.key, rows, problems)
    print(text)
    if args.write:
        (story / "status.md").write_text(text, encoding="utf-8")
    return 1 if args.check_release and not release_ready(rows, problems) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
