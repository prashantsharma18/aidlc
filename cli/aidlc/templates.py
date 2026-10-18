"""Stage-artefact templates: Markdown with YAML front matter declaring id, title, stage,
guide sections and the {{FIELDS}} the body uses."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from .paths import framework_root

_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_VAR = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
_REQUIRED = ("id", "title", "stage", "guide", "fields")


class TemplateError(Exception):
    """A template is malformed, missing a value, or would overwrite a file."""


@dataclass(frozen=True)
class Template:
    id: str
    title: str
    stage: str
    guide: list[str]
    fields: list[str]
    body: str
    path: Path


def parse_front_matter(text: str, path: Path) -> tuple[dict, str]:
    text = text.lstrip("﻿").replace("\r\n", "\n")
    match = _FRONT.match(text)
    if not match:
        raise TemplateError(f"{path}: missing front matter")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise TemplateError(f"{path}: invalid front matter: {exc}") from exc
    if not isinstance(meta, dict):
        raise TemplateError(f"{path}: front matter must be a mapping")
    return meta, text[match.end():]


def _dir(root: Path | None) -> Path:
    return (root or framework_root()) / "core" / "templates"


def _from_path(path: Path) -> Template:
    meta, body = parse_front_matter(path.read_text(encoding="utf-8"), path)
    for key in _REQUIRED:
        if key not in meta:
            raise TemplateError(f"{path}: front matter lacks '{key}'")
    if meta["id"] != path.stem:
        raise TemplateError(f"{path}: id '{meta['id']}' does not match file name")
    undeclared = set(_VAR.findall(body)) - set(meta["fields"])
    if undeclared:
        raise TemplateError(f"{path}: body uses undeclared fields {sorted(undeclared)}")
    return Template(meta["id"], meta["title"], meta["stage"], list(meta["guide"]),
                    list(meta["fields"]), body, path)


def load_template(tid: str, root: Path | None = None) -> Template:
    path = _dir(root) / f"{tid}.md"
    if not path.is_file():
        raise TemplateError(f"unknown template '{tid}' (looked for {path})")
    return _from_path(path)


def list_templates(root: Path | None = None) -> list[Template]:
    return [_from_path(p) for p in sorted(_dir(root).glob("*.md"))]


def render(t: Template, values: dict[str, str]) -> str:
    missing = [f for f in t.fields if f not in values]
    if missing:
        raise TemplateError(f"template '{t.id}' needs values for: {', '.join(missing)}")
    body = _VAR.sub(lambda m: values[m.group(1)], t.body)
    return f"<!-- aidlc template: {t.id} -->\n{body}"


def write_new(t: Template, values: dict[str, str], out: Path) -> Path:
    if out.exists():
        raise TemplateError(f"{out} exists; refusing to overwrite")
    text = render(t, values)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out
