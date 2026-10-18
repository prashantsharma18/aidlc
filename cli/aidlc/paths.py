"""Where the framework lives, and where the repository being worked on lives."""
from __future__ import annotations

import os
from pathlib import Path


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
