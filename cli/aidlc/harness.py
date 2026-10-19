"""The effective harness for one repository: the framework baseline (core/policy/permissions.yaml)
narrowed by the repository (.aidlc/permissions.yaml). A repository can add denials and asks
and remove allows. The loosenings (allow_add, network_allow_add, sandbox_allow_write_add) each
need a reason and an owner and are reported by `aidlc doctor`; sandbox write paths that would
reach the harness, the user's executables or the system are refused. Deny always beats allow
(guide 3 step 3)."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import posixpath
import re
from pathlib import Path

import jsonschema
import yaml

from . import __version__
from .paths import framework_root, safe_target
from .policy import PolicyError, load_policy, load_yaml
from .repo import load_config

KINDS = ("read", "edit", "shell", "tools")
BRANCH_RE = re.compile(r"(?!-)[A-Za-z0-9._/-]+")
# Sandbox write grants a repository may never add: the agent could then rewrite its harness
# (~/.claude, ~/.aidlc), plant executables on PATH, or write system files. An ancestor of one of
# these (for example "~" or "/") is refused too.
REFUSED_WRITE = ("~/.claude", "~/.aidlc", "~/.local/bin", "~/bin", "/usr", "/bin")


class HarnessError(Exception):
    """The repository's harness configuration is invalid."""


def _dedupe(items: list[str]) -> list[str]:
    seen, out = set(), []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def load_narrowing(repo: Path) -> dict:
    try:
        path = safe_target(repo, ".aidlc/permissions.yaml")   # refuses a symlinked file or folder
    except ValueError as exc:
        raise HarnessError(f"{exc}; keep the narrowing file inside the repository") from exc
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8").lstrip("﻿")
        data = yaml.safe_load(text) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise HarnessError(f"{path}: cannot read: {exc}") from exc
    schema = json.loads((framework_root() / "core" / "schemas" /
                         "repo-permissions.schema.json").read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(data),
                    key=lambda e: list(map(str, e.absolute_path)))
    if errors:
        raise HarnessError("\n".join(
            f"{path}: {'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in errors))
    return data


def _absolute(value: str) -> str | None:
    """A sandbox path as an absolute POSIX path ('~' expanded); None for a repository-relative one."""
    if value.startswith("~"):
        value = Path.home().as_posix() + "/" + value[1:].lstrip("/")
    return posixpath.normpath("/" + value.lstrip("/")) if value.startswith("/") else None


def _covers(outer: str, inner: str) -> bool:
    return outer == inner or inner.startswith(outer.rstrip("/") + "/")


def check_write_grant(value: str) -> None:
    """Raise HarnessError for a sandbox_allow_write_add value that reaches a refused location:
    one of REFUSED_WRITE, anything under it, or any ancestor of it (such as '~' or '/')."""
    if ".." in value.replace("\\", "/").split("/"):
        raise HarnessError(f"sandbox_allow_write_add '{value}' refused: '..' is not allowed")
    if "$" in value or "\\" in value or (value.startswith("~") and value != "~" and not value.startswith("~/")):
        raise HarnessError(f"sandbox_allow_write_add '{value}' refused: write a literal path "
                           "('~/...' or '/...'), not a variable, '~user' or a backslash")
    prefix = re.split(r"[*?\[]", value, maxsplit=1)[0]          # a glob: judge its static prefix
    path = _absolute(prefix)
    if path is None:
        return
    if prefix != value and not prefix.endswith("/"):
        path = posixpath.dirname(path)                           # '~/.c*' starts in '~'
    candidates = {path, os.path.realpath(path)}                  # a symlink to a refused place
    for refused in REFUSED_WRITE:
        target = _absolute(refused)
        targets = {target, os.path.realpath(target)}
        if any(_covers(p, t) or _covers(t, p) for p in candidates for t in targets):
            raise HarnessError(f"sandbox_allow_write_add '{value}' refused: it would let the agent "
                               f"write to {refused} (harness, executables or system files)")


def effective_permissions(repo: Path) -> dict:
    try:
        base = copy.deepcopy(load_policy("permissions"))
    except PolicyError as exc:
        raise HarnessError(str(exc)) from exc
    base.pop("meta", None)
    n = load_narrowing(repo)
    for kind in KINDS:
        for section in ("deny", "ask", "allow"):
            base.setdefault(section, {}).setdefault(kind, [])
        base["deny"][kind] += n.get("deny_add", {}).get(kind, [])
        if kind != "read":
            base["ask"][kind] += n.get("ask_add", {}).get(kind, [])
        removed = set(n.get("allow_remove", {}).get(kind, []))
        base["allow"][kind] = [p for p in base["allow"][kind] if p not in removed]
    base["secret_paths"] += n.get("secret_paths_add", [])
    base["deny"]["read"] += n.get("secret_paths_add", [])
    base["protected_paths"] += n.get("protected_paths_add", [])
    base["deny"]["edit"] += n.get("protected_paths_add", [])
    base["allow_added"] = []
    for entry in n.get("allow_add", []):
        base["allow"][entry["kind"]].append(entry["pattern"])
        base["allow_added"].append(dict(entry))
    base["network_allow_add"] = [dict(e) for e in n.get("network_allow_add", [])]
    base["sandbox_allow_write_add"] = [dict(e) for e in n.get("sandbox_allow_write_add", [])]
    for entry in base["sandbox_allow_write_add"]:
        check_write_grant(entry["value"])
    for section in ("deny", "ask", "allow"):
        for kind in KINDS:
            base[section][kind] = _dedupe(base[section][kind])
    base["secret_paths"] = _dedupe(base["secret_paths"])
    base["protected_paths"] = _dedupe(base["protected_paths"])
    return base


def map_tools(names: list[str], tool_names: dict[str, str]) -> tuple[list[str], list[str]]:
    mapped, unmapped = [], []
    for name in names:
        if name in tool_names:
            mapped.append(tool_names[name])
        else:
            unmapped.append(name)
    return mapped, unmapped


def base_branch(repo: Path) -> str:
    """harness.base_branch from .aidlc/config.yaml: the branch approvals and checks trust."""
    base = load_config(repo).harness.get("base_branch")
    if not isinstance(base, str) or not BRANCH_RE.fullmatch(base):
        raise HarnessError(f"{repo / '.aidlc/config.yaml'}: harness.base_branch must be a branch "
                           f"name, got {base!r}")
    return base


def harness_data(repo: Path) -> dict:
    eff = effective_permissions(repo)
    tool_names = load_config(repo).tool_names
    data = {
        "base_branch": base_branch(repo),
        "protected_paths": eff["protected_paths"],
        "shell_deny": eff["deny"]["shell"],
        "tool_deny": map_tools(eff["deny"]["tools"], tool_names)[0],
        "tool_ask": map_tools(eff["ask"]["tools"], tool_names)[0],
    }
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    return {"version": f"{__version__}+{digest}", **data}
