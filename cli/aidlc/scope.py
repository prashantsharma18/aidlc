"""Task scope (guide 3 step 5): the read-only list of paths a task may change, generated
from the approved bundle's MAY CHANGE field at its approval commit. Fails closed."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path



PINNED_REF = re.compile(r"^[0-9a-f]{6,40}:[^:]+$")
FULL_SHA = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")      # what aidlc ci requires of an approval


class ScopeError(Exception):
    """No usable scope: the task must not start."""


class ScopeUsageError(ScopeError):
    """The command was used wrongly (not a repository, malformed approval line): exit 2."""


def _validate(patterns: list[str]) -> None:
    """Refuse patterns that reach outside the repository, into .git, or allow everything."""
    for pattern in patterns:
        parts = pattern.replace("\\", "/").split("/")
        if pattern.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", pattern):
            raise ScopeError(f"pattern '{pattern}' is absolute")
        if ".." in parts:
            raise ScopeError(f"pattern '{pattern}' leaves the repository")
        if ".git" in (part.casefold() for part in parts):
            raise ScopeError(f"pattern '{pattern}' reaches into .git")   # anywhere, as the guard
        if any(ch in pattern for ch in "<>()"):
            raise ScopeError(f"pattern '{pattern}' looks like an unfilled placeholder")
        if not pattern.strip("*/"):
            raise ScopeError(f"pattern '{pattern}' would allow every file")


def parse_may_change(text: str) -> list[str]:
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    collected, active, found = [], False, False
    for line in lines:
        if line.startswith("MAY CHANGE"):
            active, found = True, True
            collected.append(line[len("MAY CHANGE"):].lstrip().removeprefix(":"))
            continue
        if active and line and not line[0].isspace():
            break  # continuation lines are indented; anything else starts a new field
        if active:
            collected.append(line)
    if not found:
        raise ScopeError("no MAY CHANGE field in the bundle")
    joined = " ".join(collected)
    # A paren group is an annotation only when whitespace (or a comma) separates it from the paths.
    glued = re.search(r"\S*[^\s,(]\([^)]*\)\S*|\S*\([^)]*\)[^\s,]\S*", joined)
    if glued:
        raise ScopeError(f"'{glued.group(0)}': parentheses in a glob are not supported; write the "
                         "path without them or quote it in a note")
    joined = re.sub(r"\([^)]*\)", "", joined)
    patterns = [p.strip() for p in re.split(r"[,\s]+", joined) if p.strip()]
    if not patterns:
        raise ScopeError("MAY CHANGE field is empty")
    _validate(patterns)
    return patterns


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise ScopeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


# The evidence trusted checks read from the base branch: a base commit that touches one is flagged.
EVIDENCE = ("plans/approved-bundles.txt", "plans/approved-merges.txt", "test/allowed-skips.txt",
            "test/protected-exceptions.txt", ".aidlc/config.yaml", ".aidlc/permissions.yaml")
NO_DRIVERS = ("--no-textconv", "--no-ext-diff", "--no-renames", "--no-color")
_UNPRINTABLE = re.compile(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]")


def _plain_git(repo: Path, *args: str, ok: tuple[int, ...] = (0,)) -> tuple[int, str]:
    """git with no hooks, no signature display and no GIT_* environment; bytes are decoded here, so
    a \r stays a \r (never a line break). Raises ScopeError on any exit code not in `ok`."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "core.quotePath=false",
                          "-c", "log.showSignature=false", *args], cwd=repo, env=env, capture_output=True,
                         timeout=60)
    if out.returncode not in ok:
        raise ScopeError(f"git {' '.join(args[:2])}: {out.stderr.decode('utf-8', 'replace').strip()[:200]}")
    return out.returncode, out.stdout.decode("utf-8", "replace")


def base_moves(repo: Path, pinned: str, live: str, base_branch: str) -> list[str]:
    """What a person must review before trusting a moved base: every commit from the pinned base to
    the live one, `<sha> <author> <<email>> <subject>`, with `!` before each commit that touches an
    evidence file (EVIDENCE). Author and subject are the base's history, which an agent shell can
    forge, so control characters are replaced and nothing in them can start a new line. A pinned
    base that is not an ancestor of the live one (rewritten history) is said first, loudly."""
    lines = []
    code, _ = _plain_git(repo, "merge-base", "--is-ancestor", pinned, live, ok=(0, 1, 128))
    if code != 0:
        lines.append(f"WARNING: the scope's base {pinned} is not an ancestor of {base_branch} now ({live}): "
                     "the base branch's history was rewritten, or the old base is gone. Review it as new.")
    span = [live, f"^{pinned}"] if code == 0 else [live, "-n", "50"]
    _, listed = _plain_git(repo, "log", "-z", "--no-color", "--format=%H %an <%ae> %s", *span, "--")
    for entry in (e for e in listed.split("\0") if e):
        sha = entry.split(" ", 1)[0]
        _, touched = _plain_git(repo, "diff-tree", *NO_DRIVERS, "--no-commit-id", "--name-only", "-r", "-z",
                                "-m", "--root", sha, "--", *(f":(literal){p}" for p in EVIDENCE))
        hits = sorted({t for t in touched.split("\0") if t})
        text = _UNPRINTABLE.sub("?", entry)
        lines.append(f"! {text}  (touches {', '.join(hits)})" if hits else f"  {text}")
    if code != 0:
        lines.append(f"(the last {min(50, len(lines) - 1)} commit(s) of {base_branch} are shown)")
    return lines


def require_repository(repo: Path) -> Path:
    """The repository's top-level directory (the guard keys scopes by it), or ScopeUsageError."""
    if not repo.is_dir():
        raise ScopeUsageError(f"{repo} is not a directory")
    try:
        top = _git(repo, "rev-parse", "--show-toplevel").strip()
    except ScopeError as exc:
        raise ScopeUsageError(f"{repo} is not a git repository") from exc
    if not top:
        raise ScopeUsageError(f"{repo} has no working tree")
    return Path(top).resolve()


def base_commit(repo: Path, branch: str) -> str:
    """The commit the base branch points at now; recorded in the scope as the trust root."""
    sha = _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}").strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", sha):
        raise ScopeError(f"cannot resolve base branch '{branch}'")
    return sha


def bundle_at(repo: Path, ref: str) -> str:
    if ":" not in ref:
        raise ScopeError(f"bundle ref must be <commit>:<path>, got '{ref}'")
    return _git(repo, "show", ref)


def parse_approvals(text: str, branch: str, source: str) -> str:
    """The pinned `<sha>:<path>` approved for `branch` in an approvals file's text (the last
    matching line wins). Lines split on "\\n" only: \\f, \\v or U+2028 never start a new line."""
    match = None
    for line in text.split("\n"):
        parts = line.split()
        if len(parts) >= 2 and not line.startswith("#") and parts[0] == branch:
            match = parts[1]
    if match is None:
        raise ScopeError(f"no approved bundle for branch '{branch}' in {source}")
    if not PINNED_REF.fullmatch(match):
        raise ScopeUsageError(f"approval for '{branch}' must pin a commit sha (<sha>:<path>), got '{match}'")
    return match


def approved_ref(repo: Path, branch: str, approvals_ref: str = "main") -> str:
    text = _git(repo, "show", f"{approvals_ref}:plans/approved-bundles.txt")
    return parse_approvals(text, branch, f"{approvals_ref}:plans/approved-bundles.txt")


def default_scope_path(repo: Path, branch: str) -> Path:
    """Where the guard looks for the scope (core/hooks/guard.py scope_file)."""
    home = Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()
    return home / "scopes" / repo.name / (branch.replace("/", "__") + ".scope")


def write_scope(patterns: list[str], out: Path, base: str | None = None) -> None:
    """Write the read-only scope. `base` (a commit sha) is recorded as a `base:` line; the
    post-check diffs against it, so moving the local base branch later hides nothing."""
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out.parent, prefix=".scope-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write((f"base: {base}\n" if base else "") + "".join(f"{p}\n" for p in patterns))
    os.chmod(tmp, 0o444)
    os.replace(tmp, out)
