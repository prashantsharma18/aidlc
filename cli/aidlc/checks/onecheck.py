"""The one-command check (guide 3 step 6, 8.8, 9.5): one command for engineers, agents and CI.

Command steps come from .aidlc/config.yaml (`commands` + `check_steps`), in that order. The
built-in integrity steps (BUILTINS) always run after them; a repository cannot remove them.
Every step runs even after a failure. The output is one line per step plus the tail of each
failing log, and the last line is a contract the retry counter parses:
    check  result PASS  (0 of N steps failed)
A step that cannot run is a failure (fail closed). Nothing is skipped silently."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

from ..hookbridge import hooks
from ..paths import safe_target
from ..repo import RepoConfig

CHECK_DIR = ".check"
RECORD = f"{CHECK_DIR}/result.json"
STEP_TIMEOUT_S = 1800
TAIL_LINES = 15
STEP_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
OK, FAIL, SKIPPED, NA = "ok", "FAIL", "SKIPPED", "n/a"


class CheckError(Exception):
    """The check cannot start at all (exit 2). Step problems are FAIL results instead."""


@dataclass
class StepResult:
    name: str
    status: str
    detail: str = ""
    log: str | None = None            # path relative to the repository
    tail: list[str] = field(default_factory=list)   # last log lines, read through the parent's fd


@dataclass
class CheckContext:
    repo: Path                        # where the steps run (the working copy, or a CI checkout)
    config: RepoConfig                # the configuration that judges the change
    branch: str | None
    base: str                         # the commit the change is compared with
    scope: list[str] | None           # MAY CHANGE patterns; None when no usable scope exists
    scope_mode: str = "require"       # "require", or "skip" (CHECK_SCOPE=skip, interactive only)
    scope_source: str = ""            # the scope file read (shown in the context line)
    head: str | None = None           # CI: judge git objects base..head instead of the working tree
    steering: dict[str, str] | None = None   # CI: the base's steering files, read before the change runs
    wrap: Callable[[str, str], list[str]] | None = None   # CI: argv that runs a command step (sandbox)
    today: date = field(default_factory=date.today)
    timeout_s: int = STEP_TIMEOUT_S
    started: float = 0.0              # set by run_check


@dataclass
class CheckResult:
    steps: list[StepResult]

    @property
    def failures(self) -> int:
        return sum(step.status == FAIL for step in self.steps)

    @property
    def passed(self) -> bool:
        return self.failures == 0

    def summary(self) -> str:
        verdict = "PASS" if self.passed else "FAIL"
        return f"result {verdict}  ({self.failures} of {len(self.steps)} steps failed)"

    def record(self, ctx: CheckContext, **extra) -> dict:
        return {"result": "PASS" if self.passed else "FAIL", "failures": self.failures,
                "total": len(self.steps), "steps": step_records(self.steps),
                "branch": ctx.branch, "base": ctx.base,
                "time": datetime.now(timezone.utc).isoformat(timespec="seconds"), **extra}


def step_records(steps: list[StepResult]) -> list[dict]:
    """Steps for a JSON record: log tails stay out of records."""
    return [{k: v for k, v in asdict(s).items() if k != "tail"} for s in steps]


def prepare_check_dir(repo: Path) -> Path:
    """.check/, ignoring itself. A .check, or a .check/.gitignore, that is a symlink is refused: a
    change could commit one pointing at any file, and this runs with the person's privileges."""
    try:
        check_dir = safe_target(repo, CHECK_DIR)
        check_dir.mkdir(exist_ok=True)
        ignore = safe_target(repo, f"{CHECK_DIR}/.gitignore")      # refuses a final symlink too
    except ValueError as exc:
        raise CheckError(str(exc)) from None
    fd = os.open(ignore, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write("*\n")                                       # .check never shows as a change
    return check_dir


def git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(["git", "-c", "core.quotePath=false", "-c", "core.hooksPath=/dev/null", *args],
                         cwd=repo, env=env,
                         capture_output=True, text=True, errors="replace", timeout=60)
    if out.returncode != 0:
        raise CheckError(f"git {' '.join(args)}: {out.stderr.strip()[:300]}")
    return out.stdout


def changed_paths(repo: Path, base: str, head: str | None = None) -> list[str]:
    """Files changed since `base`. With `head` (CI): between the two commits, from git objects only.
    Without: in the working copy, plus untracked files that are not ignored."""
    if head is not None:
        return sorted(p for p in git(repo, "diff", "--no-renames", "--name-only", "-z", base, head).split("\0") if p)
    tracked = git(repo, "diff", "--no-renames", "--name-only", "-z", base).split("\0")
    untracked = git(repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({p for p in (*tracked, *untracked) if p})


def local_context(repo: Path, config: RepoConfig) -> CheckContext:
    """A run in the working copy: the same scope and base the hooks use."""
    guard = hooks().guard
    branch = guard.current_branch(repo)
    read = guard._read_scope(repo) if branch else None
    scope, recorded = read if read else (None, None)
    base_ref = os.environ.get("AIDLC_BASE_REF") or recorded or config.harness.get("base_branch", "main")
    base = git(repo, "merge-base", base_ref, "HEAD").strip()
    skip = os.environ.get("CHECK_SCOPE") == "skip" and not guard._unattended()
    source = str(guard.scope_file(repo, branch)) if branch else "none"
    return CheckContext(repo=repo, config=config, branch=branch, base=base, scope=scope,
                        scope_mode="skip" if skip else "require", scope_source=source)


def context_line(ctx: CheckContext) -> str:
    """What this run judged against. The retry counter (Task 4) compares it with what the hooks
    compute, so an override (AIDLC_BASE_REF, AIDLC_SCOPE_FILE, CHECK_SCOPE, --repo elsewhere)
    can never produce a counter-resetting PASS."""
    return (f"check  context  repo={ctx.repo}  base={ctx.base}  scope={ctx.scope_source or 'none'}  "
            f"mode={ctx.scope_mode}")


def _kill_group(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    proc.wait()


def run_command(ctx: CheckContext, name: str, step: str | None = None) -> StepResult:
    """Run commands[name] in ctx.repo. Output goes to .check/<step>.log, stdin is closed, and the
    whole process group is killed at the timeout and after the command ends."""
    step = step or name
    if not STEP_NAME.fullmatch(step):
        return StepResult(step, FAIL, "step names are lower-case letters, digits and '-'")
    command = ctx.config.commands.get(name)
    if not isinstance(command, str) or not command.strip():
        return StepResult(step, FAIL, f"no command '{name}' in .aidlc/config.yaml commands")
    log_rel = f"{CHECK_DIR}/{step}.log"
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    argv = ctx.wrap(command, step) if ctx.wrap else command
    with safe_target(ctx.repo, log_rel).open("w+", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(argv, shell=ctx.wrap is None, cwd=ctx.repo, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=ctx.timeout_s)
        except subprocess.TimeoutExpired:
            code = None
        finally:
            _kill_group(proc)                     # also children that outlive the command
        size = log.seek(0, os.SEEK_END)          # the file this process opened, whatever the path now is
        log.seek(max(0, size - 65536))           # the tail only: test logs can be very large
        tail = log.read().splitlines()[-TAIL_LINES:]
    if code is None:
        return StepResult(step, FAIL, f"timed out after {ctx.timeout_s} s", log_rel, tail)
    if code != 0:
        return StepResult(step, FAIL, f"exit {code}", log_rel, tail)
    return StepResult(step, OK, "", log_rel)


def step_scope(ctx: CheckContext) -> StepResult:
    if ctx.scope_mode == "skip":
        return StepResult("scope", SKIPPED, "CHECK_SCOPE=skip; never set by the harness or CI")
    if ctx.scope is None:
        return StepResult("scope", FAIL, "no readable task scope for this branch; "
                          "run `aidlc scope --branch <branch>` after the bundle is approved")
    matches = hooks().guard.matches
    outside = [p for p in changed_paths(ctx.repo, ctx.base, ctx.head)
               if not matches(p, ctx.scope, any_depth_names=False)]
    if outside:
        shown = ", ".join(outside[:10]) + (" ..." if len(outside) > 10 else "")
        return StepResult("scope", FAIL, f"{len(outside)} file(s) outside the scope: {shown}")
    return StepResult("scope", OK)


def step_context_drift(ctx: CheckContext) -> StepResult:
    from .context_drift import check_context_drift   # imported here: it builds the CLI parser
    findings = check_context_drift(ctx.repo, ctx.today)
    fails = [str(f) for f in findings if f.level == "FAIL"]
    if fails:
        return StepResult("context-drift", FAIL, f"{len(fails)} finding(s): " + "; ".join(fails[:5]))
    warns = len(findings) - len(fails)
    return StepResult("context-drift", OK, f"{warns} warning(s)" if warns else "")


BUILTINS: list[tuple[str, Callable[[CheckContext], StepResult]]] = [
    ("scope", step_scope),
    ("context-drift", step_context_drift),
]


def _guarded(name: str, fn: Callable[[], StepResult]) -> StepResult:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - fail closed: a step that cannot run is a failure
        return StepResult(name, FAIL, f"could not run ({type(exc).__name__}: {exc})")


def run_check(ctx: CheckContext, builtins=None) -> CheckResult:
    """Run the command steps, then the built-in steps; every step runs."""
    prepare_check_dir(ctx.repo)
    ctx.started = time.time()
    steps = [_guarded(name, lambda n=name: run_command(ctx, n)) for name in ctx.config.check_steps]
    for name, fn in (BUILTINS if builtins is None else builtins):
        steps.append(_guarded(name, lambda f=fn: f(ctx)))
    return CheckResult(steps)


def print_result(result: CheckResult, repo: Path, prefix: str = "check") -> None:
    redact = hooks().guard._redact
    for step in result.steps:
        line = f"{prefix}  {step.name:<16}{step.status}"
        if step.detail:
            line += f"  {redact(step.detail)}"
        if step.status == FAIL and step.log:
            line += f"  (full log: {step.log})"
        print(line)
        for tail in step.tail:                    # captured at run time, never re-read from a path
            print(f"        | {redact(tail)}")
    print(f"{prefix}  {result.summary()}")


def write_record(repo: Path, record: dict) -> Path:
    path = safe_target(repo, RECORD)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return path
