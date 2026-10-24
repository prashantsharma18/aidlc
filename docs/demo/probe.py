#!/usr/bin/env python3
"""Clean-harness probe for the shipment-tracking demo.

Reads Claude Code's stream-json init message on stdin and fails if anything but the aidlc harness
loaded: a plugin other than aidlc, aidlc-practice or Claude Code's own built-ins; a namespaced skill
from elsewhere that the folder's settings do not deny; an MCP server other than lab-jira.

  claude -p "Reply OK." --plugin-dir … --output-format stream-json --verbose --max-turns 1 \\
    | python3 docs/demo/probe.py .claude/settings.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

AIDLC = {"aidlc", "aidlc-practice"}
ALLOWED_MCP = {"lab-jira"}


def _denied(skill: str, deny: list[str]) -> bool:
    namespace = skill.split(":", 1)[0]
    return f"Skill({skill})" in deny or f"Skill({namespace} *)" in deny


def foreign(init: dict, deny: list[str]) -> list[str]:
    """Everything in the session that is not the aidlc harness, as 'kind name' strings."""
    out = []
    for p in init.get("plugins", []):
        source = p.get("source", p.get("name", "?")) if isinstance(p, dict) else str(p)
        name = p.get("name", source.split("@")[0]) if isinstance(p, dict) else source.split("@")[0]
        if name not in AIDLC and not source.endswith("@builtin"):
            out.append(f"plugin {source}")
    for s in init.get("skills") or init.get("slash_commands") or []:
        if ":" in s and s.split(":", 1)[0] not in AIDLC and not _denied(s, deny):
            out.append(f"skill {s}")
    for m in init.get("mcp_servers", []):
        if m.get("name") not in ALLOWED_MCP:
            out.append(f"mcp {m.get('name')}")
    return out


def read_init(lines) -> dict:
    """The stream's init message. Anything else first (hooks, retries) is skipped; no init is an error."""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        message = json.loads(line)
        if message.get("type") == "system" and message.get("subtype") == "init":
            return message
    raise ValueError("no init message in the stream: cannot tell what loaded")


def main(argv: list[str]) -> int:
    try:
        init = read_init(sys.stdin)
    except ValueError as exc:
        print(f"NOT CLEAN: {exc}")
        return 1
    deny = []
    if len(argv) > 1:
        deny = json.loads(Path(argv[1]).read_text(encoding="utf-8"))["permissions"]["deny"]
    print("plugins:", sorted(p.get("source", "?") if isinstance(p, dict) else p for p in init.get("plugins", [])))
    print("mcp servers:", sorted(m.get("name", "?") for m in init.get("mcp_servers", [])))
    found = foreign(init, deny)
    if found:
        print("NOT CLEAN:", ", ".join(found))
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
