"""Context drift (guide 2.8 A7): rules files and the codebase map must name things that
exist, stay within their line budgets, and carry an owner and a fresh verification date."""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path

from .findings import Finding

SPAN = re.compile(r"`([^`\n]+)`")
EXTS = {"md", "json", "yaml", "yml", "ts", "tsx", "js", "mjs", "cjs", "cs", "csproj", "sln",
        "slnx", "py", "sh", "toml", "txt", "xml", "props", "targets", "sql", "html", "css",
        "lock", "cfg", "ini"}
FORBIDDEN = set(" <>{}()$~")
MAKEFILES = ("GNUmakefile", "makefile", "Makefile")
OPENWIKI = re.compile(r"<!-- OPENWIKI:START -->.*?<!-- OPENWIKI:END -->", re.S)
VERIFIED = re.compile(r"Last verified:\s*(\d{4}-\d{2}-\d{2}),\s*against commit\s+([0-9a-f]{7,40})")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lstrip("﻿").replace("\r\n", "\n")


def _has_ext(span: str) -> bool:
    last = span.rstrip("/").rsplit("/", 1)[-1]
    return "." in last and last.rsplit(".", 1)[1] in EXTS


def _is_path(repo: Path, span: str) -> bool:
    """A span names a repository path when it has a known file extension, ends with '/',
    contains a glob, or starts with an existing top-level entry. This skips MIME types,
    'origin/main', 'HTTP/2', 'and/or' and 'owner/repo' slugs."""
    if any(ch in FORBIDDEN for ch in span) or span.startswith(("/", "http", "-", "@")):
        return False
    if "/" not in span:
        return _has_ext(span)
    if span.endswith("/") or _has_ext(span) or any(ch in span for ch in "*?["):
        return True
    return (repo / span.split("/", 1)[0]).exists()


def _exists(repo: Path, span: str) -> bool:
    if any(ch in span for ch in "*?["):
        pattern = span.rstrip("/")
        return any(repo.glob(pattern if "/" in pattern else f"**/{pattern}"))
    target = repo / span
    return target.is_dir() if span.endswith("/") else target.exists()


def _ignored(repo: Path, span: str) -> bool:
    """Gitignored paths (build output such as dist/) legitimately do not exist in CI."""
    result = subprocess.run(["git", "check-ignore", "-q", "--no-index", span], cwd=repo,
                            capture_output=True)
    return result.returncode == 0


def _aidlc_subcommands() -> set[str]:
    from ..cli import build_parser
    parser = build_parser()
    for action in parser._subparsers._group_actions:  # argparse internals: the subparser action
        return set(action.choices)
    return set()


def _command_findings(repo: Path, rel: str, lineno: int, span: str,
                      subcommands: set[str]) -> list[Finding]:
    words = span.split()
    out = []
    if words[:2] == ["npm", "run"] and len(words) >= 3:
        pkg = repo / "package.json"
        try:
            data = json.loads(_read(pkg)) if pkg.is_file() else {}
            scripts = data.get("scripts", {})
            if not isinstance(scripts, dict):
                raise ValueError("'scripts' is not an object")
        except (ValueError, AttributeError, OSError) as exc:   # JSON and UTF-8 errors are ValueErrors
            return [Finding("FAIL", "package.json", 0, f"unreadable, so npm scripts cannot be "
                                                        f"checked: {exc}")]
        if words[2] not in scripts:
            out.append(Finding("FAIL", rel, lineno, f"npm script '{words[2]}' not in package.json"))
    elif words[0] == "make" and len(words) >= 2:
        text = ""
        for name in MAKEFILES:                      # GNU make's lookup order
            if (repo / name).is_file():
                try:
                    text = _read(repo / name)
                except (ValueError, OSError) as exc:
                    return [Finding("FAIL", name, 0, f"unreadable, so make targets cannot be "
                                                     f"checked: {exc}")]
                break
        target = re.escape(words[1])
        if not re.search(rf"^(?:[^\s:#=]+[ \t]+)*{target}(?:[ \t]+[^\s:#=]+)*[ \t]*:(?![:=])", text, re.M):
            out.append(Finding("FAIL", rel, lineno, f"make target '{words[1]}' not in Makefile"))
    elif words[0] in ("aidlc", "bin/aidlc") and len(words) >= 2 and not words[1].startswith("-"):
        if words[1] not in subcommands:
            out.append(Finding("FAIL", rel, lineno, f"aidlc subcommand '{words[1]}' does not exist"))
    return out


def _scan(repo: Path, path: Path, text: str, subcommands: set[str]) -> list[Finding]:
    rel = str(path.relative_to(repo))
    findings = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        for span in SPAN.findall(line):
            span = span.strip()
            if " " in span:
                findings += _command_findings(repo, rel, lineno, span, subcommands)
            elif _is_path(repo, span):
                if os.path.normpath(span).split("/")[0] == "..":
                    findings.append(Finding("FAIL", rel, lineno,
                                            f"names '{span}', which resolves outside the repository"))
                    continue
                try:
                    missing = not _exists(repo, span) and not _ignored(repo, span)
                except (ValueError, NotImplementedError) as exc:
                    findings.append(Finding("FAIL", rel, lineno, f"'{span}' is not a valid glob: {exc}"))
                    continue
                if missing:
                    findings.append(Finding("FAIL", rel, lineno, f"names '{span}', which does not exist"))
    return findings


def _commit_exists(repo: Path, sha: str) -> bool:
    result = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo,
                            capture_output=True)
    return result.returncode == 0


def check_context_drift(repo: Path, today: date) -> list[Finding]:
    interval = 30
    rules_file, map_file = "AGENTS.md", "docs/codebase-map.md"
    findings: list[Finding] = []
    cfg_path = repo / ".aidlc" / "config.yaml"
    if cfg_path.is_file():
        from ..repo import load_config
        try:
            ctx = load_config(repo).context
            interval = int(ctx.get("review_interval_days", 30))
            rules_file, map_file = ctx.get("rules_file", rules_file), ctx.get("map", map_file)
        except Exception as exc:   # any malformed config is a finding, never a traceback
            findings.append(Finding("FAIL", ".aidlc/config.yaml", 0, f"unusable: {exc}"))

    subcommands = _aidlc_subcommands()
    texts: dict[Path, str] = {}
    for path in [repo / rules_file, repo / "CLAUDE.md", repo / map_file,
                 *sorted((repo / ".aidlc" / "rules").glob("*.md"))]:
        if path.is_file():
            try:
                texts[path] = _read(path)
            except (ValueError, OSError) as exc:    # UnicodeDecodeError is a ValueError
                findings.append(Finding("FAIL", str(path.relative_to(repo)), 0,
                                        f"unreadable ({type(exc).__name__}); save it as UTF-8"))
    if not (repo / rules_file).is_file():
        findings.append(Finding("FAIL", rules_file, 0, "rules file missing"))
    for path, text in texts.items():
        if path.name != "README.md":
            findings += _scan(repo, path, text, subcommands)

    if (repo / rules_file) in texts:
        n = len(OPENWIKI.sub("", texts[repo / rules_file]).rstrip("\n").split("\n"))
        if n > 200:
            findings.append(Finding("FAIL", rules_file, 0, f"{n} lines; the budget is 200"))
        elif n > 80:
            findings.append(Finding("WARN", rules_file, 0, f"{n} lines; aim for 80 or fewer"))
    if (repo / "CLAUDE.md") in texts and len(texts[repo / "CLAUDE.md"].rstrip("\n").split("\n")) > 40:
        findings.append(Finding("FAIL", "CLAUDE.md", 0, "more than 40 lines; keep it thin"))

    cmap = repo / map_file
    if not cmap.is_file():
        findings.append(Finding("FAIL", map_file, 0, "codebase map missing"))
        return findings
    if cmap not in texts:
        return findings                                # unreadable: already reported
    text = texts[cmap]
    if "Owner:" not in text:
        findings.append(Finding("FAIL", map_file, 0, "no 'Owner:' line"))
    match = VERIFIED.search(text)
    if not match:
        findings.append(Finding("FAIL", map_file, 0,
                                "no 'Last verified: YYYY-MM-DD, against commit <sha>' line"))
        return findings
    try:
        verified = date.fromisoformat(match.group(1))
    except ValueError:
        findings.append(Finding("FAIL", map_file, 0, f"'{match.group(1)}' is not a valid date"))
        return findings
    age = (today - verified).days
    if age > interval:
        findings.append(Finding("WARN", map_file, 0,
                                f"last verified {age} days ago, older than {interval}"))
    if not _commit_exists(repo, match.group(2)):
        findings.append(Finding("FAIL", map_file, 0, f"commit {match.group(2)} is not in this repository"))
    return findings
