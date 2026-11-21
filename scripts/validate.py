#!/usr/bin/env python3
"""Checks the aidlc plugin at the repository root and its marketplace entry: each skill and agent in the open Agent Skills format, the
house sections of the stage and recipe skills, the practice sections of the practice skills, the workflow sections
and names of the workflow skills,
no command of the parked harness and no tool-specific syntax (in a
skill or its files), every named file present, the plugin's version, and the starter settings' secret denies.

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
# Stage skills keep the house sections.
HOUSE_PREFIXES = ("aidlc-",)
# A skill whose metadata says `kind: practice` keeps the practice sections. A skill without that kind keeps only the
# open format.
PRACTICE_SECTIONS = ("## When to use", "## Steps", "## Checks", "## Stop if", "## Common excuses", "## Red flags",
                     "## Rules")
KIND_PRACTICE = re.compile(r"^[ \t]+kind:[ \t]*['\"]?practice['\"]?[ \t]*(#.*)?$", re.M)
# A skill whose metadata says `kind: workflow` says how work runs across sessions (ADR 0025). It produces no document of
# its own and has no gate of its own, so it keeps the workflow sections. Its name tells it apart too: never `aidlc-`,
# which marks a stage, and never an "-ing" word, which marks a practice.
WORKFLOW_SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Stop if", "## Common excuses", "## Red flags",
                     "## Rules")
KIND_WORKFLOW = re.compile(r"^[ \t]+kind:[ \t]*['\"]?workflow['\"]?[ \t]*(#.*)?$", re.M)
ING_WORD = re.compile(r"^[a-z]{3,}ing(-|$)")
ING_NOUNS = frozenset({"string", "spring"})  # first words that end in "ing" but are nouns, not doing words
# The eight earlier practices keep their own structure, so PRACTICE_SECTIONS does not apply to them.
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
# A stage skill keeps every gate in SKILL.md; its references/ hold only the steps of one case, and SKILL.md names each
# one with the condition to read it (docs/design/2026-11-21-shorter-stage-skills.md).
GATE_SECTIONS = ("## Gate", "## Stop if", "## Common excuses", "## Red flags", "## Rules")


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


def check_references(folder: Path, folder_rel: str, text: str) -> list[str]:
    """A stage skill's reference holds no gate section, and the skill's SKILL.md names it."""
    problems = []
    for ref in sorted((folder / "references").glob("*")):
        if not ref.is_file():
            continue
        rel = f"{folder_rel}/references/{ref.name}"
        if f"`references/{ref.name}`" not in text:
            problems.append(f"{rel}: SKILL.md does not name it; name it with the condition to read it")
        if ref.suffix in TEXT_SUFFIXES:
            body = ref.read_text(encoding="utf-8")
            problems += [f"{rel}: holds '{h}'; a reference never holds a gate, which stays in SKILL.md"
                         for h in GATE_SECTIONS if re.search(rf"(?m)^{re.escape(h)}[ \t]*$", body)]
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
    head = text[: text.find("\n---", 4)]
    if KIND_WORKFLOW.search(head):
        if folder.startswith(HOUSE_PREFIXES):
            problems.append(f"{rel}: a workflow name never starts with 'aidlc-', which marks a stage")
        if ING_WORD.match(folder) and folder.split("-")[0] not in ING_NOUNS:
            problems.append(f"{rel}: a workflow name never starts with an '-ing' word, which marks a practice")
        problems += check_sections(rel, text, WORKFLOW_SECTIONS, "the Rules")
    elif folder.startswith(HOUSE_PREFIXES):
        problems += check_sections(rel, text, SECTIONS, "the gate")
        problems += check_references(path.parent, folder_rel, text)
    elif KIND_PRACTICE.search(head) and folder not in EARLIER_PRACTICES:
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


def load_plugin(root: Path) -> tuple[list[str], dict | None]:
    """The one plugin, at the repository root: its manifest, and every problem found in the two manifests."""
    rel = ".claude-plugin/marketplace.json"
    try:
        market = json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{rel}: unreadable ({exc})"], None
    problems = []
    entries = market.get("plugins", [])
    if [e.get("name") for e in entries] != [CORE]:
        problems.append(f"{rel}: lists {[e.get('name') for e in entries]}; it lists one plugin, '{CORE}'")
    for entry in entries:
        if entry.get("source") != "./":
            problems.append(f"{rel}: plugin '{entry.get('name')}' must have the source './' "
                            f"(got {entry.get('source')!r}); the repository root is the plugin")
    mrel = ".claude-plugin/plugin.json"
    try:
        manifest = json.loads((root / mrel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return problems + [f"{mrel}: unreadable ({exc})"], None
    if manifest.get("name") != CORE:
        problems.append(f"{mrel}: name '{manifest.get('name')}' must be '{CORE}'")
    if not SEMVER.fullmatch(str(manifest.get("version", ""))):
        problems.append(f"{mrel}: needs a semantic version such as 1.0.0")
    if manifest.get("dependencies"):
        problems.append(f"{mrel}: requires nothing")
    return problems, manifest


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
    problems, _ = load_plugin(root)
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    agents = sorted((root / "agents").glob("*.md"))
    if not skills:
        problems.append("skills/: no skills found")
    if not agents:
        problems.append("agents/: no agents found")
    for path in skills:
        problems += check_skill(path, root)
    for path in agents:
        problems += check_agent(path, root)
    return problems + check_starters(root)


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parents[1])
    problems = validate(root)
    for p in problems:
        print(p)
    count = len(list((root / "skills").glob("*/SKILL.md")))
    print(f"validate: 1 plugin, {count} skill(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
