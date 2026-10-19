"""aidlc doctor: is the harness in this repository intact and enforceable? Checks D1-D12.
Each check returns findings whose message starts with its id."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from ..adapters import get_adapter
from ..adapters.base import write_rendered
from ..adapters.claude_code import (HOOK_FILES, POST_MATCHER, PRE_MATCHER, _deny_write,
                                    _is_literal_protected, _sandbox_paths, _tracked_files)
from ..harness import HarnessError, base_branch, effective_permissions, map_tools
from ..policy import PolicyError, load_policy
from ..repo import load_config
from .findings import Finding

SETTINGS = ".claude/settings.json"
MIN_CLAUDE = (2, 1, 295)
IMPORT_FAIL_LINES = 200
IMPORT_WARN_LINES = 80
IMPORT_RE = re.compile(r"(?:^|(?<=\s))@(\S+)")


def _fail(file: str, msg: str) -> Finding:
    return Finding("FAIL", file, 0, msg)


def _warn(file: str, msg: str) -> Finding:
    return Finding("WARN", file, 0, msg)


def _settings(repo: Path) -> tuple[dict | None, list[Finding]]:
    path = repo / SETTINGS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("not a JSON object")
        return data, []
    except (OSError, ValueError) as exc:
        return None, [_fail(SETTINGS, f"D1 cannot read {SETTINGS} ({type(exc).__name__}); "
                                      "run `aidlc render --tool claude-code`")]


def _get(data: dict, *keys, default=None):
    for key in keys:
        if not isinstance(data, dict) or key not in data:
            return default
        data = data[key]
    return data


def check_d1(repo: Path) -> list[Finding]:
    adapter = get_adapter("claude-code")
    try:
        files = (adapter.render_rules(repo) + adapter.render_folder_rules(repo)
                 + adapter.render_permissions(repo) + adapter.render_hooks(repo))
    except (ValueError, HarnessError, PolicyError, OSError) as exc:
        return [_fail(".", f"D1 cannot render the expected files: {exc}")]
    problems = write_rendered(repo, files, check=True, managed_dirs=adapter.managed_dirs)
    return [_fail(".", f"D1 {p}") for p in problems]


def check_d2(repo: Path, settings: dict, eff: dict) -> list[Finding]:
    deny = _get(settings, "permissions", "deny", default=[])
    deny_read = _get(settings, "sandbox", "filesystem", "denyRead", default=[])
    out = []
    for entry in eff["secret_paths"]:
        if f"Read({entry})" not in deny:
            out.append(_fail(SETTINGS, f"D2 secret path '{entry}' has no Read({entry}) deny rule"))
        for want in _sandbox_paths(entry):
            if want not in deny_read:
                out.append(_fail(SETTINGS, f"D2 secret path '{entry}' has no sandbox denyRead entry "
                                           f"'{want}'"))
    return out


def check_d3(settings: dict) -> list[Finding]:
    sandbox = settings.get("sandbox") if isinstance(settings.get("sandbox"), dict) else {}
    out = []
    for key, want in (("enabled", True), ("failIfUnavailable", True),
                      ("allowUnsandboxedCommands", False)):
        if sandbox.get(key) is not want:
            out.append(_fail(SETTINGS, f"D3 sandbox.{key} must be {str(want).lower()}"))
    perms = settings.get("permissions") if isinstance(settings.get("permissions"), dict) else {}
    if perms.get("disableBypassPermissionsMode") != "disable":
        out.append(_fail(SETTINGS, 'D3 permissions.disableBypassPermissionsMode must be "disable"'))
    allow = perms.get("allow") if isinstance(perms.get("allow"), list) else []
    for rule in allow:
        if isinstance(rule, str) and "(" not in rule and rule != "Read":
            out.append(_fail(SETTINGS, f"D3 permissions.allow has bare tool rule '{rule}'; "
                                       "it allows every use of the tool"))
    return out


DRIVER = r"""
import importlib.util, json, sys
guard_path, cases = sys.argv[1], json.loads(sys.argv[2])
spec = importlib.util.spec_from_file_location("aidlc_doctor_guard", guard_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps([module.decide(c).get("decision") for c in cases]))
"""
SELFTEST_TIMEOUT = 10


def _selftest(repo: Path) -> list[str]:
    """Run the rendered (possibly tampered) guard in an isolated child process."""
    hooks = repo / ".aidlc" / "hooks"
    push = {"session": "doctor", "call": "1", "tool": "shell",
            "args": {"command": "git push origin main"}, "cwd": str(repo)}
    cases = [(push, "harness.json", "does not deny `git push`"),
             (push, "missing-harness-doctor.json", "does not deny when its harness data is unreadable"),
             ({"tool": "shell", "args": "garbage"}, "harness.json", "does not deny unreadable input")]
    problems = []
    for event, harness, label in cases:
        env = {k: v for k, v in os.environ.items() if k != "AIDLC_HARNESS_FILE"}
        env["AIDLC_HARNESS_FILE"] = str(hooks / harness)
        try:
            run = subprocess.run([sys.executable, "-I", "-B", "-c", DRIVER, str(hooks / "guard.py"),
                                  json.dumps([event])], capture_output=True, text=True,
                                 timeout=SELFTEST_TIMEOUT, env=env, cwd=repo)
        except subprocess.TimeoutExpired:
            return [f"guard self-test timed out after {SELFTEST_TIMEOUT}s"]
        except OSError as exc:
            return [f"guard self-test could not start ({type(exc).__name__})"]
        if run.returncode != 0:
            return [f"guard self-test exited {run.returncode}: {run.stderr.strip()[-200:]}"]
        try:
            decisions = json.loads(run.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return ["guard self-test printed unparseable output"]
        if decisions != ["deny"]:
            problems.append(f"guard {label}")
    return problems


def check_d4(repo: Path, settings: dict) -> list[Finding]:
    out = []
    for event, matcher, phase in (("PreToolUse", PRE_MATCHER, "pre"),
                                  ("PostToolUse", POST_MATCHER, "post")):
        entries = _get(settings, "hooks", event, default=[])
        if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
            out.append(_fail(SETTINGS, f"D4 {event} must have exactly one hook entry"))
            continue
        entry = entries[0]
        if entry.get("matcher") != matcher:
            out.append(_fail(SETTINGS, f"D4 {event} matcher must equal the adapter's '{matcher}' "
                                       f"(found '{entry.get('matcher')}'); tools outside it bypass the guard"))
        hooks = [h for h in entry.get("hooks", []) if isinstance(h, dict)
                 and f"claude_shim.py\" {phase}" in str(h.get("command", ""))]
        if not hooks:
            out.append(_fail(SETTINGS, f"D4 {event} has no claude_shim.py {phase} hook"))
        for hook in hooks:
            if hook.get("onFailure") != "block":
                out.append(_fail(SETTINGS, f"D4 {event} hook must set onFailure: block"))
    missing = [n for n in (*HOOK_FILES, "harness.json") if not (repo / ".aidlc/hooks" / n).is_file()]
    for name in missing:
        out.append(_fail(f".aidlc/hooks/{name}", f"D4 hook file .aidlc/hooks/{name} is missing"))
    if not missing:
        out += [_fail(".aidlc/hooks/guard.py", f"D4 {p}") for p in _selftest(repo)]
    return out


def check_d5(which) -> list[Finding]:
    if not sys.platform.startswith("linux"):
        return []
    return [_fail("", f"D5 {tool} is not on PATH; the sandbox needs it on Linux")
            for tool in ("bwrap", "socat") if not which(tool)]


def check_d6(eff: dict) -> list[Finding]:
    out = [_warn(".aidlc/permissions.yaml",
                 f"D6 allow_add '{e['pattern']}' ({e['kind']}) loosens the baseline: "
                 f"{e.get('reason')} (owner {e.get('owner')})") for e in eff["allow_added"]]
    for key, what in (("network_allow_add", "network access"), ("sandbox_allow_write_add", "sandbox writes")):
        out += [_warn(".aidlc/permissions.yaml",
                      f"D6 {key} '{e['value']}' loosens {what}: {e['reason']} (owner {e['owner']})")
                for e in eff[key]]
    return out


def check_d7(eff: dict, tool_names: dict) -> list[Finding]:
    out = []
    for section in ("allow", "ask", "deny"):
        for name in map_tools(eff[section]["tools"], tool_names)[1]:
            out.append(_warn(".aidlc/config.yaml",
                             f"D7 {section} rule '{name}' has no tool_names mapping and is dropped "
                             f"from the rendered {section} list"))
    return out


def _imports(repo: Path, rel: str) -> list[Finding]:
    path = repo / rel
    if not path.is_file():
        return []
    root = repo.resolve()
    out = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        for token in IMPORT_RE.findall(line):
            token = token.rstrip(".,;:)")
            if "/" not in token and "." not in token:
                continue                       # @team, @handle: not a path
            if token.startswith(("~", "/")):
                out.append(Finding("FAIL", rel, lineno, f"D8 import @{token} resolves outside the repository"))
                continue
            target = (root / token).resolve()
            if root != target and root not in target.parents:
                out.append(Finding("FAIL", rel, lineno, f"D8 import @{token} resolves outside the repository"))
            elif not target.is_file():
                out.append(Finding("WARN", rel, lineno, f"D8 import @{token} does not resolve to a file"))
            else:
                n = len(target.read_text(encoding="utf-8", errors="replace").splitlines())
                if n > IMPORT_FAIL_LINES:
                    out.append(Finding("FAIL", rel, lineno, f"D8 import @{token} is {n} lines "
                                       f"(limit {IMPORT_FAIL_LINES}); imports load into every session"))
                elif n > IMPORT_WARN_LINES:
                    out.append(Finding("WARN", rel, lineno, f"D8 import @{token} is {n} lines "
                                       f"(above {IMPORT_WARN_LINES})"))
    return out


def check_d8(repo: Path) -> list[Finding]:
    out, seen = [], set()
    for rel in ("CLAUDE.md", ".aidlc/claude.md"):
        for f in _imports(repo, rel):
            key = (f.level, f.message)
            if key not in seen:
                seen.add(key)
                out.append(f)
    return out


def check_d9(repo: Path) -> list[Finding]:
    path = repo / ".mcp.json"
    if not path.is_file():
        return []
    try:
        servers = json.loads(path.read_text(encoding="utf-8")).get("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError("mcpServers is not an object")
        ids = {t["id"] for t in load_policy("tool-register")["tools"]}
    except (OSError, ValueError, AttributeError, PolicyError) as exc:
        return [_warn(".mcp.json", f"D9 cannot read MCP servers ({type(exc).__name__}: {exc})")]
    return [_warn(".mcp.json", f"D9 MCP server '{name}' is not in the tool register")
            for name in servers if name not in ids]


def check_d10(claude_version: str | None) -> list[Finding]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", claude_version or "")
    if not match:
        return [_warn("", "D10 cannot determine the Claude Code version")]
    if tuple(int(g) for g in match.groups()) < MIN_CLAUDE:
        return [_fail("", f"D10 Claude Code {match.group(0)} is older than "
                          f"{'.'.join(map(str, MIN_CLAUDE))}; hook onFailure needs it")]
    return []


def check_d11(repo: Path, settings: dict, eff: dict) -> list[Finding]:
    deny = _get(settings, "permissions", "deny", default=[])
    deny_write = _get(settings, "sandbox", "filesystem", "denyWrite", default=[])
    files = _tracked_files(repo)
    out = []
    for entry in eff["protected_paths"]:
        if f"Edit({entry})" not in deny:
            out.append(_fail(SETTINGS, f"D11 protected path '{entry}' has no Edit({entry}) deny rule"))
        if not _is_literal_protected(entry):
            out.append(_warn(SETTINGS, f"D11 {entry}: sandbox denyWrite covers only files tracked at "
                                       "render time (or present and not ignored); new matching files "
                                       "rely on the Edit deny rule, the guard (Edit tools) and the "
                                       "post-check (shell)"))
            continue
        for want in _deny_write(repo, [entry], files):
            if want not in deny_write:
                out.append(_fail(SETTINGS, f"D11 protected path '{entry}' has no sandbox denyWrite "
                                           f"entry '{want}'"))
    return out


def check_d12(repo: Path) -> list[Finding]:
    """The base branch is the trust root for approvals, scope generation and the post-check."""
    try:
        base = base_branch(repo)
    except (HarnessError, ValueError, OSError) as exc:
        return [_fail(".aidlc/config.yaml", f"D12 {exc}")]
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        found = subprocess.run(["git", "rev-parse", "--verify", "-q", f"refs/heads/{base}^{{commit}}"],
                               cwd=repo, env=env, capture_output=True, timeout=SELFTEST_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [_fail(".aidlc/config.yaml", f"D12 cannot check base branch '{base}' ({type(exc).__name__})")]
    if found.returncode != 0:
        return [_fail(".aidlc/config.yaml", f"D12 base branch '{base}' does not exist; create it or set "
                                            "harness.base_branch")]
    return []


def run_doctor(repo: Path, which=shutil.which, claude_version: str | None = None) -> list[Finding]:
    findings = check_d1(repo)
    settings, problems = _settings(repo)
    findings += problems if not any(f.message.startswith("D1 cannot render") for f in findings) else []
    try:
        eff = effective_permissions(repo)
        tool_names = load_config(repo).tool_names
    except (HarnessError, PolicyError, FileNotFoundError, OSError) as exc:
        return findings + [_fail(".aidlc", f"D1 cannot compute the effective permissions: {exc}")]
    if settings is not None:
        findings += check_d2(repo, settings, eff)
        findings += check_d3(settings)
        findings += check_d4(repo, settings)
    findings += check_d5(which)
    findings += check_d6(eff)
    findings += check_d7(eff, tool_names)
    findings += check_d8(repo)
    findings += check_d9(repo)
    findings += check_d10(claude_version)
    findings += check_d12(repo)
    if settings is not None:
        try:
            findings += check_d11(repo, settings, eff)
        except HarnessError as exc:
            findings.append(_fail(SETTINGS, f"D11 cannot compute expected denyWrite entries: {exc}"))
    return findings
