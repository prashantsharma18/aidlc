#!/usr/bin/env python3
"""Claude Code adapter shim: translates Claude Code hook payloads to the generic contract and
back. Usage: claude_shim.py pre|post. "No objection" is no output (never permissionDecision
"allow"). Any internal error exits 2, which Claude Code treats as a block; settings also set
onFailure: block so a crash or timeout blocks too."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

CLASSES = {"Read": "read", "Glob": "read", "Grep": "read", "LS": "read",
           "Edit": "edit", "Write": "edit", "MultiEdit": "edit", "NotebookEdit": "edit",
           "Bash": "shell", "WebFetch": "external", "WebSearch": "external"}


def to_generic(payload: dict, phase: str) -> dict:
    name = str(payload.get("tool_name") or "")
    inp = payload.get("tool_input")
    if inp is None:
        inp = {}
    if not isinstance(inp, dict):
        raise ValueError("tool_input is not an object")
    if name.startswith("mcp__"):
        tool, args = "mcp", {"name": name}
    else:
        tool = CLASSES.get(name, "unknown")
        if tool == "edit":
            args = {"path": inp.get("notebook_path") if name == "NotebookEdit" else inp.get("file_path")}
        elif tool == "shell":
            args = {"command": inp.get("command")}
        elif tool == "read":
            args = {"path": inp.get("file_path") or inp.get("path") or inp.get("pattern")}
        elif tool == "external":
            args = {"url": inp.get("url") or inp.get("query")}
        else:
            args = {}
    event = {"session": payload.get("session_id"), "call": payload.get("tool_use_id"),
             "tool": tool, "args": args, "cwd": payload.get("cwd") or os.getcwd()}
    if phase == "post":
        event["output"] = json.dumps(payload.get("tool_response"))[:200_000]
        event["hook"] = "post-tool-check"
    return event


def main(argv: list[str]) -> int:
    guard = None
    try:
        phase = argv[1] if len(argv) > 1 else ""
        if phase not in ("pre", "post"):
            raise ValueError(f"phase must be pre or post, got '{phase}'")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import guard  # noqa: E402
        import post_check  # noqa: E402
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        event = to_generic(payload, phase)
        if phase == "pre":
            result = guard.decide(event)
            guard._log(event, result)
            if result["decision"] in ("ask", "deny"):
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": result["decision"],
                    "permissionDecisionReason": guard._redact(f"[aidlc {result['rule']}] {result['reason']}")}}))
            return 0
        result = post_check.check(event)
        guard._log(event, result)
        if result["decision"] == "flag":
            print(json.dumps({"decision": "block", "reason": guard._redact(f"[aidlc {result['rule']}] {result['reason']}")}))
        return 0
    except Exception as exc:  # noqa: BLE001 - exit 2 blocks in Claude Code
        detail = type(exc).__name__
        if guard is not None:
            try:
                detail = guard._redact(f"{type(exc).__name__}: {exc}")
            except Exception:  # noqa: BLE001
                pass
        print(f"aidlc hook failed ({detail}); blocked to be safe", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
