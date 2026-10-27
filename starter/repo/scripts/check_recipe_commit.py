#!/usr/bin/env python3
"""Checks a mechanical recipe commit, the one exception to aidlc's gates (ADR 0012): re-running the approved recipe
on the commit's parent gives exactly the commit's files, the test count is the same before and after, and the commit
names the tool. Lists every changed assertion line so the reviewer can confirm that what it checks did not change.

    python3 scripts/check_recipe_commit.py <commit> --recipe "<command>" --count "<command>"

--recipe is the command the task bundle's RECIPE field approved; --count prints the number of tests (it
must print one number). Both run in temporary copies built from git's objects (not `git archive`, which honours
.gitattributes), never in your checkout; the recipe runs alone and is compared with the commit's objects, and files
the copy's .gitignore ignores (build output) do not count. Exit 1 on any problem.
Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TRAILER = re.compile(r"^Recipe: \S+@\S+\s*$", re.MULTILINE)
ASSERTION = re.compile(r"\bAssert\.|\bassert\b|\bexpect\(|\.Should\(|\bShould\.")
ONE_NUMBER = re.compile(r"^\s*(\d+)\s*$")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def objects(repo: Path, rev: str) -> dict[str, tuple[str, bytes]]:
    """Every file of a commit as {path: (mode, content)}, read from git's objects. Unlike `git archive`, this ignores
    .gitattributes (export-ignore, export-subst), so a commit cannot hide its own files from the check."""
    entries = []
    for record in git(repo, "ls-tree", "-r", "-z", rev).split(b"\0"):
        if record:
            meta, path = record.split(b"\t", 1)
            mode, kind, sha = meta.split()
            if kind == b"blob":
                entries.append((path.decode(), mode.decode(), sha.decode()))
    files = {}
    with subprocess.Popen(["git", "-C", str(repo), "cat-file", "--batch"], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE) as cat:
        for path, mode, sha in entries:
            cat.stdin.write(sha.encode() + b"\n")
            cat.stdin.flush()
            size = int(cat.stdout.readline().split()[2])
            files[path] = (mode, cat.stdout.read(size))
            cat.stdout.read(1)
        cat.stdin.close()
    return files


def materialise(files: dict[str, tuple[str, bytes]], into: Path) -> None:
    for path, (mode, data) in files.items():
        target = into / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            os.symlink(data.decode(), target)
        else:
            target.write_bytes(data)
            if mode == "100755":
                target.chmod(0o755)


def tree(folder: Path) -> dict[str, tuple[str, bytes]]:
    found = {}
    for p in folder.rglob("*"):
        if p.is_symlink():
            found[p.relative_to(folder).as_posix()] = ("120000", os.readlink(p).encode())
        elif p.is_file():
            mode = "100755" if os.access(p, os.X_OK) else "100644"
            found[p.relative_to(folder).as_posix()] = (mode, p.read_bytes())
    return found


def ignored(repo: Path, folder: Path, paths: list[str]) -> set[str]:
    """The paths the copy's own .gitignore files ignore (build output a recipe tool may leave behind)."""
    if not paths:
        return set()
    result = subprocess.run(["git", f"--git-dir={repo / '.git'}", f"--work-tree={folder}", "check-ignore",
                             "--no-index", "-z", "--stdin"], input="\0".join(paths).encode(), capture_output=True)
    return {p.decode() for p in result.stdout.split(b"\0") if p}


def count_tests(command: str, files: dict[str, tuple[str, bytes]]) -> tuple[int | None, str]:
    with tempfile.TemporaryDirectory() as tmp:
        materialise(files, Path(tmp))
        result = subprocess.run(command, shell=True, cwd=tmp, capture_output=True, text=True)
    one = ONE_NUMBER.match(result.stdout)
    if result.returncode != 0:
        return None, f"exit {result.returncode}: {result.stderr[-300:].strip()}"
    if not one:
        return None, f"it must print one number, and printed {result.stdout.strip()[:80]!r}"
    return int(one.group(1)), ""


def check(repo: Path, commit: str, recipe: str, count: str) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    parents = git(repo, "rev-list", "--parents", "-n", "1", commit).decode().split()
    if len(parents) != 2:
        return [f"{commit[:12]}: a recipe commit has exactly one parent"], []
    parent = parents[1]
    if not TRAILER.search(git(repo, "log", "-1", "--format=%B", commit).decode()):
        problems.append(f"{commit[:12]}: the message needs the trailer 'Recipe: <tool>@<version>'")
    before, expected = objects(repo, parent), objects(repo, commit)
    # Counts first, each in its own folder; the recipe runs last, alone, and is compared with git's objects,
    # so nothing it writes outside its folder can change what it is compared with.
    n_before, why_before = count_tests(count, before)
    n_after, why_after = count_tests(count, expected)
    if n_before is None or n_after is None:
        problems.append(f"the count command failed: {why_before or why_after}; it must print one number")
    elif n_before != n_after:
        problems.append(f"the test count changed: {n_before} before, {n_after} after")
    with tempfile.TemporaryDirectory() as tmp:
        rerun = Path(tmp)
        materialise(before, rerun)
        run = subprocess.run(recipe, shell=True, cwd=rerun, capture_output=True, text=True)
        if run.returncode != 0:
            problems.append(f"the recipe failed on the parent (exit {run.returncode}): {run.stderr[-300:]}")
        else:
            actual = tree(rerun)
            extra = sorted(set(actual) - set(expected))
            for path in ignored(repo, rerun, extra):
                actual.pop(path, None)
            for path in sorted(set(expected) | set(actual)):
                if expected.get(path) != actual.get(path):
                    problems.append(f"{path}: re-running the recipe on the parent does not reproduce the commit")
    diff = git(repo, "diff", "-U0", parent, commit).decode(errors="replace")
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else current
        elif line.startswith("--- a/"):
            current = line[6:]
        elif line[:1] in "+-" and not line.startswith(("+++", "---")) and "test" in current.lower() \
                and ASSERTION.search(line):
            notes.append(f"{current}: {line}")
    return problems, notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("commit")
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--count", required=True)
    args = parser.parse_args(argv[1:])
    problems, notes = check(Path("."), args.commit, args.recipe, args.count)
    for p in problems:
        print(p)
    for n in notes:
        print(f"for the reviewer, assertion line changed: {n}")
    if not problems:
        print(f"check_recipe_commit: {args.commit[:12]} reproduces, the test count is unchanged, "
              f"{len(notes)} assertion line(s) to confirm")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
