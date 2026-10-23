"""`aidlc adopt` (ADR 0007): a read-only survey of an existing repository, and (`--import`) a patch that
moves other tools' rule files into AGENTS.md and .aidlc/rules/. It writes nothing; the person reviews
and applies the patch. Secrets are never baselined: the survey stops the adoption until they are fixed."""
from __future__ import annotations

import difflib
import fnmatch
import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from .adapters.base import _is_generated
from .adapters.capabilities import load_capabilities
from .checks.conftest_check import _fold, _is_agent_config
from .hookbridge import hooks
from .paths import framework_root
from .policy import load_yaml
from .repo import CONFIG
from .templates import TemplateError, parse_front_matter

MAX_SCAN = 1_000_000


CONTROL = re.compile(r"[\x00-\x1f\x7f]")    # a name with these could inject lines into a patch or report


class AdoptError(Exception):
    pass


IMPORTABLE = ("CLAUDE.md", ".cursorrules", ".github/copilot-instructions.md")
IMPORTABLE_GLOBS = (".cursor/rules/*.mdc", ".github/instructions/*.instructions.md")


@dataclass
class Survey:
    repo: Path
    stacks: list[dict] = field(default_factory=list)
    agent_config: list[tuple[str, str, str]] = field(default_factory=list)
    workflows: list[str] = field(default_factory=list)
    secrets: list[str] = field(default_factory=list)
    installed: bool = False
    unscanned: int = 0                                         # files over MAX_SCAN, not scanned for secrets
    unsafe_names: int = 0                                      # tracked names with control characters, skipped


def _tracked(repo: Path) -> list[str]:
    try:
        out = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "ls-files", "-z"], cwd=repo,
                             capture_output=True, text=True, check=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        raise AdoptError(f"cannot list the tracked files: {type(exc).__name__}") from None
    return [p for p in out.split("\0") if p]


def importable(rel: str) -> bool:
    return rel in IMPORTABLE or any(fnmatch.fnmatchcase(rel, g) for g in IMPORTABLE_GLOBS)


def _tool(rel: str) -> str:
    if rel == "CLAUDE.md":
        return "claude-code"
    folded, parts = _fold(rel), _fold(rel).split("/")
    for name, data in load_capabilities().items():
        config = data["agent_config"]
        if (any(p in {d.casefold() for d in config["dir_names"]} for p in parts)
                or parts[-1] in {f.casefold() for f in config["file_names"]}
                or folded.startswith(tuple(p.casefold() for p in config["prefixes"]))):
            return name
    return "aidlc"


def survey(repo: Path) -> Survey:
    s = Survey(repo=repo, installed=(repo / CONFIG).is_file())
    tracked = _tracked(repo)
    names = {PurePosixPath(p).name for p in tracked if "/" not in p}
    for hint in load_yaml(framework_root() / "core" / "context" / "stack-hints.yaml"):
        if any(fnmatch.filter(names, pattern) for pattern in hint["files"]):
            s.stacks.append(hint)
    secret = hooks().guard.BLOCK_SECRET_RE
    for rel in tracked:
        if CONTROL.search(rel):
            s.unsafe_names += 1
            continue
        path = repo / rel
        if path.is_symlink() or not path.is_file():
            continue
        if rel.startswith(".github/workflows/") and rel.endswith((".yml", ".yaml")):
            s.workflows.append(rel)
        if rel == "CLAUDE.md" or _is_agent_config(_fold(rel)):
            text = path.read_text(encoding="utf-8", errors="replace") if path.stat().st_size <= MAX_SCAN else ""
            action = "managed" if _is_generated(text) else "import" if importable(rel) else "decide"
            s.agent_config.append((rel, _tool(rel), action))
        if path.stat().st_size > MAX_SCAN:
            s.unscanned += 1
        else:
            data = path.read_bytes()
            if b"\0" not in data and secret.search(data.decode("utf-8", errors="replace")):
                s.secrets.append(rel)
    return s


def report(s: Survey) -> str:
    lines = [f"# Adoption report: {s.repo.name}", ""]
    if s.secrets:
        lines += ["## Stop: secret-shaped text", "Fix these before adopting (rotate the credential, then remove it; "
                  "secrets are never baselined):", *[f"- `{p}`" for p in s.secrets], ""]
    lines += ["## Stack and suggested commands"]
    if not s.stacks:
        lines.append("- none recognised: use the `generic` profile and write the commands in `.aidlc/config.yaml`")
    for st in s.stacks:
        lines.append(f"- **{st['name']}** → profile `{st['profile']}`" +
                     (f"; commands {st['commands']}, reports {st.get('test_reports', [])}" if st.get("commands") else "") +
                     (f" ({st['note']})" if st.get("note") else ""))
    lines += ["", "## Agent configuration found"]
    labels = {"import": "imported by `aidlc adopt --import`", "managed": "generated by aidlc",
              "decide": "decide: keep it as a plugin, move it, or remove it (the CI judge fails unmanaged config)"}
    lines += [f"- `{p}` ({tool}): {labels[action]}" for p, tool, action in s.agent_config] or ["- none"]
    if s.unsafe_names:
        lines += ["", f"## Skipped: {s.unsafe_names} tracked file name(s) with control characters",
                  "Rename them; the survey and the import do not read them."]
    lines += ["", "## Existing CI", *([f"- `{w}` (stays; aidlc adds its own workflow)" for w in s.workflows] or ["- none"])]
    lines += ["", "## Next steps",
              "1. Fix any secret above." if s.secrets else "1. No secret-shaped text found" +
              (f" in the scanned files; {s.unscanned} file(s) over 1 MB were not scanned: check them by hand."
               if s.unscanned else "."),
              "2. `aidlc init-repo . --profile <profile> …` (never overwrites)." if not s.installed else
              "2. aidlc is already initialised here.",
              "3. `aidlc adopt --import > adopt.patch`, read it, then `git apply adopt.patch`.",
              "4. `aidlc render --tool claude-code`, then write `.aidlc/baseline.yaml` for today's debt "
              "(docs/adoption/README.md).",
              "5. Open the adoption pull request; after it merges, switch on the required checks."]
    return "\n".join(lines) + "\n"


def _diff(rel: str, old: str | None, new: str | None) -> str:
    """One file's change in the form `git apply` reads."""
    a = [] if old is None else old.splitlines(keepends=True)
    b = [] if new is None else new.splitlines(keepends=True)
    head = [f"diff --git a/{rel} b/{rel}\n"]
    if old is None:
        head.append("new file mode 100644\n")
    if new is None:
        head.append("deleted file mode 100644\n")
    body = difflib.unified_diff(a, b, "/dev/null" if old is None else f"a/{rel}",
                                "/dev/null" if new is None else f"b/{rel}")
    out = "".join(head)
    for line in body:
        out += line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
    return out


def _rule(paths: list[str], body: str) -> str:
    return "---\npaths:\n" + "".join(f"  - {json.dumps(p)}\n" for p in paths) + "---\n" + body.lstrip("\n")


def _globs(value: object) -> list[str]:
    items = value if isinstance(value, list) else str(value or "").split(",")
    return [g.strip().strip("'\"") for g in items if isinstance(g, str) and g.strip()]


def _read(repo: Path, rel: str) -> str:
    """The file as stored, line endings included (CRLF stays CRLF), so the patch matches the bytes."""
    return (repo / rel).read_bytes().decode("utf-8")


def import_patch(repo: Path) -> tuple[str, list[str]]:
    if not (repo / CONFIG).is_file():
        raise AdoptError("run `aidlc init-repo` first: the import appends to its AGENTS.md")
    try:
        agents_old = _read(repo, "AGENTS.md")
    except (OSError, UnicodeDecodeError) as exc:
        raise AdoptError(f"AGENTS.md cannot be read ({type(exc).__name__}); restore it, then run the import") from None
    s = survey(repo)
    appended, changes, claimed = "", [], set()
    problems = [f"{s.unsafe_names} tracked name(s) with a control character were skipped; rename them"] \
        if s.unsafe_names else []
    for rel, _tool, action in s.agent_config:
        if action != "import":
            continue
        try:
            text = _read(repo, rel)
        except (OSError, UnicodeDecodeError):
            problems.append(f"{rel}: not UTF-8 text; move it by hand (left in place)")
            continue
        if rel.endswith((".mdc", ".instructions.md")):
            try:
                meta, body = parse_front_matter(text, repo / rel)
            except TemplateError:
                problems.append(f"{rel}: its front matter cannot be read; move it by hand (left in place)")
                continue
            raw = meta.get("globs") if rel.endswith(".mdc") else meta.get("applyTo")
            if meta.get("alwaysApply") is True:
                appended += f"\n## Imported from {rel} (review: keep what every tool needs)\n\n{body.rstrip()}\n"
                changes.append((rel, text, None))
                continue
            if "{" in str(raw or "") or "}" in str(raw or ""):
                problems.append(f"{rel}: brace globs ({raw}) need converting by hand (left in place)")
                continue
            paths = _globs(raw)
            if not paths:
                problems.append(f"{rel}: applies only when asked (no globs); decide by hand (left in place)")
                continue
            name = PurePosixPath(rel).name.removesuffix(".mdc").removesuffix(".instructions.md")
            target = f".aidlc/rules/{name}.md"
            if target in claimed or (repo / target).exists():
                problems.append(f"{rel}: {target} already exists or another file claims it; merge it by hand "
                                "(nothing overwritten, left in place)")
                continue
            claimed.add(target)
            changes.append((target, None, _rule(paths, body)))
            changes.append((rel, text, None))
            continue
        appended += f"\n## Imported from {rel} (review: keep what every tool needs)\n\n{text.rstrip()}\n"
        changes.append((rel, text, None))
    if appended:
        changes.insert(0, ("AGENTS.md", agents_old, agents_old.rstrip("\r\n") + "\n" + appended))
    return "".join(_diff(rel, old, new) for rel, old, new in changes), problems
