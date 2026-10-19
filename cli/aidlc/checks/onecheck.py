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
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..hookbridge import hooks
from ..paths import safe_target
from ..repo import RepoConfig
from .test_reports import NOTRUN, ReportError, parse_report

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
    trusted: Path | None = None       # CI: the base checkout; trusted data (the policy data) comes from it
    rerun: Any = None                 # CI: the protected re-run's own checkout, built before the change runs
    wrap: Callable[[str, str], list[str]] | None = None   # CI: argv that runs a command step (sandbox)
    today: date = field(default_factory=date.today)
    timeout_s: int = STEP_TIMEOUT_S
    started: float = 0.0              # set by run_check
    reports_before: dict = field(default_factory=dict)   # report files before the command steps ran


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
                "branch": ctx.branch, "base": ctx.base, "run": uuid.uuid4().hex,
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
        fd = os.open(ignore, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("*\n")                                   # .check never shows as a change
    except (ValueError, OSError) as exc:
        raise CheckError(f"cannot prepare {CHECK_DIR}/: {exc}") from None
    return check_dir


def git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(["git", "-c", "core.quotePath=false", "-c", "core.hooksPath=/dev/null", *args],
                         cwd=repo, env=env,
                         capture_output=True, timeout=60)
    if out.returncode != 0:
        raise CheckError(f"git {' '.join(args)}: {out.stderr.decode('utf-8', 'replace').strip()[:300]}")
    return out.stdout.decode("utf-8", "replace")      # bytes decoded here: \r and \f must survive


def changed_paths(repo: Path, base: str, head: str | None = None) -> list[str]:
    """Files changed since `base`. With `head` (CI): between the two commits, from git objects only.
    Without: in the working copy, plus untracked files that are not ignored."""
    if head is not None:
        return sorted(p for p in git(repo, "diff", *DIFF_FLAGS, "--name-only", "-z", base, head).split("\0") if p)
    tracked = git(repo, "diff", *DIFF_FLAGS, "--name-only", "-z", base).split("\0")
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


def run_command(ctx: CheckContext, name: str, step: str | None = None, cwd: Path | None = None) -> StepResult:
    """Run commands[name] in ctx.repo (or cwd: CI's protected re-run has its own checkout). Output goes to
    ctx.repo's .check/<step>.log, stdin is closed, and the whole process group is killed at the timeout
    and after the command ends."""
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
        proc = subprocess.Popen(argv, shell=ctx.wrap is None, cwd=cwd or ctx.repo, env=env, stdin=subprocess.DEVNULL,
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


EXCEPTIONS = "test/protected-exceptions.txt"
ALLOWED_SKIPS = "test/allowed-skips.txt"
STEERING = (EXCEPTIONS, ALLOWED_SKIPS)          # files that steer the checks: never judged as tests
MAX_SCAN_BYTES = 1_000_000


# Content always shown, labels fixed, and the real bytes: a branch's .gitattributes picks the diff driver,
# so a textconv or external diff would let the change decide what the judges read.
DIFF_FLAGS = ("--no-renames", "--text", "--no-textconv", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/")


def _span(base: str, head: str | None) -> list[str]:
    return [base] if head is None else [base, head]


def added_lines_by_file(patch: str) -> dict[str, list[str]]:
    """Added lines per file in a unified diff (one or more patches). The file name comes from the
    `+++` header of each `diff --git` section; a `+++ ` line counts as a header only before the
    section's first hunk, so content can never pose as a header."""
    out: dict[str, list[str]] = {}
    current, in_hunk = None, False
    for line in patch.split("\n"):                       # only \n separates diff lines, never \f, \r, U+2028...
        if line.startswith(("diff --git ", "diff --cc ", "diff --combined ")):
            current, in_hunk = None, False
        elif not in_hunk:
            if line.startswith("+++ "):
                name = line[4:].rstrip("\t")                # git appends a TAB to names with spaces
                current = name[2:] if name.startswith("b/") else (None if name == "/dev/null" else name)
            elif line.startswith("@@"):
                in_hunk = True
        elif line.startswith("+") and current is not None:
            out.setdefault(current, []).append(line[1:])
    return out


def _excepted(repo: Path, base: str, head: str | None) -> set[str]:
    """Files excused by lines THIS change adds to the exceptions file (guide 9.5)."""
    patch = git(repo, "diff", *DIFF_FLAGS, "-U0", *_span(base, head), "--", EXCEPTIONS)
    out = set()
    for line in added_lines_by_file(patch).get(EXCEPTIONS, []):
        parts = line.split()
        if len(parts) >= 3 and (parts[1].startswith("spec:") or parts[1] == "test-quality"):
            out.add(parts[0])
    return out


def protected_test_changes(repo: Path, base: str, head: str | None = None) -> tuple[list[str], list[str]]:
    """(problems, changed existing test files). An existing test file may only gain lines."""
    test_file = hooks().post_check.TEST_FILE_RE
    excepted = _excepted(repo, base, head)
    fields = [f for f in git(repo, "diff", *DIFF_FLAGS, "--name-status", "-z",
                             "--diff-filter=DMT", *_span(base, head)).split("\0") if f]
    problems, changed = [], []
    for code, path in zip(fields[::2], fields[1::2]):
        if path in STEERING or not test_file.search(path) or path in excepted:
            continue
        if code == "D":
            problems.append(f"deleted or renamed: {path}")
            continue
        if code == "T":
            problems.append(f"deleted or replaced: {path} is no longer a regular file")
            continue
        numstat = git(repo, "diff", *DIFF_FLAGS, "--numstat", *_span(base, head), "--", f":(literal){path}").split()
        removed = numstat[1] if len(numstat) >= 2 else "?"
        if removed == "-":
            problems.append(f"binary test file changed: {path}")
        elif removed != "0":
            problems.append(f"{removed} existing line(s) changed or removed: {path}")
        changed.append(path)
    return problems, changed


def step_protected_tests(ctx: CheckContext) -> StepResult:
    problems, changed = protected_test_changes(ctx.repo, ctx.base, ctx.head)
    if problems:
        return StepResult("protected-tests", FAIL, "; ".join(problems[:10]) +
                          f". Restore them, or record an approved exception in {EXCEPTIONS}")
    return StepResult("protected-tests", OK, f"{len(changed)} existing test file(s) extended" if changed else "")


def step_secrets(ctx: CheckContext) -> StepResult:
    """Credential-shaped text in added lines (CI: in every commit of base..head) or untracked
    files. Names files only, never the text."""
    secret = hooks().guard.BLOCK_SECRET_RE
    if ctx.head is not None:
        patch = git(ctx.repo, "log", "-p", "--cc", *DIFF_FLAGS, "--format=", "-U0", f"{ctx.base}..{ctx.head}")
    else:
        patch = git(ctx.repo, "diff", *DIFF_FLAGS, "-U0", ctx.base)
    hits = {path for path, lines in added_lines_by_file(patch).items() if any(secret.search(l) for l in lines)}
    unscannable: list[str] = []
    untracked = [] if ctx.head is not None else \
        git(ctx.repo, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    for rel in filter(None, untracked):
        path = ctx.repo / rel
        if path.is_symlink() or not path.is_file():
            continue
        if path.stat().st_size > MAX_SCAN_BYTES:
            unscannable.append(rel)
            continue
        data = path.read_bytes()
        if b"\0" in data:
            continue                                   # binary: not text a credential hides in
        if secret.search(data.decode("utf-8", errors="replace")):
            hits.add(rel)
    problems = [f"credential-shaped text in {rel}" for rel in sorted(hits)]
    problems += [f"{rel} is too large to scan (> 1 MB); gitignore it or commit it in its own change"
                 for rel in unscannable]
    if problems:
        return StepResult("secrets", FAIL, "; ".join(problems[:10]) +
                          (". Remove it and rotate the credential" if hits else ""))
    return StepResult("secrets", OK)


def _inside(path: Path, root: Path) -> Path | None:
    """The resolved path of a matched report file, or None when it is itself a symlink (a change could
    retarget one at a stale file) or not a file inside the checkout (reached through a symlinked
    directory that leads outside)."""
    try:
        if path.is_symlink():
            return None
        real = path.resolve()
        return real if real.is_file() and real.is_relative_to(root) else None
    except OSError:
        return None


def _report_snapshot(ctx: CheckContext) -> dict[str, tuple[int, int, int]]:
    """(mtime_ns, size, inode) of every existing report file, taken before the command steps run."""
    snap = {}
    root = ctx.repo.resolve()
    for pattern in ctx.config.test_reports:
        for path in ctx.repo.glob(pattern):
            real = _inside(path, root)
            if real is not None:
                st = os.stat(real)
                snap[str(real)] = (st.st_mtime_ns, st.st_size, st.st_ino)
    return snap


def _allowed_skips(ctx: CheckContext) -> set[str]:
    """Declared skips. CI: the base branch's text (ctx.steering); locally: the working copy's file."""
    if ctx.steering is not None:
        text = ctx.steering.get(ALLOWED_SKIPS, "")
    else:
        path = ctx.repo / ALLOWED_SKIPS
        text = path.read_text(encoding="utf-8") if path.is_file() and not path.is_symlink() else ""
    out = set()
    for line in text.splitlines():
        if line.lstrip().startswith("#") or " # " not in line:
            continue
        name, reason = line.split(" # ", 1)
        if name.strip() and reason.strip():
            out.add(name.strip())
    return out


def _fresh_reports(ctx: CheckContext) -> list[Path]:
    """Reports this run wrote: new files, or files whose snapshot changed. A previous run's file
    never counts, however recent."""
    found: list[Path] = []
    root = ctx.repo.resolve()
    for pattern in ctx.config.test_reports:
        for path in sorted(ctx.repo.glob(pattern)):
            real = _inside(path, root)
            if real is None or real in found:
                continue
            st = os.stat(real)
            if ctx.reports_before.get(str(real)) != (st.st_mtime_ns, st.st_size, st.st_ino):
                found.append(real)
    return found


def step_skips(ctx: CheckContext) -> StepResult:
    if "test" not in ctx.config.check_steps:
        return StepResult("skips", NA, "no test step in check_steps")
    if not ctx.config.test_reports:
        return StepResult("skips", FAIL, "test_reports is empty in .aidlc/config.yaml: say where the "
                          "test step writes its report, so skipped tests are visible")
    reports = _fresh_reports(ctx)
    if not reports:
        return StepResult("skips", FAIL, "no test report written by this run (looked for: "
                          + ", ".join(ctx.config.test_reports) + "): did the tests run?")
    try:
        results = [entry for path in reports for entry in parse_report(path)]
    except ReportError as exc:
        return StepResult("skips", FAIL, str(exc))
    if not results:
        return StepResult("skips", FAIL, "the test report lists no tests")
    allowed = _allowed_skips(ctx)
    not_run = [name for name, status in results if status == NOTRUN]
    unexpected = [name for name in not_run if name not in allowed]
    detail = f"{len(results)} tests, {len(not_run)} not run, {len(unexpected)} unexpected"
    if unexpected:
        return StepResult("skips", FAIL, detail + ": " + "; ".join(unexpected[:5]) +
                          f". A test that cannot run must fail; declared skips go in {ALLOWED_SKIPS}")
    return StepResult("skips", OK, detail)


BUILTINS: list[tuple[str, Callable[[CheckContext], StepResult]]] = [
    ("scope", step_scope),
    ("protected-tests", step_protected_tests),
    ("skips", step_skips),
    ("context-drift", step_context_drift),
    ("secrets", step_secrets),
]


def _guarded(name: str, fn: Callable[[], StepResult]) -> StepResult:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - fail closed: a step that cannot run is a failure
        return StepResult(name, FAIL, f"could not run ({type(exc).__name__}: {exc})")


def begin_command_steps(ctx: CheckContext) -> None:
    """The moment before the command steps run: .check/ exists, the clock starts, and the report
    files already present are recorded, so a previous run's report never counts as fresh.
    `aidlc check` and `aidlc ci` both call it, so they keep one contract."""
    prepare_check_dir(ctx.repo)
    ctx.started = time.time()
    ctx.reports_before = _report_snapshot(ctx) if "test" in ctx.config.check_steps else {}


def run_check(ctx: CheckContext, builtins=None) -> CheckResult:
    """Run the command steps, then the built-in steps; every step runs."""
    begin_command_steps(ctx)
    steps = [_guarded(name, lambda n=name: run_command(ctx, n)) for name in ctx.config.check_steps]
    for name, fn in (BUILTINS if builtins is None else builtins):
        steps.append(_guarded(name, lambda f=fn: f(ctx)))
    return CheckResult(steps)


CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")   # C0 and C1 controls except tab and newline


def print_result(result: CheckResult, repo: Path, prefix: str = "check") -> None:
    """One line per step. Details and log tails are redacted, then stripped of control characters, so
    a log cannot hide or rewrite lines on the terminal (escape sequences)."""
    guard_redact = hooks().guard._redact

    def redact(text: str) -> str:
        return CONTROL_RE.sub("", guard_redact(text))
    for step in result.steps:
        label = f"{step.name:<16}" if len(step.name) < 16 else f"{step.name} "
        line = f"{prefix}  {label}{step.status}"
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
