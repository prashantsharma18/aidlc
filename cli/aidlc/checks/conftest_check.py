"""Run the Rego pack through Conftest (ADR 0001): rendered settings, the repository's narrowing
file and CI workflows. The policy data comes from the framework's YAML, the one source of
policy data; the Rego holds only logic. Fails closed: no binary, a tool error or unreadable
output is a failure.

Conftest reads configuration from its working directory (conftest.toml) and from CONFTEST_*
variables, and a judged repository can plant either. So conftest never runs in the repository:
it gets an empty temporary directory, a minimal environment, an explicit absolute policy path,
an explicit data file and explicit absolute input paths. Inputs the change chose (symlinks,
special files, paths leaving the checkout) are findings, never read."""
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

from ..adapters.claude_code import _sandbox_paths
from ..harness import REFUSED_WRITE, effective_permissions
from ..paths import framework_root
from ..policy import load_policy
from ..tools import which_tool
from .findings import Finding

TIMEOUT_S = 120
NOT_INSTALLED = "conftest is not installed: run `aidlc tools install conftest`"


def rego_dir() -> Path:
    return framework_root() / "core" / "policy-as-code" / "rego"


def inputs(repo: Path) -> list[tuple[str, str]]:
    """(namespace, repository-relative path) for each file the pack judges. A path that exists as a
    link or special file is listed too: run_conftest refuses it with a finding."""
    out = [("aidlc.settings", ".claude/settings.json")]
    if os.path.lexists(repo / ".aidlc/permissions.yaml"):
        out.append(("aidlc.narrowing", ".aidlc/permissions.yaml"))
    workflows = repo / ".github" / "workflows"
    if workflows.is_dir():
        out += [("aidlc.workflows", str(p.relative_to(repo))) for p in sorted(workflows.iterdir())
                if p.suffix in (".yml", ".yaml")]
    return out


def policy_data(repo: Path) -> dict:
    """The data the Rego sees as data.aidlc.*. In trusted CI `repo` is the base checkout, never the head."""
    baseline = load_policy("permissions")
    eff = effective_permissions(repo)
    deny_read: list[str] = []
    for secret in eff["secret_paths"]:
        deny_read += [p for p in _sandbox_paths(secret) if p not in deny_read]
    return {"aidlc": {"effective": eff, "sandbox_deny_read": deny_read,
                      "baseline": {"deny": baseline.get("deny", {})},
                      "refused_writes": list(REFUSED_WRITE)}}


def _refusal(repo: Path, rel: str) -> str:
    """Why this input must not be handed to conftest; "missing" if absent; "" if it is a plain file."""
    path = repo / rel
    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        return f"cannot be inspected: {exc}"
    if stat.S_ISLNK(mode):
        return "is a symlink; refusing to read it (the change chose where it points)"
    if not stat.S_ISREG(mode):
        return "is not a regular file; refusing to read it"
    root = repo.resolve()
    if not path.resolve().is_relative_to(root):
        return "resolves outside the checkout (a symlinked folder); refusing to read it"
    return ""


def _env(home: Path) -> dict[str, str]:
    """A minimal allow-list: nothing the caller's environment says (CONFTEST_*, proxies) reaches conftest."""
    return {"PATH": os.environ.get("PATH") or "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
            "LANG": os.environ.get("LANG") or "C.UTF-8"}


def _parse(proc: subprocess.CompletedProcess, rel: str, namespace: str) -> list[Finding]:
    if proc.returncode not in (0, 1):
        return [Finding("FAIL", rel, 0, f"conftest failed (exit {proc.returncode}): {proc.stderr.strip()[-300:]}")]
    try:
        results = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return [Finding("FAIL", rel, 0, "conftest printed output that is not JSON"
                        + (f": {proc.stderr.strip()[-200:]}" if proc.stderr.strip() else ""))]
    out = []
    results = [r for r in results if isinstance(r, dict)] if isinstance(results, list) else []
    evaluated = sum(int(r.get("successes") or 0) + len(r.get("failures") or []) + len(r.get("warnings") or [])
                    for r in results if r.get("namespace") == namespace)
    if evaluated == 0:
        out.append(Finding("FAIL", rel, 0, f"the policy namespace {namespace} evaluated no rules; "
                                            "the pack or its data did not load"))
    for result in results:
        for failure in result.get("failures") or []:
            out.append(Finding("FAIL", rel, 0, str(failure.get("msg", failure))))
        for warning in result.get("warnings") or []:
            out.append(Finding("WARN", rel, 0, str(warning.get("msg", warning))))
    if proc.returncode == 1 and not any(f.level == "FAIL" for f in out):
        out.append(Finding("FAIL", rel, 0, "conftest exited 1 without a reported failure"))
    return out


def run_conftest(repo: Path, binary: Path | None = None, runner=subprocess.run,
                 pinned_only: bool = False, data_repo: Path | None = None) -> list[Finding]:
    """Judge `repo`'s files. The policy data is computed from `data_repo` (default `repo`); trusted CI
    passes the base checkout so the change cannot widen what it is judged against."""
    data = policy_data(data_repo or repo)   # first: a policy or narrowing error surfaces as itself
    binary = binary or which_tool("conftest", pinned_only=pinned_only)
    if binary is None:
        return [Finding("FAIL", "", 0, NOT_INSTALLED)]
    findings: list[Finding] = []
    with tempfile.TemporaryDirectory(prefix="aidlc-conftest-") as tmp:
        work, home, datadir = (Path(tmp) / n for n in ("cwd", "home", "data"))
        for directory in (work, home, datadir):
            directory.mkdir()
        data_file = datadir / "aidlc.json"
        data_file.write_text(json.dumps(data), encoding="utf-8")
        for namespace, rel in inputs(repo):
            problem = _refusal(repo, rel)
            if problem == "missing":
                findings.append(Finding("FAIL", rel, 0, f"{rel} is missing; run aidlc render"))
                continue
            if problem:
                findings.append(Finding("FAIL", rel, 0, f"{rel} {problem}"))
                continue
            cmd = [str(binary), "test", str(repo / rel), "--policy", str(rego_dir()), "--data", str(data_file),
                   "--namespace", namespace, "--output", "json"]
            try:
                proc = runner(cmd, capture_output=True, text=True, timeout=TIMEOUT_S, cwd=work, env=_env(home))
            except (OSError, subprocess.SubprocessError) as exc:
                findings.append(Finding("FAIL", rel, 0, f"conftest could not run: {exc}"))
                continue
            findings += _parse(proc, rel, namespace)
    return findings


def verify_pack(binary: Path | None = None, runner=subprocess.run) -> tuple[int, str]:
    """`conftest verify`: every test_ rule in the pack passes (ADR 0001: each rule has a failing case)."""
    binary = binary or which_tool("conftest")
    if binary is None:
        return 2, NOT_INSTALLED
    with tempfile.TemporaryDirectory(prefix="aidlc-conftest-") as tmp:
        work, home = Path(tmp) / "cwd", Path(tmp) / "home"
        work.mkdir()
        home.mkdir()
        try:
            proc = runner([str(binary), "verify", "--policy", str(rego_dir())],
                          capture_output=True, text=True, timeout=TIMEOUT_S, cwd=work, env=_env(home))
        except (OSError, subprocess.SubprocessError) as exc:
            return 2, f"conftest could not run: {exc}"
    return proc.returncode, (proc.stdout + proc.stderr).strip()
