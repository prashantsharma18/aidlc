"""GitHub Copilot adapter: an extension point only (design §4.3, decision D8)."""
from __future__ import annotations

from pathlib import Path

from .base import AdapterNotImplemented, RenderedFile

_MSG = ("the Copilot adapter is an extension point and is not built yet; "
        "see docs/adapters/copilot.md for the mapping to implement")


class CopilotAdapter:
    name = "copilot"
    managed_dirs: tuple[str, ...] = ()

    def render_rules(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)

    def render_folder_rules(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)

    def render_permissions(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)

    def render_hooks(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)

    def render_skills(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)

    def render_agents(self, repo: Path) -> list[RenderedFile]:
        raise AdapterNotImplemented(_MSG)
