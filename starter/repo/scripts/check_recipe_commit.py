#!/usr/bin/env python3
"""Checks a mechanical recipe commit, the one exception to aidlc's gates (ADR 0012): re-running the approved recipe
on the commit's parent gives exactly the commit's files, the test count is the same before and after, and the commit
names the tool. Lists every changed assertion line so the reviewer can confirm that what it checks did not change.

    python3 scripts/check_recipe_commit.py <commit> --recipe "<command>" --count "<command>"

--recipe is the command the task bundle's RECIPE field approved; --count prints the number of tests (its last integer
is read). Both run in temporary copies made with `git archive`, never in your checkout. Exit 1 on any problem.
Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

TRAILER = re.compile(r"^Recipe: \S+@\S+\s*$", re.MULTILINE)
ASSERTION = re.compile(r"\bAssert\.|\bassert\b|\bexpect\(|\.Should\(|\bShould\.")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def extract(repo: Path, rev: str, into: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", rev))) as tar:
        tar.extractall(into, filter="data")


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def count_tests(command: str, folder: Path) -> tuple[int | None, str]:
    result = subprocess.run(command, shell=True, cwd=folder, capture_output=True, text=True)
    numbers = re.findall(r"\d+", result.stdout)
    return (int(numbers[-1]) if result.returncode == 0 and numbers else None), result.stderr[-500:]


def check(repo: Path, commit: str, recipe: str, count: str) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    parents = git(repo, "rev-list", "--parents", "-n", "1", commit).decode().split()
    if len(parents) != 2:
        return [f"{commit[:12]}: a recipe commit has exactly one parent"], []
    parent = parents[1]
    if not TRAILER.search(git(repo, "log", "-1", "--format=%B", commit).decode()):
        problems.append(f"{commit[:12]}: the message needs the trailer 'Recipe: <tool>@<version>'")
    with tempfile.TemporaryDirectory() as tmp:
        rerun, before, after = Path(tmp, "rerun"), Path(tmp, "before"), Path(tmp, "after")
        for folder, rev in ((rerun, parent), (before, parent), (after, commit)):
            folder.mkdir()
            extract(repo, rev, folder)
        run = subprocess.run(recipe, shell=True, cwd=rerun, capture_output=True, text=True)
        if run.returncode != 0:
            problems.append(f"the recipe failed on the parent (exit {run.returncode}): {run.stderr[-300:]}")
        else:
            expected, actual = tree(after), tree(rerun)
            for path in sorted(set(expected) | set(actual)):
                if expected.get(path) != actual.get(path):
                    problems.append(f"{path}: re-running the recipe on the parent does not reproduce the commit")
        n_before, err_before = count_tests(count, before)
        n_after, err_after = count_tests(count, after)
        if n_before is None or n_after is None:
            problems.append(f"the count command failed: {(err_before or err_after).strip()}")
        elif n_before != n_after:
            problems.append(f"the test count changed: {n_before} before, {n_after} after")
    diff = git(repo, "diff", "-U0", parent, commit).decode(errors="replace")
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
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
