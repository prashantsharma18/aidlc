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
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}"
    r"|(?i:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S{6,})")
OP_RE = re.compile(r"&>>?|[<>][<>&|]*|[;&|()]+")
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
RESERVED = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
# wrapper -> options that take a separate argument
WRAPPERS = {"command": set(), "builtin": set(), "exec": {"-a"}, "env": {"-u", "-C", "-S", "--split-string"},
            "nohup": set(), "nice": {"-n"}, "time": {"-f", "-o"},
            "timeout": {"-s", "-k"}, "xargs": {"-n", "-L", "-I", "-P", "-s", "-d", "-E", "-a"},
            "stdbuf": {"-i", "-o", "-e"}, "watch": {"-n"}}
GIT_ARG_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}


def _redact(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text)


def _result(decision: str, rule: str, reason: str) -> dict:
    return {"decision": decision, "rule": rule, "reason": _redact(reason)}


def _unattended() -> bool:
    value = os.environ.get("AIDLC_UNATTENDED", "").strip().lower()
    return value not in ("", "0", "false", "no")


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


def _glob_regex(pat: str) -> "re.Pattern[str]":
    """Segment-aware glob: '*' and '?' stay inside one path segment; only '**' crosses '/'."""
    out, i = [], 0
    while i < len(pat):
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("/**", i) and i + 3 == len(pat):
            out.append("(?:/.*)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif pat[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pat[i] == "?":
            out.append("[^/]")
            i += 1
        elif pat[i] == "[" and pat.find("]", i + 2) != -1:
            j = pat.index("]", i + 2)
            body = pat[i + 1:j]
            neg = body.startswith("!")
            body = body[1:] if neg else body
            out.append("[" + ("^/" if neg else "") + body.replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(pat[i]))
            i += 1
    return re.compile("".join(out), re.DOTALL)


def matches(path: str, patterns: list[str], any_depth_names: bool = True) -> bool:
    for pat in patterns:
        if pat.startswith("~"):
            continue                          # home patterns apply outside the repository
        rx = _glob_regex(pat)
        if rx.fullmatch(path):
            return True
        if any_depth_names and "/" not in pat and rx.fullmatch(path.rsplit("/", 1)[-1]):
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
    for pat in patterns:
        segments = pat.replace("\\", "/").split("/")
        if pat.startswith(("/", "~")) or ".." in segments or ".git" in (x.casefold() for x in segments):
            return None                       # a scope may not reach outside or into .git
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
    if ".git" in (seg.casefold() for seg in rel.split("/")):
        return _result("deny", "protected-path", f"{rel} is inside .git; git internals are protected")
    if matches(rel.casefold(), [p.casefold() for p in data["protected_paths"]]):
        return _result("deny", "protected-path", f"{rel} is protected (harness, rules, CI, plans "
                       "or contracts). Do not work around it; describe the need in your notes.")
    if resolved.is_file() and resolved.stat().st_nlink > 1:
        return _result("deny", "hard-link", f"{rel} has several hard links; one may be a protected file")
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


def _substitutions(command: str) -> tuple[str, list[str]]:
    """Return the command with $(..), <(..), >(..) and `..` replaced by a placeholder, plus
    the inner texts. Parentheses are balanced; an unclosed one takes the rest of the string."""
    outer, inners, i = [], [], 0
    while i < len(command):
        two = command[i:i + 2]
        if two in ("$(", "<(", ">("):
            start, depth, j = i + 2, 1, i + 2
            while j < len(command) and depth:
                depth += {"(": 1, ")": -1}.get(command[j], 0)
                j += 1
            inners.append(command[start:j - 1 if depth == 0 else j])
            outer.append(" SUBST ")
            i = j
        elif command[i] == "`":
            j = command.find("`", i + 1)
            j = len(command) if j == -1 else j
            inners.append(command[i + 1:j])
            outer.append(" SUBST ")
            i = j + 1
        else:
            outer.append(command[i])
            i += 1
    return "".join(outer), inners


def _lex(text: str) -> list[tuple[str, str]]:
    """Quote-aware tokeniser: ("word", value), ("sep", op) or ("redir", op). Raises ValueError
    on unbalanced quotes. Quoted operators stay words; unquoted newlines are separators."""
    out: list[tuple[str, str]] = []
    buf: list[str] = []
    state = {"in": False, "quoted": False}

    def flush(next_char: str = "") -> None:
        if state["in"]:
            word = "".join(buf)
            fd_number = word.isdigit() and not state["quoted"] and next_char in ("<", ">")
            if not fd_number:
                out.append(("word", word))
        buf.clear()
        state["in"] = state["quoted"] = False

    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            if i + 1 < n and text[i + 1] == "\n":
                i += 2
                continue
            buf.append(text[i + 1] if i + 1 < n else "\\")
            state["in"] = state["quoted"] = True
            i += 2
        elif c == "'":
            j = text.find("'", i + 1)
            if j == -1:
                raise ValueError("unterminated single quote")
            buf.append(text[i + 1:j])
            state["in"] = state["quoted"] = True
            i = j + 1
        elif c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\\" and j + 1 < n:
                    if text[j + 1] in '"\\$`':
                        buf.append(text[j + 1])
                    elif text[j + 1] != "\n":
                        buf.append(text[j:j + 2])
                    j += 2
                else:
                    buf.append(text[j])
                    j += 1
            if j >= n:
                raise ValueError("unterminated double quote")
            state["in"] = state["quoted"] = True
            i = j + 1
        elif c in " \t":
            flush()
            i += 1
        elif c == "\n":
            flush()
            out.append(("sep", "\n"))
            i += 1
        elif c in ";&|<>()":
            flush(c if c in "<>" else "")
            match = OP_RE.match(text, i)
            op = match.group(0)
            out.append(("redir" if op[0] in "<>" or op.startswith("&>") else "sep", op))
            i += len(op)
        else:
            buf.append(c)
            state["in"] = True
            i += 1
    flush()
    return out


def _segments(text: str) -> list[dict]:
    """Split a command into segments of words; redirections and their targets are dropped."""
    segments: list[dict] = []
    current = {"words": [], "piped": False, "stdin": False}
    piped_next = False
    tokens = _lex(text)
    skip_target = False
    for kind, value in tokens:
        if skip_target:
            skip_target = False
            if kind == "word":
                continue
        if kind == "word":
            current["words"].append(value)
        elif kind == "redir":
            current["stdin"] = current["stdin"] or value.startswith("<")
            skip_target = True
        else:
            segments.append(current)
            piped_next = value in ("|", "|&")
            current = {"words": [], "piped": piped_next, "stdin": False}
    segments.append(current)
    return [seg for seg in segments if seg["words"]]


def _argv(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Strip assignments, reserved words and wrappers; normalise argv0 and git options.
    The list holds command strings supplied by `env -S`, which are analysed too."""
    nested: list[str] = []
    changed = True
    while tokens and changed:
        changed = False
        head = tokens[0]
        if ASSIGN_RE.match(head) or head in RESERVED:
            tokens, changed = tokens[1:], True
            continue
        name = head.rsplit("/", 1)[-1]
        if name in WRAPPERS:
            takes_arg, rest = WRAPPERS[name], tokens[1:]
            while rest and (rest[0].startswith("-") or ASSIGN_RE.match(rest[0])):
                if name == "env" and (rest[0].startswith("-S") or rest[0].startswith("--split-string")):
                    opt = rest[0]
                    nested.append(opt[2:] if opt.startswith("-S") and len(opt) > 2 else
                                  opt.split("=", 1)[1] if "=" in opt else
                                  (rest[1] if len(rest) > 1 else ""))
                rest = rest[2:] if rest[0] in takes_arg else rest[1:]
            if name == "timeout" and rest:
                rest = rest[1:]                       # the duration
            elif name == "nice" and rest and re.fullmatch(r"-?\d+", rest[0]):
                rest = rest[1:]
            tokens, changed = rest, True
    if not tokens:
        return tokens, nested
    tokens = [tokens[0].rsplit("/", 1)[-1], *tokens[1:]]
    if tokens[0] == "git":
        rest = tokens[1:]
        while rest and rest[0].startswith("-"):
            rest = rest[2:] if rest[0] in GIT_ARG_OPTS else rest[1:]
        tokens = ["git", *rest]
    return tokens, nested


def _is_recursive_rm(argv: list[str]) -> bool:
    for tok in argv[1:]:
        if tok == "--":
            return False
        if tok.startswith("--"):
            if len(tok) >= 3 and "--recursive".startswith(tok.split("=")[0]):
                return True
        elif tok.startswith("-") and ("{" in tok or re.search("[rR]", tok)):
            return True
    return False


def _check_segment(words: list[str], piped: bool, stdin: bool, patterns: list[str],
                   asks: list[dict], pending: list[str]) -> dict | None:
    argv, env_split = _argv(words)
    if not argv:
        if env_split:
            asks.append(_ask("nested-shell", "a nested shell hides its command; a person must read it"))
        return None
    joined = " ".join(argv)
    for pat in patterns:
        if fnmatch.fnmatchcase(joined, pat):
            return _result("deny", "shell-deny", f"'{_redact(joined)[:80]}' matches the denied pattern '{pat}'")
    if argv[0] == "rm" and _is_recursive_rm(argv):
        return _result("deny", "recursive-delete", "recursive rm is not allowed")
    if argv[0] in SHELLS and piped:
        return _result("deny", "pipe-to-shell", "piping into a shell is not allowed")
    if argv[0] in SHELLS:
        for index, tok in enumerate(argv[1:], start=1):
            if tok.startswith("-") and not tok.startswith("--") and "c" in tok:
                if index + 1 < len(argv):
                    pending.append(argv[index + 1])        # the script text is analysed too
                break
    elif argv[0] == "eval":
        pending.append(" ".join(argv[1:]))
    if (argv[0] in SHELLS and (len(argv) > 1 or stdin)) or argv[0] in ("eval", "source", ".") or env_split:
        asks.append(_ask("nested-shell", "a nested shell hides its command; a person must read it"))
    return None


def _decide_shell(event: dict, data: dict) -> dict:
    command = (event.get("args") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return _result("deny", "fail-safe", "shell call without a command")
    patterns = [" ".join(p.split()) for p in data["shell_deny"]]
    asks: list[dict] = []
    pending, seen = [command], 0
    while pending:
        seen += 1
        if seen > 200:
            return _result("deny", "fail-safe", "command too deeply nested to inspect")
        outer, inners = _substitutions(pending.pop())
        pending += inners
        try:
            segments = _segments(outer)
        except ValueError:
            asks.append(_ask("unparseable", "a command part could not be parsed; a person must read it"))
            crude = re.sub(r"[\"']", " ", outer)
            segments = [{"words": part.split(), "piped": False, "stdin": False}
                        for part in re.split(r"[;&|()<>\n]+", crude)]
        for seg in segments:
            denied = _check_segment(seg["words"], seg["piped"], seg["stdin"], patterns, asks, pending)
            if denied:
                return denied
    return asks[0] if asks else _result("allow", "no-guarded-command", "no guarded command found")


def decide(event: dict) -> dict:
    return _decide(event)[0]


def _decide(event: dict) -> tuple[dict, str]:
    """Return (decision, harness version). The version comes from the data actually used."""
    try:
        data = load_harness()
    except Exception as exc:  # noqa: BLE001 - any failure here must block
        return _result("deny", "fail-safe", f"harness data unreadable ({type(exc).__name__}); "
                       "run `aidlc render --tool claude-code`"), "unknown"
    return _decide_with(event, data), str(data.get("version", "unknown"))


def _decide_with(event: dict, data: dict) -> dict:
    try:
        tool = event.get("tool")
        if tool == "read":
            return _result("allow", "read", "read-only; secrets are left to permissions and sandbox")
        if tool == "edit":
            return _decide_edit(event, data)
        if tool == "shell":
            return _decide_shell(event, data)
        if tool == "mcp":
            name = (event.get("args") or {}).get("name")
            if not isinstance(name, str) or not name.strip():
                return _result("deny", "fail-safe", "mcp call without a tool name")
            name = name.strip()
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


def _log(event: dict, result: dict, version: str | None = None) -> None:
    try:
        if version is None:
            try:
                version = str(load_harness().get("version", "unknown"))
            except Exception:  # noqa: BLE001
                version = "unknown"
        args = event.get("args") or {}
        target = str(args.get("path") or args.get("command") or args.get("name") or args.get("url") or "")
        record = {"ts": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
                  "hook": "pre-tool-guard", "session": event.get("session"), "call": event.get("call"),
                  "harness": version, "tool": event.get("tool"),
                  "target": _redact(target)[:200], **result}
        record = {k: (_redact(v) if isinstance(v, str) else v) for k, v in record.items()}
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
        result, version = _decide(event)
    except Exception:  # noqa: BLE001
        event, result, version = {}, _result("deny", "fail-safe", "unreadable tool call"), "unknown"
    _log(event, result, version)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
