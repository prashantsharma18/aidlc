"""Context drift (guide 2.8 A7): rules files and the codebase map must name things that
exist, stay within their line budgets, and carry an owner and a fresh verification date."""
from __future__ import annotations

import json
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
OPENWIKI = re.compile(r"<!-- OPENWIKI:START -->.*?<!-- OPENWIKI:END -->", re.S)
VERIFIED = re.compile(r"Last verified:\s*(\d{4}-\d{2}-\d{2}),\s*against commit\s+([0-9a-f]{7,40})")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lstrip("﻿").replace("\r\n", "\n")


def _is_path(span: str) -> bool:
    if any(ch in FORBIDDEN for ch in span) or span.startswith(("/", "http", "-", "@")):
        return False
    if "/" in span:
        return True
    return "." in span and span.rsplit(".", 1)[1] in EXTS


def _exists(repo: Path, span: str) -> bool:
    if any(ch in span for ch in "*?["):
        return any(repo.glob(span.rstrip("/")))
    target = repo / span
    return target.is_dir() if span.endswith("/") else target.exists()


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
        scripts = json.loads(_read(pkg)).get("scripts", {}) if pkg.is_file() else {}
        if words[2] not in scripts:
            out.append(Finding("FAIL", rel, lineno, f"npm script '{words[2]}' not in package.json"))
    elif words[0] == "make" and len(words) >= 2:
        makefile = repo / "Makefile"
        text = _read(makefile) if makefile.is_file() else ""
        if not re.search(rf"^{re.escape(words[1])}\s*:", text, re.M):
            out.append(Finding("FAIL", rel, lineno, f"make target '{words[1]}' not in Makefile"))
    elif words[0] in ("aidlc", "bin/aidlc") and len(words) >= 2 and not words[1].startswith("-"):
        if words[1] not in subcommands:
            out.append(Finding("FAIL", rel, lineno, f"aidlc subcommand '{words[1]}' does not exist"))
    return out


def _scan(repo: Path, path: Path, subcommands: set[str]) -> list[Finding]:
    rel = str(path.relative_to(repo))
    findings = []
    for lineno, line in enumerate(_read(path).split("\n"), start=1):
        for span in SPAN.findall(line):
            span = span.strip()
            if " " in span:
                findings += _command_findings(repo, rel, lineno, span, subcommands)
            elif _is_path(span) and not _exists(repo, span):
                findings.append(Finding("FAIL", rel, lineno, f"names '{span}', which does not exist"))
    return findings


def _commit_exists(repo: Path, sha: str) -> bool:
    result = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=repo,
                            capture_output=True)
    return result.returncode == 0


def check_context_drift(repo: Path, today: date) -> list[Finding]:
    interval = 30
    rules_file, map_file = "AGENTS.md", "docs/codebase-map.md"
    cfg_path = repo / ".aidlc" / "config.yaml"
    if cfg_path.is_file():
        from ..repo import load_config
        ctx = load_config(repo).context
        interval = int(ctx.get("review_interval_days", 30))
        rules_file, map_file = ctx.get("rules_file", rules_file), ctx.get("map", map_file)

    findings: list[Finding] = []
    subcommands = _aidlc_subcommands()
    sources = [repo / rules_file, repo / "CLAUDE.md", repo / map_file,
               *sorted((repo / ".aidlc" / "rules").glob("*.md"))]
    if not (repo / rules_file).is_file():
        findings.append(Finding("FAIL", rules_file, 0, "rules file missing"))
    for path in sources:
        if path.is_file() and path.name != "README.md":
            findings += _scan(repo, path, subcommands)

    if (repo / rules_file).is_file():
        n = len(OPENWIKI.sub("", _read(repo / rules_file)).rstrip("\n").split("\n"))
        if n > 200:
            findings.append(Finding("FAIL", rules_file, 0, f"{n} lines; the budget is 200"))
        elif n > 80:
            findings.append(Finding("WARN", rules_file, 0, f"{n} lines; aim for 80 or fewer"))
    claude = repo / "CLAUDE.md"
    if claude.is_file() and len(_read(claude).rstrip("\n").split("\n")) > 40:
        findings.append(Finding("FAIL", "CLAUDE.md", 0, "more than 40 lines; keep it thin"))

    cmap = repo / map_file
    if not cmap.is_file():
        findings.append(Finding("FAIL", map_file, 0, "codebase map missing"))
        return findings
    text = _read(cmap)
    if "Owner:" not in text:
        findings.append(Finding("FAIL", map_file, 0, "no 'Owner:' line"))
    match = VERIFIED.search(text)
    if not match:
        findings.append(Finding("FAIL", map_file, 0,
                                "no 'Last verified: YYYY-MM-DD, against commit <sha>' line"))
        return findings
    age = (today - date.fromisoformat(match.group(1))).days
    if age > interval:
        findings.append(Finding("WARN", map_file, 0,
                                f"last verified {age} days ago, older than {interval}"))
    if not _commit_exists(repo, match.group(2)):
        findings.append(Finding("FAIL", map_file, 0, f"commit {match.group(2)} is not in this repository"))
    return findings
