#!/usr/bin/env python3
"""Claude Code adapter shim: translates Claude Code hook payloads to the generic contract and
back. Usage: claude_shim.py pre|post|post-failure. "No objection" is no output (never permissionDecision
"allow"). Any internal error exits 2, which Claude Code treats as a block; settings also set
onFailure: block so a crash or timeout blocks too."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never leave __pycache__ in the repository (post-check would flag it)
MAX_OUTPUT_CHARS = 5_000_000  # larger output is flagged unscanned, never passed
# Every tool reaches the pre hook (matcher ".*"). Read and control tools are class "read" and
# allowed by the guard; a tool missing here is class "unknown", which asks a person (deny when
# unattended). Keep this list in step with the tool's documented tool names.
READ_TOOLS = ("Read", "Glob", "Grep", "LS", "NotebookRead", "TodoWrite", "Task", "Agent", "ToolSearch",
              "BashOutput", "KillShell", "KillBash", "ExitPlanMode", "EnterPlanMode", "Skill",
              "SlashCommand", "AskUserQuestion", "ListMcpResourcesTool", "ReadMcpResourceTool",
              # Claude Code 2.1.296 built-ins: task list, language server, agent messages.
              "TaskCreate", "TaskUpdate", "TaskList", "TaskGet", "TaskStop", "TaskOutput", "LSP",
              "SendMessage")
CLASSES = {**{name: "read" for name in READ_TOOLS},
           "Edit": "edit", "Write": "edit", "MultiEdit": "edit", "NotebookEdit": "edit",
           "Bash": "shell", "Monitor": "shell", "WebFetch": "external", "WebSearch": "external"}


EXIT_CODE_RE = re.compile(r"Exit code (\d+)")


def _text(response) -> str:
    if isinstance(response, dict):
        return "\n".join(str(response.get(key) or "") for key in ("stdout", "stderr"))
    return response if isinstance(response, str) else json.dumps(response)


def to_generic(payload: dict, phase: str) -> dict:
    name = payload.get("tool_name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool_name is missing or not a string")
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
    if phase in ("post", "post-failure"):
        event["hook"] = "post-tool-check"
        if phase == "post":
            response = payload.get("tool_response")
            event["output"], event["text"], event["exit_code"] = json.dumps(response), _text(response), 0
        else:
            error = payload.get("error")
            error = error if isinstance(error, str) else json.dumps(error)
            match = EXIT_CODE_RE.match(error)
            event["output"], event["text"] = error, error
            event["exit_code"] = int(match.group(1)) if match else None
    return event


def main(argv: list[str]) -> int:
    guard = None
    payload = None
    try:
        phase = argv[1] if len(argv) > 1 else ""
        if phase not in ("pre", "post", "post-failure"):
            raise ValueError(f"phase must be pre, post or post-failure, got '{phase}'")
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import guard  # noqa: E402
        import post_check  # noqa: E402
        payload = json.loads(sys.stdin.read())
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        event = to_generic(payload, phase)
        if phase == "pre":
            result, version = guard._decide(event)
            guard._log(event, result, version)
            if result["decision"] in ("ask", "deny"):
                print(json.dumps({"hookSpecificOutput": {
                    "hookEventName": "PreToolUse", "permissionDecision": result["decision"],
                    "permissionDecisionReason": guard._redact(f"[aidlc {result['rule']}] {result['reason']}")}}))
            return 0
        attempt = post_check.record_check(event)
        if attempt is not None:
            guard._log({**event, "hook": "check-attempts"}, attempt)
        if len(event["output"]) > MAX_OUTPUT_CHARS:
            result = {"decision": "flag", "rule": "fail-safe",
                      "reason": "tool output too large to scan for credentials"}
        else:
            result = post_check.check(event)
        if result["decision"] != "flag" and attempt is not None and attempt["decision"] == "flag":
            result = attempt
        guard._log(event, result)
        if result["decision"] == "flag":
            print(json.dumps({"decision": "block",
                              "reason": guard._redact(f"[aidlc {result['rule']}] {result['reason']}")}))
        return 0
    except Exception as exc:  # noqa: BLE001 - exit 2 blocks in Claude Code
        detail = type(exc).__name__
        if guard is not None:
            try:
                detail = guard._redact(f"{type(exc).__name__}: {exc}")
                pre = phase == "pre"
                ids = payload if isinstance(payload, dict) else {}
                session, call = ids.get("session_id"), ids.get("tool_use_id")
                guard._log({"hook": "pre-tool-guard" if pre else "post-tool-check", "tool": None,
                            "session": session if isinstance(session, str) else None,
                            "call": call if isinstance(call, str) else None},
                           {"decision": "deny" if pre else "flag", "rule": "fail-safe",
                            "reason": f"aidlc hook failed ({detail}); blocked to be safe"})
            except Exception:  # noqa: BLE001 - logging must never change the outcome
                pass
        print(f"aidlc hook failed ({detail}); blocked to be safe", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
