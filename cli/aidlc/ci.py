"""aidlc ci: the gates against a task branch (design §8; guide 9.5-9.7, 11.8). GitHub mode, inside
GitHub Actions, is the trusted CI; local mode is a preview, never evidence (ADR 0002).

The change's own code (install script, tests) was written by an agent, so the order is the
security property:
1. prepare: detached worktrees of the base and the head; read every piece of evidence (the base's
   configuration, approvals, a private copy of the steering files); every judge
   is already imported;
2. judge, before any of the change's code runs, from git objects and the untouched checkout;
3. run the change's own commands in the bubblewrap sandbox, then the checks that read their
   output (skips, the protected re-run). From here on no git command runs in the checkout: the
   change's code could have planted git configuration or attributes there;
4. a self-hashed record, labelled github-actions or local-preview. Merge readiness is GitHub's.
The GitHub Actions workflow (core/ci/github/aidlc-verify.yml) runs the same code on two checkouts."""
from __future__ import annotations

import dataclasses
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
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

import yaml

from . import __version__
from .checks.findings import Finding
from .checks.conftest_check import judge_generated, run_conftest
from .baseline import BASELINE, BaselineError, parse as parse_baseline
from .checks.onecheck import (DIFF_FLAGS, FAIL, OK, STEERING, report_only, CheckContext, CheckError, CheckResult, StepResult,
                              _excepted, prepare_check_dir,
                              begin_command_steps, git, print_result, run_command, step_context_drift,
                              step_protected_tests, step_records, step_scope, step_secrets, step_skips)
from .harness import BRANCH_RE
from .harness import base_branch as configured_base
from .hookbridge import hooks
from .paths import safe_target
from .repo import CONFIG, load_config
from .sandbox import Sandbox, available, toolchain_env, toolchain_paths
from .scope import FULL_SHA, ScopeError, base_commit, bundle_at, parse_approvals, parse_may_change

LOCAL_LABEL = "local-preview"       # ADR 0002: a local run is a preview, never evidence
GITHUB_LABEL = "github-actions"     # the trusted run: GitHub mode inside GitHub Actions
RECORDS = ".aidlc/ci-records"
APPROVALS = "plans/approved-bundles.txt"
GROUPS = ("compile", "check", "scans")
SANDBOX_MODES = ("require", "auto")
INSTALL_STEPS = ("install", "restore")
COMPILE_STEPS = {"install", "restore", "build", "compile"}
SCAN_STEPS = {"secrets", "config-policy"}
SHA40 = re.compile(r"[0-9a-f]{40}")
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
    label: str = LOCAL_LABEL   # a preview unless GitHub mode says otherwise (ADR 0002): fail closed


def group_of(step: str) -> str:
    if step in COMPILE_STEPS:
        return "compile"
    if step in SCAN_STEPS:
        return "scans"
    return "check"


RESTORE_MODES = {"100644": 0o644, "100755": 0o755}      # regular files only; never a link or a submodule


@dataclass
class Rerun:
    """The protected re-run's own checkout of the head, with the base test suite in place. Built before
    any of the change's code runs; the first run's sandbox never binds it."""
    path: Path                     # the checkout: the only writable tree of the re-run's sandbox
    home: Path                     # its own private home (never the first run's)
    touched: list[str]             # "restored <path>" and "removed <path>", for the step's message
    problem: str = ""              # a setup failure: the re-run FAILs with it
    wrap: Callable[[str, str], list[str]] | None = None


def _test_changes(repo: Path, base: str, head: str) -> tuple[dict[str, str], list[str]]:
    """From git objects: {path: base mode} of every test file the change modified, retyped or deleted,
    and the test files it added. The same test patterns as protected_test_changes; steering files and
    approved exceptions keep the change's version."""
    test_file = hooks().post_check.TEST_FILE_RE
    excepted = _excepted(repo, base, head)
    fields = [f for f in git(repo, "diff", *DIFF_FLAGS, "--name-status", "-z", base, head).split("\0") if f]
    restore: dict[str, str] = {}
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
        if len(meta.split()) != 3 or listed != rel:
            raise CiError(f"cannot read the mode of {rel} at {base[:12]}")
        restore[rel] = meta.split()[0]
    return restore, sorted(remove)


def _open_slot(root: Path, rel: str, create_parents: bool) -> Path | None:
    """root/rel with nothing at it. Every parent is checked with safe_target: a symlinked component,
    which the change chose by committing it, is refused. A file, link or FIFO at rel is unlinked, never
    followed; a directory there is refused. None: a parent is missing and create_parents is False."""
    parts = Path(rel).parts
    for i in range(1, len(parts)):
        parent = safe_target(root, str(Path(*parts[:i])))
        if not os.path.lexists(parent):
            if not create_parents:
                return None
            parent.mkdir()
        elif not parent.is_dir():
            raise ValueError(f"{rel}: '{Path(*parts[:i])}' is not a directory")
    target = root.resolve() / rel
    if os.path.lexists(target):
        if stat.S_ISDIR(os.lstat(target).st_mode):
            raise ValueError(f"{rel} is a directory where a test file belongs")
        target.unlink()
    return target


def _prepare_rerun(repo: Path, tmp: Path, base: str, head: str) -> Rerun | None:
    """Before any of the change's code runs: a detached worktree of the head at tmp/rerun, where every
    test file the change touched gets its base bytes and mode back and every test file it added is
    removed. Nothing the first run does can reach it. None: the change touches no test file."""
    restore, remove = _test_changes(repo, base, head)
    if not restore and not remove:
        return None
    path, home = tmp / "rerun", tmp / "home"
    home.mkdir()
    git(repo, "worktree", "add", "--detach", str(path), head)
    rerun = Rerun(path, home, [f"restored {rel}" for rel in sorted(restore)] + [f"removed {rel}" for rel in remove])
    bad = [f"{rel} (mode {mode})" for rel, mode in sorted(restore.items()) if mode not in RESTORE_MODES]
    if bad:
        rerun.problem = (f"cannot restore the base version of {', '.join(bad[:5])}: only regular files "
                         "(100644, 100755) can be restored")
        return rerun
    try:
        for rel, mode in sorted(restore.items()):
            data = _blob(repo, base, rel)
            target = _open_slot(path, rel, create_parents=True)
            fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, RESTORE_MODES[mode])
            with os.fdopen(fd, "wb") as handle:
                os.fchmod(handle.fileno(), RESTORE_MODES[mode])     # exact mode, whatever the umask
                handle.write(data)
        for rel in remove:
            _open_slot(path, rel, create_parents=False)
        prepare_check_dir(path)
    except (ValueError, OSError, CheckError) as exc:
        rerun.problem = f"cannot set up the base suite: {exc}"
    return rerun


@contextmanager
def rerun_checkout(repo: Path, git_dir: Path, base: str, head: str, enabled: bool) -> Iterator[Rerun | None]:
    """The protected re-run's checkout (see _prepare_rerun), always removed. Cleanup runs git from the
    common git directory, never from a checkout the change's code ran in."""
    if not enabled:
        yield None
        return
    tmp = Path(tempfile.mkdtemp(prefix="aidlc-ci-rerun-"))
    try:
        yield _prepare_rerun(repo, tmp, base, head)
    finally:
        _remove_tree(tmp / "rerun")
        _quiet(git_dir, "worktree", "remove", "--force", str(tmp / "rerun"))
        _remove_tree(tmp)


def step_protected_rerun(ctx: CheckContext) -> StepResult:
    """Guide 9.5 rule 3: the base test suite must pass on the new code. The change's tests may only
    add lines, but an added line, or an added test file that monkeypatches the code, can still hide a
    regression. The re-run uses its own checkout (ctx.rerun), built before any of the change's code
    ran: the base version of every test file the change touched, none of the test files it added, and
    nothing the first run wrote. It runs in its own sandbox with a fresh private home: install, the
    compile steps, then the test step. Its logs go to its own .check/ (rerun/.check/, prepared before
    any of the change's code ran), never to the first checkout's, which the change's code owned."""
    rerun: Rerun | None = ctx.rerun
    if rerun is None:
        return StepResult("protected-rerun", OK, "no existing test file changed")
    if rerun.problem:
        return StepResult("protected-rerun", FAIL, rerun.problem)
    if rerun.wrap is None:
        return StepResult("protected-rerun", FAIL, "the protected re-run runs only in the sandbox")
    if "test" not in ctx.config.commands:
        return StepResult("protected-rerun", FAIL, "no test command to re-run the base suite with")
    rctx = dataclasses.replace(ctx, repo=rerun.path, wrap=rerun.wrap)
    install = [n for n in INSTALL_STEPS if n in ctx.config.commands][:1]
    builds = [n for n in ctx.config.check_steps if group_of(n) == "compile" and n not in INSTALL_STEPS]
    for name in install + builds:                             # `dotnet test --no-build` needs a fresh build
        built = _rerun_log(run_command(rctx, name, step=f"protected-rerun-{name}", cwd=rerun.path))
        if built.status == FAIL:
            built.name, built.detail = "protected-rerun", f"preparing the base suite failed at {name} ({built.detail})"
            return built
    result = _rerun_log(run_command(rctx, "test", step="protected-rerun", cwd=rerun.path))
    if result.status == FAIL:
        touched = rerun.touched
        result.detail = (f"the base test suite fails on this change ({result.detail}; {', '.join(touched[:5])}"
                         f"{' ...' if len(touched) > 5 else ''}): a changed or added test hid a regression")
    return result


def _rerun_log(result: StepResult) -> StepResult:
    """The re-run's log lives in the re-run's checkout: say so in the record and the output."""
    if result.log:
        result.log = f"rerun/{result.log}"
    return result


def step_config_policy(ctx: CheckContext) -> StepResult:
    """ADR 0001: the change's rendered settings, narrowing and workflows pass the Rego pack. A judge
    step: it runs before any of the change's code, with the pinned (checksum-verified) conftest. The
    files judged come from the head checkout; the policy data comes from the base (ctx.trusted), so
    the change cannot widen what it is judged against. The generated files are re-rendered from the
    head's sources and compared (nothing is written). Nothing from the head is executed."""
    trusted = getattr(ctx, "trusted", None)
    findings = run_conftest(ctx.repo, pinned_only=True, data_repo=trusted or ctx.repo)
    if trusted is None:
        findings.append(Finding("FAIL", "", 0, "no trusted checkout; policy data must come from the base"))
    else:
        findings += judge_generated(ctx.repo, trusted)
    fails = [str(f) for f in findings if f.level == "FAIL"]
    if fails:
        return StepResult("config-policy", FAIL, f"{len(fails)} violation(s): " + "; ".join(fails[:5]))
    warns = len(findings) - len(fails)
    return StepResult("config-policy", OK, f"{warns} warning(s)" if warns else "")


def _head_text(ctx: CheckContext, rel: str) -> str:
    """A file of the change: from git objects at ctx.head in CI (never the working tree, never through a
    link), the working copy locally. "" when the change has no such file; a link or other non-file raises."""
    if ctx.head is not None:
        entry = git(ctx.repo, "ls-tree", "-z", ctx.head, "--", rel).strip("\0")
        if not entry:
            return ""
        if entry.split(" ", 1)[0] not in ("100644", "100755"):
            raise ValueError(f"{rel} is not a regular file in the change")
        return _blob(ctx.repo, ctx.head, rel).decode("utf-8")
    path = ctx.repo / rel
    if path.is_symlink():
        raise ValueError(f"{rel} is a symlink; the judge does not follow it")
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def step_baseline(ctx: CheckContext) -> StepResult:
    """The ratchet (ADR 0007): the change's .aidlc/baseline.yaml may only shrink. It is compared with the
    base's copy, read before any of the change's code runs. A skip, or a report-only step, that the base
    does not list FAILs, unless the step is new: absent from the base's check_steps and added by this
    change. Any entry past its review date FAILs. A date moved later is allowed (the code owners review
    it) and named in the result, so it is never silent."""
    try:
        base = parse_baseline((ctx.steering or {}).get(BASELINE, ""), f"base {BASELINE}")
        head = parse_baseline(_head_text(ctx, BASELINE))
        head_config = yaml.safe_load(_head_text(ctx, str(CONFIG)) or "{}") or {}
    except (BaselineError, CiError, ValueError, OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return StepResult("baseline", FAIL, str(exc))
    head_steps = head_config.get("check_steps") if isinstance(head_config, dict) else None
    head_steps = set(head_steps) if isinstance(head_steps, list) and all(isinstance(x, str) for x in head_steps) else set()
    known = {(e.kind, e.key): e for e in base}
    runs = set(ctx.config.check_steps)                # the base's configuration judges the change
    today = date.today()
    problems, moved = [], []
    for e in head:
        new_step = e.kind == "report_only" and e.key not in runs and e.key in head_steps
        before = known.get((e.kind, e.key))
        if before is None and not new_step:
            problems.append(f"{e.kind} '{e.key}' is new: the baseline may only shrink")
        if e.review_by < today:
            problems.append(f"{e.kind} '{e.key}' passed its review date {e.review_by}: fix it, or its owner "
                            "moves the date in a reviewed change")
        if before is not None and e.review_by > before.review_by:
            moved.append(f"{e.key}: {before.review_by} -> {e.review_by}")
    if problems:
        return StepResult("baseline", FAIL, "; ".join(problems[:5]))
    paid = len(set(known) - {(e.kind, e.key) for e in head})
    detail = f"{len(head)} entries" + (f", {paid} paid off" if paid else "")
    if moved:
        detail += "; dates moved later (code owners review): " + ", ".join(moved)
    return StepResult("baseline", OK, detail)


# Judges: run before any of the change's code, from git objects (ctx.head) or the untouched checkout.
JUDGE_STEPS: list[tuple[str, Callable[[CheckContext], StepResult]]] = [
    ("scope", step_scope),
    ("protected-tests", step_protected_tests),
    ("secrets", step_secrets),
    ("context-drift", step_context_drift),
    ("baseline", step_baseline),
    ("config-policy", step_config_policy),
]
# After the change's commands: checks that read their output, then the re-run in its own checkout.
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
    begin_command_steps(ctx)                          # .check/, the clock, the report snapshot
    install = [n for n in INSTALL_STEPS if n in ctx.config.commands][:1]
    commands = install + [n for n in ctx.config.check_steps if n not in install]
    commands = [n for n in commands if n in install or _selected(n, group, command=True)]
    for name in commands:
        guarded(name, lambda n=name: report_only(ctx, run_command(ctx, n)))
    if group != "compile":
        for name, fn in AFTER_STEPS:
            guarded(name, lambda f=fn: f(ctx))
    return CheckResult(steps)


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


def verified_approval(repo: Path, ref: str) -> str:
    """The approval ref `<sha>:<path>`, accepted only when <sha> is a full commit SHA that resolves to
    itself. CI resolves it in an object store the change controls: a short sha can be matched by a
    commit the change wrote, and a tag object would peel to another commit (final review I1)."""
    sha = ref.split(":", 1)[0]
    if not FULL_SHA.fullmatch(sha):
        raise ScopeError(f"the approval pins '{sha}', which is not a full commit SHA; CI needs all 40 (or 64) "
                         "hex digits, because a short one can match a commit the change wrote")
    try:
        resolved = git(repo, "rev-parse", "--verify", "-q", f"{sha}^{{commit}}").strip()
    except CheckError:
        resolved = ""
    if resolved != sha:
        raise ScopeError(f"the approval pins {sha[:12]}, which does not resolve to that commit in this repository")
    return ref


def _steering(trusted: Path) -> dict[str, str]:
    """The base's steering files, read into memory before any of the change's code runs."""
    out = {}
    for rel in STEERING:
        source = trusted / rel
        if source.is_file() and not source.is_symlink():
            out[rel] = source.read_text(encoding="utf-8")
    return out


def _seal(body: dict) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()


def verify_record(record: dict) -> bool:
    """True when the record was not edited after it was written. The hash is unkeyed: it detects
    edits, it does not prove who wrote the record (docs/checks/ci.md)."""
    body = {k: v for k, v in record.items() if k != "record_sha256"}
    return record.get("record_sha256") == _seal(body)


CONFIG_FILES = (".aidlc", ".aidlc/config.yaml", ".aidlc/permissions.yaml")


def refuse_linked_config(root: Path) -> None:
    """Configuration is read from a checkout the change controls: refuse it before reading when it
    is a link or not a regular file, so its target (a host file, perhaps a secret) is never opened.
    `.aidlc/permissions.yaml` is optional; the other two must exist."""
    for rel in CONFIG_FILES:
        path = root / rel
        if path.is_symlink():
            raise CiError(f"{rel} is a symlink in {root}; aidlc ci does not follow it")
        if rel == ".aidlc":
            ok = path.is_dir()
        else:
            ok = path.is_file() or (rel.endswith("permissions.yaml") and not os.path.lexists(path))
        if not ok:
            raise CiError(f"{rel} in {root} is missing or not a regular "
                          f"{'directory' if rel == '.aidlc' else 'file'}; aidlc ci does not read it")


def run_ci(plan: CiPlan, group: str | None = None) -> tuple[CheckResult, dict]:
    if group is not None and group not in GROUPS:
        raise CiError(f"unknown group '{group}'; choose from {', '.join(GROUPS)}")
    if plan.sandbox not in SANDBOX_MODES:
        raise CiError(f"unknown sandbox mode '{plan.sandbox}'; choose from {', '.join(SANDBOX_MODES)}")
    # 1. Prepare: evidence read and judges loaded before any of the change's code runs.
    hooks()                                           # the guard and post-check modules the judges use
    refuse_linked_config(plan.trusted)
    config = load_config(plan.trusted)
    if config.harness.get("base_branch", "main") != plan.base_branch:
        named = config.harness.get("base_branch")
        raise CiError(f"the base branch's configuration names base '{named}', not '{plan.base_branch}'")
    approvals = _read_trusted(plan.trusted / APPROVALS)
    try:
        ref = verified_approval(plan.repo, parse_approvals(approvals, plan.branch, f"{plan.base_branch}:{APPROVALS}"))
        scope, why = parse_may_change(bundle_at(plan.repo, ref)), ""
    except ScopeError as exc:
        scope, why = None, str(exc)
    steering = _steering(plan.trusted)
    for owned, owner in ((".check", "the check owns (a committed symlink there could redirect the check's writes)"),
                         (RECORDS, "aidlc ci owns (a committed record would land in the records folder at checkout)")):
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
        # The re-run's checkout is complete before anything else; the change's code runs in neither yet.
        with rerun_checkout(plan.repo, git_dir, merge_base, plan.head, enabled=group in (None, "check")) as rerun:
            wrap = Sandbox(work=plan.work, private_home=home, git_dir=git_dir, readable=readable,
                           env_names=env_names).argv if use_sandbox else None
            if rerun is not None and use_sandbox:
                box = Sandbox(work=rerun.path, private_home=rerun.home, git_dir=git_dir, readable=readable,
                              env_names=env_names)
                rerun.wrap = lambda command, step: box.argv(command, step.removeprefix("protected-rerun-"))
            ctx = CheckContext(repo=plan.work, config=config, branch=plan.branch, base=merge_base, scope=scope,
                               head=plan.head, steering=steering, wrap=wrap, rerun=rerun,
                               trusted=plan.trusted)
            # 2 and 3: judges, then the change's code in the sandbox, then what reads its output.
            result = _run_phases(ctx, group)
    finally:
        _remove_tree(home)
    if scope is None:
        for step in result.steps:
            if step.name == "scope" and step.status == FAIL:
                step.detail = f"no approved scope: {why}"
    # 4. The record. Merge readiness is GitHub's (required checks and rulesets, ADR 0002), never ours.
    body = {"label": plan.label, "framework": __version__, "branch": plan.branch, "head": plan.head,
            "base_branch": plan.base_branch, "base": plan.base, "group": group or "all",
            "sandbox": "bwrap" if use_sandbox else "none",
            "result": "PASS" if result.passed else "FAIL", "failures": result.failures,
            "steps": step_records(result.steps),
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
    """Local mode, a preview (ADR 0002): the base and the head as detached worktrees of `repo`, the
    change's code in the sandbox, and a record labelled local-preview. It is never evidence: the base
    comes from the working copy, which the change controls; GitHub Actions is the trusted CI."""
    refuse_linked_config(repo)                     # the working copy's config: never through a link
    base_branch = configured_base(repo)
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
                      base_branch=base_branch, base=base, records=records, label=LOCAL_LABEL)
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
                  base_branch=base_branch, base=base, records=records, sandbox=sandbox_mode,
                  label=GITHUB_LABEL)
    result, record = _run_ci_and_print(plan, group, head_dir)
    return result, record, write_ci_record(records, record, fresh=True)
