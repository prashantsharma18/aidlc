#!/usr/bin/env python3
"""Checks a story branch against its approved task bundles, mechanically, so the rules hold whoever wrote the code
(aidlc ADR 0019). It reports: a changed path outside every bundle's MAY CHANGE, or inside a MUST NOT; an existing test
or assertion removed or changed and not restored later on the branch, outside AMENDED ASSERTIONS and approved recipe
commits; a dependency manifest that MAY CHANGE does not name; a suppression or skip in the branch's net result without
a valid `aidlc-exception: reason=...; owner=...; expires=YYYY-MM-DD`; and a Tier 2 or 3 plan or bundle added or
changed in a code pull request (ADR 0020).

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
            lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
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
    return Branch(changed, patches, at_base, base_docs, head_docs, net, folder)


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


def marker_of(text: str) -> str | None:
    """The suppression or skip a line carries, spaces dropped ("#type:ignore"), or None."""
    m = SUPPRESS.search(text) or SKIP.search(text)
    return re.sub(r"\s+", "", m.group(0)) if m else None


def marker_problems(patch: str, today: dt.date) -> list[str]:
    """Judged on the net diff. A `+` marker line is not a new suppression when the same file loses a `-` line with
    the same marker (an edited or moved suppressed line); a marker beyond those removed still needs its exception."""
    removed = collections.Counter((path, marker_of(text)) for path, kind, text in hunks(patch)
                                  if kind == "-" and marker_of(text))
    problems, previous = [], ""
    for path, kind, text in hunks(patch):
        if kind == "@":
            previous = ""
            continue
        marker = marker_of(text)
        if kind == "+" and not path.endswith(PROSE_SUFFIXES) and marker:
            if valid_exception(text, today) or valid_exception(previous, today):
                pass
            elif removed[(path, marker)] > 0:
                removed[(path, marker)] -= 1
            else:
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
    problems += marker_problems(branch.net, today or dt.date.today())
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
