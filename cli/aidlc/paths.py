"""Where the framework lives, and where the repository being worked on lives."""
from __future__ import annotations

import os
from pathlib import Path

CI_WORKFLOW = ".github/workflows/aidlc-verify.yml"


def framework_root() -> Path:
    """The framework checkout. AIDLC_HOME overrides it (used by tests)."""
    override = os.environ.get("AIDLC_HOME")
    if override:
        return Path(override).resolve()
    return Path(__file__).resolve().parents[2]


def find_repo_root(start: Path) -> Path:
    """The nearest directory at or above `start` that holds a .git entry."""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError(f"not inside a git repository: {start}")


def safe_target(repo: Path, rel: str) -> Path:
    """repo/rel for writing. Refuses absolute paths, '..', and any symlinked component
    (including a dangling final symlink), so nothing is written outside the repository."""
    root = repo.resolve()
    rel_path = Path(rel)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError(f"{rel}: must be a relative path inside the repository")
    current = root
    for part in rel_path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{rel}: '{current.relative_to(root)}' is a symlink; "
                             "refusing to write through it")
    return current
