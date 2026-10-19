"""Record this checkout's own `aidlc` entry point for the hooks.

The retry counter (core/hooks/post_check.py) accepts a PASS only from the framework's own entry
point, so a fake `aidlc` earlier on PATH cannot reset it. The file is machine-local, outside every
repository, under the sandbox's write deny on ~/.aidlc."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

NAME = "cli.json"


def home_dir() -> Path:
    return Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()


def entry_point() -> Path | None:
    """<framework root>/bin/aidlc, resolved; None when this checkout has no such file."""
    entry = Path(__file__).resolve().parents[2] / "bin" / "aidlc"
    return entry.resolve() if entry.is_file() else None


def write_cli_entry() -> Path | None:
    """Write $AIDLC_HOME_DIR/cli.json atomically. Never through a symlink: a symlinked target
    or home directory is refused. Returns the path, or None when nothing was written."""
    entry = entry_point()
    if entry is None:
        return None
    home = home_dir()
    target = home / NAME
    if home.is_symlink() or target.is_symlink():
        raise OSError(f"{target}: refusing to write through a symlink")
    home.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=home, prefix=".cli-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"entry": str(entry)}, fh)
    os.replace(tmp, target)
    return target
