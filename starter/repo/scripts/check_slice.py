#!/usr/bin/env python3
"""Checks a story branch against its approved task bundles, mechanically, so the rules hold whoever wrote the code
(aidlc ADR 0019). It reports: a changed path outside every bundle's MAY CHANGE, or inside a MUST NOT; an existing test
or assertion removed or changed and not restored later on the branch, outside AMENDED ASSERTIONS and approved recipe
commits; a dependency manifest that MAY CHANGE does not name; a suppression or skip in the branch's net result, new or
wider than the one it replaces, without a valid `aidlc-exception: reason=...; owner=...; expires=YYYY-MM-DD`; and a
Tier 2 or 3 plan or bundle added or changed in a code pull request (ADR 0020).

    python3 scripts/check_slice.py [--key KEY] [--part N] [--base REF] [--branch NAME] [--root DIR]
    python3 scripts/check_slice.py --hook        (as a Stop hook: reads the hook's JSON on stdin)

The key comes from --key or the branch name (feat/SHIP-12-api gives SHIP-12). A branch that names no key is not an
aidlc story and is not checked. Without --part, a branch that changes one `plans/<KEY>/part-<n>/` folder is checked
against that part's bundles. `plans/<KEY>/**` is exempt from the scope check. A commit's `Recipe: <tool>@<version>`
trailer exempts it from the assertion check only when an approved bundle's RECIPE names that tool and version.
Exit 0 clean, 1 problems; as a Stop hook, 2 on problems so the session continues and reads them, and 0 on its second
run, when it cannot check, or when no bundle or brief exists yet (a planning, verify or review turn).
Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import subprocess
import sys
from collections.abc import Callable
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
SUPPRESS = re.compile(r"eslint-disable|@ts-ignore|@ts-expect-error|@ts-nocheck|(?i:#\s*noqa\b)"
                      r"|(?i:#\s*(?:flake8|ruff)\s*:\s*noqa\b)|#\s*type:\s*ignore|#\s*mypy:\s*ignore-errors"
                      r"|pylint:\s*(?:disable|skip-file)"
                      r"|#pragma\s+warning\s+disable|\[SuppressMessage|//\s*nolint|@SuppressWarnings|NOSONAR"
                      r"|(?:istanbul|c8|v8) ignore\b(?!\s+stop\b)")
SKIP = re.compile(r"\b(?:it|test|describe)\.(?:skip|only|todo)\s*\(|\bx(?:it|describe|test)\s*\("
                  r"|@pytest\.mark\.(?:skip|skipif|xfail)\b|@unittest\.skip|\bpytest\.skip\(|\[Ignore\b"
                  r"|\bSkip\s*=\s*\"|@Disabled\b|@Ignore\b|\bt\.Skip\("
                  r"|\bpytestmark\b.*?\bpytest\.mark\.(?:skip|skipif|xfail)\b")
MARKER = re.compile(f"{SUPPRESS.pattern}|{SKIP.pattern}")
# A closing directive ends a suppression its family opened earlier in the file; it is never a marker itself
CLOSER = re.compile(r"(?P<eslint>eslint-enable)\b|(?P<csharp_pragma>#pragma\s+warning\s+restore)\b"
                    r"|(?P<pylint>pylint:\s*enable)\s*=|(?P<coverage>(?:istanbul|c8|v8) ignore\s+stop)\b")
# How far a marker reaches, smallest first. A skip reads the same ranks as test < suite < file (`.only` skips the rest
# of the file).
SCOPE_LINE = 1                     # one line or statement
SCOPE_BLOCK = 2                    # a block, a declaration or a class
SCOPE_FILE = 3                     # the whole file
SCOPE_TEST = SCOPE_LINE            # one test
SCOPE_SUITE = SCOPE_BLOCK          # a suite, a test class or a test module
SCOPE_NAMES = {SCOPE_LINE: "line", SCOPE_BLOCK: "block", SCOPE_FILE: "file"}
SKIP_SCOPE_NAMES = {SCOPE_TEST: "test", SCOPE_SUITE: "suite", SCOPE_FILE: "file"}
RECIPE_TRAILER = re.compile(r"^Recipe: (\S+@\S+)", re.MULTILINE)
EXCEPTION = re.compile(r"aidlc-exception:\s*reason=[^;]+;\s*owner=[^;]+;\s*expires=(\d{4}-\d{2}-\d{2})")
PROSE_SUFFIXES = (".md", ".txt", ".rst")


@dataclass
class Bundle:
    name: str
    tier: int | None
    may_change: list[str]
    must_not: list[str]
    amended: str
    recipe: str = ""               # the approved RECIPE value; empty when it is none


@dataclass
class Patch:
    text: str                      # a unified diff
    commit: str = ""               # the commit it comes from; empty for the working tree
    trailer: str = ""              # the commit's `Recipe:` trailer (tool@version), if it has one


@dataclass
class Branch:
    changed: dict[str, str]        # path -> A, M or D, against the merge base
    patches: list[Patch]           # each non-merge commit's diff, in order (and the working tree's, as a hook)
    at_base: set[str]              # files that exist at the merge base
    base_docs: dict[str, str]      # the story folder's plan, bundles and briefs at the merge base
    head_docs: dict[str, str]      # the same documents now
    net: str = ""                  # the branch's net diff against the merge base, renames detected
    folder: str = ""               # the folder whose bundles scope the work (the story folder, or a part's)
    base: str = ""                 # the merge base commit
    worktree: bool = False         # the head is the working tree (the Stop hook), not HEAD (CI)


@dataclass(frozen=True)
class Marker:
    """A suppression or skip, read: which tool's mechanism, how far it reaches, and which rules it names."""
    family: str                    # eslint, noqa, mypy, pylint, ts, csharp-pragma, csharp-attr, go-nolint, java,
                                   # sonar, coverage or skip
    scope: int                     # SCOPE_LINE < SCOPE_BLOCK < SCOPE_FILE (a skip: SCOPE_TEST < SCOPE_SUITE)
    rules: frozenset[str] | None   # the rules or codes it names; None when it names none, so it silences every rule
    self_checking: bool = False    # it fails once it silences nothing (`@ts-expect-error`), so it is narrower

    @property
    def scope_name(self) -> str:
        return (SKIP_SCOPE_NAMES if self.family == "skip" else SCOPE_NAMES)[self.scope]

    @property
    def width(self) -> tuple[int, bool, int, bool]:
        """Orders markers of one family from narrowest to widest."""
        return self.scope, self.rules is None, len(self.rules or ()), not self.self_checking

    def covers(self, added: Marker) -> bool:
        """A removed marker covers an added one that is no wider: same family, scope no larger, every rule the added
        one names named here too (a marker that names no rule is covered only by another that names none), and not
        self-checking where this one was."""
        return (self.family == added.family and added.scope <= self.scope
                and (self.rules is None or (added.rules is not None and added.rules <= self.rules))
                and (added.self_checking or not self.self_checking))

    def wider_than(self, removed: Marker) -> bool:
        """Reaches further than a removed marker of its family: a larger scope, more rules, or no longer self-checking.
        Rules that differ without one list holding the other are another suppression, not a wider one."""
        more_rules = removed.rules is not None and (self.rules is None or self.rules > removed.rules)
        return self.family == removed.family and (self.scope > removed.scope or more_rules
                                                  or (removed.self_checking and not self.self_checking))

    def __str__(self) -> str:
        rules = ",".join(sorted(self.rules)) if self.rules is not None else "all rules"
        return f"{self.family}, {self.scope_name}, {rules}" + (", self-checking" if self.self_checking else "")


@dataclass
class Review:
    problems: list[str]
    notes: list[str]               # for the reviewer: amended assertions
    recipe_notes: list[str]        # for the reviewer: the recipe commits exempted from the assertion check, or not
    no_bundle: bool = False        # code changed, but nothing approved to check it against


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
    recipe = f.get("RECIPE", "none").strip()
    return Bundle(name, tier_of(text), path_tokens(f.get("MAY CHANGE", "")), path_tokens(f.get("MUST NOT", "")),
                  "" if amended.lower().startswith("none") else amended,
                  "" if recipe.lower().startswith("none") or recipe.startswith("<") else recipe)


def approved_recipes(bundles: list[Bundle]) -> set[str]:
    """The tool@version tokens the approved bundles' RECIPE values name."""
    return {t.strip("`'\",;:()") for b in bundles for t in b.recipe.split() if "@" in t}


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
        trailer = RECIPE_TRAILER.search(git(repo, "log", "-1", "--format=%B", commit))
        patches.append(Patch(git(repo, "-c", "core.quotepath=off", "show", "--format=", "--no-renames", "-U1", commit),
                             commit, trailer.group(1) if trailer else ""))
    new_files = []
    for path in untracked:
        file = repo / path
        if file.is_file() and file.stat().st_size < 1_000_000:
            lines = git_lines(file.read_bytes().decode("utf-8", errors="replace"))
            new_files.append(f"diff --git a/{path} b/{path}\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n"
                             + "".join(f"+{line}\n" for line in lines))
    if worktree:
        patches.append(Patch(git(repo, "-c", "core.quotepath=off", "diff", "--no-renames", "-U1", "HEAD")))
        patches += [Patch(text) for text in new_files]
    # The net result: only what survives counts for markers (a slip undone later is gone), and a moved file keeps
    # its suppressions (renames detected)
    net = "\n".join([git(repo, "-c", "core.quotepath=off", "diff", "-M", "-U1", mb, *target)] + new_files)
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
    return Branch(changed, patches, at_base, base_docs, head_docs, net, folder, mb, worktree)


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


def git_lines(text: str) -> list[str]:
    """Split text into lines as git counts them: on "\n" only, so a form feed or U+2028 stays inside its line (Python's
    splitlines would split there and put every later line number out of step with the diff); a trailing "\r" goes."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    return [line.removesuffix("\r") for line in lines]


@dataclass
class DiffLine:
    path: str | None               # the file's path after the change (its old path when it was deleted)
    old_path: str | None           # its path before the change; None for a new file
    kind: str                      # '-', '+' or ' '; '@' starts a hunk
    text: str
    old_number: int = 0            # the line's number in the old file ('-', ' '), or the old line it comes before ('+')
    new_number: int = 0            # the line's number in the new file ('+', ' '), or the new line it comes before ('-')
    deleted: bool = False          # the change deletes the file

    @property
    def number(self) -> int:
        """Its line number in its own version: the old file for '-', the new one otherwise."""
        return self.old_number if self.kind == "-" else self.new_number


def diff_lines(patch: str):
    """Yield a DiffLine for each hunk start and body line of a unified diff."""
    path, old_path, deleted, in_header, old_no, new_no = None, None, False, False, 0, 0
    for line in git_lines(patch):
        if line.startswith("diff --git "):
            path, old_path, deleted, in_header = None, None, False, True
        elif in_header and line.startswith("--- "):
            old = unquote(line[4:].split("\t", 1)[0])     # git adds a trailing tab after a path with a space
            path = old_path = old[2:] if old.startswith("a/") else None
        elif in_header and line.startswith("+++ "):
            new = unquote(line[4:].split("\t", 1)[0])
            path = new[2:] if new.startswith("b/") else path
            deleted = new == "/dev/null"
        elif line.startswith("@@"):
            in_header = False
            start = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            old_no, new_no = (int(start.group(1)), int(start.group(2))) if start else (0, 0)
            yield DiffLine(path, old_path, "@", "", old_no, new_no, deleted)
        elif not in_header and path and line[:1] in ("-", "+", " "):
            yield DiffLine(path, old_path, line[0], line[1:], old_no, new_no, deleted)
            old_no += line[0] != "+"
            new_no += line[0] != "-"


def hunks(patch: str):
    """Yield (path, kind, text) for each body line of a unified diff: kind is '-', '+' or ' '; '@' starts a hunk."""
    for d in diff_lines(patch):
        yield d.path, d.kind, d.text


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


def test_problems(branch: Branch, bundles: list[Bundle], exempt: set[str]) -> tuple[list[str], list[str]]:
    """Removals are found commit by commit, so an exempt recipe commit's own changes stay out. A removal is dropped
    when another counted commit (or the working tree) in the same file adds the same line: earlier means the line was
    added on this branch, later means it was restored. Each added line covers one removal, no more."""
    amended = amended_paths(bundles)
    patches = [p for p in branch.patches if not p.commit or p.commit not in exempt]
    added = [collections.Counter((path, text.strip()) for path, kind, text in hunks(p.text) if kind == "+")
             for p in patches]
    problems, notes = [], []
    for i, patch in enumerate(patches):
        for path, text in removed_tests(patch.text):
            if path not in branch.at_base or not TEST_PATH.search(path):
                continue
            line = (path, text.strip())
            cover = next((j for j in [*range(i), *range(i + 1, len(patches))] if added[j][line] > 0), None)
            if cover is not None:
                added[cover][line] -= 1
                continue
            where = f"{path}: {text.strip()[:120]}"
            if path in amended:
                notes.append(f"amended assertion, listed under AMENDED ASSERTIONS: {where}")
            else:
                problems.append(f"an existing test or assertion is removed or changed: {where}")
    return problems, notes


def valid_exception(text: str, today: dt.date) -> bool:
    m = EXCEPTION.search(text)
    if not m:
        return False
    try:
        return dt.date.fromisoformat(m.group(1)) >= today
    except ValueError:
        return False


def rule_set(listed: str) -> frozenset[str]:
    """The rule names in a list: split on commas and whitespace, order and duplicates dropped."""
    return frozenset(name for name in re.split(r"[,\s]+", listed) if name)


@dataclass(frozen=True)
class Place:
    """Where a marker stands, which some families need to read its scope."""
    own_line: bool                 # nothing but comment openers before it on its line
    on_class: bool                 # the next code line below it declares a class
    on_header: bool = False        # it trails a Python `def` or `class` line, so it covers that block


# Each reader takes the line from the marker on (`rest`) and its Place; it returns the Marker, or None when it cannot
# read the details (the caller treats that as new).

def read_eslint(rest: str, at: Place) -> Marker | None:
    m = re.match(r"eslint-disable(-next-line|-line)?(?=\s|\*/|--|$)(.*)", rest)
    if not m:
        return None
    rules = rule_set(re.split(r"\*/|--", m.group(2), maxsplit=1)[0])     # the list ends at a description or the */
    if any(not re.fullmatch(r"[\w@/.-]+", name) for name in rules):
        return None
    return Marker("eslint", SCOPE_LINE if m.group(1) else SCOPE_BLOCK, rules or None)


def read_ts(rest: str, at: Place) -> Marker | None:
    """`@ts-expect-error` fails once the line has no error, so `@ts-ignore` is wider than it."""
    m = re.match(r"@ts-(ignore|expect-error|nocheck)\b", rest)
    if not m:
        return None
    if m.group(1) == "nocheck":
        return Marker("ts", SCOPE_FILE, None)
    return Marker("ts", SCOPE_LINE, None, self_checking=m.group(1) == "expect-error")


def read_noqa(rest: str, at: Place) -> Marker | None:
    """flake8 and Ruff: `# noqa`, `# noqa: E501,F401`, and the file-level `# ruff: noqa` / `# flake8: noqa`. A colon
    followed by anything but codes is not read (flake8 would silence everything)."""
    m = re.match(r"#\s*(?:(flake8|ruff)\s*:\s*)?noqa\b(.*)", rest, re.IGNORECASE)
    if not m:
        return None
    scope = SCOPE_FILE if m.group(1) else SCOPE_LINE
    codes = re.match(r":\s?([A-Z]+[0-9]+(?:[,\s]+[A-Z]+[0-9]+)*)", m.group(2), re.IGNORECASE)
    if codes:
        return Marker("noqa", scope, rule_set(codes.group(1).upper()))
    return None if m.group(2).lstrip().startswith(":") else Marker("noqa", scope, None)


def read_mypy(rest: str, at: Place) -> Marker | None:
    """`# type: ignore[code, ...]`; on a line of its own at the top of a file it silences the whole file, so a
    `# type: ignore` on its own line ranks as file."""
    if re.match(r"#\s*mypy:\s*ignore-errors\b", rest):
        return Marker("mypy", SCOPE_FILE, None)
    m = re.match(r"#\s*type:\s*ignore(.*)", rest)
    if not m:
        return None
    tail, scope = m.group(1), SCOPE_FILE if at.own_line else SCOPE_LINE
    if tail.startswith("["):
        codes = re.match(r"\[\s*([\w-]+(?:\s*,\s*[\w-]+)*)\s*\]", tail)
        return Marker("mypy", scope, rule_set(codes.group(1))) if codes else None
    if tail and not tail[0].isspace() and tail[0] != "#":
        return None
    return Marker("mypy", scope, None)


def read_pylint(rest: str, at: Place) -> Marker | None:
    if re.match(r"pylint:\s*skip-file\b", rest):
        return Marker("pylint", SCOPE_FILE, None)
    m = re.match(r"pylint:\s*disable(-next)?\s*=\s*([\w-]+(?:\s*,\s*[\w-]+)*)", rest)
    if not m:
        return None
    rules = rule_set(m.group(2))
    # On its own line it reaches the end of the block; trailing a `def` or `class` line, it covers that block
    scope = SCOPE_LINE if m.group(1) or not (at.own_line or at.on_header) else SCOPE_BLOCK
    return Marker("pylint", scope, None if "all" in rules else rules)


def read_pragma(rest: str, at: Place) -> Marker | None:
    m = re.match(r"#pragma\s+warning\s+disable\b(.*)", rest)
    if not m:
        return None
    rules = rule_set(m.group(1).split("//", 1)[0])
    if any(not re.fullmatch(r"\w+", code) for code in rules):
        return None
    return Marker("csharp-pragma", SCOPE_BLOCK, rules or None)


def read_suppress_message(rest: str, at: Place) -> Marker | None:
    """`[SuppressMessage("Category", "CA1062:Title")]`: the rule is the check id before the colon."""
    m = re.match(r'\[SuppressMessage(?:Attribute)?\s*\(\s*@?"[^"]*"\s*,\s*@?"([^":]*)(?::[^"]*)?"', rest)
    if not m or not m.group(1).strip():
        return None
    scope = SCOPE_FILE if at.on_class or re.search(r"\bScope\s*=", rest) else SCOPE_BLOCK
    return Marker("csharp-attr", scope, frozenset({m.group(1).strip()}))


def read_nolint(rest: str, at: Place) -> Marker | None:
    """golangci-lint: `//nolint` or `//nolint:a,b`, then nothing or a `// explanation`. On a line of its own it covers
    the declaration below it."""
    m = re.match(r"//\s*nolint\b(.*)", rest)
    if not m:
        return None
    tail, rules = m.group(1), None
    if tail.startswith(":"):
        listed = re.match(r":([\w-]+(?:,[\w-]+)*)(?=\s*(?://|$))", tail)
        if not listed:
            return None
        rules = rule_set(listed.group(1))
        rules = None if "all" in rules else rules
    elif tail and not tail[0].isspace():
        return None
    return Marker("go-nolint", SCOPE_BLOCK if at.own_line else SCOPE_LINE, rules)


def read_java(rest: str, at: Place) -> Marker | None:
    m = re.match(r"@SuppressWarnings\s*\(([^)]*)\)", rest)
    names = re.findall(r'"([^"]*)"', m.group(1)) if m else []
    if not names:
        return None
    rules = frozenset(name.strip() for name in names)
    return Marker("java", SCOPE_FILE if at.on_class else SCOPE_BLOCK, None if "all" in rules else rules)


def read_sonar(rest: str, at: Place) -> Marker | None:
    return Marker("sonar", SCOPE_LINE, None)


def read_coverage(rest: str, at: Place) -> Marker | None:
    """istanbul, c8 and v8: `ignore next [n]`, `if`, `else`, `start`, `file` (`stop` is a closing directive)."""
    m = re.match(r"(?:istanbul|c8|v8) ignore\s+(next|if|else|start|file)\b(?:\s+(\d+))?", rest)
    if not m:
        return None
    word, count = m.group(1), int(m.group(2) or 1)
    if word == "file":
        return Marker("coverage", SCOPE_FILE, None)
    wide = word == "start" or (word == "next" and count > 1)
    return Marker("coverage", SCOPE_BLOCK if wide else SCOPE_LINE, None)


def read_skip(rest: str, at: Place) -> Marker | None:
    js = re.match(r"(?:(it|test|describe)\.(skip|only|todo)|x(it|describe|test))\s*\(", rest)
    if js:
        if js.group(2) == "only":
            return Marker("skip", SCOPE_FILE, None)     # every other test in the file stops running
        suite = "describe" in (js.group(1), js.group(3))
        return Marker("skip", SCOPE_SUITE if suite else SCOPE_TEST, None)
    if re.match(r"pytestmark\b", rest):
        return Marker("skip", SCOPE_SUITE, None)
    if re.match(r"pytest\.skip\(", rest):
        module = re.search(r"allow_module_level\s*=\s*True", rest)
        return Marker("skip", SCOPE_SUITE if module else SCOPE_TEST, None)
    if re.match(r"@pytest\.mark\.|@unittest\.skip|\[Ignore\b|@Disabled\b|@Ignore\b", rest):
        return Marker("skip", SCOPE_SUITE if at.on_class else SCOPE_TEST, None)     # on a class: the whole suite
    if re.match(r"Skip\s*=|t\.Skip\(", rest):
        return Marker("skip", SCOPE_TEST, None)
    return None


READERS = [(re.compile(r"eslint-disable"), read_eslint),
           (re.compile(r"@ts-"), read_ts),
           (re.compile(r"#\s*(?:(?:flake8|ruff)\s*:\s*)?noqa", re.IGNORECASE), read_noqa),
           (re.compile(r"#\s*(?:type|mypy):"), read_mypy),
           (re.compile(r"pylint:"), read_pylint),
           (re.compile(r"#pragma"), read_pragma),
           (re.compile(r"\[SuppressMessage"), read_suppress_message),
           (re.compile(r"//\s*nolint"), read_nolint),
           (re.compile(r"@SuppressWarnings"), read_java),
           (re.compile(r"NOSONAR"), read_sonar),
           (re.compile(r"istanbul|c8|v8"), read_coverage)]
CLASS_LINE = re.compile(r"\s*(?:[\w@]+\s+)*class\s+\w")     # `class T(...)`, `public final class OrderTest {`
BLOCK_HEADER = re.compile(r"\s*(?:async\s+)?(?:def|class)\s")    # a Python `def` or `class` line


def markers_of(text: str, following: str | None = "", added: bool = True) -> list[Marker | None]:
    """Every suppression or skip on a line, in order, each read as a Marker, or None where the details cannot be read.
    `following` is the next code line below it, which tells whether a decorator or attribute sits on a class. When it
    is unknown (None), an added marker is read as on a class (its widest) and a removed one as not (its narrowest)."""
    on_class = CLASS_LINE.match(following) is not None if following is not None else added
    found = []
    for m in MARKER.finditer(text):
        rest = text[m.start():].split("aidlc-exception", 1)[0]     # an exception's text is not part of the marker
        before = text[:m.start()]
        at = Place(re.fullmatch(r"[\s#/*{<!-]*", before) is not None, on_class, BLOCK_HEADER.match(before) is not None)
        reader = next((read for head, read in READERS if head.match(rest)), read_skip)
        found.append(reader(rest, at))
    return found


def parse_marker(text: str, following: str = "") -> Marker | None:
    """The first suppression or skip on a line, read; None when the line has none or its details cannot be read."""
    found = markers_of(text, following)
    return found[0] if found else None


# A file's lines in one version: side '-' is the merge base, '+' the head (the working tree for the hook, HEAD in CI);
# None when that version cannot be read
Source = Callable[[str, str], list[str] | None]
NOT_CODE = ("@", "[", "#", "//", "/*", "*")     # decorators, attributes and comments


def following_code(file_lines: list[str], number: int) -> str | None:
    """The first code line below line `number` (1-based), past decorators, attributes (with their continuation
    lines), comments and blank lines; None when the file ends first."""
    def opened(text: str) -> int:
        return text.count("(") + text.count("[") - text.count(")") - text.count("]")

    depth = max(0, opened(file_lines[number - 1])) if 0 < number <= len(file_lines) else 0     # a multi-line decorator
    for text in file_lines[number:]:
        stripped = text.strip()
        if depth or stripped.startswith(("@", "[")):
            depth = max(0, depth + opened(stripped))
        elif stripped and not stripped.startswith(NOT_CODE):
            return text
    return None


def following_line(d: DiffLine, source: Source | None) -> str | None:
    """The code line below a diff line, read from its own version of the file; None when it cannot be read."""
    path = d.old_path if d.kind == "-" else d.path
    file_lines = source(d.kind, path) if source and path and d.number else None
    return following_code(file_lines, d.number) if file_lines is not None else None


def head_number(lines: list[DiffLine], path: str, number: int) -> int:
    """Where an unchanged line of the old file (line `number`) sits in the new one: shifted by the lines the diff
    added and removed above it."""
    shift = 0
    for d in lines:
        if d.path != path or d.kind == "@":
            continue
        old_after, new_after = d.old_number + (d.kind != "+"), d.new_number + (d.kind != "-")
        if old_after > number:
            break
        shift = new_after - old_after
    return number + shift


def read_closer(text: str) -> tuple[str, frozenset[str] | None, str] | None:
    """(family, the rules it ends or None for every rule, its directive) for the closing directive on a line."""
    m = CLOSER.search(text)
    if not m:
        return None
    family, directive, rest = m.lastgroup.replace("_", "-"), re.sub(r"\s+", " ", m.group(m.lastgroup)), text[m.end():]
    if family == "eslint":
        listed = re.split(r"\*/|--", rest, maxsplit=1)[0]
    elif family == "pylint":
        names = re.match(r"\s*=\s*([\w-]+(?:\s*,\s*[\w-]+)*)", rest)
        listed = names.group(1) if names and names.group(1) != "all" else ""
    elif family == "csharp-pragma":
        listed = rest.split("//", 1)[0]
    else:
        listed = ""     # coverage: `ignore stop` ends whatever `ignore start` began
    return family, rule_set(listed) or None, directive


def overlap(a: frozenset[str] | None, b: frozenset[str] | None) -> bool:
    """Two rule lists share a rule; a list that names none (None) shares every rule."""
    return a is None or b is None or bool(a & b)


def still_open(head: list[str], before: int, family: str) -> list[tuple[int, frozenset[str] | None]]:
    """(line, rules still off) for each opener of a family still open just above line `before` of the head file: a
    block-or-wider marker, less the rules each later closer of its family ends (a closer naming no rule ends them all;
    one naming some cannot narrow an opener that names none, which stays open)."""
    opened: list[tuple[int, frozenset[str] | None]] = []
    for number, text in enumerate(head[:max(0, before - 1)], start=1):
        closer = read_closer(text)
        if closer and closer[0] == family:
            ended, kept = closer[1], []
            for at, rules in opened:
                if ended is None:     # a closer naming no rule ends every opener
                    continue
                left = None if rules is None else rules - ended     # an opener naming no rule stays open
                if left is None or left:
                    kept.append((at, left))
            opened = kept
        opened += [(number, m.rules) for m in markers_of(text)
                   if m is not None and m.family == family and m.scope >= SCOPE_BLOCK]
    return opened


def closer_problems(lines: list[DiffLine], source: Source | None, today: dt.date) -> list[str]:
    """A closing directive removed in the net diff may leave a suppression running further. It is judged on the head
    file at the closer's former place: each opener of its family still open there with rules it ended needs a valid
    exception on its own line or the line above it, in the head. A deleted file is clean; a head that cannot be read
    is reported (fail safe)."""
    problems = []
    for d in lines:
        closer = read_closer(d.text) if d.kind == "-" and not d.path.endswith(PROSE_SUFFIXES) else None
        if not closer or d.deleted:
            continue
        family, rules, directive = closer
        head = source("+", d.path) if source else None
        if head is not None:
            # Up to the next old line's place, so a closer that replaced it on the same spot counts
            place = head_number(lines, d.path, d.number + 1)
            unexcused = [at for at, left in still_open(head, place, family) if overlap(left, rules)
                         and not (valid_exception(head[at - 1], today)
                                  or (at > 1 and valid_exception(head[at - 2], today)))]
            if not unexcused:
                continue
        problems.append(f"{d.path}: a suppression got wider (its closing {directive} was removed) without a valid "
                        f"aidlc-exception: {d.text.strip()[:120]}")
    return problems


def marker_problems(patch: str, today: dt.date, source: Source | None = None) -> list[str]:
    """Judged on the net diff. An added marker is not a new suppression when the same file loses a marker of the same
    family that covers it: no wider in scope and naming every rule it names (an edited, moved or narrowed suppression).
    Each removed marker covers one added marker. A wider marker, one beyond those removed, or one whose details cannot
    be read (fail safe) still needs its exception; so does a removed closing directive. `source` reads each version of
    a file, to tell whether a decorator sits on a class; without it, the fail-safe reading applies."""
    lines = list(diff_lines(patch))
    unused = collections.defaultdict(list)     # (path, family) -> removed markers not yet spent as a cover
    for d in lines:
        if d.kind == "-" and MARKER.search(d.text):
            for marker in markers_of(d.text, following_line(d, source), added=False):
                if marker:
                    unused[(d.path, marker.family)].append(marker)
    needed, previous = [], ""     # (path, text, markers) for each added marker line without a valid exception
    for d in lines:
        if d.kind == "@":
            previous = ""
            continue
        is_marker = bool(MARKER.search(d.text))
        if d.kind == "+" and is_marker and not d.path.endswith(PROSE_SUFFIXES):
            if not (valid_exception(d.text, today) or valid_exception(previous, today)):
                needed.append((d.path, d.text, markers_of(d.text, following_line(d, source), added=True)))
        if is_marker:
            previous = ""     # a marker line never lends its exception to the next line
        elif d.kind in ("+", " "):
            previous = d.text
    # Widest first, each taking the narrowest removed marker that covers it, so a broad cover is not spent on a
    # narrow marker that a narrower one could cover
    readable = [(n, m) for n, (_, _, markers) in enumerate(needed) if None not in markers for m in markers]
    uncovered = collections.defaultdict(list)
    for n, marker in sorted(readable, key=lambda item: item[1].width, reverse=True):
        pool = unused[(needed[n][0], marker.family)]
        covers = [removed for removed in pool if removed.covers(marker)]
        if covers:
            pool.remove(min(covers, key=lambda removed: removed.width))
        else:
            uncovered[n].append(marker)
    problems = []
    for n, (path, text, markers) in enumerate(needed):
        line = text.strip()[:120]
        if None not in markers and not uncovered[n]:
            continue
        # "got wider" only when a removed marker of the family is one this added marker widens
        pair = next(((old, new) for new in uncovered[n] for old in unused[(path, new.family)]
                     if new.wider_than(old)), None)
        if pair:
            unused[(path, pair[1].family)].remove(pair[0])
            problems.append(f"{path}: a suppression or skip got wider ({pair[0]} \u2192 {pair[1]}) without a valid "
                            f"aidlc-exception: {line}")
        else:
            problems.append(f"{path}: a suppression or skip without a valid aidlc-exception (reason, owner and an "
                            f"expiry date not past): {line}")
    return problems + closer_problems(lines, source, today)


def file_source(repo: Path, branch: Branch) -> Source:
    """Reads a file at the merge base ('-') or at the head ('+'), once each."""
    cache: dict[tuple[str, str], list[str] | None] = {}

    def read(side: str, path: str) -> list[str] | None:
        if (side, path) not in cache:
            text = None
            if side == "+" and branch.worktree:
                file = repo / path
                if file.is_file():     # bytes: read_text would turn a lone "\r" into a line break git does not count
                    text = file.read_bytes().decode("utf-8", errors="replace")
            else:
                rev = branch.base if side == "-" else "HEAD"
                shown = subprocess.run(["git", "-C", str(repo), "show", f"{rev}:{path}"], capture_output=True)
                if shown.returncode == 0:
                    text = shown.stdout.decode("utf-8", errors="replace")
            cache[(side, path)] = None if text is None else git_lines(text)
        return cache[(side, path)]
    return read


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


def review(repo: Path, base: str, key: str, part: int | None = None, worktree: bool = False,
           today: dt.date | None = None) -> Review:
    key_folder = f"plans/{key}"
    branch = collect(repo, base, key_folder if part is None else f"{key_folder}/part-{part}", worktree)
    if all(path.startswith(key_folder + "/") for path in branch.changed):
        return Review([], [], [])     # a documents-only branch (spec, design or plan pull request, or a planning session)
    if part is None:     # CI and the hook pass no --part: the part is the one part folder the branch changes
        parts = sorted({m.group(1) for path in branch.changed
                        if (m := re.match(re.escape(key_folder) + r"/(part-\d+)/", path))})
        if len(parts) > 1:
            return Review([f"{key_folder}: this branch changes several parts; one part per branch "
                           f"({', '.join(parts)})"], [], [])
        if parts:
            branch.folder = f"{key_folder}/{parts[0]}"
    bundles = approved_bundles(branch)
    if not bundles:
        return Review([f"{branch.folder}: no bundle or brief found; there is nothing approved to check this branch "
                       f"against"], [], [], no_bundle=True)
    recipes = approved_recipes(bundles)
    exempt, recipe_notes = set(), []
    for patch in branch.patches:
        if not patch.trailer:
            continue
        if patch.trailer in recipes:
            exempt.add(patch.commit)
            recipe_notes.append(f"recipe commit {patch.commit[:12]} (Recipe: {patch.trailer}) is exempt from the "
                                f"assertion check; read its recipe check output")
        else:
            recipe_notes.append(f"commit {patch.commit[:12]} carries the trailer 'Recipe: {patch.trailer}', which no "
                                f"approved bundle's RECIPE names; it was checked as an ordinary commit")
    problems = scope_problems(branch.changed, key_folder, bundles) + manifest_problems(branch.changed, bundles)
    found, notes = test_problems(branch, bundles, exempt)
    problems += found
    problems += marker_problems(branch.net, today or dt.date.today(), file_source(repo, branch))
    problems += approval_problems(branch, key_folder)
    return Review(problems, notes, recipe_notes)


def check(repo: Path, base: str, key: str, part: int | None = None, worktree: bool = False,
          today: dt.date | None = None) -> tuple[list[str], list[str]]:
    """(problems, notes on amended assertions); `review` also gives the recipe notes."""
    result = review(repo, base, key, part, worktree, today)
    return result.problems, result.notes


def default_base(repo: Path) -> str:
    remote = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", check=False).strip()
    if remote:
        return remote
    return "main" if git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/main", check=False).strip() else "master"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--key")
    parser.add_argument("--part", type=int)
    parser.add_argument("--base")
    parser.add_argument("--branch")
    parser.add_argument("--root", default=".")
    parser.add_argument("--hook", action="store_true")
    args = parser.parse_args(argv)
    repo = Path(args.root).resolve()
    out = sys.stderr if args.hook else sys.stdout
    if args.hook:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}
        if payload.get("stop_hook_active"):
            return 0
    try:
        branch = args.branch or git(repo, "branch", "--show-current").strip()
        key = args.key or key_from_branch(branch)
        if not key:
            print(f"check_slice: the branch '{branch}' names no story key; nothing to check", file=out)
            return 0
        result = review(repo, args.base or default_base(repo), key, args.part, worktree=args.hook)
    except RuntimeError as error:
        print(f"check_slice: cannot check: {error}", file=sys.stderr)
        return 0 if args.hook else 1
    problems, notes = result.problems, result.notes + result.recipe_notes
    if args.hook and result.no_bundle:     # a planning, verify or review turn: nothing approved to check yet
        print(f"check_slice: note: {problems[0]}; not checked on this turn (CI fails it)", file=out)
        return 0
    for note in notes:
        print(f"for the reviewer: {note}", file=out)
    for problem in problems:
        print(problem, file=out)
    if problems:
        if args.hook:
            print("check_slice: if you are building this slice, fix these or stop it (STATUS stopped); "
                  "otherwise report them.", file=out)
        return 2 if args.hook else 1
    print(f"check_slice: {key}: scope, tests, manifests, markers and approved documents hold "
          f"({len(notes)} note(s) for the reviewer)", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
