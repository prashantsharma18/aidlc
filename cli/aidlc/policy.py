"""Load YAML policies and validate them. Every policy has a `meta` block (owner,
review date, guide sections) and its own JSON Schema in core/schemas/."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from .paths import framework_root


class PolicyError(Exception):
    """A policy cannot be read or does not match its schema."""


def load_yaml(path: Path) -> Any:
    try:
        text = path.read_text(encoding="utf-8").lstrip("﻿")
        data = yaml.safe_load(text)
    except OSError as exc:
        raise PolicyError(f"{path}: cannot read: {exc}") from exc
    except yaml.YAMLError as exc:
        # The problem and its position only: PyYAML's own message quotes the offending line, and the
        # file may be a link to something it should never print (a host secret).
        mark = getattr(exc, "problem_mark", None)
        where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark is not None else ""
        raise PolicyError(f"{path}: cannot read: {getattr(exc, 'problem', None) or type(exc).__name__}{where}") from exc
    if data is None:
        raise PolicyError(f"{path}: empty")
    return data


def _schema(root: Path, name: str) -> dict:
    path = root / "core" / "schemas" / f"{name}.schema.json"
    if not path.is_file():
        raise PolicyError(f"no schema {path.name} for policy '{name}'")
    return json.loads(path.read_text(encoding="utf-8"))


def _errors(schema: dict, data: Any, label: str) -> list[str]:
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(map(str, e.absolute_path))):
        where = "/".join(str(p) for p in err.absolute_path) or "<root>"
        out.append(f"{label}: {where}: {err.message}")
    return out


def _check(root: Path, name: str, data: Any, path: Path) -> list[str]:
    label = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
    if not isinstance(data, dict) or "meta" not in data:
        return [f"{label}: <root>: 'meta' is a required property"]
    problems = _errors(_schema(root, "meta"), data["meta"], f"{label} meta")
    problems += _errors(_schema(root, name), data, label)
    if isinstance(data["meta"], dict) and data["meta"].get("id") not in (None, f"policy-{name}"):
        problems.append(f"{label}: meta/id: expected 'policy-{name}'")
    return problems


def load_policy(name: str, root: Path | None = None) -> dict:
    root = root or framework_root()
    path = root / "core" / "policy" / f"{name}.yaml"
    data = load_yaml(path)
    problems = _check(root, name, data, path)
    if problems:
        raise PolicyError("\n".join(problems))
    return data


def validate_all(root: Path | None = None) -> list[str]:
    root = root or framework_root()
    problems: list[str] = []
    paths = sorted((root / "core" / "policy").glob("*.yaml"))
    if not paths:
        return [f"no policies found under {root / 'core' / 'policy'}"]
    for path in paths:
        name = path.stem
        try:
            problems += _check(root, name, load_yaml(path), path)
        except PolicyError as exc:
            problems.append(f"{path.name}: {exc}")
    return problems
