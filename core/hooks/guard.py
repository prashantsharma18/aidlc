#!/usr/bin/env python3
"""aidlc pre-tool guard (guide chapter 3, step 5). Standard library only; no network.

Generic contract (docs/adapters/interface.md):
  stdin   {"session": str, "call": str, "tool": "read|edit|shell|mcp|external", "args": {...}, "cwd": str}
  stdout  {"decision": "allow|ask|deny", "rule": str, "reason": str}
"allow" means "no objection": permissions and the sandbox still apply. Fails closed: any error,
unreadable input, missing harness data or missing task scope gives "deny".
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRET_RE = re.compile(r"(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
                       r"|sk-ant-[A-Za-z0-9_-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)")
SPLIT_RE = re.compile(r"&&|\|\||;|\|&|\||&|\n")
SUBST_RE = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")
PIPE_TO_SHELL_RE = re.compile(r"\|\s*(sudo\s+)?(ba|z|da|k)?sh(\s|$)")
NESTED_RE = re.compile(r"^(bash|sh|zsh|dash)\s+-c\b|^eval\s")
GIT_OPTS_RE = re.compile(r"^git((\s+-C\s+\S+)|(\s+-c\s+\S+))+\s+")
ENV_PREFIX_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*=\S*\s+)+")


def _result(decision: str, rule: str, reason: str) -> dict:
    return {"decision": decision, "rule": rule, "reason": reason}


def _unattended() -> bool:
    return os.environ.get("AIDLC_UNATTENDED") == "1"


def _ask(rule: str, reason: str) -> dict:
    if _unattended():
        return _result("deny", rule, reason + " (unattended run: ask means deny)")
    return _result("ask", rule, reason)


def load_harness() -> dict:
    path = Path(os.environ.get("AIDLC_HARNESS_FILE") or HERE / "harness.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    for key in ("protected_paths", "shell_deny", "tool_deny", "tool_ask"):
        if not isinstance(data.get(key), list):
            raise ValueError(f"harness data lacks '{key}'")
    return data


def matches(path: str, patterns: list[str], any_depth_names: bool = True) -> bool:
    for pat in patterns:
        if pat.startswith("~"):
            continue                          # home patterns apply outside the repository
        if fnmatch.fnmatchcase(path, pat):
            return True
        if pat.startswith("**/") and fnmatch.fnmatchcase(path, pat[3:]):
            return True
        if pat.endswith("/**") and path == pat[:-3]:
            return True
        if any_depth_names and "/" not in pat and fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], pat):
            return True
    return False


def repo_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def current_branch(root: Path) -> str | None:
    dotgit = root / ".git"
    if dotgit.is_file():                       # a worktree: ".git" names the real git dir
        text = dotgit.read_text(encoding="utf-8").strip()
        if not text.startswith("gitdir:"):
            return None
        gitdir = (root / text[len("gitdir:"):].strip()).resolve()
    else:
        gitdir = dotgit
    head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    prefix = "ref: refs/heads/"
    return head[len(prefix):] if head.startswith(prefix) else None


def scope_file(root: Path, branch: str) -> Path:
    explicit = os.environ.get("AIDLC_SCOPE_FILE")
    if explicit:
        return Path(explicit).expanduser()
    home = Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()
    return home / "scopes" / root.name / (branch.replace("/", "__") + ".scope")


def load_scope(root: Path) -> list[str] | None:
    branch = current_branch(root)
    if not branch:
        return None
    path = scope_file(root, branch)
    if path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        return None
    patterns = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    return patterns or None


def _decide_edit(event: dict, data: dict) -> dict:
    raw = (event.get("args") or {}).get("path")
    if not isinstance(raw, str) or not raw:
        return _result("deny", "fail-safe", "edit without a path")
    cwd = Path(event.get("cwd") or os.getcwd())
    root = repo_root(cwd)
    if root is None:
        return _result("deny", "outside-repo", "not inside a git repository")
    target = Path(raw) if Path(raw).is_absolute() else cwd / raw
    resolved = Path(os.path.realpath(target))
    try:
        rel = resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return _result("deny", "outside-repo", f"{raw} is outside the repository")
    if matches(rel, data["protected_paths"]):
        return _result("deny", "protected-path", f"{rel} is protected (harness, rules, CI, plans "
                       "or contracts). Do not work around it; describe the need in your notes.")
    if os.environ.get("AIDLC_SCOPE") == "off":
        if _unattended():
            return _result("deny", "no-scope", "AIDLC_SCOPE=off is refused in unattended runs")
        return _result("allow", "scope-off", "task scope switched off by AIDLC_SCOPE=off (logged)")
    scope = load_scope(root)
    if scope is None:
        branch = current_branch(root) or "<detached>"
        return _result("deny", "no-scope", f"no task scope for branch '{branch}': run "
                       f"`aidlc scope --branch {branch}` after the bundle is approved")
    if not matches(rel, scope, any_depth_names=False):
        return _result("deny", "outside-scope", f"{rel} is outside this task's MAY CHANGE list. "
                       "Stop and ask if the change is needed.")
    return _result("allow", "in-scope", "inside the task scope")


def _parts(command: str) -> list[str]:
    parts = []
    for inner in SUBST_RE.findall(command):
        parts += _parts(inner[0] or inner[1])
    for part in SPLIT_RE.split(command):
        part = part.strip().lstrip("(").strip()
        if part:
            part = ENV_PREFIX_RE.sub("", part)
            parts.append(GIT_OPTS_RE.sub("git ", part))
    return parts


def _decide_shell(event: dict, data: dict) -> dict:
    command = (event.get("args") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return _result("deny", "fail-safe", "shell call without a command")
    if PIPE_TO_SHELL_RE.search(command):
        return _result("deny", "pipe-to-shell", "piping into a shell is not allowed")
    for part in _parts(command):
        for pat in data["shell_deny"]:
            if fnmatch.fnmatchcase(part, pat):
                return _result("deny", "shell-deny", f"'{part[:80]}' matches the denied pattern '{pat}'")
        if NESTED_RE.search(part):
            return _ask("nested-shell", "a nested shell hides its command; a person must read it")
    return _result("allow", "no-guarded-command", "no guarded command found")


def decide(event: dict) -> dict:
    try:
        data = load_harness()
    except Exception as exc:  # noqa: BLE001 - any failure here must block
        return _result("deny", "fail-safe", f"harness data unreadable ({type(exc).__name__}); "
                       "run `aidlc render --tool claude-code`")
    try:
        tool = event.get("tool")
        if tool == "read":
            return _result("allow", "read", "read-only; secrets are left to permissions and sandbox")
        if tool == "edit":
            return _decide_edit(event, data)
        if tool == "shell":
            return _decide_shell(event, data)
        if tool == "mcp":
            name = str((event.get("args") or {}).get("name", ""))
            if any(fnmatch.fnmatchcase(name, p) for p in data["tool_deny"]):
                return _result("deny", "tool-deny", f"{name} is denied by policy")
            if any(fnmatch.fnmatchcase(name, p) for p in data["tool_ask"]):
                return _ask("tool-ask", f"{name} needs a person's approval")
            return _result("allow", "integration", "integration call; permissions decide")
        if tool == "external":
            return _ask("external", "reaching outside the workspace needs a person's approval")
        return _result("deny", "unknown-tool", f"unknown tool class '{tool}'")
    except Exception as exc:  # noqa: BLE001
        return _result("deny", "fail-safe", f"guard error ({type(exc).__name__}); blocked to be safe")


def _log(event: dict, result: dict) -> None:
    try:
        try:
            version = load_harness().get("version", "unknown")
        except Exception:  # noqa: BLE001
            version = "unknown"
        args = event.get("args") or {}
        target = str(args.get("path") or args.get("command") or args.get("name") or args.get("url") or "")
        record = {"ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                  "hook": "pre-tool-guard", "session": event.get("session"), "call": event.get("call"),
                  "harness": version, "tool": event.get("tool"),
                  "target": SECRET_RE.sub("[REDACTED]", target)[:200], **result}
        logdir = Path(os.environ.get("AIDLC_LOG_DIR") or "~/.aidlc/logs").expanduser()
        logdir.mkdir(parents=True, exist_ok=True)
        with (logdir / "decisions.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001 - logging must never change the decision
        pass


def main() -> int:
    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
        result = decide(event)
    except Exception:  # noqa: BLE001
        event, result = {}, _result("deny", "fail-safe", "unreadable tool call")
    _log(event, result)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
