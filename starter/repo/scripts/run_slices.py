#!/usr/bin/env python3
"""Runs approved delegate slices one after another, each in a fresh headless agent session, and stops at the first
slice that does not end done. The person names the slices, in order, once their bundles are approved; the person
reviews the diffs at the end and pushes. The runner never pushes. Standard library only; copied into a repository from
aidlc's starter/repo/scripts/.

    python3 scripts/run_slices.py <KEY> <slice> [<slice> ...] [--part <n>] [--command "<agent command>"]
                                  [--prompt "<prompt with {key}, {slice} and {part}>"]

A slice named `fix` reads plans/<KEY>/fix.md, `brief` reads plans/<KEY>/brief.md, any other reads
plans/<KEY>/bundle-<slice>.md (plans/<KEY>/part-<n>/ with --part). Each must say MODE delegate (Tier 1) or delegate
with checkpoints (Tiers 1 and 2); a hands-on slice is built with a person. After each session the slice's progress
note must read STATUS done, the session must exit 0 and the tree must be clean; anything else ends the run. A paused
slice runs again only after the person adds "- <pause> confirmed by <name>, <date>" to its progress note. The
default command denies `git push` to the session, whatever the repository's settings say.
Exit codes: 0 every slice done; 1 a slice did not end done; 2 the run could not start."""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable

DEFAULT_COMMAND = 'claude --disallowedTools "Bash(git push*)" -p --permission-mode acceptEdits'
DEFAULT_PROMPT = "/aidlc:aidlc-build {key} {slice}"
HIGHEST_TIER = {"delegate": 1, "delegate with checkpoints": 2}
BRIEFS = {"fix": "fix.md", "brief": "brief.md"}

Invoke = Callable[[list, Path], int]


def field(text: str, name: str) -> str | None:
    """The value of the line that starts with NAME, without its note in parentheses; None when absent or a
    placeholder."""
    match = re.search(rf"^\**{re.escape(name)}\**:?[ \t]+(.+)$", text, re.M)
    if not match:
        return None
    value = re.split(r"[ \t]{2,}\(", match.group(1), maxsplit=1)[0].strip().strip("`*").strip()
    return None if not value or value.startswith(("<", "{{")) else value


def tier(text: str) -> int | None:
    value = field(text, "TIER")
    match = re.match(r"(\d)\b", value or "")
    return int(match.group(1)) if match else None


def document(plans: Path, name: str) -> Path:
    return plans / BRIEFS.get(name, f"bundle-{name}.md")


def status(note: Path) -> str:
    if not note.is_file():
        return "missing"
    return field(note.read_text(encoding="utf-8"), "STATUS") or "missing"


def pause_confirmed(note: Path, state: str) -> bool:
    """A paused note may run again only when the person recorded "- <pause> confirmed by <name>, <date>"; a
    placeholder (<name> or {{name}}) is not a confirmation."""
    pause = state.split(":", 1)[1].strip()
    line = rf"^-[ \t]+{re.escape(pause)}[ \t]+confirmed by[ \t]+[^<{{\s]"
    return bool(re.search(line, note.read_text(encoding="utf-8"), re.M))


def preflight(plans: Path, slices: list[str]) -> list[str]:
    problems = []
    if len(set(slices)) != len(slices):
        problems.append("a slice is named twice")
    for name in slices:
        path = document(plans, name)
        if not path.is_file():
            problems.append(f"{name}: {path} not found")
            continue
        text = path.read_text(encoding="utf-8")
        mode, level = field(text, "MODE"), tier(text)
        if mode is None:
            problems.append(f"{name}: no MODE: it runs hands-on, with a person, not by this runner")
        elif mode == "hands-on":
            problems.append(f"{name}: MODE hands-on: build it with a person, not by this runner")
        elif mode not in HIGHEST_TIER:
            problems.append(f"{name}: MODE '{mode}' is not a mode")
        elif level is None:
            problems.append(f"{name}: no TIER")
        elif level > HIGHEST_TIER[mode]:
            problems.append(f"{name}: MODE {mode} is not allowed at Tier {level}")
        if name in BRIEFS and field(text, "CONFIRMED") is None:
            problems.append(f"{name}: the brief is not confirmed")
        note = plans / f"progress-{name}.md"
        state = status(note)
        if state == "done":
            problems.append(f"{name}: already done; leave it out")
        elif state.startswith("paused:") and not pause_confirmed(note, state):
            problems.append(f"{name}: {state} is not confirmed: the person adds "
                            f"'- {state.split(':', 1)[1].strip()} confirmed by <name>, <date>' to the progress note")
    return problems


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True).stdout.strip()


def default_branch(root: Path) -> str:
    remote = git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if remote:
        return remote.split("/", 1)[-1]
    return "main" if git(root, "rev-parse", "--verify", "--quiet", "refs/heads/main") else "master"


def tree_problems(root: Path, key: str) -> list[str]:
    inside = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=root, capture_output=True, text=True)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return [f"{root} is not a git repository"]
    problems = []
    if git(root, "status", "--porcelain"):
        problems.append("the working tree has uncommitted changes")
    branch = git(root, "branch", "--show-current")
    if not branch:
        problems.append("HEAD is detached: switch to the story's branch")
    elif branch == default_branch(root):
        problems.append(f"on the default branch ({branch}): switch to the story's branch")
    elif key not in branch:
        problems.append(f"the branch {branch} does not name {key}: switch to the story's branch")
    return problems


def run(root: Path, key: str, slices: list[str], invoke: Invoke, command: list[str], prompt: str,
        part: int | None = None, out: Callable[[str], None] = print) -> int:
    plans = root / "plans" / key if part is None else root / "plans" / key / f"part-{part}"
    if part is not None and "{part}" not in prompt:
        prompt += " part {part}"
    problems = preflight(plans, slices) + tree_problems(root, key)
    try:
        prompt.format(key=key, slice="x", part=part or "")
    except (KeyError, IndexError, ValueError) as error:
        problems.append(f"--prompt: only {{key}}, {{slice}} and {{part}} can be filled ({error})")
    if problems:
        for problem in problems:
            out(f"cannot start: {problem}")
        return 2
    start = git(root, "rev-parse", "HEAD")
    for name in slices:
        out(f"{name}: running in a fresh session")
        try:
            code = invoke(command + [prompt.format(key=key, slice=name, part=part or "")], root)
        except OSError as error:
            out(f"cannot start: the agent command could not start ({error}); check --command")
            return 2
        state = status(plans / f"progress-{name}.md")
        out(f"{name}: {state}")
        why = None
        if code != 0:
            why = f"the session exited with {code}"
        elif state != "done":
            why = f"STATUS is {state}"
        elif git(root, "status", "--porcelain"):
            why = "the session left uncommitted changes"
        if why:
            out(f"stopped at {name}: {why}. Review: git diff {start[:12]}..HEAD and the progress note.")
            return 1
    out(f"every slice done. Review the diffs (git diff {start[:12]}..HEAD), then push and open the pull request.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run approved delegate slices, one fresh session each.")
    parser.add_argument("key")
    parser.add_argument("slices", nargs="+")
    parser.add_argument("--part", type=int)
    parser.add_argument("--root", default=".")
    parser.add_argument("--command", default=DEFAULT_COMMAND)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    args = parser.parse_args(argv)

    def invoke(command: list, cwd: Path) -> int:
        return subprocess.run(command, cwd=cwd).returncode

    return run(Path(args.root).resolve(), args.key, args.slices, invoke, shlex.split(args.command), args.prompt,
               args.part)


if __name__ == "__main__":
    sys.exit(main())
