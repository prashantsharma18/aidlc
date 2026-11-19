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
import collections
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
PROSE = {"e.g", "i.e", "etc", "none"}     # abbreviations and words that are not paths
MANIFEST_SUFFIXES = (".csproj", ".fsproj", ".vbproj")
TEST_PATH = re.compile(r"(^|/)(tests?|Tests?|__tests__|specs?)/|(^|/)test_[^/]+$|_test\.\w+$|\.(test|spec)\.\w+$"
                       r"|[a-z0-9]Tests?\.\w+$")
ASSERTION = re.compile(r"\bassert\b|\bassert[A-Z]\w*\s*\(|\bAssert\.|\bexpect\(|\.Should\(|\bShould\.|\bassertThat\("
                       r"|\.to(?:Be|Equal|Have|Throw|Match|Contain)\w*\(")
TEST_DEF = re.compile(r"^\s*(?:async\s+)?def\s+test_\w*|\b(?:it|test)\s*\(\s*['\"`]"
                      r"|\[(?:Fact|Theory|Test|TestMethod|TestCase)\b|@Test\b")
SUPPRESS = re.compile(r"eslint-disable|@ts-ignore|@ts-expect-error|#\s*noqa\b|#\s*type:\s*ignore|pylint:\s*disable"
                      r"|#pragma\s+warning\s+disable|\[SuppressMessage|//\s*nolint|@SuppressWarnings|NOSONAR"
                      r"|istanbul ignore|c8 ignore")
SKIP = re.compile(r"\b(?:it|test|describe)\.(?:skip|only|todo)\s*\(|\bx(?:it|describe|test)\s*\("
                  r"|@pytest\.mark\.(?:skip|skipif|xfail)\b|@unittest\.skip|\bpytest\.skip\(|\[Ignore\b"
                  r"|\bSkip\s*=\s*\"|@Disabled\b|@Ignore\b|\bt\.Skip\(")
EXCEPTION = re.compile(r"aidlc-exception:\s*reason=[^;]+;\s*owner=[^;]+;\s*expires=(\d{4}-\d{2}-\d{2})")
PROSE_SUFFIXES = (".md", ".txt", ".rst")


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
    folder: str = ""               # the folder whose bundles scope the work (the story folder, or a part's)


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
        if not token or "<" in token or "{" in token or token.lower() in PROSE:
            continue
        if ("/" in token or "*" in token or re.search(r"\.[A-Za-z0-9]+$", token)
                or token in MANIFESTS or token[0].isupper()):
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
    return re.compile(pattern + r"\Z", re.DOTALL)     # a file name may hold a newline


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
    # -z: git quotes non-ASCII, tab, quote and newline in paths otherwise, and a quoted path would slip past every glob
    parts = git(repo, "diff", "--name-status", "--no-renames", "-z", mb, *target).split("\0")
    for status, path in zip(parts[0::2], parts[1::2]):
        changed[path] = status[0]
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")[:-1] if worktree else []
    for path in untracked:
        changed[path] = "A"
    patches = []
    for commit in git(repo, "rev-list", "--reverse", "--no-merges", f"{mb}..HEAD").split():
        if re.search(r"^Recipe: \S+@\S+", git(repo, "log", "-1", "--format=%B", commit), re.M):
            continue
        patches.append(git(repo, "-c", "core.quotepath=off", "show", "--format=", "--no-renames", "-U1", commit))
    if worktree:
        patches.append(git(repo, "-c", "core.quotepath=off", "diff", "--no-renames", "-U1", "HEAD"))
        for path in untracked:
            file = repo / path
            if file.is_file() and file.stat().st_size < 1_000_000:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
                patches.append(f"diff --git a/{path} b/{path}\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n"
                               + "".join(f"+{line}\n" for line in lines))
    at_base = set(git(repo, "ls-tree", "-r", "--name-only", "-z", mb).split("\0")[:-1])

    story = "/".join(folder.split("/")[:2])     # plans/<KEY>: the plan lives here even when the work is a part

    def docs_in(names: list[str]) -> list[str]:
        return [p for p in names if p.startswith(story + "/") and DOC.match(p.rsplit("/", 1)[1])]

    base_docs = {p: git(repo, "show", f"{mb}:{p}") for p in docs_in(sorted(at_base))}
    if worktree:
        here = [p.relative_to(repo).as_posix() for p in (repo / story).rglob("*.md")] if (repo / story).is_dir() else []
        head_docs = {p: (repo / p).read_text(encoding="utf-8", errors="replace") for p in docs_in(sorted(here))}
    else:
        now = git(repo, "ls-tree", "-r", "--name-only", "-z", "HEAD").split("\0")[:-1]
        head_docs = {p: git(repo, "show", f"HEAD:{p}") for p in docs_in(now)}
    return Branch(changed, patches, at_base, base_docs, head_docs, folder)


def approved_bundles(branch: Branch) -> list[Bundle]:
    """At Tier 2 and 3 the copy on the base branch is the approved one; at Tier 1 the bundle travels with the code."""
    bundles = []
    for path in sorted(set(branch.base_docs) | set(branch.head_docs)):
        folder, name = path.rsplit("/", 1)
        if folder != branch.folder or not BUNDLE_DOC.match(name):
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


def unquote(path: str) -> str:
    """Decode a C-quoted path from a diff header ("a/caf\\303\\251.py"); an unquoted path comes back unchanged."""
    if not (len(path) >= 2 and path.startswith('"') and path.endswith('"')):
        return path
    simple = {"t": b"\t", "n": b"\n", "r": b"\r", "a": b"\a", "b": b"\b", "f": b"\f", "v": b"\v",
              '"': b'"', "\\": b"\\"}
    inner, out, i = path[1:-1], bytearray(), 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner):
            octal = re.match(r"[0-7]{1,3}", inner[i + 1:])
            if octal:
                out.append(int(octal.group(), 8) & 0xFF)
                i += 1 + len(octal.group())
                continue
            out += simple.get(inner[i + 1], inner[i + 1].encode())
            i += 2
        else:
            out += c.encode()
            i += 1
    return out.decode("utf-8", errors="replace")


def hunks(patch: str):
    """Yield (path, kind, text) for each body line of a unified diff: kind is '-', '+' or ' '; '@' starts a hunk."""
    path, in_header = None, False
    for line in patch.splitlines():
        if line.startswith("diff --git "):
            path, in_header = None, True
        elif in_header and line.startswith("--- "):
            old = unquote(line[4:].split("\t", 1)[0])     # git adds a trailing tab after a path with a space
            path = old[2:] if old.startswith("a/") else None
        elif in_header and line.startswith("+++ "):
            new = unquote(line[4:].split("\t", 1)[0])
            path = new[2:] if new.startswith("b/") else path
        elif line.startswith("@@"):
            in_header = False
            yield path, "@", ""
        elif not in_header and path and line[:1] in ("-", "+", " "):
            yield path, line[0], line[1:]


def removed_tests(patch: str) -> list[tuple[str, str]]:
    """(file, line) for each test definition or assertion the patch removes that the same patch does not add back
    (a moved or renamed test is not a removed one). Each added line covers one removal of the same text, no more."""
    removed, added = [], collections.Counter()
    for path, kind, text in hunks(patch):
        if kind == "-" and (ASSERTION.search(text) or TEST_DEF.search(text)):
            removed.append((path, text))
        elif kind == "+":
            added[text.strip()] += 1
    left = []
    for path, text in removed:
        if added[text.strip()] > 0:
            added[text.strip()] -= 1
        else:
            left.append((path, text))
    return left


def amended_paths(bundles: list[Bundle]) -> set[str]:
    """The files named under AMENDED ASSERTIONS: `path::test_name: reason` entries give the path; matched exactly."""
    return {t for b in bundles for t in path_tokens(re.sub(r"::\S*", "", b.amended))}


def test_problems(branch: Branch, bundles: list[Bundle]) -> tuple[list[str], list[str]]:
    amended = amended_paths(bundles)
    problems, notes, added_before = [], [], collections.Counter()
    for patch in branch.patches:
        for path, text in removed_tests(patch):
            if path not in branch.at_base or not TEST_PATH.search(path):
                continue
            if added_before[(path, text.strip())] > 0:     # added earlier on this branch, in this same file
                added_before[(path, text.strip())] -= 1
                continue
            where = f"{path}: {text.strip()[:120]}"
            if path in amended:
                notes.append(f"amended assertion, listed under AMENDED ASSERTIONS: {where}")
            else:
                problems.append(f"an existing test or assertion is removed or changed: {where}")
        for path, kind, text in hunks(patch):
            if kind == "+":
                added_before[(path, text.strip())] += 1
    return problems, notes


def valid_exception(text: str, today: dt.date) -> bool:
    m = EXCEPTION.search(text)
    if not m:
        return False
    try:
        return dt.date.fromisoformat(m.group(1)) >= today
    except ValueError:
        return False


def marker_problems(patch: str, today: dt.date) -> list[str]:
    problems, previous = [], ""
    for path, kind, text in hunks(patch):
        if kind == "@":
            previous = ""
            continue
        if kind == "+" and not path.endswith(PROSE_SUFFIXES) and (SUPPRESS.search(text) or SKIP.search(text)):
            if not (valid_exception(text, today) or valid_exception(previous, today)):
                problems.append(f"{path}: a suppression or skip without a valid aidlc-exception (reason, owner and an "
                                f"expiry date not past): {text.strip()[:120]}")
        if SUPPRESS.search(text) or SKIP.search(text):
            previous = ""     # a marker line never lends its exception to the next line
        elif kind in ("+", " "):
            previous = text
    return problems


def approval_problems(branch: Branch, key_folder: str) -> list[str]:
    """ADR 0020: at Tier 2 and 3 a code pull request never adds, changes or removes the plan or a bundle."""
    if all(path.startswith(key_folder + "/") for path in branch.changed):
        return []
    base_tiers = [tier_of(t) or 1 for t in branch.base_docs.values()]
    story = max(base_tiers, default=1)     # the tier the plan was approved at
    highest = max([story] + [tier_of(t) or 1 for t in branch.head_docs.values()])
    problems = []
    for path in sorted(branch.changed):
        status = branch.changed[path]
        text = branch.head_docs.get(path) if status != "D" else None
        if path not in branch.head_docs and not (status == "D" and path in branch.base_docs):
            continue
        if status in ("A", "M") and text is None:
            continue
        name = path.rsplit("/", 1)[1]
        if name in ("fix.md", "brief.md"):
            continue
        if name == "plan.md":
            level = highest
        else:
            level = max(tier_of(text) or 1, tier_of(branch.base_docs.get(path)) or 1, story)
        if level >= 2:
            verb = {"A": "added", "M": "changed", "D": "removed"}.get(status, "changed")
            problems.append(f"{path}: a Tier {level} plan or bundle is {verb} in a code pull request; it merges first "
                            f"in its own pull request, approved by the tech lead (ADR 0020)")
    return problems


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
    found, notes = test_problems(branch, bundles)
    problems += found
    for patch in branch.patches:
        problems += marker_problems(patch, today or dt.date.today())
    problems += approval_problems(branch, key_folder)
    return problems, notes
