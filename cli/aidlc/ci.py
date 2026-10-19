"""aidlc ci: the local trusted-CI runner (design §8; guide 9.5-9.7, 11.8).

The change's own code (install script, tests) was written by an agent, so the order is the
security property:
1. prepare: detached worktrees of the base and the head; read every piece of evidence (trusted
   configuration, approvals, merge approvals, a private copy of the steering files); every judge
   is already imported;
2. judge, before any of the change's code runs, from git objects and the untouched checkout;
3. run the change's own commands in the bubblewrap sandbox, then the checks that read their
   output (skips, the protected re-run). From here on no git command runs in the checkout: the
   change's code could have planted git configuration or attributes there;
4. verdict and a self-hashed record labelled simulated-ci.
The GitHub Actions workflow (core/ci/github/aidlc-verify.yml) runs the same code on two checkouts."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from . import __version__
from .checks.onecheck import (DIFF_FLAGS, FAIL, OK, STEERING, CheckContext, CheckResult, StepResult, _excepted,
                              begin_command_steps, git, print_result, run_command, step_context_drift,
                              step_protected_tests, step_records, step_scope, step_secrets, step_skips)
from .cliinfo import recorded_base
from .harness import BRANCH_RE
from .harness import base_branch as configured_base
from .hookbridge import hooks
from .paths import safe_target
from .repo import load_config
from .sandbox import Sandbox, available, toolchain_env, toolchain_paths
from .scope import ScopeError, base_commit, bundle_at, parse_approvals, parse_may_change

LABEL = "simulated-ci"
RECORDS = ".aidlc/ci-records"
APPROVALS = "plans/approved-bundles.txt"
MERGES = "plans/approved-merges.txt"
GROUPS = ("compile", "check", "scans")
SANDBOX_MODES = ("require", "auto")
INSTALL_STEPS = ("install", "restore")
COMPILE_STEPS = {"install", "restore", "build", "compile"}
SCAN_STEPS = {"secrets", "config-policy"}
SHA40 = re.compile(r"[0-9a-f]{40}")
NO_BASE = "the trusted record has no base branch for this repository; a person must run aidlc render"
NO_SANDBOX = ("bubblewrap cannot start a sandbox here (sudo apt install bubblewrap); "
              "aidlc ci never runs the change's code unsandboxed in local mode")


class CiError(Exception):
    """aidlc ci cannot start (exit 2)."""


@dataclass
class CiPlan:
    repo: Path              # where the history lives (the repository, or the PR checkout on GitHub)
    branch: str             # the task branch: approvals are keyed on it
    head: str               # the commit under test
    trusted: Path           # checkout of the base commit
    work: Path              # disposable checkout of the head: the change's code runs here
    base_branch: str
    base: str               # the base commit
    records: Path           # where the record is written
    sandbox: str = "require"   # "require" or "auto" (GitHub mode, --group scans only)


def group_of(step: str) -> str:
    if step in COMPILE_STEPS:
        return "compile"
    if step in SCAN_STEPS:
        return "scans"
    return "check"


RESTORE_MODES = {"100644": 0o644, "100755": 0o755}      # regular files only; never a link or a submodule


def rerun_plan(repo: Path, base: str, head: str) -> tuple[dict[str, tuple[str, bytes]], list[str]]:
    """What the protected re-run needs, read from git objects before any of the change's code runs:
    the base (mode, bytes) of every test file the change modified, retyped or deleted, and the test
    files it added. The same test patterns as protected_test_changes; steering files and approved
    exceptions keep the change's version."""
    test_file = hooks().post_check.TEST_FILE_RE
    excepted = _excepted(repo, base, head)
    fields = [f for f in git(repo, "diff", *DIFF_FLAGS, "--name-status", "-z", base, head).split("\0") if f]
    restore: dict[str, tuple[str, bytes]] = {}
    remove: list[str] = []
    for code, rel in zip(fields[::2], fields[1::2]):
        if rel in STEERING or not test_file.search(rel):
            continue
        if code == "A":
            remove.append(rel)
            continue
        if rel in excepted:
            continue
        entry = git(repo, "ls-tree", "-z", base, "--", f":(literal){rel}").split("\0")[0]   # "<mode> <type> <oid>\t<path>"
        meta, _, listed = entry.partition("\t")
        meta = meta.split()
        if len(meta) != 3 or listed != rel:
            raise CiError(f"cannot read the mode of {rel} at {base[:12]}")
        mode, kind = meta[0], meta[1]
        restore[rel] = (mode, _blob(repo, base, rel) if kind == "blob" else b"")
    return restore, sorted(remove)


def _open_slot(repo: Path, rel: str, create_parents: bool) -> Path | None:
    """The path for rel with nothing at it, after the change's code ran. Every parent is checked with
    safe_target (a symlinked component is refused); a file, link or FIFO at rel is unlinked, never
    followed; a directory there is refused. None: a parent is missing and create_parents is False."""
    parts = Path(rel).parts
    for i in range(1, len(parts)):
        parent = safe_target(repo, str(Path(*parts[:i])))
        if not os.path.lexists(parent):
            if not create_parents:
                return None
            parent.mkdir()
        elif not parent.is_dir():
            raise ValueError(f"{rel}: '{Path(*parts[:i])}' is not a directory")
    target = repo.resolve() / rel
    if os.path.lexists(target):
        if stat.S_ISDIR(os.lstat(target).st_mode):
            raise ValueError(f"{rel} is a directory where a test file belongs")
        target.unlink()
    return target


def step_protected_rerun(ctx: CheckContext) -> StepResult:
    """Guide 9.5 rule 3: the base test suite must pass on the new code. The change's tests may only
    add lines, but an added line (or an added test file that monkeypatches the code) can still hide a
    regression, so the re-run restores the base version of every test file the change touched,
    removes the test files it added, and runs the base suite. Everything was read from git objects
    before the change's code ran (ctx.rerun_base, ctx.rerun_remove); now the checkout is untrusted,
    so files are written and removed with plain file calls, never with git. It rewrites files, so it
    runs last, sandboxed like every test run."""
    restore, remove = ctx.rerun_base, ctx.rerun_remove
    if not restore and not remove:
        return StepResult("protected-rerun", OK, "no existing test file changed")
    if "test" not in ctx.config.commands:
        return StepResult("protected-rerun", FAIL, "no test command to re-run the base suite with")
    bad = [f"{rel} (mode {mode})" for rel, (mode, _) in sorted(restore.items()) if mode not in RESTORE_MODES]
    if bad:
        return StepResult("protected-rerun", FAIL, "cannot restore the base version of " + ", ".join(bad[:5]) +
                          ": only regular files (100644, 100755) can be restored")
    try:
        for rel, (mode, data) in sorted(restore.items()):
            target = _open_slot(ctx.repo, rel, create_parents=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, RESTORE_MODES[mode])
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), RESTORE_MODES[mode])     # exact mode, whatever the umask
                handle.write(data)
        for rel in remove:
            _open_slot(ctx.repo, rel, create_parents=False)
    except (ValueError, OSError) as exc:
        return StepResult("protected-rerun", FAIL, f"cannot set up the base suite: {exc}")
    problems = _drop_bytecode(ctx.repo)                       # stale caches must not shadow the tests
    if problems:
        return StepResult("protected-rerun", FAIL, "cannot clear the bytecode caches: " + "; ".join(problems[:3]))
    for name in ctx.config.check_steps:                       # rebuild: `dotnet test --no-build` would
        if group_of(name) == "compile" and name not in INSTALL_STEPS:   # re-run the change's binaries
            built = run_command(ctx, name, step=f"protected-rerun-{name}")
            if built.status == FAIL:
                built.name, built.detail = "protected-rerun", f"rebuilding with the base tests failed ({built.detail})"
                return built
    result = run_command(ctx, "test", step="protected-rerun")
    if result.status == FAIL:
        touched = [f"restored {rel}" for rel in sorted(restore)] + [f"removed {rel}" for rel in remove]
        result.detail = (f"the base test suite fails on this change ({result.detail}; {', '.join(touched[:5])}"
                         f"{' ...' if len(touched) > 5 else ''}): a changed or added test hid a regression")
    return result


# Judges: run before any of the change's code, from git objects (ctx.head) or the untouched checkout.
JUDGE_STEPS: list[tuple[str, Callable[[CheckContext], StepResult]]] = [
    ("scope", step_scope),
    ("protected-tests", step_protected_tests),
    ("secrets", step_secrets),
    ("context-drift", step_context_drift),
]
# After the change's commands: checks that read their output. The re-run rewrites files: last.
AFTER_STEPS: list[tuple[str, Callable[[CheckContext], StepResult]]] = [
    ("skips", step_skips),
    ("protected-rerun", step_protected_rerun),
]


def _git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _quiet(repo: Path, *args: str) -> None:
    """A git call whose failure must not mask the original error (cleanup only)."""
    try:
        subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *args], cwd=repo, capture_output=True,
                       timeout=60, env=_git_env())
    except (OSError, subprocess.SubprocessError):
        pass


def _remove_tree(path: Path) -> None:
    """Delete a directory the change's code may have written into, never following symlinks. A
    directory it made unreadable or unwritable is opened up first (its code has stopped by now)."""
    if not os.path.lexists(path):
        return
    shutil.rmtree(path, ignore_errors=True)
    if not os.path.lexists(path):
        return
    pending = [str(path)]
    while pending:
        current = pending.pop()
        try:
            if not stat.S_ISDIR(os.lstat(current).st_mode):
                continue
            os.chmod(current, 0o700)
            with os.scandir(current) as entries:
                pending.extend(e.path for e in entries if e.is_dir(follow_symlinks=False))
        except OSError:
            continue
    shutil.rmtree(path, ignore_errors=True)


@contextmanager
def checkouts(repo: Path, base: str, head: str) -> Iterator[tuple[Path, Path]]:
    """Detached worktrees of the base and the head in a private temporary directory, always removed.
    The directories are deleted first, by Python; git then only drops its record of each one, so no
    git command reads the checkout after the change's code ran (and other worktrees are untouched)."""
    tmp = Path(tempfile.mkdtemp(prefix="aidlc-ci-"))
    added: list[Path] = []
    try:
        for name, ref in (("trusted", base), ("head", head)):
            path = tmp / name
            added.append(path)                    # registered even if `add` fails half-way
            git(repo, "worktree", "add", "--detach", str(path), ref)
        yield added[0], added[1]
    finally:
        for path in reversed(added):
            _remove_tree(path)
            _quiet(repo, "worktree", "remove", "--force", str(path))
        _remove_tree(tmp)


def _selected(name: str, group: str | None, command: bool) -> bool:
    if group is None:
        return True
    if command and group == "check":
        return True                                   # build steps are prerequisites of the tests
    return group_of(name) == group


def _run_phases(ctx: CheckContext, group: str | None) -> CheckResult:
    """Judge first, then the change's own commands (sandboxed), then what reads their output."""
    steps: list[StepResult] = []

    def guarded(name: str, fn: Callable[[], StepResult]) -> None:
        try:
            steps.append(fn())
        except Exception as exc:  # noqa: BLE001 - fail closed: a step that cannot run is a failure
            steps.append(StepResult(name, FAIL, f"could not run ({type(exc).__name__}: {exc})"))

    for name, fn in JUDGE_STEPS:
        if _selected(name, group, command=False):
            guarded(name, lambda f=fn: f(ctx))
    if group == "scans":                              # the scans job never runs the change's code
        return CheckResult(steps)
    # Last moment before the change's code runs: everything that needs git in the checkout.
    if group != "compile":
        ctx.rerun_base, ctx.rerun_remove = rerun_plan(ctx.repo, ctx.base, ctx.head)
    begin_command_steps(ctx)                          # .check/, the clock, the report snapshot
    install = [n for n in INSTALL_STEPS if n in ctx.config.commands][:1]
    commands = install + [n for n in ctx.config.check_steps if n not in install]
    commands = [n for n in commands if n in install or _selected(n, group, command=True)]
    for name in commands:
        guarded(name, lambda n=name: run_command(ctx, n))
    if group != "compile":
        for name, fn in AFTER_STEPS:
            guarded(name, lambda f=fn: f(ctx))
    return CheckResult(steps)


def _drop_bytecode(work: Path) -> list[str]:
    """Remove __pycache__ directories in the checkout (never following symlinks). Returns the
    problems: a directory the walk cannot read could hold a stale cache, so the caller fails."""
    problems: list[str] = []

    def failed(exc: OSError) -> None:
        where = Path(exc.filename).relative_to(work) if exc.filename and Path(exc.filename).is_relative_to(work) \
            else exc.filename
        problems.append(f"{where}: {exc.strerror or exc}")

    for root, dirs, _files in os.walk(work, onerror=failed):
        dirs[:] = [d for d in dirs if d != ".git"]
        for d in list(dirs):
            path = Path(root) / d
            if d == "__pycache__":
                try:
                    if path.is_symlink():
                        path.unlink()
                    else:
                        shutil.rmtree(path)
                except OSError as exc:
                    failed(exc)
                dirs.remove(d)
    return problems


def _blob(repo: Path, commit: str, rel: str) -> bytes:
    """A file's bytes at a commit, from git objects (never the working tree, never a textconv)."""
    try:
        out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "cat-file", "blob", f"{commit}:{rel}"],
                             cwd=repo, env=_git_env(), capture_output=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CiError(f"cannot read {rel} at {commit[:12]}: {exc}") from None
    if out.returncode != 0:
        raise CiError(f"cannot read {rel} at {commit[:12]}: {out.stderr.decode(errors='replace').strip()[:200]}")
    return out.stdout


def _read_trusted(path: Path) -> str:
    """A file of the base checkout, or "" when it is absent. A symlink or a non-file is refused."""
    if not os.path.lexists(path):
        return ""
    if path.is_symlink() or not path.is_file():
        raise CiError(f"{path} in the base checkout is not a regular file; refusing to read it")
    return path.read_text(encoding="utf-8")


def _steering(trusted: Path) -> dict[str, str]:
    """The base's steering files, read into memory before any of the change's code runs."""
    out = {}
    for rel in STEERING:
        source = trusted / rel
        if source.is_file() and not source.is_symlink():
            out[rel] = source.read_text(encoding="utf-8")
    return out


def _merge_ready(merges: str, plan: CiPlan, result: CheckResult, group: str | None) -> tuple[bool, str]:
    if group is not None:
        return False, f"partial run (--group {group})"
    if not result.passed:
        return False, "gates failed"
    for line in merges.split("\n"):                   # "\n" only, as every approvals parser here
        parts = line.split()
        if len(parts) >= 3 and not line.startswith("#") and parts[0] == plan.branch and parts[1] == plan.head:
            return True, f"approved by {parts[2]}"
    return False, f"no approval record for {plan.branch} at {plan.head[:12]} in {plan.base_branch}:{MERGES}"


def _seal(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def verify_record(record: dict) -> bool:
    """True when the record was not edited after it was written. The hash is unkeyed: it detects
    edits, it does not prove who wrote the record (docs/checks/ci.md)."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    return record.get("record_sha256") == _seal(body)


def run_ci(plan: CiPlan, group: str | None = None) -> tuple[CheckResult, dict]:
    if group is not None and group not in GROUPS:
        raise CiError(f"unknown group '{group}'; choose from {', '.join(GROUPS)}")
    if plan.sandbox not in SANDBOX_MODES:
        raise CiError(f"unknown sandbox mode '{plan.sandbox}'; choose from {', '.join(SANDBOX_MODES)}")
    # 1. Prepare: evidence read and judges loaded before any of the change's code runs.
    hooks()                                           # the guard and post-check modules the judges use
    config = load_config(plan.trusted)
    if config.harness.get("base_branch", "main") != plan.base_branch:
        raise CiError(f"the base branch's configuration names base '{config.harness.get('base_branch')}', "
                      f"not '{plan.base_branch}'")
    approvals = _read_trusted(plan.trusted / APPROVALS)
    merges = _read_trusted(plan.trusted / MERGES)
    try:
        ref = parse_approvals(approvals, plan.branch, f"{plan.base_branch}:{APPROVALS}")
        scope, why = parse_may_change(bundle_at(plan.repo, ref)), ""
    except ScopeError as exc:
        scope, why = None, str(exc)
    steering = _steering(plan.trusted)
    for owned, owner in ((".check", "the check owns (a committed symlink there could redirect the check's writes)"),
                         (RECORDS, "aidlc ci owns (a committed record would pose as trusted evidence at checkout)")):
        tracked = [p for p in git(plan.work, "ls-tree", "-r", "-z", "--name-only", plan.head, "--", owned)
                   .split("\0") if p]
        if tracked:
            raise CiError(f"the change tracks {', '.join(tracked[:5])} under {owned}/, which {owner}; remove them")
    use_sandbox = available()
    if not use_sandbox and plan.sandbox == "require":
        raise CiError(NO_SANDBOX)
    if not use_sandbox and group != "scans":
        raise CiError("bubblewrap cannot start a sandbox here, and --sandbox auto is only for --group scans, "
                      "which runs none of the change's code; aidlc ci never runs it unsandboxed")
    merge_base = git(plan.work, "merge-base", plan.base, plan.head).strip()
    git_dir = Path(git(plan.work, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    readable, env_names = toolchain_paths(config.profile), toolchain_env(config.profile)
    home = Path(tempfile.mkdtemp(prefix="aidlc-ci-home-"))
    try:
        wrap = Sandbox(work=plan.work, private_home=home, git_dir=git_dir, readable=readable,
                       env_names=env_names).argv if use_sandbox else None
        ctx = CheckContext(repo=plan.work, config=config, branch=plan.branch, base=merge_base, scope=scope,
                           head=plan.head, steering=steering, wrap=wrap)
        # 2 and 3: judges, then the change's code in the sandbox, then what reads its output.
        result = _run_phases(ctx, group)
    finally:
        _remove_tree(home)
    if scope is None:
        for step in result.steps:
            if step.name == "scope" and step.status == FAIL:
                step.detail = f"no approved scope: {why}"
    # 4. Verdict from the evidence read in step 1.
    ready, reason = _merge_ready(merges, plan, result, group)
    body = {"label": LABEL, "framework": __version__, "branch": plan.branch, "head": plan.head,
            "base_branch": plan.base_branch, "base": plan.base, "group": group or "all",
            "sandbox": "bwrap" if use_sandbox else "none",
            "result": "PASS" if result.passed else "FAIL", "failures": result.failures,
            "steps": step_records(result.steps), "merge_ready": ready, "merge_ready_reason": reason,
            "time": datetime.now(timezone.utc).isoformat(timespec="microseconds")}
    body["record_sha256"] = _seal(body)
    return result, body


def _create(path: Path, text: str, replace: bool = False) -> None:
    """Write a file without following a symlink at its name. replace=False: it must not exist."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | (os.O_TRUNC if replace else os.O_EXCL)
    fd = os.open(path, flags, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def write_ci_record(directory: Path, record: dict, fresh: bool = False) -> Path:
    """Write the record. fresh=True: the directory must not exist yet (GitHub mode), so nothing the
    change's code planted can travel with it."""
    if fresh:
        directory.mkdir(parents=True, exist_ok=False)
    else:
        if directory.is_symlink():
            raise CiError(f"{directory} is a symlink; refusing to write a record through it")
        directory.mkdir(parents=True, exist_ok=True)
    _create(directory / ".gitignore", "*\n", replace=True)          # records are never committed
    stamp = re.sub(r"[^0-9T]", "", str(record.get("time", "")))[:21] + "Z"
    branch = re.sub(r"[^A-Za-z0-9._-]", "_", str(record["branch"]).replace("/", "__"))
    stem = f"{stamp}-{branch}-{str(record['head'])[:12]}"
    text = json.dumps(record, indent=2) + "\n"
    for n in range(1000):
        path = directory / (f"{stem}.json" if n == 0 else f"{stem}-{n}.json")
        try:
            _create(path, text)
            return path
        except FileExistsError:
            continue
    raise CiError(f"cannot find a free record name for {stem} in {directory}")


def _branch_name(branch: str) -> str:
    if not BRANCH_RE.fullmatch(branch) or ".." in branch:
        raise CiError(f"'{branch}' is not a branch name")
    return branch


def _run_ci_and_print(plan: CiPlan, group: str | None, work: Path) -> tuple[CheckResult, dict]:
    result, record = run_ci(plan, group)
    print_result(result, work, prefix="ci")
    return result, record


def ci_local(repo: Path, branch: str | None, group: str | None) -> tuple[CheckResult, dict, Path]:
    """Local mode: the base and the head as detached worktrees of `repo`; the sandbox is required."""
    base_branch = recorded_base(repo)             # never the working copy's config: that is the branch's
    if base_branch is None:
        raise CiError(NO_BASE)
    branch = branch or hooks().guard.current_branch(repo)
    if not branch:
        raise CiError("detached HEAD; pass --branch")
    branch = _branch_name(branch)
    if branch == base_branch:
        raise CiError(f"aidlc ci checks a task branch, not the base branch '{base_branch}'")
    if not available():
        raise CiError(NO_SANDBOX)
    head = git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}").strip()
    base = base_commit(repo, base_branch)
    records = safe_target(repo, RECORDS)
    with checkouts(repo, base, head) as (trusted, work):
        plan = CiPlan(repo=repo, branch=branch, head=head, trusted=trusted, work=work,
                      base_branch=base_branch, base=base, records=records)
        result, record = _run_ci_and_print(plan, group, work)
        return result, record, write_ci_record(records, record)


def ci_checkouts(trusted: Path, head_dir: Path, branch: str, head_sha: str, records: Path,
                 group: str | None, sandbox_mode: str = "require") -> tuple[CheckResult, dict, Path]:
    """GitHub mode: the workflow has already checked out the base (trusted) and the change."""
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise CiError("GitHub mode runs only inside GitHub Actions (GITHUB_ACTIONS=true); use local mode")
    branch = _branch_name(branch)
    if not SHA40.fullmatch(head_sha or ""):
        raise CiError(f"--head-sha must be a full 40-character commit sha, got '{head_sha}'")
    checked_out = git(head_dir, "rev-parse", "HEAD").strip()
    if checked_out != head_sha:
        raise CiError(f"--head-sha {head_sha[:12]} is not the commit checked out in {head_dir} "
                      f"({checked_out[:12]}); check out the pull request head, not the merge ref")
    if os.path.lexists(records):
        raise CiError(f"the records directory {records} must not exist before the run")
    if records.resolve().is_relative_to(head_dir.resolve()):
        raise CiError(f"the records directory {records} must be outside the pull request checkout")
    base_branch = configured_base(trusted)
    base = git(trusted, "rev-parse", "HEAD").strip()
    plan = CiPlan(repo=head_dir, branch=branch, head=head_sha, trusted=trusted, work=head_dir,
                  base_branch=base_branch, base=base, records=records, sandbox=sandbox_mode)
    result, record = _run_ci_and_print(plan, group, head_dir)
    return result, record, write_ci_record(records, record, fresh=True)
