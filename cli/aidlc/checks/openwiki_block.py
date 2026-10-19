"""OpenWiki governance (design §6.4): the managed block in AGENTS.md stays a short pointer,
never appears in CLAUDE.md, and the ignore file keeps the framework baseline."""
from __future__ import annotations

from pathlib import Path

from ..paths import framework_root
from .findings import Finding

START, END = "<!-- OPENWIKI:START -->", "<!-- OPENWIKI:END -->"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8").lstrip("﻿").replace("\r\n", "\n")


def _block(text: str, rel: str) -> tuple[list[str] | None, list[Finding]]:
    starts, ends = text.count(START), text.count(END)
    if starts == 0 and ends == 0:
        return None, []
    if starts != 1 or ends != 1 or text.index(START) > text.index(END):
        return None, [Finding("FAIL", rel, 0, "OPENWIKI markers are not one ordered START/END pair")]
    inner = text[text.index(START) + len(START):text.index(END)]
    return [line for line in inner.split("\n") if line.strip()], []


def check_openwiki(repo: Path, max_lines: int = 15) -> list[Finding]:
    findings: list[Finding] = []
    agents, claude = repo / "AGENTS.md", repo / "CLAUDE.md"
    block = None
    if agents.is_file():
        block, problems = _block(_read(agents), "AGENTS.md")
        findings += problems
    if block is not None:
        if len(block) > max_lines:
            findings.append(Finding("FAIL", "AGENTS.md", 0,
                                    f"OpenWiki block has {len(block)} lines; the limit is {max_lines}"))
        for line in block:
            stripped = line.strip()
            if stripped.startswith("```"):
                findings.append(Finding("FAIL", "AGENTS.md", 0, "code fence inside the OpenWiki block"))
            elif not stripped.startswith("#") and "openwiki/" not in stripped:
                findings.append(Finding("FAIL", "AGENTS.md", 0,
                                        f"OpenWiki block line is not a pointer: {stripped[:60]}"))
    if claude.is_file() and (START in _read(claude) or END in _read(claude)):
        findings.append(Finding("FAIL", "CLAUDE.md", 0,
                                "contains an OpenWiki block; CLAUDE.md only imports AGENTS.md"))

    if (repo / "openwiki").is_dir():
        if block is None and not findings:
            findings.append(Finding("WARN", "AGENTS.md", 0, "openwiki/ exists but AGENTS.md has no pointer block"))
        ignore = repo / ".openwikiignore"
        baseline = [l for l in _read(framework_root() / "core" / "context" / "openwiki"
                                     / "openwikiignore.baseline").split("\n")
                    if l.strip() and not l.startswith("#")]
        present = set(_read(ignore).split("\n")) if ignore.is_file() else set()
        if not ignore.is_file():
            findings.append(Finding("FAIL", ".openwikiignore", 0, "missing; copy the framework baseline"))
        else:
            for pattern in baseline:
                if pattern not in present:
                    findings.append(Finding("FAIL", ".openwikiignore", 0,
                                            f"baseline pattern '{pattern}' removed"))
    return findings
