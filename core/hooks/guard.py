#!/usr/bin/env python3
"""aidlc pre-tool guard (guide chapter 3, step 5). Standard library only; no network.

Generic contract (docs/adapters/interface.md):
  stdin   {"session": str, "call": str, "tool": "read|edit|shell|mcp|external", "args": {...}, "cwd": str}
  stdout  {"decision": "allow|ask|deny", "rule": str, "reason": str}
"allow" means "no objection": permissions and the sandbox still apply. Fails closed: any error,
unreadable input, missing harness data or missing task scope gives "deny". An unknown tool class
gives "ask", which is "deny" in unattended runs.
"""
from __future__ import annotations

import datetime as _dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True  # never leave __pycache__ in the repository (post-check would flag it)
HERE = Path(__file__).resolve().parent
SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{36,}"
    r"|github_pat_[A-Za-z0-9_]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}"
    r"|(?i:password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S{6,})")
# Output that blocks (post-check): only high-confidence credential shapes. SECRET_RE above stays
# broad because it only redacts. Quotes may arrive JSON-escaped (\"), so an optional backslash
# precedes each quote. The generic form needs a quoted literal of 12+ characters with a digit and
# a letter that is not an environment reference (${..}, process.env, os.environ) or a plain
# identifier such as "my_token_name2".
BLOCK_SECRET_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|gh[opsu]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{20,}"
    r"|sk-ant-[A-Za-z0-9_-]{20,}|sk-proj-[A-Za-z0-9_-]{20,}|xox[abprs]-[A-Za-z0-9-]{10,}"
    r"|glpat-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{20,}"
    r"|(?i:password|passwd|secret|token|api[_-]?key)\\?[\"']?\s*[=:]\s*\\?([\"'])"
    r"(?!\$\{|process\.env|os\.environ)"
    r"(?![A-Za-z]+(?:[_.-][A-Za-z]+)+\d*\\?[\"'])"
    r"(?=[^\"'\s\\]*\d)(?=[^\"'\s\\]*[A-Za-z])"
    r"[^\"'\s\\]{12,}\\?\2)")
OP_RE = re.compile(r"&>>?|[<>][<>&|]*|[;&|]+|[()]")
ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
RESERVED = {"{", "}", "!", "if", "then", "else", "elif", "fi", "do", "done", "while", "until"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh", "fish"}
# wrapper -> options that take a separate argument
WRAPPERS = {"command": set(), "builtin": set(), "exec": {"-a"}, "env": {"-u", "-C", "-S", "--split-string"},
            "nohup": set(), "coproc": set(), "nice": {"-n"}, "time": {"-f", "-o"},
            "timeout": {"-s", "-k"}, "xargs": {"-n", "-L", "-I", "-P", "-s", "-d", "-E", "-a"},
            "stdbuf": {"-i", "-o", "-e"}, "watch": {"-n"}}
GIT_ARG_OPTS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
BRANCH_RE = re.compile(r"(?!-)[A-Za-z0-9._/-]+")
SHA_RE = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")


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
    base = data.setdefault("base_branch", "main")     # harness.json files before Plan 2 F4
    if not isinstance(base, str) or not BRANCH_RE.fullmatch(base):
        raise ValueError("harness data has an invalid 'base_branch'")
    cap = data.setdefault("retry_cap", DEFAULT_RETRY_CAP)   # harness.json files before Plan 3
    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise ValueError("harness data has an invalid 'retry_cap'")
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


def _read_scope(root: Path) -> tuple[list[str], str | None] | None:
    """(patterns, base sha or None), or None when there is no usable scope. A `base:` line
    records the base commit at scope generation (aidlc scope); a malformed one voids the scope."""
    branch = current_branch(root)
    if not branch:
        return None
    path = scope_file(root, branch)
    if path.resolve().is_relative_to(root.resolve()) or not path.is_file():
        return None
    patterns, base = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if text.startswith("base:"):
            value = text[len("base:"):].strip()
            if base is not None or not SHA_RE.fullmatch(value):
                return None
            base = value
            continue
        patterns.append(text)
    for pat in patterns:
        segments = pat.replace("\\", "/").split("/")
        if pat.startswith(("/", "~")) or ".." in segments or ".git" in (x.casefold() for x in segments):
            return None                       # a scope may not reach outside or into .git
    return (patterns, base) if patterns else None


def load_scope(root: Path) -> list[str] | None:
    scope = _read_scope(root)
    return scope[0] if scope else None


def scope_base(root: Path) -> str | None:
    """The base commit recorded in the scope file, or None (no scope, or an old scope file)."""
    scope = _read_scope(root)
    return scope[1] if scope else None


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


MAX_COMMAND_CHARS = 65536
TIME_BUDGET_S = 0.5
MAX_DEPTH = 40
CHECK_RESULT_RE = re.compile(r"^check  result (PASS|FAIL)  \(", re.M)
NAMED_CHECKS = {"context-drift", "openwiki"}
DEFAULT_RETRY_CAP = 3


class _TooComplex(Exception):
    """The command is too large or too deeply nested to analyse within the time budget."""


def _tick(deadline: float | None) -> None:
    if deadline is not None and time.monotonic() > deadline:
        raise _TooComplex


def _heredoc_head(text: str, i: int) -> tuple[str, bool, bool] | None:
    """Parse `<<[-]DELIM` at text[i:]. Returns (delimiter, quoted, strip_tabs). Line
    continuations (backslash-newline) are removed first, as bash does."""
    j = i + 2
    while text.startswith("\\\n", j):
        j += 2
    strip = text[j:j + 1] == "-"
    j += 1 if strip else 0
    while j < len(text) and (text[j] in " \t" or text.startswith("\\\n", j)):
        j += 1 if text[j] in " \t" else 2
    delim, quoted = [], False
    while j < len(text) and text[j] not in " \t\n;&|<>()":
        c = text[j]
        if c in "'\"":
            k = text.find(c, j + 1)
            if k == -1:
                return None
            delim.append(text[j + 1:k])
            quoted, j = True, k + 1
        elif c == "\\" and text[j + 1:j + 2] == "\n":
            j += 2                                    # line continuation, as in the lexer
        elif c == "\\" and j + 1 < len(text):
            delim.append(text[j + 1])
            quoted, j = True, j + 2
        else:
            delim.append(c)
            j += 1
    return ("".join(delim), quoted, strip) if delim else None


FD_VAR_RE = re.compile(r"^\{[A-Za-z_][A-Za-z0-9_]*\}$")
# Runs of characters with no meaning in each context, consumed in one step.
CMD_RUN = re.compile(r"[^ \t\n'\"\\`$;&|<>()]+")
DQ_RUN = re.compile(r"[^\"\\$`]+")
HEREDOC_RUN = re.compile(r"[^\\$`]+")
ARITH_RUN = re.compile(r"[^'\"\\$`()]+")
PARAM_RUN = re.compile(r"[^'\"\\$`}]+")


class _Frame:
    """One nesting level. Kinds: "top" (a command text), "sub" ($(..), <(..), >(..)),
    "arith" ((( .. )) and $(( .. ))), "param" (${ .. }) and "heredoc" (an unquoted heredoc
    body, read like a double-quoted string). Only "top" and "sub" produce tokens."""
    __slots__ = ("kind", "depth", "start", "mark", "tokens", "buf", "in_word", "quoted",
                 "dq", "heredocs", "parens", "cases", "in_dq")

    def __init__(self, kind: str, depth: int, start: int = 0, mark: int = 0) -> None:
        self.kind, self.depth, self.start, self.mark = kind, depth, start, mark
        self.tokens: list[tuple[str, str]] = []
        self.buf: list[str] = []
        self.heredocs: list[tuple[str, bool, bool]] = []
        self.in_word = self.quoted = False
        self.dq = kind == "heredoc"
        self.in_dq = False                        # param: opened inside "..." or a heredoc body
        self.parens = self.cases = 0


class _Scanner:
    """The one shell scanner. A single left-to-right pass with a stack of frames tracks
    quotes, comments, substitutions, arithmetic, ${..} and heredocs together, so each of
    them is recognised only where bash recognises it: '<<' opens a heredoc only when it is
    unquoted, uncommented and outside (( )), $(( )) and ${ }. Backtick bodies and unquoted
    heredoc bodies are scanned recursively. Every closed substitution becomes its own
    token stream in `streams`."""

    def __init__(self, deadline: float | None) -> None:
        self.deadline = deadline
        self.streams: list[tuple[int, list[tuple[str, str]]]] = []
        self.steps = 0

    def scan(self, text: str, kind: str, depth: int) -> list[tuple[str, str]]:
        if depth > MAX_DEPTH:
            raise _TooComplex
        frames = [_Frame(kind, depth)]
        no_arith: set[int] = set()               # '((' positions that proved not arithmetic
        i, n = 0, len(text)
        while True:
            self.steps += 1
            if not self.steps & 511:
                _tick(self.deadline)
            f = frames[-1]
            if i < n and text.startswith("\\\n", i + 1) and (text[i] == "$" or (
                    text[i] in "<>()&|;" and not f.dq and f.kind != "param")):
                # bash joins the lines first, so this would be one operator ('<<', '$(' ...)
                raise ValueError("line continuation inside an operator")
            if i >= n:
                if f.dq and f.kind != "heredoc":
                    raise ValueError("unterminated double quote")
                if f.kind == "arith":
                    i = self._backtrack(frames, no_arith)
                elif f.kind == "param":
                    raise ValueError("unterminated ${")
                elif len(frames) == 1:
                    self._flush(f)
                    return f.tokens
                else:
                    self._close_sub(frames)      # an unclosed $( is analysed, never ignored
                continue
            if f.dq:
                i = self._quoted(text, i, frames, no_arith)
            elif f.kind == "arith":
                i = self._arith(text, i, frames, no_arith)
            elif f.kind == "param":
                i = self._param(text, i, frames, no_arith)
            else:
                i = self._command(text, i, frames, no_arith)

    # -- frames -------------------------------------------------------------------------
    def _push(self, frames: list[_Frame], kind: str, start: int) -> None:
        frame = _Frame(kind, frames[-1].depth + 1, start, len(self.streams))
        frame.in_dq = frames[-1].dq
        if frame.depth > MAX_DEPTH:
            raise _TooComplex
        frames.append(frame)

    def _close_sub(self, frames: list[_Frame]) -> None:
        frame = frames.pop()
        self._flush(frame)
        if frame.heredocs:
            # bash then reads the body from the next raw newline, even inside quotes
            raise ValueError("here-document left open inside a substitution")
        self.streams.append((frame.depth, frame.tokens))
        frames[-1].in_word = True                # the substitution is (part of) a word

    def _backtrack(self, frames: list[_Frame], no_arith: set[int]) -> int:
        """'((' or '$((' not closed by '))' is a subshell or a command substitution, as in
        bash: forget what the arithmetic reading produced and scan it again."""
        frame = frames.pop()
        del self.streams[frame.mark:]
        no_arith.add(frame.start)
        return frame.start

    @staticmethod
    def _flush(f: _Frame, next_char: str = "") -> None:
        if f.in_word:
            word = "".join(f.buf)
            fd = (not f.quoted and next_char in ("<", ">")
                  and (word.isdigit() or FD_VAR_RE.match(word)))
            if not fd:
                if word in ("case", "esac") and not f.quoted and (
                        not f.tokens or f.tokens[-1][0] == "sep" or f.tokens[-1][1] in RESERVED):
                    f.cases = f.cases + 1 if word == "case" else max(f.cases - 1, 0)
                f.tokens.append(("word", word))
        f.buf.clear()
        f.in_word = f.quoted = False

    # -- contexts -----------------------------------------------------------------------
    def _command(self, text: str, i: int, frames: list[_Frame], no_arith: set[int]) -> int:
        f, c, nxt = frames[-1], text[i], text[i + 1:i + 2]
        if c == "\\":
            if nxt == "\n":
                return i + 2                      # line continuation
            f.buf.append(nxt or "\\")
            f.in_word = f.quoted = True
            return i + 2
        if c == "'":
            j = text.find("'", i + 1)
            if j == -1:
                raise ValueError("unterminated single quote")
            f.buf.append(text[i + 1:j])
            f.in_word = f.quoted = True
            return j + 1
        if c == '"':
            f.dq = f.in_word = f.quoted = True
            return i + 1
        if c == "$":
            return self._dollar(text, i, frames, no_arith)
        if c == "`":
            return self._backtick(text, i, f)
        if c in " \t":
            self._flush(f)
            return i + 1
        if c == "#" and not f.in_word:
            j = text.find("\n", i)
            return len(text) if j == -1 else j    # a comment; the newline still separates
        if c == "\n":
            self._flush(f)
            f.tokens.append(("sep", "\n"))
            return self._bodies(text, i + 1, f) if f.heredocs else i + 1
        if c in "<>" and nxt == "(":
            self._flush(f)
            self._push(frames, "sub", i)
            return i + 2
        if c == "(" and nxt == "(" and i not in no_arith:
            self._flush(f)
            self._push(frames, "arith", i)
            return i + 2
        if c == ")" and f.kind == "sub" and not f.parens and not f.cases:
            self._close_sub(frames)
            return i + 1
        if c in ";&|<>()":
            self._flush(f, c if c in "<>" else "")
            op = OP_RE.match(text, i).group(0)
            if op == "(":
                f.parens += 1
            elif op == ")" and f.parens:
                f.parens -= 1
            elif op == "<<":
                head = _heredoc_head(text, i)
                if head:
                    f.heredocs.append(head)
            f.tokens.append(("redir" if op[0] in "<>" or op.startswith("&>") else "sep", op))
            return i + len(op)
        end = CMD_RUN.match(text, i).end()
        f.buf.append(text[i:end])
        f.in_word = True
        return end

    def _quoted(self, text: str, i: int, frames: list[_Frame], no_arith: set[int]) -> int:
        """Inside "..." or an unquoted heredoc body (where '"' is an ordinary character)."""
        f, c = frames[-1], text[i]
        heredoc = f.kind == "heredoc"
        if c == '"' and not heredoc:
            f.dq = False
            return i + 1
        if c == "\\":
            nxt = text[i + 1:i + 2]
            if nxt and nxt in ("\\$`\n" if heredoc else "\\$`\n\""):
                if nxt != "\n":
                    f.buf.append(nxt)
            else:
                f.buf.append(text[i:i + 2])
            return i + 2
        if c == "$":
            return self._dollar(text, i, frames, no_arith)
        if c == "`":
            return self._backtick(text, i, f)
        end = (HEREDOC_RUN if heredoc else DQ_RUN).match(text, i).end()
        f.buf.append(text[i:end])
        return end

    def _arith(self, text: str, i: int, frames: list[_Frame], no_arith: set[int]) -> int:
        """Inside (( .. )) or $(( .. )): '<<' is a shift and '#' is not a comment; only
        quotes, nested parentheses and substitutions matter."""
        f, c = frames[-1], text[i]
        if c == "'":
            return self._skip_single(text, i)
        if c == '"':
            f.dq = True
            return i + 1
        if c == "\\":
            return i + 2
        if c == "$":
            return self._dollar(text, i, frames, no_arith)
        if c == "`":
            return self._backtick(text, i, f)
        if c == "(":
            f.parens += 1
            return i + 1
        if c == ")":
            if f.parens:
                f.parens -= 1
                return i + 1
            if text[i + 1:i + 2] != ")":
                return self._backtrack(frames, no_arith)
            frames.pop()
            if text[f.start] == "$":
                frames[-1].in_word = True
            return i + 2
        return ARITH_RUN.match(text, i).end()

    def _param(self, text: str, i: int, frames: list[_Frame], no_arith: set[int]) -> int:
        """Inside ${ .. }: blanks, '#', '<<', ';' and ')' are literal; quotes and
        substitutions nest; the first unquoted '}' closes it. A "'" inside "${ .. }" is a
        quote to bash but a plain character to sh (dash), so it is not guessed."""
        f, c = frames[-1], text[i]
        if c == "'":
            if f.in_dq:
                raise ValueError("a ' inside \"${..}\" is read differently by bash and sh")
            return self._skip_single(text, i)
        if c == '"':
            f.dq = True
            return i + 1
        if c == "\\":
            return i + 2
        if c == "$":
            return self._dollar(text, i, frames, no_arith)
        if c == "`":
            return self._backtick(text, i, f)
        if c == "}":
            frames.pop()
            frames[-1].in_word = True
            return i + 1
        return PARAM_RUN.match(text, i).end()

    # -- shared pieces ------------------------------------------------------------------
    @staticmethod
    def _skip_single(text: str, i: int) -> int:
        j = text.find("'", i + 1)
        if j == -1:
            raise ValueError("unterminated single quote")
        return j + 1

    def _dollar(self, text: str, i: int, frames: list[_Frame], no_arith: set[int]) -> int:
        f, nxt = frames[-1], text[i + 1:i + 2]
        f.in_word = True
        if nxt == "(":
            if text[i + 2:i + 3] == "(" and i not in no_arith:
                self._push(frames, "arith", i)
                return i + 3
            self._push(frames, "sub", i)
            return i + 2
        if nxt == "{":
            self._push(frames, "param", i)
            return i + 2
        if not f.dq and nxt == "'":               # $'..': backslash escapes do not end it
            j = i + 2
            while j < len(text) and text[j] != "'":
                j += 2 if text[j] == "\\" else 1
            if j >= len(text):
                raise ValueError("unterminated $' quote")
            f.buf.append(text[i + 2:j])
            f.quoted = True
            return j + 1
        if not f.dq and nxt == '"':
            return i + 1                          # $"..": a double-quoted string
        f.buf.append("$")
        return i + 1

    def _backtick(self, text: str, i: int, f: _Frame) -> int:
        """`..`: ends at the next unescaped backtick (an unclosed one takes the rest).
        The body is a command, scanned recursively."""
        j = i + 1
        while j < len(text) and text[j] != "`":
            j += 2 if text[j] == "\\" else 1
        body = re.sub(r"\\([\\`$])", r"\1", text[i + 1:j])
        self.streams.append((f.depth + 1, self.scan(body, "top", f.depth + 1)))
        f.in_word = True
        return j + 1

    def _bodies(self, text: str, i: int, f: _Frame) -> int:
        """Read the bodies of every heredoc opened on the line just ended, in order. Bodies
        with a quoted delimiter are data; unquoted bodies are scanned for substitutions, and
        in them a backslash-newline joins two lines before the terminator test, as in bash."""
        n = len(text)
        for delim, quoted, strip in f.heredocs:
            start, body_end = i, n
            while i < n:
                _tick(self.deadline)
                line_start, parts = i, []
                while True:
                    end = text.find("\n", i)
                    end = n if end == -1 else end
                    piece, i = text[i:end], min(end + 1, n)
                    if quoted or end == n or (len(piece) - len(piece.rstrip("\\"))) % 2 == 0:
                        parts.append(piece)
                        break
                    parts.append(piece[:-1])
                line = "".join(parts)
                if (line.lstrip("\t") if strip else line) == delim:
                    body_end = line_start
                    break
            if not quoted:
                self.scan(text[start:body_end], "heredoc", f.depth)
        f.heredocs = []
        return i


def _lex(text: str, deadline: float | None = None, depth: int = 0) -> list[tuple[int, list[tuple[str, str]]]]:
    """Tokenise a command: ("word", value), ("sep", op) or ("redir", op). Returns (depth,
    tokens) for the command itself first, then for every substitution inside it. Raises
    ValueError on unbalanced quotes and _TooComplex past the deadline or nesting limit."""
    scanner = _Scanner(deadline)
    top = scanner.scan(text, "top", depth)
    return [(depth, top), *scanner.streams]


class _Prefix:
    """Incremental prefix stripping (assignments, reserved words, `function NAME`, wrappers
    with their options), O(1) per word. Drives both _argv and the command-position test
    for '{' and '}' in _segments."""
    __slots__ = ("count", "mode", "wrapper", "start", "nested", "coproc_at", "function_at", "keywords")

    def __init__(self) -> None:
        self.count, self.mode, self.wrapper = 0, "cmd", ""
        self.start = self.function_at = None
        self.coproc_at = -2                       # where `coproc` stood as a reserved word
        self.keywords = True                      # only reserved words so far
        self.nested: list[str] = []

    @property
    def at_command(self) -> bool:
        """True when the next word would start a command (so a bare '{' or '}' is a keyword)."""
        return self.mode in ("cmd", "wrap") or self.count == self.coproc_at + 2

    def feed(self, word: str) -> None:
        mode, leading = self.mode, self.keywords
        self.keywords = leading and word in RESERVED
        if mode == "fname":
            self.mode = "cmd"
        elif mode == "optarg":
            self.mode = "wrap"
        elif mode != "args":
            if mode == "wrap":
                if word.startswith("-") or ASSIGN_RE.match(word):
                    split = self.wrapper == "env" and _is_split_string(word)
                    if split:
                        self.nested.append(word)
                    if word in WRAPPERS[self.wrapper] or (split and word.endswith("S")):
                        self.mode = "optarg"
                    self.count += 1
                    return
                self.mode = "cmd"
                if self.wrapper == "timeout" or (self.wrapper == "nice" and re.fullmatch(r"-?\d+", word)):
                    self.count += 1                   # the duration or the niceness
                    return
            if ASSIGN_RE.match(word) or word in RESERVED:
                pass
            elif word == "function":
                self.mode, self.function_at = "fname", self.count
            elif word.rsplit("/", 1)[-1] in WRAPPERS:
                self.mode, self.wrapper = "wrap", word.rsplit("/", 1)[-1]
                if self.wrapper == "coproc" and leading:
                    self.coproc_at = self.count       # `coproc NAME {` opens a group
            else:
                self.mode, self.start = "args", self.count
        self.count += 1


def _argv(tokens: list[str]) -> tuple[list[str], list[str]]:
    """Strip assignments, reserved words and wrappers; normalise argv0 and git options.
    The list holds command strings supplied by `env -S`; it only drives an ask."""
    prefix = _Prefix()
    for word in tokens:
        if prefix.mode == "args":
            break
        prefix.feed(word)
    if prefix.mode == "args":
        start = prefix.start
    elif prefix.mode == "fname":
        start = prefix.function_at                    # a lone `function` is the command
    else:
        return [], prefix.nested
    argv0 = tokens[start].rsplit("/", 1)[-1]
    if argv0 != "git":
        return [argv0, *tokens[start + 1:]], prefix.nested
    k = start + 1
    while k < len(tokens) and tokens[k].startswith("-"):
        k += 2 if tokens[k] in GIT_ARG_OPTS else 1
    return ["git", *tokens[k:]], prefix.nested


def _is_split_string(opt: str) -> bool:
    """env -S in any form: a short cluster containing S, or a long prefix of --split-string."""
    if opt.startswith("--"):
        base = opt.split("=", 1)[0]
        return len(base) >= 4 and "--split-string".startswith(base)
    return opt.startswith("-") and "S" in opt


def _segments(tokens: list[tuple[str, str]], deadline: float | None = None) -> list[dict]:
    """Split a token stream into segments of words; redirections and their targets are dropped."""
    segments: list[dict] = []
    current = {"words": [], "piped": False, "stdin": False}
    prefix = _Prefix()
    skip_target = False
    for count, (kind, value) in enumerate(tokens):
        if not count & 255:
            _tick(deadline)
        if skip_target:
            skip_target = False
            if kind == "word":
                continue
        if kind == "word":
            if value in ("{", "}") and prefix.at_command:
                segments.append(current)
                current, prefix = {"words": [], "piped": False, "stdin": False}, _Prefix()
            else:
                current["words"].append(value)
                prefix.feed(value)
        elif kind == "redir":
            current["stdin"] = current["stdin"] or value.startswith("<")
            skip_target = True
        else:
            bare = value.replace("(", "").replace(")", "")
            if bare == "" and not current["words"]:
                continue                              # keeps the piped flag across '('
            segments.append(current)
            current = {"words": [], "piped": bare in ("|", "|&"), "stdin": False}
            prefix = _Prefix()
    segments.append(current)
    return [seg for seg in segments if seg["words"]]


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


def _moves_base(argv: list[str], base: str) -> bool:
    """True for the git commands that move, delete, rename or recreate the base branch, the
    trust root that the post-check and scope generation read (final-fixes F3)."""
    if len(argv) < 2 or argv[0] != "git":
        return False
    sub, rest = argv[1], argv[2:]
    names = {base.casefold(), f"refs/heads/{base}".casefold()}

    def is_base(token: str) -> bool:
        return token.lstrip("+").casefold() in names

    positional = [t for t in rest if not t.startswith("-")]
    if sub == "branch":
        flags: set[str] = set()
        for tok in rest:
            if tok.startswith("--"):
                flags.add({"--force": "f", "--delete": "d", "--move": "m", "--copy": "c"}.get(
                    tok.split("=", 1)[0], ""))
            elif tok.startswith("-"):
                flags.update(tok[1:])
        if flags & set("dDmMcC"):
            return any(is_base(t) for t in positional)
        return "f" in flags and bool(positional) and is_base(positional[0])
    if sub == "update-ref":
        if "--stdin" in rest:
            return True                       # reads ref updates it cannot show us
        args, i = [], 0
        while i < len(rest):
            if rest[i] == "-m":
                i += 2
                continue
            if not rest[i].startswith("-"):
                args.append(rest[i])
            i += 1
        return bool(args) and is_base(args[0])
    if sub in ("checkout", "switch"):
        creates = ("-b", "-B", "--orphan") if sub == "checkout" else (
            "-c", "-C", "--create", "--force-create", "--orphan")
        for i, tok in enumerate(rest):
            for opt in creates:
                if tok == opt:
                    target = rest[i + 1] if i + 1 < len(rest) else ""
                elif opt.startswith("--") and tok.startswith(opt + "="):
                    target = tok[len(opt) + 1:]
                elif not opt.startswith("--") and not tok.startswith("--") and tok.startswith(opt):
                    target = tok[len(opt):]
                else:
                    continue
                if is_base(target):
                    return True
        return False
    if sub in ("fetch", "push"):
        return any(":" in t and is_base(t.rsplit(":", 1)[1]) for t in positional)
    return False


def _check_segment(words: list[str], piped: bool, stdin: bool, patterns: list[str],
                   asks: list[dict], pending: list[str], base: str = "main") -> dict | None:
    argv, env_split = _argv(words)
    if not argv:
        if env_split:
            asks.append(_ask("nested-shell", "a nested shell hides its command; a person must read it"))
        return None
    if _moves_base(argv, base):
        return _result("deny", "base-ref", f"'{_redact(' '.join(argv))[:80]}' would move the base branch "
                       f"'{base}', which approvals and checks trust. A person moves it, not the agent.")
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


def _is_one_check(argv: list[str]) -> bool:
    """`aidlc check` with no named check anywhere after it. The value after `--repo` is skipped
    (`--repo X` and `--repo=X`), so a repository called "context-drift" is not a named check."""
    if argv[:2] != ["aidlc", "check"]:
        return False
    skip = False
    for word in argv[2:]:
        if skip:
            skip = False
        elif word == "--repo":
            skip = True
        elif word.startswith("--repo="):
            continue
        elif word in NAMED_CHECKS:
            return False
    return True


def _inner_strings(argv: list[str]) -> list[str]:
    """The command text a nested shell or eval runs."""
    if argv and argv[0] in SHELLS:
        for index, tok in enumerate(argv[1:], start=1):
            if tok.startswith("-") and not tok.startswith("--") and "c" in tok:
                return [argv[index + 1]] if index + 1 < len(argv) else []
        return []
    if argv and argv[0] == "eval":
        return [" ".join(argv[1:])]
    return []


def cli_entry() -> str | None:
    """The framework's own `aidlc` entry point (realpath), as the CLI recorded it in
    $AIDLC_HOME_DIR/cli.json when it rendered the harness. None: missing, a symlink, unreadable
    or malformed. A PASS needs it (a fake `aidlc` on PATH must never reset the counter)."""
    path = _home_dir() / "cli.json"
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as fh:
            data = json.loads(fh.read(65537)[:65536].decode("utf-8"))
    except Exception:  # noqa: BLE001 - fail closed: no entry point, no PASS
        return None
    entry = data.get("entry") if isinstance(data, dict) else None
    return entry if isinstance(entry, str) and entry else None


def _is_entry_point(word: str, cwd: str | None) -> bool:
    entry = cli_entry()
    if entry is None:
        return False
    try:
        if "/" in word:
            found = Path(word) if word.startswith("/") else Path(cwd or os.getcwd()) / word
        else:
            found = shutil.which(word)
            if found is None:
                return False
        return os.path.realpath(found) == entry
    except Exception:  # noqa: BLE001
        return False


def check_segments(command, cwd: str | None = None) -> tuple[bool, bool]:
    """(contains, exact) for the one-command check in a shell command. `contains`: some part of it
    runs `aidlc check` (also inside a substitution, `bash -c` or `eval`). `exact`: the whole
    command is `aidlc check`, optionally with `--repo <path>`. Only an exact, passing run resets
    the retry counter (guide 8.8); any other command that runs the check is a failing attempt."""
    if not isinstance(command, str) or not command.strip() or len(command) > MAX_COMMAND_CHARS:
        return False, False
    deadline = time.monotonic() + TIME_BUDGET_S
    contains = False
    queue: list[tuple[str, int]] = [(command, 0)]
    try:
        while queue:
            text, depth = queue.pop()
            if depth > MAX_DEPTH:
                return True, False
            for d, tokens in _lex(text, deadline, depth):
                for seg in _segments(tokens, deadline):
                    argv, nested = _argv(seg["words"])
                    contains = contains or _is_one_check(argv)
                    queue += [(s, d + 1) for s in _inner_strings(argv) + nested]
        if not contains:
            return False, False
        top = _lex(command, deadline)
        segments = _segments(top[0][1], deadline) if len(top) == 1 else []
        if len(segments) != 1:
            return True, False
        words = segments[0]["words"]                      # raw words: no prefix or wrapper is stripped
        exact = (len(words) in (2, 4) and words[0].rsplit("/", 1)[-1] == "aidlc" and words[1] == "check"
                 and (len(words) == 2 or words[2] == "--repo") and _is_entry_point(words[0], cwd))
        return True, exact
    except (ValueError, _TooComplex):
        return bool(re.search(r"aidlc\S*\s+check", command)), False


DETACHED = "__detached__"


def _home_dir() -> Path:
    return Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser()


def attempts_file(root: Path, branch: str | None) -> Path:
    """One record per repository (name plus a hash of its path, so same-named clones never collide)
    and branch. A detached HEAD has its own key, so detaching never escapes the counter."""
    home = _home_dir()
    tag = hashlib.sha256(str(root.resolve()).encode("utf-8")).hexdigest()[:8]
    name = DETACHED if branch is None else branch.replace("/", "__")
    return home / "attempts" / f"{root.name}-{tag}" / f"{name}.json"


def attempts_unsafe(path: Path) -> bool:
    """True when the record's directories or its lock are links or not what they should be.
    Such a record cannot be trusted or updated, so it counts as at the limit."""
    try:
        for directory in (path.parent.parent, path.parent):
            if directory.is_symlink():
                return True
        lock = path.parent / ".lock"
        try:
            mode = os.lstat(lock).st_mode
        except FileNotFoundError:
            return False
        return not stat.S_ISREG(mode)
    except OSError:
        return True


def read_failures(root: Path, branch: str | None) -> int | None:
    """Failing checks in a row on this branch. None means the record is unreadable."""
    path = attempts_file(root, branch)
    if attempts_unsafe(path):
        return None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return 0
    except OSError:
        return None
    try:
        with os.fdopen(fd, "rb") as fh:
            data = json.loads(fh.read(65537)[:65536].decode("utf-8"))
    except Exception:  # noqa: BLE001 - an unreadable record fails closed at the caller
        return None
    count = data.get("failures") if isinstance(data, dict) else None
    return count if isinstance(count, int) and not isinstance(count, bool) and count >= 0 else None


def retry_limit_reason(failures: int, cap: int) -> str:
    return (f"retry limit reached: {failures} failing checks in a row (limit {cap}). Stop. Report what "
            "you tried and the failure; a person reviews it and runs `aidlc attempts --reset`.")


def _retry_block(event: dict, data: dict) -> dict | None:
    root = repo_root(Path(event.get("cwd") or os.getcwd()))
    if root is None:
        return None
    failures = read_failures(root, current_branch(root))     # None branch: the detached key
    if failures is None:
        return _result("deny", "retry-limit", "the attempts record is unreadable; a person checks it "
                       "and runs `aidlc attempts --reset`")
    if failures >= data["retry_cap"]:
        return _result("deny", "retry-limit", retry_limit_reason(failures, data["retry_cap"]))
    return None


def _decide_shell(event: dict, data: dict) -> dict:
    command = (event.get("args") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return _result("deny", "fail-safe", "shell call without a command")
    too_complex = _result("deny", "fail-safe", "command too complex to analyse")
    if len(command) > MAX_COMMAND_CHARS:
        return too_complex
    deadline = time.monotonic() + TIME_BUDGET_S
    patterns = [" ".join(p.split()) for p in data["shell_deny"]]
    asks: list[dict] = []
    queue: list[tuple[str, int]] = [(command, 0)]
    seen = 0
    try:
        while queue:
            _tick(deadline)
            seen += 1
            text, depth = queue.pop()
            if seen > 200 or depth > MAX_DEPTH:
                return too_complex
            try:
                streams = [(d, _segments(tokens, deadline)) for d, tokens in _lex(text, deadline, depth)]
            except ValueError:
                asks.append(_ask("unparseable", "a command part could not be parsed; a person must read it"))
                crude = re.sub(r"[\"']", " ", text)
                streams = [(depth, [{"words": part.split(), "piped": False, "stdin": False}
                                    for part in re.split(r"[;&|()<>\n`]+", crude)])]
            for d, segments in streams:
                for seg in segments:
                    found: list[str] = []
                    denied = _check_segment(seg["words"], seg["piped"], seg["stdin"], patterns, asks, found,
                                            data["base_branch"])
                    if denied:
                        return denied
                    queue += [(t, d + 1) for t in found]
    except _TooComplex:
        return too_complex
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
        if tool in ("edit", "shell"):
            blocked = _retry_block(event, data)
            if blocked:
                return blocked
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
        return _ask("unknown-tool", f"unknown tool class '{tool}'; a person must approve it "
                    "(add the tool to the adapter's classes if it is common)")
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
                  "hook": event.get("hook", "pre-tool-guard"), "session": event.get("session"), "call": event.get("call"),
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
