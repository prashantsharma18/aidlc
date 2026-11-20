#!/usr/bin/env python3
"""The consumer's contract pin (aidlc ADR 0022; change list F9). A consumer keeps a read-only copy of each provider's
published contract in contracts/<provider>/, beside a SOURCE file that names where the copy came from:

    repository: <git URL of the provider repository>
    tag:        api-v<MAJOR.MINOR.PATCH>
    commit:     <the full commit the tag named when the copy was taken>
    path:       <the contract's path in the provider repository>
    sha256:     <the copy's sha256>

    python3 scripts/check_contract_pin.py [--root DIR]            every copy matches its SOURCE (offline; CI runs it)
    python3 scripts/check_contract_pin.py --online [--root DIR]   also: the tag still names that commit, and the
                                                                  file there hashes the same
    python3 scripts/check_contract_pin.py --update <provider> <tag> [--repository URL --path PATH] [--root DIR]

--update fetches one published version, named exactly (never "latest"), and rewrites the copy and SOURCE; commit
both in a slice whose MAY CHANGE names contracts/<provider>/**, in a reviewed pull request. --repository and --path
are needed the first time only. Exit 0 clean, 1 problems, 2 a usage error. Standard library only; git fetches, with
the credentials it already has."""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_contract_version import TAG, info_version, semver  # noqa: E402

KEYS = ("repository", "tag", "commit", "path", "sha256")
PROVIDER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
HOST_PATH = r"[A-Za-z0-9][A-Za-z0-9._~%@:+/-]*"
REPOSITORY = re.compile(rf"(https|ssh)://{HOST_PATH}|git@[A-Za-z0-9][A-Za-z0-9.-]*:[A-Za-z0-9._~%+/][A-Za-z0-9._~%+/-]*"
                        rf"|/[A-Za-z0-9._~%+@:/-]+")
GIT_TIMEOUT = 120
RUN_TIMEOUT = 300


def read_source(text: str) -> dict[str, str]:
    """The key: value lines of a SOURCE file; a key written twice raises ValueError."""
    found = {}
    for line in text.splitlines():
        m = re.match(r"^([a-z0-9]+):\s*(\S.*?)\s*$", line)
        if m:
            if m.group(1) in found:
                raise ValueError(f"{m.group(1)} appears twice")
            found[m.group(1)] = m.group(2)
    return found


def source_text(fields: dict[str, str]) -> str:
    return "".join(f"{key + ':':<12}{fields[key]}\n" for key in KEYS)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def copy_of(folder: Path, path: str) -> Path:
    return folder / PurePosixPath(path).name


def load_source(folder: Path) -> dict[str, str] | str:
    """The fields of folder/SOURCE, or why it cannot be read."""
    try:
        return read_source((folder / "SOURCE").read_text(encoding="utf-8"))
    except ValueError as error:  # includes UnicodeDecodeError
        if isinstance(error, UnicodeDecodeError):
            return f"contracts/{folder.name}/SOURCE: cannot be read (UnicodeDecodeError); restore it or run --update"
        return f"contracts/{folder.name}/SOURCE: {error}; one line per key"
    except OSError as error:
        return f"contracts/{folder.name}/SOURCE: cannot be read ({type(error).__name__}); restore it or run --update"


def repository_problem(repository: str) -> str | None:
    """Why a repository value is not safe to hand to git, or None. It comes from SOURCE or the command line, so it
    is data: only https, ssh, scp-like git@host:path and an absolute local path are allowed, with no whitespace or
    control character, and nothing git could read as an option."""
    if repository.startswith("-") or re.search(r"[\s\x00-\x1f\x7f]", repository) or "::" in repository:
        return f"repository {repository!r} is not a plain git URL or absolute path"
    if not REPOSITORY.fullmatch(repository):
        return (f"repository {repository!r} must be https://..., ssh://..., git@host:path or an absolute local "
                f"path")
    return None


def offline_problems(folder: Path) -> list[str]:
    """The copy in contracts/<provider>/ is exactly the published version its SOURCE names."""
    rel = f"contracts/{folder.name}"
    if not (folder / "SOURCE").is_file():
        return [f"{rel}: no SOURCE naming the repository, tag, commit, path and sha256 of the copy"]
    fields = load_source(folder)
    if isinstance(fields, str):
        return [fields]
    missing = [key for key in KEYS if key not in fields]
    if missing:
        return [f"{rel}/SOURCE: {', '.join(missing)} missing"]
    problems = []
    unsafe = repository_problem(fields["repository"])
    if unsafe:
        problems.append(f"{rel}/SOURCE: {unsafe}")
    tag = TAG.match(fields["tag"])
    if not tag:
        problems.append(f"{rel}/SOURCE: {fields['tag']} is not a published version (api-v<MAJOR.MINOR.PATCH>)")
    if not re.fullmatch(r"[0-9a-f]{40}", fields["commit"]):
        problems.append(f"{rel}/SOURCE: commit must be the full 40-character commit")
    copy = copy_of(folder, fields["path"])
    if not copy.is_file():
        return problems + [f"{rel}: no {copy.name} beside SOURCE"]
    data = copy.read_bytes()
    if sha256(data) != fields["sha256"].lower():
        problems.append(f"{rel}/{copy.name}: differs from the copy SOURCE names (sha256); the copy is read-only: "
                        f"change it with --update, in its own pull request")
    elif tag and info_version(data.decode("utf-8", errors="replace")) != tag.group(1):
        problems.append(f"{rel}/{copy.name}: info.version is {info_version(data.decode('utf-8', errors='replace'))!r}, "
                        f"but SOURCE pins {fields['tag']}")
    return problems


def fetch(repository: str, tag: str, path: str, deadline: float | None = None) -> tuple[str, bytes] | str:
    """(the commit the tag names, the contract's bytes there), or why they cannot be read. Git runs without a
    credential prompt and with only the https, ssh and file transports, and every git call shares one deadline
    (a time.monotonic() value; two minutes from now when none is given)."""
    unsafe = repository_problem(repository)
    if unsafe or not TAG.match(tag):
        return f"cannot fetch {tag}: {unsafe or 'not a published version'}"
    deadline = time.monotonic() + GIT_TIMEOUT if deadline is None else deadline
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "https:ssh:file"}
    with tempfile.TemporaryDirectory() as tmp:
        def run(*args: str, text: bool = True) -> subprocess.CompletedProcess:
            left = deadline - time.monotonic()
            if left <= 0:
                raise subprocess.TimeoutExpired("git", 0)
            return subprocess.run(["git", "-C", tmp, *args], capture_output=True, text=text, env=env,
                                  stdin=subprocess.DEVNULL, timeout=min(left, GIT_TIMEOUT))
        try:
            run("init", "-q")
            got = run("fetch", "-q", "--depth", "1", "--no-tags", "--", repository, f"refs/tags/{tag}:refs/tags/{tag}")
            if got.returncode != 0:
                return f"cannot fetch {tag} from {repository}: {got.stderr.strip()[:200]}"
            named = run("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
            commit = named.stdout.strip()
            if named.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", commit):
                return f"cannot fetch {tag} from {repository}: the tag names no commit"
            blob = run("show", f"refs/tags/{tag}:{path}", text=False)
        except subprocess.TimeoutExpired:
            return f"cannot fetch {tag} from {repository}: timed out"
        except OSError as error:
            return f"cannot fetch {tag} from {repository}: {error}"
        if blob.returncode != 0:
            return f"{tag} in {repository} has no {path}"
        return commit, blob.stdout


def online_problems(folder: Path, deadline: float | None = None) -> list[str]:
    """The tag still names the commit SOURCE recorded, and the file there is the copy: a published version never
    changes."""
    fields = load_source(folder)
    if isinstance(fields, str):
        return [fields]
    got = fetch(fields["repository"], fields["tag"], fields["path"], deadline)
    if isinstance(got, str):
        return [f"contracts/{folder.name}: {got}"]
    commit, data = got
    if commit != fields["commit"]:
        return [f"contracts/{folder.name}: {fields['tag']} now names {commit[:12]}, not {fields['commit'][:12]}: "
                f"a published version moved; ask the provider"]
    if sha256(data) != fields["sha256"].lower():
        return [f"contracts/{folder.name}: {fields['path']} at {fields['tag']} does not hash to SOURCE's sha256"]
    return []


def write_pair(folder: Path, copy: Path, data: bytes, source: bytes) -> None:
    """Writes the copy and SOURCE as one unit: both go to temporary files first, then the copy and SOURCE are
    renamed into place. When anything fails, the previous copy and SOURCE are restored and the temporaries removed."""
    made = not folder.exists()
    folder.mkdir(parents=True, exist_ok=True)
    temps, previous = [], copy.read_bytes() if copy.is_file() else None
    try:
        for target, content in ((copy, data), (folder / "SOURCE", source)):
            handle, name = tempfile.mkstemp(dir=folder, prefix=".pin-")
            temps.append(Path(name))
            with os.fdopen(handle, "wb") as out:
                out.write(content)
        os.replace(temps[0], copy)
        try:
            os.replace(temps[1], folder / "SOURCE")
        except OSError:
            if previous is None:
                copy.unlink(missing_ok=True)
            else:
                copy.write_bytes(previous)
            raise
    except OSError:
        for temp in temps:
            temp.unlink(missing_ok=True)
        if made:
            for leftover in folder.glob("*"):
                leftover.unlink(missing_ok=True)
            folder.rmdir()
        raise


def update(root: Path, provider: str, tag: str, repository: str | None = None,
           path: str | None = None) -> tuple[int, list[str]]:
    """Fetches one published version and rewrites contracts/<provider>/ and its SOURCE."""
    if not PROVIDER.fullmatch(provider):
        return 2, [f"{provider}: a provider is named by one folder name under contracts/"]
    if not TAG.match(tag):
        return 2, [f"{tag}: name one published version, api-v<MAJOR.MINOR.PATCH>; never latest"]
    folder = root / "contracts" / provider
    old = {}
    if (folder / "SOURCE").is_file():
        old = load_source(folder)
        if isinstance(old, str):
            return 1, [old]
    repository, path = repository or old.get("repository"), path or old.get("path")
    if not repository or not path:
        return 2, [f"contracts/{provider} has no SOURCE yet: pass --repository and --path"]
    if not PurePosixPath(path).name or path.endswith("/"):
        return 2, [f"{path}: --path names a file, not a folder"]
    unsafe = repository_problem(repository)
    if unsafe:
        return 2, [unsafe]
    got = fetch(repository, tag, path)
    if isinstance(got, str):
        return 1, [got]
    commit, data = got
    found = info_version(data.decode("utf-8", errors="replace"))
    if found != TAG.match(tag).group(1):
        return 1, [f"{path} at {tag}: info.version is {found!r}, but the tag is {tag}; nothing written, ask the provider"]
    fields = {"repository": repository, "tag": tag, "commit": commit, "path": path, "sha256": sha256(data)}
    try:
        write_pair(folder, copy_of(folder, path), data, source_text(fields).encode("utf-8"))
    except OSError as error:
        return 1, [f"contracts/{provider}: cannot write the copy and SOURCE ({error}); the previous files are kept"]
    if old.get("path") and copy_of(folder, old["path"]).name != copy_of(folder, path).name:
        copy_of(folder, old["path"]).unlink(missing_ok=True)
    messages = [f"contracts/{provider}: now {tag} ({commit[:12]}); commit the copy and SOURCE together, in a slice "
                f"whose MAY CHANGE names contracts/{provider}/**"]
    before = TAG.match(old.get("tag", ""))
    if before and semver(before.group(1)) > semver(TAG.match(tag).group(1)):
        messages.append(f"note: {tag} is older than the {old['tag']} it replaces")
    return 0, messages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".")
    parser.add_argument("--online", action="store_true")
    parser.add_argument("--update", nargs=2, metavar=("PROVIDER", "TAG"))
    parser.add_argument("--repository")
    parser.add_argument("--path")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.update:
        code, messages = update(root, *args.update, repository=args.repository, path=args.path)
        for message in messages:
            print(message, file=sys.stderr if code else sys.stdout)
        return code
    contracts = root / "contracts"
    folders = sorted(p for p in contracts.iterdir() if p.is_dir()) if contracts.is_dir() else []
    if not folders:
        print("check_contract_pin: no vendored contracts")
        return 0
    problems, deadline = [], time.monotonic() + RUN_TIMEOUT
    for folder in folders:
        found = offline_problems(folder)
        problems += found if found or not args.online else online_problems(folder, deadline)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"check_contract_pin: {len(folders)} vendored contract(s) match their SOURCE"
              + (" and their published tags" if args.online else ""))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
