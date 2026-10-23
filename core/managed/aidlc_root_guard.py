#!/usr/bin/env python3
"""aidlc root guard: a machine-level PreToolUse hook, installed by the organisation through Claude
Code's managed settings (docs/harness/root-guard.md).

Claude Code loads a repository's .claude/settings.json only when the session starts at that
repository's root. A session started in a subdirectory, or one that works on an aidlc repository's
files from another folder, runs with none of that repository's permissions, sandbox or hooks
(verified 2026-10-19). This guard refuses every tool call whose working directory or target path is
inside an aidlc repository (a git root holding .aidlc/config.yaml) other than the folder where the
session started. "No objection" is no output. Any internal error exits 2, which blocks.

Limits: it sees the working directory and the file_path, notebook_path and path inputs. A shell
command that reaches another repository by its own path (cd /other && ...) is not parsed; that
repository's trusted CI still judges every change. Standard library only."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
MARKER = Path(".aidlc") / "config.yaml"
PATH_KEYS = ("file_path", "notebook_path", "path")


def aidlc_root(start: Path) -> Path | None:
    for candidate in (start, *start.parents):
        if (candidate / MARKER).is_file() and (candidate / ".git").exists():
            return candidate
    return None


def targets(payload: dict, cwd: Path) -> list[Path]:
    found = [cwd]
    tool_input = payload.get("tool_input")
    if isinstance(tool_input, dict):
        for key in PATH_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                path = Path(value).expanduser()
                found.append(path if path.is_absolute() else cwd / path)
    return found


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        cwd = Path(payload.get("cwd") or os.getcwd()).resolve()
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or cwd).resolve()
        for target in targets(payload, cwd):
            target = target.resolve()
            root = aidlc_root(target if target.is_dir() else target.parent)
            if root is not None and root != project:
                reason = (f"[aidlc root-guard] {root} is an aidlc repository, but this session started at "
                          f"{project}. Its harness (permissions, sandbox, hooks) loads only when Claude Code "
                          f"starts at the repository root: start a new session in {root}.")
                print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                         "permissionDecision": "deny",
                                                         "permissionDecisionReason": reason}}))
                return 0
        return 0
    except Exception as exc:  # noqa: BLE001 - exit 2 blocks in Claude Code
        print(f"aidlc root guard failed ({type(exc).__name__}); blocked to be safe", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
