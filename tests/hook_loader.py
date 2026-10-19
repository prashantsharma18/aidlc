"""Load a core/hooks script as a module (hooks are not part of the aidlc package)."""
import importlib.util
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1] / "core" / "hooks"


def load_hook(name: str):
    spec = importlib.util.spec_from_file_location(f"aidlc_hook_{name}", HOOKS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
