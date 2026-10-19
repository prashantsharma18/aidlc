#!/usr/bin/env python3
"""aidlc post-tool check (guide chapter 3 step 5; 9.5). Standard library only; no network.
Runs after a modifying or executing tool call. It cannot undo the action: it flags, and the
adapter shows the reason to the agent. Flags: high-confidence credential shapes in output, a new or
changed protected path (shell writes the Edit deny rules cannot see), files written outside the
task scope, an existing assertion changed or removed. The base is the commit recorded in the scope
file, so moving the local base branch does not hide changes. Trusted CI is the real check; this is
the fast first line. Fails closed: errors give "flag"."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
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
                               "or stop and ask if you did not create it.")
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


def _exists_at(root: Path, base: str, path: str) -> bool:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    return subprocess.run(["git", "cat-file", "-e", f"{base}:{path}"], cwd=root, env=env,
                          capture_output=True, timeout=10).returncode == 0


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
