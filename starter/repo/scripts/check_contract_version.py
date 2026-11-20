#!/usr/bin/env python3
"""The provider's contract check (aidlc ADR 0022; change list F9, decision D9). The provider owns the OpenAPI file
that its AGENTS.md names, and publishes each version as the git tag api-v<info.version>, only from the default
branch.

    python3 scripts/check_contract_version.py --contract openapi.yaml [--oasdiff PATH] [--root DIR]
    python3 scripts/check_contract_version.py --contract openapi.yaml --publish-tag [--root DIR]

On a pull request it compares the contract with the last published version (the highest api-v* tag in the clone):
a changed contract must raise info.version, and a breaking change (oasdiff breaking --fail-on ERR) must raise its
MAJOR, with the consumers' agreement recorded in the pull request, which a person checks. oasdiff runs with external
$refs refused, because a pull request is untrusted. --publish-tag prints the tag to create for the contract on this
commit, or nothing when that version is already published. The contract must be one file: relative $refs to other
files are not followed (--allow-external-refs=false). It needs full history and tags (fetch-depth: 0). Exit 0 clean,
1 problems. Standard library only; oasdiff
is a release binary that the workflow downloads at a pinned version and checks against its sha256."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

NUMBER = r"(0|[1-9][0-9]*)"
SEMVER = re.compile(rf"^{NUMBER}\.{NUMBER}\.{NUMBER}\Z")
TAG = re.compile(rf"^api-v({NUMBER}\.{NUMBER}\.{NUMBER})\Z")
Semver = tuple[int, int, int]


def info_version(text: str) -> str | None:
    """info.version of an OpenAPI document in JSON, or in YAML written in block style; None when it has none."""
    if text.lstrip().startswith("{"):
        try:
            value = json.loads(text).get("info", {}).get("version")
        except (ValueError, AttributeError):
            return None
        return None if value is None else str(value)
    inside, indent = False, None
    for line in text.splitlines():
        if re.match(r"^info:\s*(#.*)?$", line):
            inside = True
            continue
        if not inside or not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[:1].isspace():
            break
        depth = len(line) - len(line.lstrip())
        indent = depth if indent is None else indent
        m = re.match(r"^\s+version:\s*(['\"]?)([^'\"#\s]+)\1\s*(#.*)?$", line)
        if m and depth == indent:
            return m.group(2)
    return None


def semver(value: str | None) -> Semver | None:
    m = SEMVER.match(value or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def show(version: Semver) -> str:
    return ".".join(map(str, version))


def git(root: Path, *args: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def published(root: Path) -> list[tuple[Semver, str]]:
    """Every api-v<MAJOR.MINOR.PATCH> tag in the clone, lowest version first."""
    found = []
    for tag in (git(root, "tag", "--list", "api-v*") or "").split():
        m = TAG.match(tag)
        if m:
            found.append((semver(m.group(1)), tag))
    return sorted(found)


def no_history_problem(root: Path) -> str | None:
    """A problem when the clone cannot tell us whether any api-v* tag exists: shallow, or git failed."""
    if (git(root, "rev-parse", "--is-shallow-repository") or "").strip() == "false":
        return None
    return ("cannot tell whether a contract version was published: fetch the full history and tags "
            "(fetch-depth: 0 with tags) before this check")


def run_oasdiff(oasdiff: str, base: str, revision: str, suffix: str) -> tuple[int, str]:
    """oasdiff's exit code and output for `breaking --fail-on ERR` between two contract texts: 0 no breaking change,
    1 a breaking change, anything else a failure to compare. External $refs are refused."""
    with tempfile.TemporaryDirectory() as tmp:
        old, new = Path(tmp) / f"base{suffix}", Path(tmp) / f"revision{suffix}"
        old.write_text(base, encoding="utf-8")
        new.write_text(revision, encoding="utf-8")
        try:
            result = subprocess.run([oasdiff, "breaking", "--fail-on", "ERR", "--allow-external-refs=false",
                                     str(old), str(new)], capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired) as error:
            return 127, f"cannot run {oasdiff}: {error}"
    return result.returncode, (result.stdout + result.stderr).strip()


def version_problem(contract: str, found: str | None) -> str:
    if found is None:
        return f"info.version not found in {contract} (only block-style YAML or JSON is read)"
    return f"{contract}: info.version must be MAJOR.MINOR.PATCH, not {found!r}"


def check(root: Path, contract: str, oasdiff: str = "oasdiff") -> tuple[list[str], list[str]]:
    """(problems, notes) for the contract in the working tree against its last published version."""
    path = root / contract
    tags = published(root)
    if not path.is_file():
        if tags:
            return [f"the published contract {contract} is missing; deleting a published contract is a breaking "
                    f"change"], []
        return [], [f"no contract at {contract}; nothing to check"]
    head = path.read_text(encoding="utf-8")
    found = info_version(head)
    version = semver(found)
    if version is None:
        return [version_problem(contract, found)], []
    if not tags:
        missing = no_history_problem(root)
        if missing:
            return [missing], []
        return [], [f"no api-v* tag yet: {contract} {show(version)} becomes the first published version"]
    last, tag = tags[-1]
    base = git(root, "show", f"{tag}:{contract}")
    if base is None:
        return [f"{tag} has no {contract}: when the contract moves, name its new path in AGENTS.md and in each "
                f"consumer's SOURCE"], []
    if base == head:
        return [], [f"{contract} is unchanged since {tag}"]
    problems, notes = [], []
    if version <= last:
        problems.append(f"{contract} changed since {tag}, but info.version {show(version)} is not above "
                        f"{show(last)}: raise it")
    code, output = run_oasdiff(oasdiff, base, head, path.suffix)
    if code == 0:
        notes.append(f"no breaking change since {tag}")
    elif code == 1 and version[0] > last[0]:
        notes.append(f"a breaking change since {tag}, with MAJOR raised to {version[0]}: the pull request records "
                     f"each consumer's agreement (a person checks it)")
    elif code == 1:
        problems.append(f"a breaking change since {tag} without a new MAJOR version: make it additive, or raise "
                        f"MAJOR with the consumers' agreement (expand and contract)")
    else:
        problems.append(f"oasdiff could not compare the contracts (exit {code})")
        notes.append("install the pinned oasdiff release (checked against its sha256) or pass --oasdiff <path>")
    if output:
        notes.append(output[:4000])
    return problems, notes


def publish_tag(root: Path, contract: str) -> tuple[str | None, list[str]]:
    """(the tag to create on this commit, problems): no tag when there is no contract or its version is published."""
    path = root / contract
    if not path.is_file():
        return None, []
    head = path.read_text(encoding="utf-8")
    version = semver(info_version(head))
    if version is None:
        return None, [version_problem(contract, info_version(head))]
    tag, tags = f"api-v{show(version)}", published(root)
    if not tags and no_history_problem(root):
        return None, [no_history_problem(root)]
    if any(name == tag for _, name in tags):
        if git(root, "show", f"{tag}:{contract}") != head:
            return None, [f"{contract} differs from the published {tag} without a new info.version: a published "
                          f"version never changes"]
        return None, []
    if tags and version <= tags[-1][0]:
        return None, [f"{contract} {show(version)} is not above the published {tags[-1][1]}"]
    return tag, []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contract", required=True)
    parser.add_argument("--oasdiff", default="oasdiff")
    parser.add_argument("--publish-tag", action="store_true")
    parser.add_argument("--root", default=".")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.publish_tag:
        tag, problems = publish_tag(root, args.contract)
        for problem in problems:
            print(problem, file=sys.stderr)
        if tag:
            print(tag)
        return 1 if problems else 0
    problems, notes = check(root, args.contract, args.oasdiff)
    for note in notes:
        print(note)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"check_contract_version: {args.contract}: versioned and compatible with its last published tag")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
