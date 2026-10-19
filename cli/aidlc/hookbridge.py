"""Load the framework's hook modules (core/hooks) into the CLI process without side effects.

The hooks are standalone standard-library scripts that import each other by name (`import guard`).
This loader gives the CLI the same code the hooks run, so a check and a hook never disagree. It
restores sys.path and sys.modules["guard"] afterwards and never writes __pycache__."""
from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from types import ModuleType, SimpleNamespace

from .paths import framework_root


def _load(name: str, alias: str) -> ModuleType:
    path = framework_root() / "core" / "hooks" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load hook module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=1)
def hooks() -> SimpleNamespace:
    """The guard and post_check modules, loaded once."""
    saved_path, saved_guard = list(sys.path), sys.modules.get("guard")
    saved_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        guard = _load("guard", "guard")
        sys.modules["guard"] = guard              # post_check does `import guard`
        post_check = _load("post_check", "aidlc_post_check")
    finally:
        sys.path[:] = saved_path
        if saved_guard is None:
            sys.modules.pop("guard", None)
        else:
            sys.modules["guard"] = saved_guard
        sys.dont_write_bytecode = saved_bytecode
    return SimpleNamespace(guard=guard, post_check=post_check)
