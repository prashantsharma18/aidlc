#!/usr/bin/env python3
"""aidlc post-tool check (guide chapter 3 step 5; 9.5). Standard library only; no network.
Runs after a modifying or executing tool call. It cannot undo the action: it flags, and the
adapter shows the reason to the agent. Flags: high-confidence credential shapes in output, a new or
changed protected path (shell writes the Edit deny rules cannot see), files written outside the
task scope, an existing assertion changed or removed. The base is the commit recorded in the scope
file, so moving the local base branch does not hide changes. Trusted CI is the real check; this is
the fast first line. Fails closed: errors give "flag"."""
from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True  # never leave __pycache__ in the repository (post-check would flag it)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import guard  # noqa: E402  (same directory)

ASSERT_RE = re.compile(r"(expect\(|\bassert|Assert\.|\.Should\(|Should\.|\.toBe\(|\.toEqual\(|"
                       r"\.toMatch|\.toThrow|Verify\(|\.(not\.)?to[A-Z]\w*\(|\.Should\w*\()")
TEST_FILE_RE = re.compile(
    r"(^|/)(test|tests|spec|__tests__)/|(^|/)[^/]*\.Tests?/|\.(test|spec)\.[cm]?[jt]sx?$"
    r"|(Test|Tests|Spec)\.(cs|java|kt)$|(^|/)test_[^/]*\.py$|_test\.py$|_test\.go$")
SKIP_RE = re.compile(r"\.skip\b|\bx(it|describe|test)\s*\(|\.fixme\s*\(|@(Disabled|Ignore)\b|\[Ignore\b|"
                     r"\[(Fact|Theory)\([^)]*Skip\s*=|@pytest\.mark\.skip|@unittest\.skip|\bt\.Skip\w*\(|"
                     r"\.only\b|\b(fit|fdescribe|ftest)\s*\(")


def _result(decision: str, rule: str, reason: str) -> dict:
    return {"decision": decision, "rule": rule, "reason": reason}


def _git(root: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, errors="replace", env=env, timeout=10)
    if out.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {out.stderr.strip()[:200]}")
    return out.stdout


def check(event: dict) -> dict:
    try:
        if guard.BLOCK_SECRET_RE.search(str(event.get("output") or "")):
            return _result("flag", "secret-in-output", "output contains something shaped like a "
                           "credential. Do not repeat it; stop and tell a person.")
        if event.get("tool") not in ("edit", "shell"):
            return _result("pass", "not-modifying", "read or integration call")
        root = guard.repo_root(Path(event.get("cwd") or os.getcwd()))
        if root is None:
            return _result("flag", "fail-safe", "not inside a git repository")
        harness = guard.load_harness()
        protected = [p.casefold() for p in harness["protected_paths"]]
        scope_off = os.environ.get("AIDLC_SCOPE") == "off" and not guard._unattended()
        read = None if scope_off else guard._read_scope(root)
        if read is None and not scope_off:
            return _result("flag", "no-scope", "no readable task scope; changes cannot be checked")
        scope, recorded = read if read else (None, None)
        # The base recorded at scope generation is the trust root; the branch name is only the
        # fallback for scope files written before it was recorded.
        ref = os.environ.get("AIDLC_BASE_REF") or recorded or harness["base_branch"]
        base = _git(root, "merge-base", ref, "HEAD").strip()
        changed = {p for p in _git(root, "diff", "--no-renames", "--name-only", "-z", base).split("\0") if p}
        changed |= {p for p in _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0") if p}
        for path in sorted(changed):
            if (".git" in (seg.casefold() for seg in path.split("/"))
                    or guard.matches(path.casefold(), protected)):
                return _result("flag", "protected-path", f"{guard._redact(path)} is a protected path "
                               "(harness, rules, CI, plans or contracts) and is new or changed on this "
                               "branch. Do not change it through the shell; commit it, gitignore it, "
                               "or stop and ask if you did not create it. A person's own file: commit "
                               "it on the base branch." + _moved_hint(root, recorded, harness, base))
        for path in sorted(changed):
            if scope is not None and not guard.matches(path, scope, any_depth_names=False):
                return _result("flag", "outside-scope", f"{guard._redact(path)} was written outside the task's "
                               "MAY CHANGE list. Revert it, or stop and ask.")
            if TEST_FILE_RE.search(path) and _exists_at(root, base, path):
                lines = _git(root, "diff", "--no-renames", "-U0", base, "--", path).splitlines()
                removed = [ln for ln in lines if ln.startswith("-") and not ln.startswith("---")
                           and ASSERT_RE.search(ln)]
                if removed:
                    return _result("flag", "changed-assertion", f"an existing assertion in {guard._redact(path)} "
                                   f"was changed or removed. Restore it, or stop and ask: "
                                   f"{guard._redact(removed[0])[:120]}")
                if any(ln.startswith("+") and not ln.startswith("+++") and SKIP_RE.search(ln) for ln in lines):
                    return _result("flag", "skipped-test", f"a test was disabled or the suite was narrowed in "
                                   f"{guard._redact(path)}. Revert it, or stop and ask.")
        return _result("pass", "no-rule-broken", "no rule broken")
    except Exception as exc:  # noqa: BLE001 - fail closed
        return _result("flag", "fail-safe", f"post-tool check failed ({type(exc).__name__}); "
                       "treat the result as unchecked")


def _moved_hint(root: Path, recorded: str | None, harness: dict, base: str) -> str:
    """When this branch was updated from a base that moved since the scope was approved, the
    flagged change may be the base's own, not the agent's: say so instead of blaming the agent."""
    if not recorded:
        return ""
    try:
        current = _git(root, "merge-base", harness["base_branch"], "HEAD").strip()
    except Exception:  # noqa: BLE001 - a hint must never change the decision
        return ""
    if current and current != base:
        return (" The base branch has moved since the scope was approved; if this branch was "
                "updated from it, a person must re-run aidlc scope.")
    return ""


def _exists_at(root: Path, base: str, path: str) -> bool:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "cat-file", "-e", f"{base}:{path}"], cwd=root, env=env,
                          capture_output=True, timeout=10).returncode == 0


CONTEXT_RE = re.compile(r"^check  context  repo=(.*?)  base=([0-9a-f]{40,64})  scope=(.*?)  mode=(\w+)$", re.M)
SKIPPED_RE = re.compile(r"^check  \S+\s+SKIPPED\b", re.M)


def _context_ok(root: Path, branch: str, text: str) -> bool:
    """The run judged exactly what the hooks judge: this repository, the base the post-check uses,
    the scope file the guard reads, and a required scope. Any override fails this."""
    found = CONTEXT_RE.findall(text)
    if len(found) != 1:
        return False
    repo, base, scope, mode = found[0]
    read = guard._read_scope(root)
    ref = os.environ.get("AIDLC_BASE_REF") or (read[1] if read else None) or guard.load_harness()["base_branch"]
    try:
        expected = _git(root, "merge-base", ref, "HEAD").strip()
    except Exception:  # noqa: BLE001 - no expected base: the run cannot be a clean pass
        return False
    return (Path(repo).resolve() == root.resolve() and base == expected
            and scope == str(guard.scope_file(root, branch)) and mode == "require")


MAX_ARTEFACT_BYTES = 1 << 20


def check_run_id(root: Path) -> str | None:
    """The `run` id in <root>/.check/result.json, the check's own record of its latest run. None:
    absent, a symlink, too big or malformed. That is "no signal", never an error."""
    try:
        if (root / ".check").is_symlink():
            return None
        fd = os.open(root / ".check" / "result.json", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as fh:
            raw = fh.read(MAX_ARTEFACT_BYTES + 1)
        if len(raw) > MAX_ARTEFACT_BYTES:
            return None
        run = json.loads(raw.decode("utf-8")).get("run")
    except Exception:  # noqa: BLE001
        return None
    return run if isinstance(run, str) and run else None


def _update_attempts(path: Path, counted_call: bool, passed: bool, run: str | None, cap: int) -> int | None:
    """Read-modify-write under an exclusive lock (parallel hooks never lose a count).
    `counted_call`: the command itself runs the check. Otherwise the call counts (as one failing
    attempt) only when the check's own record shows a run this counter has not seen. Returns the
    failures in a row, or None when the call did not count. Unsafe or unreadable: at the limit."""
    if guard.attempts_unsafe(path):
        return cap
    path.parent.mkdir(parents=True, exist_ok=True)
    if guard.attempts_unsafe(path):
        return cap
    try:
        lock_fd = os.open(path.parent / ".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    except OSError:
        return cap
    with os.fdopen(lock_fd, "r+", encoding="utf-8") as lock:   # never opened through a symlink
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            before, last_run, fresh = None, None, False
            try:
                if path.is_symlink():                       # never trust a link: fail closed
                    raise OSError("attempts record is a symlink")
                data = json.loads(path.read_text(encoding="utf-8"))
                before = data.get("failures") if isinstance(data, dict) else None
                before = before if isinstance(before, int) and not isinstance(before, bool) and before >= 0 else None
                last_run = data.get("last_run") if isinstance(data, dict) else None
                last_run = last_run if isinstance(last_run, str) else None
            except FileNotFoundError:
                before, fresh = 0, True
            except Exception:  # noqa: BLE001 - unreadable: fail closed (counts as at the limit)
                before = None
            if not counted_call and fresh and run is not None:
                run_adopted = {"failures": 0, "last": "NONE",
                               "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               "last_run": run}                  # the first sight of a run: not counted
                fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".attempts-")
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(run_adopted, fh)
                os.replace(tmp, path)
                return None
            if not counted_call and not (run is not None and run != last_run):
                return None
            failures = 0 if passed else (cap if before is None else before + 1)
            record = {"failures": failures, "last": "PASS" if passed else "FAIL",
                      "updated": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            if run is not None or last_run is not None:
                record["last_run"] = run if run is not None else last_run
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".attempts-")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(record, fh)
            os.replace(tmp, path)
            return failures
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def record_check(event: dict) -> dict | None:
    """Count runs of the one-command check (guide 8.8: the harness enforces the retry limit). A run
    is a PASS only when the command is exactly the framework's own `aidlc check`, it exited 0 and
    its last result line says PASS. Any other command that runs the check is a failing attempt. A
    command the parser cannot see (`python3 -m aidlc check`, `$A check`, make) is still counted
    once, from the new run id in the check's own record."""
    if event.get("tool") != "shell":
        return None
    cwd = event.get("cwd") or os.getcwd()
    contains, exact = guard.check_segments((event.get("args") or {}).get("command"), cwd)
    root = guard.repo_root(Path(cwd))
    if root is None:
        return None
    run = check_run_id(root)
    if not contains and run is None:
        return None
    branch = guard.current_branch(root)                      # None: counted under the detached key
    text = str(event.get("text") or "")
    results = guard.CHECK_RESULT_RE.findall(text)
    passed = (contains and exact and branch is not None and event.get("exit_code") == 0 and bool(results)
              and results[-1] == "PASS" and not SKIPPED_RE.search(text) and _context_ok(root, branch, text))
    cap = guard.load_harness()["retry_cap"]
    failures = _update_attempts(guard.attempts_file(root, branch), contains, passed, run, cap)
    if failures is None:
        return None
    hint = ""
    if contains and not exact:
        entry = guard.recorded_entry(root)
        hint = (f" Only this earns credit: run exactly: {entry} check" if entry else
                " The aidlc entry point is not recorded for this repository: a person runs `aidlc render`.")
    if failures >= cap:
        return _result("flag", "retry-limit", guard.retry_limit_reason(failures, cap) + hint)
    return _result("pass", "check-recorded",
                   f"check {'PASS' if passed else 'FAIL'}; {failures} failing in a row (limit {cap}).{hint}")


def main() -> int:
    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise ValueError("event is not an object")
        result = check(event)
    except Exception:  # noqa: BLE001
        event, result = {}, _result("flag", "fail-safe", "unreadable tool result")
    guard._log({**event, "hook": "post-tool-check"}, result)
    print(json.dumps({k: (guard._redact(v) if isinstance(v, str) else v) for k, v in result.items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
