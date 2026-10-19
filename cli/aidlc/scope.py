"""Task scope (guide 3 step 5): the read-only list of paths a task may change, generated
from the approved bundle's MAY CHANGE field at its approval commit. Fails closed."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path



PINNED_REF = re.compile(r"^[0-9a-f]{6,40}:[^:]+$")


class ScopeError(Exception):
    """No usable scope: the task must not start."""


def _validate(patterns: list[str]) -> None:
    """Refuse patterns that reach outside the repository, into .git, or allow everything."""
    for pattern in patterns:
        parts = pattern.replace("\\", "/").split("/")
        if pattern.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", pattern):
            raise ScopeError(f"pattern '{pattern}' is absolute")
        if ".." in parts:
            raise ScopeError(f"pattern '{pattern}' leaves the repository")
        if parts[0] == ".git":
            raise ScopeError(f"pattern '{pattern}' reaches into .git")
        if not pattern.strip("*/"):
            raise ScopeError(f"pattern '{pattern}' would allow every file")


def parse_may_change(text: str) -> list[str]:
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    collected, active, found = [], False, False
    for line in lines:
        if line.startswith("MAY CHANGE"):
            active, found = True, True
            collected.append(line[len("MAY CHANGE"):])
            continue
        if active and line and not line[0].isspace():
            break  # continuation lines are indented; anything else starts a new field
        if active:
            collected.append(line)
    if not found:
        raise ScopeError("no MAY CHANGE field in the bundle")
    joined = re.sub(r"\([^)]*\)", "", " ".join(collected))
    patterns = [p.strip() for p in re.split(r"[,\s]+", joined) if p.strip()]
    if not patterns:
        raise ScopeError("MAY CHANGE field is empty")
    _validate(patterns)
    return patterns


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if result.returncode != 0:
        raise ScopeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def bundle_at(repo: Path, ref: str) -> str:
    if ":" not in ref:
        raise ScopeError(f"bundle ref must be <commit>:<path>, got '{ref}'")
    return _git(repo, "show", ref)


def approved_ref(repo: Path, branch: str, approvals_ref: str = "main") -> str:
    text = _git(repo, "show", f"{approvals_ref}:plans/approved-bundles.txt")
    match = None
    for line in text.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("#") and parts[0] == branch:
            match = parts[1]
    if match is None:
        raise ScopeError(f"no approved bundle for branch '{branch}' in "
                         f"{approvals_ref}:plans/approved-bundles.txt")
    if not PINNED_REF.match(match):
        raise ScopeError(f"approval for '{branch}' must pin a commit sha (<sha>:<path>), got '{match}'")
    return match


def write_scope(patterns: list[str], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=".scope-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("".join(f"{p}\n" for p in patterns))
    os.chmod(tmp, 0o444)
    os.replace(tmp, out)
