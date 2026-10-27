#!/usr/bin/env python3
"""Checks that the packs AGENTS.md declares under "## Packs used here" are really installed, and that the settings
switch on no pack from aidlc's marketplace that AGENTS.md leaves out. It reads Claude Code's shared and local
settings and Copilot's `.github/copilot/settings.json`. Run it in CI and at the start of work.

    python3 scripts/check_packs.py [repository]

A pack line names the plugin and its skills in full, in backticks; the first skill is where that kind of work starts:
    - `aidlc-modernize`: `aidlc-modernize:modernize-assess`, `aidlc-modernize:dotnet-modernize`
A repository that uses no pack writes the single line "- none". Prints one line per problem and exits 1 when there is
any. Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEADING = "## Packs used here"
CORE = "aidlc"
MARKETPLACE = "aidlc"
# Where each tool switches plugins on, lowest precedence first: Claude Code's shared and local settings; Copilot's.
TOOL_SETTINGS = ((".claude/settings.json", ".claude/settings.local.json"), (".github/copilot/settings.json",))
# Folders where Copilot, Codex, Claude Code and Cursor read copied skills.
COPY_DIRS = (".github/skills", ".agents/skills", ".claude/skills", ".cursor/skills")
TOKEN = re.compile(r"`([^`]+)`")


def parse(agents_md: str) -> tuple[dict[str, list[str]], list[str]]:
    """{plugin: [skill, ...]} from the section, and every line that could not be read."""
    lines = agents_md.splitlines()
    if HEADING not in lines:
        return {}, [f"AGENTS.md: no '{HEADING}' section (write '- none' when the repository uses no pack)"]
    packs: dict[str, list[str]] = {}
    problems, entries = [], 0
    for line in lines[lines.index(HEADING) + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("- "):
            continue
        entries += 1
        if line.strip() == "- none":
            continue
        tokens = TOKEN.findall(line)
        if not tokens:
            problems.append(f"AGENTS.md: cannot read the pack line {line.strip()!r}; "
                            f"name the plugin and its skills in backticks")
            continue
        plugin, skills = tokens[0], tokens[1:]
        for s in skills:
            if not s.startswith(plugin + ":"):
                problems.append(f"AGENTS.md: skill `{s}` is not written as `{plugin}:<skill>`")
        packs[plugin] = [s.split(":", 1)[1] for s in skills if s.startswith(plugin + ":")]
    if entries == 0:
        problems.append(f"AGENTS.md: the '{HEADING}' section is empty (write '- none' when the repository uses no pack)")
    return packs, problems


def enabled_in(repo: Path, rel: str) -> tuple[dict | None, str | None]:
    """The file's enabledPlugins, None when the file does not exist, or a problem when it cannot be read."""
    path = repo / rel
    if not path.exists():
        return None, None
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("enabledPlugins", {}), None
    except (OSError, ValueError) as exc:
        return None, f"{rel}: unreadable ({exc})"


def check_config(packs: dict[str, list[str]], layers: list[tuple[str, dict]]) -> list[str]:
    """One tool's settings, lowest precedence first: every declared pack on, and no undeclared aidlc pack on."""
    merged: dict[str, object] = {}
    source: dict[str, str] = {}
    for rel, enabled in layers:
        for key, value in enabled.items():
            merged[key], source[key] = value, rel
    # aidlc's own marketplace, plus any other marketplace core is installed from.
    markets = {MARKETPLACE} | {k.partition("@")[2] for k in merged if k.partition("@")[0] == CORE}
    problems = []
    for plugin in packs:
        if not any(k.partition("@")[0] == plugin and v is True for k, v in merged.items()):
            problems.append(f"{layers[0][0]}: AGENTS.md declares `{plugin}`, but enabledPlugins does not switch it on")
    for key, value in merged.items():
        name, _, market = key.partition("@")
        if value is True and market in markets and name != CORE and name not in packs:
            problems.append(f"{source[key]}: switches on `{name}`, which AGENTS.md does not declare under '{HEADING}'")
    return problems


def check(repo: Path) -> list[str]:
    try:
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    except OSError as exc:
        return [f"AGENTS.md: unreadable ({exc})"]
    packs, problems = parse(text)
    configs = []
    for tool in TOOL_SETTINGS:
        layers = []
        for rel in tool:
            enabled, problem = enabled_in(repo, rel)
            if problem:
                return problems + [problem]
            if enabled is not None:
                layers.append((rel, enabled))
        if layers:
            configs.append(layers)
    copies = [repo / d for d in COPY_DIRS if (repo / d / "aidlc-start" / "SKILL.md").is_file()]
    if packs and not configs and not copies:
        problems.append("no aidlc install found: no settings that switch plugins on and no copied skills folder")
    for layers in configs:
        problems += check_config(packs, layers)
    for copy in copies:
        for plugin, skills in packs.items():
            for s in skills:
                if not (copy / s / "SKILL.md").is_file():
                    problems.append(f"{copy.relative_to(repo).as_posix()}/: AGENTS.md declares `{plugin}:{s}`, "
                                    f"but the folder `{s}` is missing")
    return problems


def main(argv: list[str]) -> int:
    repo = Path(argv[1] if len(argv) > 1 else ".")
    problems = check(repo)
    for p in problems:
        print(p)
    if not problems:
        packs = parse((repo / "AGENTS.md").read_text(encoding="utf-8"))[0]
        print(f"check_packs: {len(packs)} pack(s), {sum(map(len, packs.values()))} skill(s) declared; all installed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
