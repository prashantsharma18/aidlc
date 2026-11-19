#!/usr/bin/env python3
"""Checks a story branch against its approved task bundles, mechanically, so the rules hold whoever wrote the code
(aidlc ADR 0019). It reports: a changed path outside every bundle's MAY CHANGE, or inside a MUST NOT; an existing test
or assertion removed or changed, outside AMENDED ASSERTIONS and recipe commits; a dependency manifest that MAY CHANGE
does not name; a suppression or skip added without a valid `aidlc-exception: reason=...; owner=...;
expires=YYYY-MM-DD`; and a Tier 2 or 3 plan or bundle added or changed in a code pull request (ADR 0020).

    python3 scripts/check_slice.py [--key KEY] [--part N] [--base REF] [--branch NAME] [--root DIR]
    python3 scripts/check_slice.py --hook        (as a Stop hook: reads the hook's JSON on stdin)

The key comes from --key or the branch name (feat/SHIP-12-api gives SHIP-12). A branch that names no key is not an
aidlc story and is not checked. `plans/<KEY>/**` is exempt from the scope check. Exit 0 clean, 1 problems; as a Stop
hook, 2 on problems so the session continues and reads them, and 0 on its second run or when it cannot check.
Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FIELDS = {"GOAL", "INTENT", "PINS", "TIER", "MODE", "LOAD FIRST", "PATTERN", "USE SKILLS", "RECIPE", "MAY CHANGE",
          "MUST NOT", "AMENDED ASSERTIONS", "EVIDENCE", "OPEN", "DO", "DONE WHEN", "STOP IF", "RETURN", "REPRO",
          "EXPECTED", "SOURCE", "ACTUAL", "DESIGN", "LIKELY AREA", "CONFIRMED", "OUTCOME", "CRITERIA", "OWNER",
          "DEPENDENCIES", "DATA"}
FIELD_NAMES = sorted(FIELDS, key=len, reverse=True)     # "DONE WHEN" is tried before "DO"
KEY = re.compile(r"(?:^|/)([A-Z][A-Z0-9]+-\d+)(?=-|$)")
DOC = re.compile(r"^(plan\.md|bundle-[^/]+\.md|fix\.md|brief\.md)$")
BUNDLE_DOC = re.compile(r"^(bundle-[^/]+\.md|fix\.md|brief\.md)$")
MANIFESTS = {"package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml", "yarn.lock",
             "pyproject.toml", "poetry.lock", "uv.lock", "Pipfile", "Pipfile.lock", "packages.lock.json",
             "Directory.Packages.props", "go.mod", "go.sum", "pom.xml", "build.gradle", "build.gradle.kts",
             "Cargo.toml", "Cargo.lock", "Gemfile", "Gemfile.lock"}
MANIFEST_SUFFIXES = (".csproj", ".fsproj", ".vbproj")


@dataclass
class Bundle:
    name: str
    tier: int | None
    may_change: list[str]
    must_not: list[str]
    amended: str


@dataclass
class Branch:
    changed: dict[str, str]        # path -> A, M or D, against the merge base
    patches: list[str]             # the diffs of the non-merge, non-recipe commits (and the working tree as a hook)
    at_base: set[str]              # files that exist at the merge base
    base_docs: dict[str, str]      # the story folder's plan, bundles and briefs at the merge base
    head_docs: dict[str, str]      # the same documents now


def field_of(line: str) -> tuple[str, str] | None:
    """(NAME, value) when the line starts with a known field name and a space: templates align most values with two
    or more spaces, but long names (LIKELY AREA, DEPENDENCIES) are followed by one."""
    for name in FIELD_NAMES:
        if line.startswith(name) and line[len(name):len(name) + 1] in (" ", "\t"):
            return name, line[len(name):].strip()
    return None


def fields(text: str) -> dict[str, str]:
    """The FIELD lines of a bundle or brief, with indented continuation lines joined by newlines."""
    found: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        hit = field_of(line)
        if hit:
            current = hit[0]
            found[current] = hit[1]
        elif current and line[:1] in (" ", "\t") and line.strip():
            found[current] += "\n" + line.strip()
        else:
            current = None
    return found


def path_tokens(value: str) -> list[str]:
    """The paths and globs in a MAY CHANGE or MUST NOT value: notes in parentheses, placeholders and prose dropped."""
    value = re.sub(r"\([^)]*\)", " ", value)
    tokens = []
    for raw in re.split(r"[,\s]+", value):
        token = raw.strip("`'\"").rstrip(".;:")
        if not token or "<" in token or "{" in token:
            continue
        if "/" in token or "*" in token or re.search(r"\.[A-Za-z0-9]+$", token):
            token = token.removeprefix("./").lstrip("/")
            if token:
                tokens.append(token)
    return tokens


def glob_regex(glob: str) -> re.Pattern:
    """`**` crosses folders, `*` and `?` stay inside one; a trailing `/` means the whole folder."""
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    pattern = "".join(out) + (".*" if glob.endswith("/") else "")
    return re.compile(pattern + r"\Z")


def matches(path: str, globs: list[str]) -> bool:
    return any(glob_regex(g).match(path) for g in globs)


def key_from_branch(branch: str) -> str | None:
    m = KEY.search(branch or "")
    return m.group(1) if m else None


def tier_of(text: str | None) -> int | None:
    m = re.match(r"\s*(\d)", fields(text or "").get("TIER", ""))
    return int(m.group(1)) if m else None


def parse_bundle(name: str, text: str) -> Bundle:
    f = fields(text)
    amended = f.get("AMENDED ASSERTIONS", "none").strip()
    return Bundle(name, tier_of(text), path_tokens(f.get("MAY CHANGE", "")), path_tokens(f.get("MUST NOT", "")),
                  "" if amended.lower().startswith("none") else amended)


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout.decode("utf-8", errors="replace")


def collect(repo: Path, base: str, folder: str, worktree: bool) -> Branch:
    mb = git(repo, "merge-base", base, "HEAD").strip()
    target = [] if worktree else ["HEAD"]
    changed = {}
    for line in git(repo, "diff", "--name-status", "--no-renames", mb, *target).splitlines():
        status, path = line.split("\t", 1)
        changed[path] = status[0]
    untracked = git(repo, "ls-files", "--others", "--exclude-standard").splitlines() if worktree else []
    for path in untracked:
        changed[path] = "A"
    patches = []
    for commit in git(repo, "rev-list", "--reverse", "--no-merges", f"{mb}..HEAD").split():
        if re.search(r"^Recipe: \S+@\S+", git(repo, "log", "-1", "--format=%B", commit), re.M):
            continue
        patches.append(git(repo, "show", "--format=", "--no-renames", "-U1", commit))
    if worktree:
        patches.append(git(repo, "diff", "--no-renames", "-U1", "HEAD"))
        for path in untracked:
            file = repo / path
            if file.is_file() and file.stat().st_size < 1_000_000:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
                patches.append(f"diff --git a/{path} b/{path}\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n"
                               + "".join(f"+{line}\n" for line in lines))
    at_base = set(git(repo, "ls-tree", "-r", "--name-only", mb).splitlines())

    def docs_in(names: list[str]) -> list[str]:
        return [p for p in names if p.startswith(folder + "/") and DOC.match(p[len(folder) + 1:])]

    base_docs = {p: git(repo, "show", f"{mb}:{p}") for p in docs_in(sorted(at_base))}
    if worktree:
        here = [p.relative_to(repo).as_posix() for p in (repo / folder).glob("*.md")] if (repo / folder).is_dir() else []
        head_docs = {p: (repo / p).read_text(encoding="utf-8") for p in docs_in(sorted(here))}
    else:
        now = git(repo, "ls-tree", "-r", "--name-only", "HEAD").splitlines()
        head_docs = {p: git(repo, "show", f"HEAD:{p}") for p in docs_in(now)}
    return Branch(changed, patches, at_base, base_docs, head_docs)


def approved_bundles(branch: Branch) -> list[Bundle]:
    """At Tier 2 and 3 the copy on the base branch is the approved one; at Tier 1 the bundle travels with the code."""
    bundles = []
    for path in sorted(set(branch.base_docs) | set(branch.head_docs)):
        name = path.rsplit("/", 1)[1]
        if not BUNDLE_DOC.match(name):
            continue
        base, head = branch.base_docs.get(path), branch.head_docs.get(path)
        text = base if base is not None and (head is None or (tier_of(base) or 1) >= 2) else head
        if text is not None:
            bundles.append(parse_bundle(name, text))
    return bundles


def scope_problems(changed: dict[str, str], key_folder: str, bundles: list[Bundle]) -> list[str]:
    may = [g for b in bundles for g in b.may_change]
    must_not = [g for b in bundles for g in b.must_not]
    problems = []
    for path in sorted(changed):
        if path.startswith(key_folder + "/"):
            continue
        if matches(path, must_not):
            problems.append(f"{path}: changed, but a bundle's MUST NOT names it")
        elif not matches(path, may):
            problems.append(f"{path}: outside every bundle's MAY CHANGE")
    return problems


def is_manifest(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (name in MANIFESTS or name.endswith(MANIFEST_SUFFIXES)
            or (name.startswith("requirements") and name.endswith(".txt")))


def manifest_problems(changed: dict[str, str], bundles: list[Bundle]) -> list[str]:
    named = {g for b in bundles for g in b.may_change if not any(c in g for c in "*?") and not g.endswith("/")}
    return [f"{path}: a dependency manifest changed; a new dependency needs a person's approval (MAY CHANGE names "
            f"the file only when the plan approved the dependency)"
            for path in sorted(changed) if is_manifest(path) and path not in named]


def check(repo: Path, base: str, key: str, part: int | None = None, worktree: bool = False,
          today: dt.date | None = None) -> tuple[list[str], list[str]]:
    key_folder = f"plans/{key}"
    folder = key_folder if part is None else f"{key_folder}/part-{part}"
    branch = collect(repo, base, folder, worktree)
    if all(path.startswith(key_folder + "/") for path in branch.changed):
        return [], []     # a documents-only branch (spec, design or plan pull request, or a planning session)
    bundles = approved_bundles(branch)
    if not bundles:
        return [f"{folder}: no bundle or brief found; there is nothing approved to check this branch against"], []
    problems = scope_problems(branch.changed, key_folder, bundles) + manifest_problems(branch.changed, bundles)
    return problems, []
