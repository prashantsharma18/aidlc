#!/usr/bin/env python3
"""Checks the aidlc marketplace and every plugin it lists: each skill and agent in the open Agent Skills format, the
house sections of the stage and recipe skills, the practice sections of the practice skills,
no command of the parked harness and no tool-specific syntax (in a
skill or its files), every named file present, skill names unique across plugins, core never naming a pack, plugin
versions and dependencies, and the starter settings' secret denies.

    python3 scripts/validate.py [root]

Prints one line per problem and exits 1 when there is any. Standard library only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CORE = "aidlc"
SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Produces", "## Gate", "## Stop if",
            "## Common excuses", "## Red flags", "## Rules")
GATE_LINE = "You draft; you never approve."
# Stage, method and recipe skills keep the house sections.
HOUSE_PREFIXES = ("aidlc-", "modernize-", "dotnet-", "java-")
# A skill whose metadata says `kind: practice` keeps the practice sections. A skill without that kind keeps only the
# open format.
PRACTICE_SECTIONS = ("## When to use", "## Steps", "## Checks", "## Stop if", "## Common excuses", "## Red flags",
                     "## Rules")
KIND_PRACTICE = re.compile(r"^\s+kind:\s*['\"]?practice['\"]?\s*$", re.M)
# Practices still in their earlier shape, exempt from PRACTICE_SECTIONS until their content is rewritten.
# This list only shrinks.
EARLIER_PRACTICES = frozenset({"adding-observability", "building-user-interfaces", "debugging-failures",
                               "designing-apis", "migrating-safely", "reviewing-code", "securing-code",
                               "tuning-performance"})
# Commands and files of the harness parked under the tag harness-v1 (docs/archive/harness-v1.md).
REMOVED = re.compile(r"aidlc\s+(check|scope|ci|new|attempts|render|init-repo|doctor|trace|adopt|plugin\s+build)\b"
                     r"|approved-bundles\.txt|\.aidlc/(config|hooks|baseline)|core/(policy|schemas|hooks)\b"
                     r"|hook decision log|bin/aidlc\b")
# Syntax one tool understands and the others do not: skills must run unchanged in every tool.
TOOL_SPECIFIC = re.compile(r"/aidlc:[a-z]|\$ARGUMENTS\b|\$\{CLAUDE_[A-Z_]+\}")
# Allowing a whole tool at the workspace root opens every path it can reach, home folder included.
WHOLE_TOOLS = {"Read", "Edit", "Write", "Bash", "Grep", "Glob"}
# Files a skill names, relative to its folder: templates, reference pages and scripts.
SKILL_DIRS = ("assets", "references", "scripts")
NAMED_FILE = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9._-]+)`")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".txt", ".json", ".yml", ".yaml"}


def front_matter(text: str) -> dict[str, str] | None:
    """The top-level `key: value` lines between the opening `---` and the next one (values unquoted)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("'\"")
    return fields


def portability(rel: str, text: str) -> list[str]:
    problems = [f"{rel}: names a removed harness command or file: '{' '.join(m.group(0).split())}'"
                for m in REMOVED.finditer(text)]
    return problems + [f"{rel}: uses tool-specific syntax: '{m.group(0)}'" for m in TOOL_SPECIFIC.finditer(text)]


def check_sections(rel: str, text: str, sections: tuple[str, ...], gate_where: str) -> list[str]:
    """Every section present, in order, and the gate line somewhere in the skill."""
    positions = [text.find(s) for s in sections]
    problems = [f"{rel}: missing section '{s}'" for s, pos in zip(sections, positions) if pos < 0]
    found = [p for p in positions if p >= 0]
    if found != sorted(found):
        problems.append(f"{rel}: sections are out of order (expected {', '.join(sections)})")
    if GATE_LINE not in text:
        problems.append(f"{rel}: {gate_where} must end with '{GATE_LINE}'")
    return problems


def check_skill(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    folder_rel = path.parent.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = front_matter(text)
    if fm is None:
        return [f"{rel}: no front matter"]
    problems = []
    name, description = fm.get("name", ""), fm.get("description", "")
    folder = path.parent.name
    if name != folder:
        problems.append(f"{rel}: name '{name}' does not match its folder '{folder}'")
    if not NAME.fullmatch(name) or len(name) > 64:
        problems.append(f"{rel}: name must be lower-case words joined by hyphens, at most 64 characters")
    if not description or len(description) > 1024:
        problems.append(f"{rel}: description is missing or longer than 1024 characters")
    elif "Use when" not in description:
        problems.append(f"{rel}: description must say when to use the skill ('Use when ...')")
    if folder.startswith(HOUSE_PREFIXES):
        problems += check_sections(rel, text, SECTIONS, "the gate")
    elif KIND_PRACTICE.search(text[: text.find("\n---", 4)]) and folder not in EARLIER_PRACTICES:
        problems += check_sections(rel, text, PRACTICE_SECTIONS, "the Rules")
    problems += portability(rel, text)
    for sub in SKILL_DIRS:
        for extra in sorted((path.parent / sub).glob("*")):
            if extra.is_file() and extra.suffix in TEXT_SUFFIXES:
                problems += portability(f"{folder_rel}/{sub}/{extra.name}", extra.read_text(encoding="utf-8"))
    for named in sorted(set(NAMED_FILE.findall(text))):
        if not (path.parent / named).is_file():
            problems.append(f"{rel}: names `{named}`, which does not exist")
    return problems


def check_agent(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = front_matter(text)
    if fm is None:
        return [f"{rel}: no front matter"]
    problems = [f"{rel}: front matter needs '{k}'" if k == "name" else f"{rel}: front matter needs a description"
                for k in ("name", "description") if not fm.get(k)]
    if fm.get("name") and fm["name"] != path.stem:
        problems.append(f"{rel}: name '{fm['name']}' does not match the file name")
    return problems + portability(rel, text)


def load_plugins(root: Path) -> tuple[list[str], list[tuple[str, Path, dict]]]:
    """The marketplace's plugins as (name, folder, manifest), and every problem found in the manifests."""
    rel = ".claude-plugin/marketplace.json"
    try:
        market = json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{rel}: unreadable ({exc})"], []
    problems, plugins = [], []
    for entry in market.get("plugins", []):
        name, source = entry.get("name", ""), entry.get("source")
        if not isinstance(source, str) or not source.startswith("./plugins/") or ".." in source:
            problems.append(f"{rel}: plugin '{name}' must have a source under './plugins/' (got {source!r})")
            continue
        folder = root / source[2:].rstrip("/")
        mrel = f"{folder.relative_to(root).as_posix()}/.claude-plugin/plugin.json"
        try:
            manifest = json.loads((root / mrel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{mrel}: unreadable ({exc})")
            continue
        if manifest.get("name") != name:
            problems.append(f"{mrel}: name '{manifest.get('name')}' does not match the marketplace entry '{name}'")
        if not SEMVER.fullmatch(str(manifest.get("version", ""))):
            problems.append(f"{mrel}: needs a semantic version such as 1.0.0")
        plugins.append((name, folder, manifest))
    names = {n for n, _, _ in plugins}
    if CORE not in names:
        problems.append(f"{rel}: the core plugin '{CORE}' is missing")
    for name, folder, manifest in plugins:
        mrel = f"{folder.relative_to(root).as_posix()}/.claude-plugin/plugin.json"
        deps = manifest.get("dependencies", [])
        if name == CORE and deps:
            problems.append(f"{mrel}: core requires nothing; it never depends on a pack")
        for dep in deps:
            dep_name = dep if isinstance(dep, str) else dep.get("name", "")
            if dep_name.split("@")[0] not in names:
                problems.append(f"{mrel}: requires '{dep_name}', which the marketplace does not list")
    return problems, plugins


def check_core_names_no_pack(root: Path, core: Path, pack_names: set[str]) -> list[str]:
    """Core is written like a CI runner: it runs what approved files name, so its own text names no pack."""
    if not pack_names:
        return []
    alternatives = "|".join(sorted(map(re.escape, pack_names), key=len, reverse=True))
    pattern = re.compile(rf"(?<![A-Za-z0-9_-])({alternatives})(?![A-Za-z0-9_-])")
    problems = []
    for f in sorted(core.rglob("*")):
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            for m in pattern.finditer(f.read_text(encoding="utf-8")):
                problems.append(f"{f.relative_to(root).as_posix()}: names the pack '{m.group(1)}'; "
                                f"core never names a pack")
    return problems


def check_starters(root: Path) -> list[str]:
    """The workspace root reads with the same secret denies as a repository, and never allows a whole tool."""
    settings = {}
    for kind in ("repo", "workspace"):
        rel = f"starter/{kind}/.claude/settings.json"
        try:
            settings[kind] = json.loads((root / rel).read_text(encoding="utf-8")).get("permissions", {})
        except (OSError, ValueError) as exc:
            return [f"{rel}: unreadable ({exc})"]
    rel = "starter/workspace/.claude/settings.json"
    ws = settings["workspace"]
    problems = [f"{rel}: allows the whole '{rule}' tool; allow paths, never a tool"
                for rule in ws.get("allow", []) if rule in WHOLE_TOOLS]
    secrets = [r for r in settings["repo"].get("deny", []) if r.startswith("Read(")]
    problems += [f"{rel}: misses the repository starter's deny '{r}'" for r in secrets if r not in ws.get("deny", [])]
    return problems


def validate(root: Path) -> list[str]:
    problems, plugins = load_plugins(root)
    owner_of: dict[str, str] = {}
    pack_names: set[str] = set()
    core_folder = None
    for name, folder, _ in plugins:
        frel = folder.relative_to(root).as_posix()
        skills = sorted((folder / "skills").glob("*/SKILL.md"))
        agents = sorted((folder / "agents").glob("*.md"))
        if not skills:
            problems.append(f"{frel}/skills/: no skills found")
        if name == CORE:
            core_folder = folder
            if not agents:
                problems.append(f"{frel}/agents/: no agents found")
        else:
            pack_names.add(name)
        for path in skills:
            problems += check_skill(path, root)
            skill = path.parent.name
            if skill in owner_of:
                problems.append(f"{frel}/skills/{skill}: the name '{skill}' is also used by plugin "
                                f"'{owner_of[skill]}'; skill names must be unique across the marketplace")
            else:
                owner_of[skill] = name
            if name != CORE:
                pack_names.add(skill)
        for path in agents:
            problems += check_agent(path, root)
            if name != CORE:
                pack_names.add(path.stem)
    if core_folder is not None:
        problems += check_core_names_no_pack(root, core_folder, pack_names)
    return problems + check_starters(root)


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parents[1])
    problems = validate(root)
    for p in problems:
        print(p)
    plugins = load_plugins(root)[1]
    count = sum(len(list((folder / "skills").glob("*/SKILL.md"))) for _, folder, _ in plugins)
    print(f"validate: {len(plugins)} plugin(s), {count} skill(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
