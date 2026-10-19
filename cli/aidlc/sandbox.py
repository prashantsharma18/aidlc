"""Run the change's own commands in a bubblewrap sandbox (design §8; independent plan reviews,
2026-10-19). `aidlc ci` loads its judges and reads its evidence first; this keeps the change's
install script and tests, written by an agent, away from anything that could alter the verdict:
- the filesystem is read-only; /tmp and /run are empty (no host sockets: Docker, D-Bus);
- $HOME is a private per-run directory, so secrets, ~/.aidlc and the person's settings are
  invisible; toolchains under home (framework profile data) are bound back read-only;
- only the disposable checkout is writable, and its .git and the common git directory are bound
  back read-only on top of it, so the change cannot redirect or reconfigure git;
- the environment is cleared except for an allow-list;
- there is no network except for the install step;
- the process tree has its own PID namespace and dies with its parent."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .paths import framework_root
from .policy import load_yaml

NETWORK_STEPS = ("install", "restore")
BASE_ENV = ("PATH", "LANG", "LC_ALL", "TERM")
# Only the install step has a network; it may need the organisation's proxy and CA bundle.
NETWORK_ENV = ("HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy",
               "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE")


class SandboxError(Exception):
    """The sandbox cannot be used (bwrap missing or refused)."""


def bwrap_path() -> str | None:
    return shutil.which("bwrap")


def available() -> bool:
    """True only if a sandbox actually starts here. The probe uses the real argv builder, so it
    exercises the flags a run would use. Any failure means False."""
    if not bwrap_path():
        return False
    tmp = Path(tempfile.mkdtemp(prefix="aidlc-probe-"))
    try:
        dirs = {name: tmp / name for name in ("work", "private", "home")}
        for d in dirs.values():
            d.mkdir()
        box = Sandbox(work=dirs["work"], private_home=dirs["private"], home=dirs["home"])
        probe = subprocess.run(box.argv("true", "probe"), capture_output=True, timeout=10)
        return probe.returncode == 0
    except (OSError, subprocess.SubprocessError, SandboxError):
        return False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _profile(profile: str) -> dict:
    data = load_yaml(framework_root() / "core" / "context" / "profiles.yaml")
    if not isinstance(data, dict) or not isinstance(data.get(profile), dict):
        raise SandboxError(f"profile '{profile}' is not in core/context/profiles.yaml")
    return data[profile]


def _string_list(profile: str, key: str) -> list[str]:
    value = _profile(profile).get(key)
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SandboxError(f"profile '{profile}': {key} must be a list of strings")
    return value


def toolchain_paths(profile: str) -> list[Path]:
    """Toolchain directories strictly under home to bind read-only (framework data, never the branch's)."""
    home = Path.home()
    paths = []
    for raw in _string_list(profile, "ci_sandbox_read"):
        path = Path(os.path.normpath(Path(raw).expanduser()))
        if not raw or not path.is_absolute() or path == home or home not in path.parents:
            raise SandboxError(f"profile '{profile}': ci_sandbox_read entry '{raw}' must be under {home}")
        paths.append(path)
    return paths


def toolchain_env(profile: str) -> list[str]:
    """Extra environment names a toolchain needs inside the sandbox (framework data)."""
    return _string_list(profile, "ci_sandbox_env")


# The root is an allow-list. A whole-root read-only bind would leave unix sockets reachable
# (Docker Desktop and proxy sockets under /mnt/wsl) and expose the real home (/mnt/wslg, /mnt/c).
ROOT_BINDS = ("/usr", "/etc", "/opt")
ROOT_LINKS = ("/bin", "/sbin", "/lib", "/lib64", "/lib32", "/libx32")


def _root_args() -> list[str]:
    args: list[str] = []
    for path in ROOT_BINDS:
        if os.path.isdir(path):
            args += ["--ro-bind", path, path]
    for path in ROOT_LINKS:
        if os.path.islink(path):
            args += ["--symlink", os.readlink(path), path]
        elif os.path.isdir(path):
            args += ["--ro-bind", path, path]
    return args


def _resolver_file() -> str | None:
    """The file /etc/resolv.conf resolves to. Only the file is bound, never its directory."""
    real = os.path.realpath("/etc/resolv.conf")
    return real if os.path.isfile(real) else None


@dataclass
class Sandbox:
    work: Path                                  # the only writable tree
    private_home: Path                          # per-run home, discarded after the run
    home: Path = field(default_factory=Path.home)
    git_dir: Path | None = None                 # the repository's common .git, read-only
    readable: list[Path] = field(default_factory=list)
    env_names: list[str] = field(default_factory=list)   # profile ci_sandbox_env

    def argv(self, command: str, step: str) -> list[str]:
        exe = bwrap_path()
        if not exe:
            raise SandboxError("bwrap is not installed (sudo apt install bubblewrap)")
        network = step in NETWORK_STEPS          # any other step name, even an empty one, gets no network
        for label, path in (("work tree", self.work), ("private home", self.private_home),
                            ("home", self.home), ("git directory", self.git_dir)):
            if path is not None and not Path(path).exists():
                raise SandboxError(f"the {label} {path} does not exist; refusing to run without it")
        args = [exe, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts"]
        args += _root_args()
        args += ["--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
        resolver = _resolver_file() if network else None
        if resolver is not None:
            args += ["--ro-bind", resolver, resolver]
        args += ["--bind", str(self.private_home), str(self.home)]
        for path in self.readable:
            if path.exists():
                args += ["--ro-bind", str(path), str(path)]
        args += ["--bind", str(self.work), str(self.work)]
        gitlink = self.work / ".git"
        if gitlink.exists() or gitlink.is_symlink():
            args += ["--ro-bind", str(gitlink), str(gitlink)]        # on top of the writable work tree
        if self.git_dir is not None and self.git_dir.resolve() != gitlink.resolve():
            args += ["--ro-bind", str(self.git_dir), str(self.git_dir)]
        args += ["--chdir", str(self.work), "--clearenv"]
        for name in (*BASE_ENV, *self.env_names, *(NETWORK_ENV if network else ())):
            if name in os.environ:
                args += ["--setenv", name, os.environ[name]]
        args += ["--setenv", "HOME", str(self.home), "--setenv", "TMPDIR", "/tmp", "--setenv", "CI", "true"]
        if not network:
            args.append("--unshare-net")
        return args + ["/bin/sh", "-c", command]
