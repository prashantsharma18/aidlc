"""Adapter registry."""
from __future__ import annotations

from .base import Adapter
from .claude_code import ClaudeCodeAdapter
from .copilot import CopilotAdapter

_ADAPTERS: dict[str, type] = {"claude-code": ClaudeCodeAdapter, "copilot": CopilotAdapter}


def get_adapter(name: str) -> Adapter:
    try:
        return _ADAPTERS[name]()
    except KeyError:
        raise ValueError(f"unknown tool '{name}'; choose from {', '.join(_ADAPTERS)}") from None


def adapter_names() -> list[str]:
    return list(_ADAPTERS)
