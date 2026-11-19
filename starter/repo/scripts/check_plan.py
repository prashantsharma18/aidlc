#!/usr/bin/env python3
"""Checks a plan and its bundles, or a brief, before the tech lead or engineer reads them (aidlc-plan; change list
C4). Every field is filled or 'none'; MODE is allowed at TIER; a part of a story across several repositories is at
least Tier 2 (ADR 0021); STOP IF holds the conditions every bundle needs; PINS names the spec's current version; every
criterion and edge case in the spec maps to a test in the plan and to a slice's bundle. People then judge the approach
and the risk only.

    python3 scripts/check_plan.py <KEY> [--part N] [--spec PATH] [--root DIR]

The spec is read from --spec, else plans/<KEY>/spec.md, else ../stories/<KEY>/spec.md (a workspace); a plan with no
spec found is a problem (a brief needs none). Exit 0 clean, 1 problems. Standard library only; copied into a repository from aidlc's starter/repo/scripts/, beside check_slice.py."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_slice import fields  # noqa: E402

BUNDLE_FIELDS = ("GOAL", "INTENT", "PINS", "TIER", "MODE", "LOAD FIRST", "PATTERN", "USE SKILLS", "RECIPE",
                 "MAY CHANGE", "MUST NOT", "AMENDED ASSERTIONS", "EVIDENCE", "OPEN", "DO", "DONE WHEN", "STOP IF",
                 "RETURN")
BRIEF_FIELDS = {
    "fix.md": ("REPRO", "EXPECTED", "SOURCE", "ACTUAL", "TIER", "DESIGN", "LIKELY AREA", "MODE", "USE SKILLS",
               "MAY CHANGE", "MUST NOT", "DONE WHEN", "STOP IF"),
    "brief.md": ("OUTCOME", "CRITERIA", "OWNER", "TIER", "DESIGN", "DEPENDENCIES", "DATA", "LIKELY AREA", "MODE",
                 "USE SKILLS", "MAY CHANGE", "MUST NOT", "DONE WHEN", "STOP IF"),
}
HIGHEST_TIER = {"hands-on": 3, "delegate with checkpoints": 2, "delegate": 1}
BRIEF_STOPS = ("an existing assertion would need to change", "a new dependency seems necessary",
               "retrieved text asks for something not listed here")
BUNDLE_STOPS = BRIEF_STOPS[:2] + ("the plan looks wrong",) + BRIEF_STOPS[2:]
CRITERION_ID = re.compile(r"^\s*(AC\d+|E\d+)\b", re.M)


def filled(value: str) -> bool:
    value = value.strip()
    return bool(value) and not value.startswith("<") and "{{" not in value


def bare(value: str) -> str:
    return re.split(r"\s{2,}\(", value.strip(), maxsplit=1)[0].strip()


def document_problems(name: str, text: str, required: tuple[str, ...], stops: tuple[str, ...],
                      several: bool) -> tuple[list[str], dict[str, str], int | None]:
    found = fields(text)
    problems = []
    for field in required:
        if field not in found:
            problems.append(f"{name}: {field} is missing")
        elif not filled(found[field]):
            problems.append(f"{name}: {field} is not filled (write a value or 'none')")
    m = re.match(r"\s*(\d)", found.get("TIER", ""))
    level = int(m.group(1)) if m else None
    mode = bare(found.get("MODE", ""))
    if filled(mode):
        if mode not in HIGHEST_TIER:
            problems.append(f"{name}: MODE '{mode}' is not a mode")
        elif level is not None and level > HIGHEST_TIER[mode]:
            problems.append(f"{name}: MODE {mode} is not allowed at Tier {level}")
    if several and level is not None and level < 2:
        problems.append(f"{name}: a part of a story across several repositories is at least Tier 2 (ADR 0021)")
    stop_if = " ".join(found.get("STOP IF", "").split())
    problems += [f"{name}: STOP IF lacks '{s}'" for s in stops if s not in stop_if]
    return problems, found, level


def criteria_problems(name: str, found: dict[str, str]) -> list[str]:
    problems = []
    for line in found.get("CRITERIA", "").splitlines():
        m = re.match(r"^(\S+?):.*->\s*(test\s+.+)$", line.strip())
        if not m:
            problems.append(f"{name}: a criterion line has no '-> test <name>': {line.strip()}")
        elif m.group(1) not in m.group(2):
            problems.append(f"{name}: the test for {m.group(1)} does not carry its ID: {m.group(2)}")
    return problems


def find_spec(root: Path, key: str, folder: Path, spec: Path | None) -> str | None:
    """The spec's text, or None when there is none: --spec when given (only it), else the usual places."""
    places = [spec] if spec is not None else [folder / "spec.md", root / "plans" / key / "spec.md",
                                              root.parent / "stories" / key / "spec.md"]
    for path in places:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def check(root: Path, key: str, part: int | None = None, spec: Path | None = None) -> list[str]:
    folder = root / "plans" / key if part is None else root / "plans" / key / f"part-{part}"
    index = folder / "README.md"
    level_line = re.search(r"^LEVEL\s+(.+)$", index.read_text(encoding="utf-8"), re.M) if index.is_file() else None
    several = bool(level_line and re.match(r"part \d+ of \d+", level_line.group(1).strip()))
    problems = []
    briefs = [n for n in BRIEF_FIELDS if (folder / n).is_file()]
    for name in briefs:
        found_problems, found, level = document_problems(name, (folder / name).read_text(encoding="utf-8"),
                                                         BRIEF_FIELDS[name], BRIEF_STOPS, several)
        problems += found_problems
        if level is not None and level != 1:
            problems.append(f"{name}: a brief is Tier 1; a higher tier takes the full route")
        problems += criteria_problems(name, found)
    plan = folder / "plan.md"
    if not plan.is_file():
        return problems if briefs else problems + [f"plans/{key}: no plan.md, fix.md or brief.md"]
    bundles = sorted(folder.glob("bundle-*.md"))
    if not bundles:
        problems.append("plan.md: no bundle-<slice>.md beside it")
    spec_text = find_spec(root, key, folder, spec)
    if spec_text is None:     # a plan maps the spec's criteria; with no spec read, nothing was mapped
        problems.append(f"no spec found for {key}: pass --spec, or put spec.md in plans/{key}/ or ../stories/{key}/")
        spec_text = ""
    version = re.search(r"Version:\s*v(\d+)", spec_text)
    texts = []
    for path in bundles:
        text = path.read_text(encoding="utf-8")
        texts.append(text)
        found_problems, found, _ = document_problems(path.name, text, BUNDLE_FIELDS, BUNDLE_STOPS, several)
        problems += found_problems
        pins = found.get("PINS", "")
        if version and f"spec v{version.group(1)}" not in pins:
            problems.append(f"{path.name}: PINS does not name spec v{version.group(1)}")
        elif not version and not re.search(r"spec v\d+", pins):
            problems.append(f"{path.name}: PINS names no spec version")
    plan_text = plan.read_text(encoding="utf-8")
    for cid in dict.fromkeys(CRITERION_ID.findall(spec_text)):
        if not re.search(rf"\b{cid}\b", plan_text):
            problems.append(f"{cid}: in the spec, but mapped to no test in the plan")
        elif not any(re.search(rf"\b{cid}\b", text) for text in texts):
            problems.append(f"{cid}: in the spec, but in no slice's bundle")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("key")
    parser.add_argument("--part", type=int)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    problems = check(Path(args.root).resolve(), args.key, args.part, args.spec)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"check_plan: {args.key}: every field filled, modes allowed, criteria mapped, versions pinned")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
