#!/usr/bin/env python3
"""Checks the aidlc skills package: every skill and agent in the open Agent Skills format, the house sections of the
stage skills, no command of the parked harness, every named asset present, and the Claude Code plugin manifest.

    python3 scripts/validate.py [root]

Prints one line per problem and exits 1 when there is any. Standard library only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Produces", "## Gate", "## Stop if",
            "## Common excuses", "## Red flags", "## Rules")
GATE_LINE = "You draft; you never approve."
# Commands and files of the harness parked under the tag harness-v1 (docs/archive/harness-v1.md).
REMOVED = re.compile(r"aidlc (check|scope|ci|new|attempts|render|init-repo|doctor|trace|adopt|plugin build)\b"
                     r"|approved-bundles\.txt|\.aidlc/(config|hooks|baseline)")
ASSET = re.compile(r"`assets/([A-Za-z0-9._-]+)`")


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


def check_skill(path: Path) -> list[str]:
    rel = path.relative_to(path.parents[2]).as_posix()
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
    if folder.startswith("aidlc-"):
        positions = [text.find(s) for s in SECTIONS]
        for section, pos in zip(SECTIONS, positions):
            if pos < 0:
                problems.append(f"{rel}: missing section '{section}'")
        found = [p for p in positions if p >= 0]
        if found != sorted(found):
            problems.append(f"{rel}: sections are out of order (expected {', '.join(SECTIONS)})")
        if GATE_LINE not in text:
            problems.append(f"{rel}: the gate must end with '{GATE_LINE}'")
    for m in REMOVED.finditer(text):
        problems.append(f"{rel}: names a removed harness command or file: '{m.group(0)}'")
    for asset in sorted(set(ASSET.findall(text))):
        if not (path.parent / "assets" / asset).is_file():
            problems.append(f"{rel}: names `assets/{asset}`, which does not exist")
    return problems


def check_agent(path: Path) -> list[str]:
    rel = f"agents/{path.name}"
    fm = front_matter(path.read_text(encoding="utf-8"))
    if fm is None:
        return [f"{rel}: no front matter"]
    problems = [f"{rel}: front matter needs '{k}'" if k == "name" else f"{rel}: front matter needs a description"
                for k in ("name", "description") if not fm.get(k)]
    if fm.get("name") and fm["name"] != path.stem:
        problems.append(f"{rel}: name '{fm['name']}' does not match the file name")
    text = path.read_text(encoding="utf-8")
    problems += [f"{rel}: names a removed harness command or file: '{m.group(0)}'" for m in REMOVED.finditer(text)]
    return problems


def check_plugin(root: Path) -> list[str]:
    problems = []
    try:
        plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f".claude-plugin: unreadable manifest ({exc})"]
    if plugin.get("name") != "aidlc":
        problems.append(".claude-plugin/plugin.json: the plugin must be named 'aidlc'")
    sources = [p.get("source") for p in market.get("plugins", []) if p.get("name") == "aidlc"]
    if sources != ["./"]:
        problems.append(".claude-plugin/marketplace.json: the 'aidlc' plugin's source must be './' (the repository root)")
    return problems


def validate(root: Path) -> list[str]:
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    problems = [] if skills else ["skills/: no skills found"]
    for path in skills:
        problems += check_skill(path)
    for path in sorted((root / "agents").glob("*.md")):
        problems += check_agent(path)
    return problems + check_plugin(root)


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parents[1])
    problems = validate(root)
    for p in problems:
        print(p)
    count = len(list((root / "skills").glob("*/SKILL.md")))
    print(f"validate: {count} skill(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
