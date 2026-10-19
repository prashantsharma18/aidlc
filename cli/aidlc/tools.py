"""Pinned external tools (ADR 0001; guide 13.9). Each has an exact version, the SHA-256 of its
release asset and an entry in core/policy/tool-register.yaml. `aidlc tools install` downloads,
verifies and installs them for people and CI. It never runs inside an agent session: the sandbox
has no route to the download host and cannot write ~/.aidlc."""
from __future__ import annotations

import hashlib
import io
import os
import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .policy import load_policy

TOOLS_DIR_ENV = "AIDLC_TOOLS_DIR"
MAX_DOWNLOAD = 200 * 1024 * 1024
CHUNK = 1024 * 1024
TIMEOUT_S = 120


class ToolError(Exception):
    """A tool cannot be found, downloaded or verified."""


def tools_dir() -> Path:
    """AIDLC_TOOLS_DIR, else <AIDLC_HOME_DIR or ~/.aidlc>/bin (the same home scope.py resolves)."""
    override = os.environ.get(TOOLS_DIR_ENV)
    if override:
        return Path(override).expanduser()
    return Path(os.environ.get("AIDLC_HOME_DIR") or "~/.aidlc").expanduser() / "bin"


def platform_tag() -> str:
    """The register's platform name for this machine, e.g. linux-x86_64 (WSL2 and Ubuntu)."""
    system = "linux" if sys.platform.startswith("linux") else sys.platform
    machine = platform.machine().lower()
    if machine == "amd64":
        machine = "x86_64"
    return f"{system}-{machine}"


def artifact(name: str, register: dict | None = None) -> dict:
    register = register if register is not None else load_policy("tool-register")
    for tool in register["tools"]:
        if tool["id"] != name:
            continue
        tag = platform_tag()
        for art in tool.get("artifacts", []):
            if art["platform"] == tag:
                return {**art, "version": tool.get("version", "")}
        raise ToolError(f"{name} has no pinned artifact for {tag} in core/policy/tool-register.yaml")
    raise ToolError(f"{name} is not in core/policy/tool-register.yaml")


def which_tool(name: str, pinned_only: bool = False) -> Path | None:
    """The pinned install first (what `aidlc tools install` verified), then PATH unless pinned_only.
    Trusted CI uses pinned_only=True: an unverified binary on PATH never judges a change."""
    pinned = tools_dir() / name
    if pinned.is_file() and os.access(pinned, os.X_OK):
        return pinned
    if pinned_only:
        return None
    found = shutil.which(name)
    return Path(found) if found else None


def _require_https(url: str) -> None:
    if not url.startswith("https://"):
        raise ToolError(f"refusing a non-https download: {url}")


def _download(url: str, opener) -> tuple[bytes, str]:
    """The body (read in chunks, capped) and its SHA-256, hashed while reading."""
    _require_https(url)
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0
    with opener(url, timeout=TIMEOUT_S) as response:
        geturl = getattr(response, "geturl", None)
        if geturl is not None:
            _require_https(geturl())  # a redirect must not leave https
        while True:
            chunk = response.read(CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD:
                raise ToolError(f"{url}: larger than {MAX_DOWNLOAD // (1024 * 1024)} MB")
            digest.update(chunk)
            chunks.append(chunk)
    return b"".join(chunks), digest.hexdigest()


def _member(data: bytes, member: str) -> bytes:
    """The bytes of one regular-file member. Never extracts to disk."""
    if member.startswith("/") or ".." in Path(member).parts:
        raise ToolError(f"unsafe member name '{member}'")
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            try:
                info = tar.getmember(member)
            except KeyError:
                raise ToolError(f"archive has no member '{member}'") from None
            if not info.isfile():
                raise ToolError(f"archive member '{member}' is not a regular file")
            handle = tar.extractfile(info)
            if handle is None:
                raise ToolError(f"archive member '{member}' cannot be read")
            return handle.read()
    except tarfile.TarError as exc:
        raise ToolError(f"archive cannot be read: {exc}") from None


def install(name: str, dest: Path | None = None, register: dict | None = None,
            opener=urllib.request.urlopen) -> Path:
    """Download, verify the SHA-256 before writing anything, and install atomically (0755)."""
    art = artifact(name, register)
    data, digest = _download(art["url"], opener)
    if digest != art["sha256"]:
        raise ToolError(f"{name}: checksum mismatch (expected {art['sha256']}, got {digest}); nothing installed")
    payload = data if art["kind"] == "binary" else _member(data, art["member"])
    dest = dest or tools_dir()
    if dest.is_symlink():
        raise ToolError(f"{dest} is a symlink; refusing to install through it")
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    if target.is_symlink():
        raise ToolError(f"{target} is a symlink; refusing to replace it")
    fd, tmp = tempfile.mkstemp(dir=dest, prefix=f".{name}-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
        os.chmod(tmp, 0o755)
        os.replace(tmp, target)
    except BaseException:
        if os.path.lexists(tmp):
            os.unlink(tmp)
        raise
    return target
