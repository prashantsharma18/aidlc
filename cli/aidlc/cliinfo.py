"""Record this checkout's own `aidlc` entry point for the hooks, per repository.

The retry counter (core/hooks/post_check.py) credits a PASS only for the exact recorded entry
path, so a fake `aidlc` cannot reset it. The record is $AIDLC_HOME_DIR/entry/<repo>-<hash8>.json,
outside every repository and under the sandbox's write deny on ~/.aidlc. Render refuses to record
an entry the agent could rewrite: inside the repository, a sandbox allowWrite path or a temp
directory."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .hookbridge import hooks

TEMP_ROOTS = ("/tmp", "/var/tmp", "/dev/shm")


def entry_point() -> Path | None:
    """<framework root>/bin/aidlc, resolved; None when this checkout has no such file."""
    entry = Path(__file__).resolve().parents[2] / "bin" / "aidlc"
    return entry.resolve() if entry.is_file() else None


def writable_roots(repo: Path, allow_write: list[str]) -> list[str]:
    """Every place an agent shell can write, as real paths: the repository, each sandbox allowWrite
    path rendered for it (`~` expanded, relative paths against the repository), the temp directories
    and $TMPDIR."""
    roots = [str(repo), *TEMP_ROOTS]
    if os.environ.get("TMPDIR"):
        roots.append(os.environ["TMPDIR"])
    for item in allow_write:
        path = Path(item).expanduser()
        roots.append(str(path if path.is_absolute() else repo / path))
    return sorted({os.path.realpath(r) for r in roots})


def _under(path: str, roots: list[str]) -> bool:
    return any(path == r or path.startswith(r.rstrip("/") + "/") for r in roots)


def record_entry(repo: Path, allow_write: list[str]) -> tuple[str, str | None]:
    """Record the entry point for this repository. Returns (status, entry): "recorded", "missing"
    (no bin/aidlc, nothing written) or "refused" (a location the agent can write; any stale record
    is removed). Written atomically, never through a symlink."""
    guard = hooks().guard
    target = guard.entry_file(repo)
    if target.parent.is_symlink() or target.is_symlink():
        raise OSError(f"{target}: refusing to write through a symlink")
    entry = entry_point()
    if entry is None:
        return "missing", None
    real = os.path.realpath(entry)
    if _under(real, writable_roots(repo, allow_write)):
        target.unlink(missing_ok=True)
        return "refused", real
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".entry-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"entry": real}, fh)
    os.replace(tmp, target)
    return "recorded", real
