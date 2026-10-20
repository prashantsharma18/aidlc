"""Render the GitHub Actions workflow that mirrors `aidlc ci` (design §8). Rendered only when
.aidlc/config.yaml lists `ci: [github]`; recorded in the generated-file manifest like every other
rendered file, so a hand edit is refused and reported by doctor D1."""
from __future__ import annotations

import re
from pathlib import Path

from .adapters.base import RenderedFile
from .harness import BRANCH_RE
from .paths import CI_WORKFLOW, framework_root
from .policy import load_yaml
from .repo import load_config

TEMPLATE = "core/ci/github/aidlc-verify.yml"
OUTPUT = CI_WORKFLOW


def render_ci(repo: Path) -> list[RenderedFile]:
    try:
        config = load_config(repo)
    except FileNotFoundError:
        return []                                   # the framework repository has no config
    if "github" not in config.ci:
        return []
    base = config.harness.get("base_branch", "main")
    if not isinstance(base, str) or not BRANCH_RE.fullmatch(base):
        raise ValueError(f"harness.base_branch '{base}' is not a valid branch name")
    root = framework_root() / "core" / "ci" / "github"
    setup = load_yaml(root / "setup.yaml").get(config.profile, "") or ""
    text = (root / "aidlc-verify.yml").read_text(encoding="utf-8")
    text = text.replace("{{BASE_BRANCH}}", base).replace("{{SETUP}}\n", setup)
    if "{{" in re.sub(r"\$\{\{.*?\}\}", "", text):
        raise ValueError(f"{TEMPLATE}: a template token was not replaced")
    return [RenderedFile(OUTPUT, text, source=TEMPLATE)]
