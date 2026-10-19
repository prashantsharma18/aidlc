"""Shared test helpers. Commits disable the user's global git hooks."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import tempfile
from pathlib import Path

GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "user.name=aidlc-test",
       "-c", "user.email=aidlc-test@example.invalid", "-c", "commit.gpgsign=false"]


def git(root: Path, *args: str) -> str:
    result = subprocess.run([*GIT, *args], cwd=root, check=True,
                            capture_output=True, text=True)
    return result.stdout.strip()


class TempRepo:
    """A throwaway git repository. Files are committed when given."""

    def __init__(self, files: dict[str, str] | None = None):
        self._files = files or {}
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory(prefix="aidlc-test-")
        root = Path(self._tmp.name)
        git(root, "init", "-q", "-b", "main")
        for rel, content in self._files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        if self._files:
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "fixture")
        return root

    def __exit__(self, *exc: object) -> None:
        assert self._tmp is not None
        self._tmp.cleanup()


def run_cli(*args: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run aidlc.cli.main in-process; returns (exit code, stdout, stderr)."""
    from aidlc.cli import main

    out, err = io.StringIO(), io.StringIO()
    old = Path.cwd()
    try:
        if cwd is not None:
            os.chdir(cwd)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(args))
            except SystemExit as exc:  # argparse exits on --help/--version/errors
                code = int(exc.code or 0)
    finally:
        os.chdir(old)
    return code, out.getvalue(), err.getvalue()
