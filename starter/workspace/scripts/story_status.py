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
Exits 2 when the story's index or coordination plan is missing. Standard library only.

When the workspace root is itself a git repository (the home repository, ADR 0022), each part's spec pin also names a
home commit, `spec v<n> @ <commit>`: it must be on the home repository's default branch, and the story's spec must not
have changed since it. Each part keeps a read-only copy of its criteria beside its index, plans/<KEY>/criteria.md,
whose SOURCE line names the commit it copies; every copied line must be in the spec at that commit."""
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
AT_COMMIT = re.compile(r"\s*@\s*([0-9a-fA-F]{7,40})$")
SOURCE_LINE = re.compile(r"^SOURCE\s+(\S+)\s+(\S+)\s+@\s+([0-9a-fA-F]{7,40})\b", re.M)

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
        m = VERSION.match(without_commit(item).lower())
        if m:
            parts = tuple(int(n) for n in m.group(2).split("."))
            versions[m.group(1)] = parts[0] if len(parts) == 1 else parts
    return versions


def unread_items(text: str) -> list[str]:
    return [item for item in items(text) if not VERSION.match(without_commit(item).lower())]


def without_commit(item: str) -> str:
    """'spec v2 @ 1a2b3c4' -> 'spec v2': the version part of a pin that also names its home commit."""
    return AT_COMMIT.sub("", item)


def parse_commits(text: str) -> dict[str, str]:
    """'spec v2 @ 1A2B3C4 · plan v1' -> {'spec': '1a2b3c4'}: the home commit each pin names, when it names one."""
    commits = {}
    for item in items(text):
        at, version = AT_COMMIT.search(item), VERSION.match(without_commit(item).lower())
        if at and version:
            commits[version.group(1)] = at.group(1).lower()
    return commits


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
    spec_now = as_tuple(current["spec"])[0] if "spec" in current else 0
    covered = spec_now > 0 and unaffected.get(repository, 0) >= spec_now
    needs += drift_needs(workspace, key, index, pins_text, needs, covered)
    return PartStatus(number, repository, reached, pins_text or "-", needs)


def own_repository(folder: Path) -> bool:
    """True when the folder is the top of its own git repository, not a folder inside another one."""
    top = git(folder, "rev-parse", "--show-toplevel")
    return top is not None and Path(top).resolve() == folder.resolve()


def default_ref(folder: Path) -> str | None:
    """The ref that stands for the default branch: origin's (the freshest after a fetch), else a local main or master."""
    remote = git(folder, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD")
    if remote:
        return remote
    return next((b for b in ("main", "master") if git(folder, "rev-parse", "--verify", "--quiet", f"refs/heads/{b}")),
                None)


def copied_lines(text: str) -> list[str]:
    """The lines criteria.md copies from the spec: everything below its first criteria, edge-case or non-goals
    heading, except headings, fences, blank lines and template placeholders; whitespace runs collapsed."""
    lines, inside = [], False
    for line in text.splitlines():
        if re.match(r"^##\s+(Acceptance criteria|Edge cases|Non-goals)", line):
            inside = True
            continue
        flat = " ".join(line.split())
        if inside and flat and not flat.startswith(("#", "```")) and "{{" not in flat:
            lines.append(flat)
    return lines


def criteria_needs(workspace: Path, index: Path, commit: str | None) -> list[str]:
    """F5: the part's read-only copy of its criteria matches the home spec at the commit it names."""
    copy = index.parent / "criteria.md"
    if not copy.is_file():
        return ["no criteria.md beside the part index (the part's read-only copy of its criteria, ADR 0022)"]
    text = read(copy)
    source = SOURCE_LINE.search(text)
    if not source:
        return ["criteria.md has no SOURCE line naming the home repository, the spec's path and its commit"]
    path, at = source.group(2), source.group(3).lower()
    needs = []
    if commit and not (commit.startswith(at) or at.startswith(commit)):
        needs.append(f"criteria.md copies {at[:7]}, but the spec pin names {commit[:7]}")
    spec = git(workspace, "show", f"{at}:{path}")
    if spec is None:
        return needs + [f"criteria.md: {path} at {at[:7]} cannot be read in the home repository"]
    spec_lines = {" ".join(line.split()) for line in spec.splitlines()}
    needs += [f"criteria.md differs from {path} at {at[:7]}: {line[:80]}"
              for line in copied_lines(text) if line not in spec_lines]
    return needs


def drift_needs(workspace: Path, key: str, index: Path, pins_text: str, needs: list[str], covered: bool) -> list[str]:
    """F4 and F5, when the workspace root is a git repository (the home repository): the spec pin names a home
    commit on the default branch, the spec has not changed since it, and the criteria copy matches it. `covered` is
    true when an UNAFFECTED line clears this part at the current spec."""
    if not own_repository(workspace):
        return []
    base = default_ref(workspace)
    if base is None:
        return ["the home repository's default branch cannot be found"]
    found, spec_rel = [], f"stories/{key}/spec.md"
    commit = parse_commits(pins_text).get("spec")
    if commit is None:
        if "spec" in parse_versions(pins_text):
            found.append("the spec pin names no home commit (spec v<n> @ <commit>)")
    elif git(workspace, "cat-file", "-e", f"{commit}^{{commit}}") is None:
        return found + [f"pinned home commit {commit[:7]} not found: run git fetch in the home repository"]
    elif git(workspace, "merge-base", "--is-ancestor", commit, base) is None:
        found.append(f"pinned home commit {commit[:7]} is not on the home repository's {base}")
    elif (not covered and not any(n.startswith("re-plan: spec") for n in needs)
          and git(workspace, "diff", "--quiet", commit, base, "--", spec_rel) is None):
        found.append(f"re-plan: {spec_rel} changed on {base} since {commit[:7]}")
    return found + criteria_needs(workspace, index, commit)


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
