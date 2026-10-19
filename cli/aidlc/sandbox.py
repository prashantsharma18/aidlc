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
    """True only if a sandbox actually starts here (bwrap present and user namespaces allowed)."""
    exe = bwrap_path()
    if not exe:
        return False
    try:
        probe = subprocess.run([exe, "--die-with-parent", "--unshare-net", "--ro-bind", "/", "/",
                                "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/run", "true"],
                               capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0


def _profile(profile: str) -> dict:
    return load_yaml(framework_root() / "core" / "context" / "profiles.yaml").get(profile) or {}


def toolchain_paths(profile: str) -> list[Path]:
    """Toolchain directories under home to bind read-only (framework data, never the branch's)."""
    return [Path(p).expanduser() for p in _profile(profile).get("ci_sandbox_read", [])]


def toolchain_env(profile: str) -> list[str]:
    """Extra environment names a toolchain needs inside the sandbox (framework data)."""
    return list(_profile(profile).get("ci_sandbox_env", []))


def _resolver_dir() -> Path | None:
    """The directory /etc/resolv.conf resolves into, when that is under /run (systemd-resolved)."""
    target = Path("/etc/resolv.conf").resolve()
    return target.parent if str(target).startswith("/run/") and target.exists() else None


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
        args = [exe, "--die-with-parent", "--new-session", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
                "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run"]
        resolver = _resolver_dir() if network else None
        if resolver is not None:
            args += ["--ro-bind", str(resolver), str(resolver)]
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
