"""The effective harness for one repository: the framework baseline (core/policy/permissions.yaml)
narrowed by the repository (.aidlc/permissions.yaml). A repository can add denials and asks
and remove allows; the only loosening (allow_add) needs a reason and an owner and is reported
by `aidlc doctor`. Deny always beats allow (guide 3 step 3)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import yaml

from . import __version__
from .paths import framework_root
from .policy import PolicyError, load_policy, load_yaml
from .repo import load_config

KINDS = ("read", "edit", "shell", "tools")


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
    path = repo / ".aidlc" / "permissions.yaml"
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
    base["network_allow_add"] = list(n.get("network_allow_add", []))
    base["sandbox_allow_write_add"] = list(n.get("sandbox_allow_write_add", []))
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


def harness_data(repo: Path) -> dict:
    eff = effective_permissions(repo)
    tool_names = load_config(repo).tool_names
    data = {
        "protected_paths": eff["protected_paths"],
        "shell_deny": eff["deny"]["shell"],
        "tool_deny": map_tools(eff["deny"]["tools"], tool_names)[0],
        "tool_ask": map_tools(eff["ask"]["tools"], tool_names)[0],
    }
    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:12]
    return {"version": f"{__version__}+{digest}", **data}
