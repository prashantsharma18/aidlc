# Plan 8: plugins, the pack contract and aidlc-modernize — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn aidlc into one marketplace with a core plugin and an `aidlc-modernize` plugin, joined by a pack contract that never makes core name a pack, and prove it by moving a real .NET Framework 4.8 app to .NET 10 through the standard lane.

**Architecture:** Core moves to `plugins/aidlc/` (version 2.0.0); `plugins/aidlc-modernize/` (0.1.0) requires it. A repository declares its packs in AGENTS.md; a starter script checks that declaration against what is installed; the task bundle names pack skills in full; the build loads them or stops. One narrow exception to core's gates, the mechanical recipe commit, is checked by a second starter script. Deterministic work (parity runs, retargeting) is done by scripts; agents read their output.

**Tech Stack:** Markdown skills (open Agent Skills format), Python 3.12 standard library scripts with unittest, Claude Code plugin manifests; demo: C# 7.3 on .NET Framework 4.8 (built by the Linux .NET 10 SDK, run through WSL interop), xUnit v3, .NET 10.

**Spec:** `docs/design/2026-10-26-plugins-and-modernize.md` (visual: the "aidlc Plugin Map" page, v3)

**Decisions (user, 2026-10-26):** one `aidlc-modernize` plugin with .NET and Java factories inside it, split later when complexity calls for it; the mechanical recipe commit on its five conditions (spec section of that name), "only if it is the correct way and not a shortcut"; .NET first; the demo is a very small real .NET Framework 4.8 app; AI review in CI and the GitHub push are later.

**Decision to confirm with this plan (D8-1):** the validator test `test_the_plugin_must_point_at_the_root` encodes the old layout (plugin at the repository root). The new layout makes that requirement wrong. It is replaced by `test_a_plugin_source_outside_plugins_is_a_problem`, whose assertion is unchanged (`any("marketplace" in p)`) and whose input becomes the old, now-wrong source `"./"`. This is a requirement change by design, not a test edited to pass; it needs your approval with the plan.

## Global Constraints

- Python scripts: 3.12, standard library only, `unittest` tests under `scripts/`, run by `python3 -m unittest discover -s scripts -p 'test_*.py'`.
- Skills follow the open format: folder name equals `name:`; the description says what it does and "Use when …". Skills whose names start with `aidlc-`, `modernize-`, `dotnet-` or `java-` keep the house sections (When to use, Inputs, Steps, Produces, Gate, Stop if, Common excuses, Red flags, Rules) and the line "You draft; you never approve."
- No skill names a tool-specific command; commands are "the repository's commands from AGENTS.md".
- Core never names a pack, a pack skill or a pack agent. Skill names are unique across the marketplace.
- Versions: core `2.0.0`, `aidlc-modernize` `0.1.0`; `aidlc-modernize` requires `{"name": "aidlc", "version": "^2.0"}`.
- The mechanical recipe commit's five conditions are quoted verbatim wherever the exception is stated (ADR 0012, `aidlc-build`).
- No new dependency in the aidlc repository. Demo packages: `Microsoft.NETFramework.ReferenceAssemblies` 1.0.3 and `xunit.v3` 2.0.3 (legacy side); any package the port needs is a dependency decision at the plan gate.
- Commits use `prashantsharma18 <6386481+prashantsharma18@users.noreply.github.com>`; the demo repository gets that local identity before its first commit. Nothing is pushed.
- Never change an existing test assertion to make a test pass (D8-1 is the one approved requirement change).

## Review Focus

1. AGENTS.md declares a pack that is not switched on, a copy install lacks a declared skill, or the settings switch on an undeclared pack → `check_packs.py` names each problem and exits 1 (Task 2 tests).
2. Two plugins ship a skill with the same name → the validator fails, because Copilot silently keeps the first (Task 1 test).
3. A core file names a pack, a pack skill or a pack agent → the validator fails (Task 1 test).
4. A "recipe" commit that a re-run does not reproduce, that changes the test count, or that has no `Recipe:` trailer → `check_recipe_commit.py` fails (Task 3 tests).
5. Parity across Windows and Linux: CRLF output from the .NET Framework build against LF from .NET 10 is not a difference; run-to-run noise is reported as NOISY, not hidden (Task 4 tests).

---

### Task 1: Core moves to `plugins/aidlc/`; the validator checks a marketplace

**Files:**
- Move: `skills/` → `plugins/aidlc/skills/`, `agents/` → `plugins/aidlc/agents/`, `.claude-plugin/plugin.json` → `plugins/aidlc/.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`, `scripts/validate.py` (rewrite), `scripts/test_validate.py`
- Create: `docs/design/2026-10-26-plugins-and-modernize.md` (already written; committed here)

**Interfaces:**
- Produces: `validate.validate(root: Path) -> list[str]`; `validate.load_plugins(root: Path) -> tuple[list[str], list[tuple[str, Path, dict]]]`; constants `CORE = "aidlc"`, `HOUSE_PREFIXES = ("aidlc-", "modernize-", "dotnet-", "java-")`. Later tasks add plugins and rely on these checks.

- [ ] **Step 1: Update the test fixture to the new layout and add the new tests**

Replace the fixture block (everything from `STAGE_BODY` usage helpers `def package` to `def skill`) in `scripts/test_validate.py` with:

```python
SECRET_DENIES = ["Read(**/.env)", "Read(~/.ssh/**)"]
REPO_SETTINGS = {"permissions": {"deny": SECRET_DENIES}}
WORKSPACE_SETTINGS = {"permissions": {"allow": ["Edit(/stories/**)"], "deny": SECRET_DENIES}}
EXPLORER = "---\nname: explorer\ndescription: Reads.\n---\nbody\n"


def write_plugin(root: Path, name: str, skills: dict[str, str], agents: dict[str, str] | None = None,
                 assets=("plan.md",), version="2.0.0", deps=None):
    base = root / "plugins" / name
    for skill_name, text in skills.items():
        d = base / "skills" / skill_name
        (d / "assets").mkdir(parents=True)
        (d / "SKILL.md").write_text(text, encoding="utf-8")
        for a in assets:
            (d / "assets" / a).write_text("x", encoding="utf-8")
    if agents is not None:
        (base / "agents").mkdir(parents=True, exist_ok=True)
        for agent_name, text in agents.items():
            (base / "agents" / f"{agent_name}.md").write_text(text, encoding="utf-8")
    (base / ".claude-plugin").mkdir(parents=True, exist_ok=True)
    manifest = {"name": name, "version": version}
    if deps is not None:
        manifest["dependencies"] = deps
    (base / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest), encoding="utf-8")


def package(root: Path, skills: dict[str, str], agents: dict[str, str] | None = None, assets=("plan.md",),
            packs=()):
    write_plugin(root, "aidlc", skills, agents or {"explorer": EXPLORER}, assets)
    for pack in packs:
        write_plugin(root, **pack)
    entries = [{"name": "aidlc", "source": "./plugins/aidlc"}]
    entries += [{"name": p["name"], "source": f"./plugins/{p['name']}"} for p in packs]
    (root / ".claude-plugin").mkdir()
    (root / ".claude-plugin" / "marketplace.json").write_text(
        json.dumps({"name": "aidlc", "plugins": entries}), encoding="utf-8")
    for kind, settings in (("repo", REPO_SETTINGS), ("workspace", WORKSPACE_SETTINGS)):
        (root / "starter" / kind / ".claude").mkdir(parents=True)
        (root / "starter" / kind / ".claude" / "settings.json").write_text(json.dumps(settings), encoding="utf-8")


def skill(name, description="Does things. Use when needed.", body=STAGE_BODY):
    return f"---\nname: {name}\ndescription: {description}\n---\n{body}"
```

In the existing tests change only setup paths: in `test_harness_references_in_assets_are_problems` write to `root / "plugins" / "aidlc" / "skills" / "aidlc-plan" / "assets" / "plan.md"`; in `test_a_missing_agents_folder_is_a_problem` iterate and remove `root / "plugins" / "aidlc" / "agents"`. Replace `test_the_plugin_must_point_at_the_root` (D8-1) with:

```python
    def test_a_plugin_source_outside_plugins_is_a_problem(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./"}]}))
            self.assertTrue(any("marketplace" in p for p in validate.validate(root)))
```

Add these tests to `ValidateTest`:

```python
    PACK = {"name": "aidlc-modernize", "skills": {"modernize-assess": None}, "version": "0.1.0",
            "deps": [{"name": "aidlc", "version": "^2.0"}]}

    def pack(self, **changes):
        p = dict(self.PACK, **changes)
        p["skills"] = {k: v or skill(k) for k, v in p["skills"].items()}
        return p

    def test_a_core_and_pack_marketplace_has_no_problems(self):
        self.assertEqual(self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack()]), [])

    def test_skill_names_are_unique_across_plugins(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")},
                              packs=[self.pack(skills={"aidlc-plan": None})])
        self.assertTrue(any("unique" in p and "aidlc-plan" in p for p in problems), problems)

    def test_core_never_names_a_pack(self):
        body = STAGE_BODY.replace("## Produces", "Then run modernize-assess.\n## Produces")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)}, packs=[self.pack()])
        self.assertTrue(any("never names a pack" in p and "modernize-assess" in p for p in problems), problems)

    def test_core_requires_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack()])
            core = root / "plugins" / "aidlc" / ".claude-plugin" / "plugin.json"
            core.write_text(json.dumps({"name": "aidlc", "version": "2.0.0", "dependencies": ["aidlc-modernize"]}))
            self.assertTrue(any("core requires nothing" in p for p in validate.validate(root)))

    def test_a_dependency_must_be_in_the_marketplace(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack(deps=["aidlc-elsewhere"])])
        self.assertTrue(any("aidlc-elsewhere" in p for p in problems), problems)

    def test_versions_are_semantic(self):
        problems = self.check({"aidlc-plan": skill("aidlc-plan")}, packs=[self.pack(version="latest")])
        self.assertTrue(any("semantic version" in p for p in problems), problems)

    def test_a_named_reference_or_script_must_exist(self):
        body = STAGE_BODY.replace("## Produces", "Read `references/hop.md`; run `scripts/go.py`.\n## Produces")
        problems = self.check({"aidlc-plan": skill("aidlc-plan", body=body)})
        self.assertTrue(any("references/hop.md" in p for p in problems), problems)
        self.assertTrue(any("scripts/go.py" in p for p in problems), problems)

    def test_pack_stage_skills_keep_the_house_sections(self):
        bare = "---\nname: modernize-assess\ndescription: Assesses. Use when asked.\n---\n# Assess\n"
        problems = self.check({"aidlc-plan": skill("aidlc-plan")},
                              packs=[self.pack(skills={"modernize-assess": bare})])
        self.assertTrue(any("modernize-assess" in p and "## Gate" in p for p in problems), problems)
```

- [ ] **Step 2: Run the tests and watch the new ones fail**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -15`
Expected: FAIL — the old validator looks for `skills/` at the root, so most tests report "skills/: no skills found" or a marketplace problem; the new tests fail on their assertions.

- [ ] **Step 3: Move core with git**

```bash
mkdir -p plugins/aidlc/.claude-plugin
git mv skills plugins/aidlc/skills
git mv agents plugins/aidlc/agents
git mv .claude-plugin/plugin.json plugins/aidlc/.claude-plugin/plugin.json
```

Set `plugins/aidlc/.claude-plugin/plugin.json` to:

```json
{
  "name": "aidlc",
  "version": "2.0.0",
  "description": "Stage skills, engineering-practice skills and agent roles for AI-assisted software delivery. Portable: the same skills work in Claude Code, GitHub Copilot, Codex and Cursor.",
  "author": {"name": "Prashant Sharma"},
  "license": "MIT"
}
```

Set `.claude-plugin/marketplace.json` to:

```json
{
  "name": "aidlc",
  "owner": {"name": "prashantsharma18"},
  "description": "aidlc: skills for AI-assisted software delivery, from a requirement to a verified, reviewed change, and packs that extend it.",
  "plugins": [
    {
      "name": "aidlc",
      "source": "./plugins/aidlc",
      "description": "Core: stage skills (start to feedback, onboard), engineering-practice skills and agent roles. Each stage stops at its human gate."
    }
  ]
}
```

- [ ] **Step 4: Rewrite `scripts/validate.py`**

```python
#!/usr/bin/env python3
"""Checks the aidlc marketplace and every plugin it lists: each skill and agent in the open Agent Skills format, the
house sections of the stage and recipe skills, no command of the parked harness and no tool-specific syntax (in a
skill or its files), every named file present, skill names unique across plugins, core never naming a pack, plugin
versions and dependencies, and the starter settings' secret denies.

    python3 scripts/validate.py [root]

Prints one line per problem and exits 1 when there is any. Standard library only."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
CORE = "aidlc"
SECTIONS = ("## When to use", "## Inputs", "## Steps", "## Produces", "## Gate", "## Stop if",
            "## Common excuses", "## Red flags", "## Rules")
GATE_LINE = "You draft; you never approve."
# Stage, method and recipe skills keep the house sections; the adapted practice skills keep only the open format.
HOUSE_PREFIXES = ("aidlc-", "modernize-", "dotnet-", "java-")
# Commands and files of the harness parked under the tag harness-v1 (docs/archive/harness-v1.md).
REMOVED = re.compile(r"aidlc\s+(check|scope|ci|new|attempts|render|init-repo|doctor|trace|adopt|plugin\s+build)\b"
                     r"|approved-bundles\.txt|\.aidlc/(config|hooks|baseline)|core/(policy|schemas|hooks)\b"
                     r"|hook decision log|bin/aidlc\b")
# Syntax one tool understands and the others do not: skills must run unchanged in every tool.
TOOL_SPECIFIC = re.compile(r"/aidlc:[a-z]|\$ARGUMENTS\b|\$\{CLAUDE_[A-Z_]+\}")
# Allowing a whole tool at the workspace root opens every path it can reach, home folder included.
WHOLE_TOOLS = {"Read", "Edit", "Write", "Bash", "Grep", "Glob"}
# Files a skill names, relative to its folder: templates, reference pages and scripts.
SKILL_DIRS = ("assets", "references", "scripts")
NAMED_FILE = re.compile(r"`((?:assets|references|scripts)/[A-Za-z0-9._-]+)`")
TEXT_SUFFIXES = {".md", ".py", ".sh", ".txt", ".json", ".yml", ".yaml"}


def front_matter(text: str) -> dict[str, str] | None:
    """The top-level `key: value` lines between the opening `---` and the next one (values unquoted)."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    fields = {}
    for line in text[4:end].split("\n"):
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip().strip("'\"")
    return fields


def portability(rel: str, text: str) -> list[str]:
    problems = [f"{rel}: names a removed harness command or file: '{' '.join(m.group(0).split())}'"
                for m in REMOVED.finditer(text)]
    return problems + [f"{rel}: uses tool-specific syntax: '{m.group(0)}'" for m in TOOL_SPECIFIC.finditer(text)]


def check_skill(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    folder_rel = path.parent.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = front_matter(text)
    if fm is None:
        return [f"{rel}: no front matter"]
    problems = []
    name, description = fm.get("name", ""), fm.get("description", "")
    folder = path.parent.name
    if name != folder:
        problems.append(f"{rel}: name '{name}' does not match its folder '{folder}'")
    if not NAME.fullmatch(name) or len(name) > 64:
        problems.append(f"{rel}: name must be lower-case words joined by hyphens, at most 64 characters")
    if not description or len(description) > 1024:
        problems.append(f"{rel}: description is missing or longer than 1024 characters")
    elif "Use when" not in description:
        problems.append(f"{rel}: description must say when to use the skill ('Use when ...')")
    if folder.startswith(HOUSE_PREFIXES):
        positions = [text.find(s) for s in SECTIONS]
        for section, pos in zip(SECTIONS, positions):
            if pos < 0:
                problems.append(f"{rel}: missing section '{section}'")
        found = [p for p in positions if p >= 0]
        if found != sorted(found):
            problems.append(f"{rel}: sections are out of order (expected {', '.join(SECTIONS)})")
        if GATE_LINE not in text:
            problems.append(f"{rel}: the gate must end with '{GATE_LINE}'")
    problems += portability(rel, text)
    for sub in SKILL_DIRS:
        for extra in sorted((path.parent / sub).glob("*")):
            if extra.is_file() and extra.suffix in TEXT_SUFFIXES:
                problems += portability(f"{folder_rel}/{sub}/{extra.name}", extra.read_text(encoding="utf-8"))
    for named in sorted(set(NAMED_FILE.findall(text))):
        if not (path.parent / named).is_file():
            problems.append(f"{rel}: names `{named}`, which does not exist")
    return problems


def check_agent(path: Path, root: Path) -> list[str]:
    rel = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    fm = front_matter(text)
    if fm is None:
        return [f"{rel}: no front matter"]
    problems = [f"{rel}: front matter needs '{k}'" if k == "name" else f"{rel}: front matter needs a description"
                for k in ("name", "description") if not fm.get(k)]
    if fm.get("name") and fm["name"] != path.stem:
        problems.append(f"{rel}: name '{fm['name']}' does not match the file name")
    return problems + portability(rel, text)


def load_plugins(root: Path) -> tuple[list[str], list[tuple[str, Path, dict]]]:
    """The marketplace's plugins as (name, folder, manifest), and every problem found in the manifests."""
    rel = ".claude-plugin/marketplace.json"
    try:
        market = json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{rel}: unreadable ({exc})"], []
    problems, plugins = [], []
    for entry in market.get("plugins", []):
        name, source = entry.get("name", ""), entry.get("source")
        if not isinstance(source, str) or not source.startswith("./plugins/") or ".." in source:
            problems.append(f"{rel}: plugin '{name}' must have a source under './plugins/' (got {source!r})")
            continue
        folder = root / source[2:].rstrip("/")
        mrel = f"{folder.relative_to(root).as_posix()}/.claude-plugin/plugin.json"
        try:
            manifest = json.loads((root / mrel).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{mrel}: unreadable ({exc})")
            continue
        if manifest.get("name") != name:
            problems.append(f"{mrel}: name '{manifest.get('name')}' does not match the marketplace entry '{name}'")
        if not SEMVER.fullmatch(str(manifest.get("version", ""))):
            problems.append(f"{mrel}: needs a semantic version such as 1.0.0")
        plugins.append((name, folder, manifest))
    names = {n for n, _, _ in plugins}
    if CORE not in names:
        problems.append(f"{rel}: the core plugin '{CORE}' is missing")
    for name, folder, manifest in plugins:
        mrel = f"{folder.relative_to(root).as_posix()}/.claude-plugin/plugin.json"
        deps = manifest.get("dependencies", [])
        if name == CORE and deps:
            problems.append(f"{mrel}: core requires nothing; it never depends on a pack")
        for dep in deps:
            dep_name = dep if isinstance(dep, str) else dep.get("name", "")
            if dep_name.split("@")[0] not in names:
                problems.append(f"{mrel}: requires '{dep_name}', which the marketplace does not list")
    return problems, plugins


def check_core_names_no_pack(root: Path, core: Path, pack_names: set[str]) -> list[str]:
    """Core is written like a CI runner: it runs what approved files name, so its own text names no pack."""
    if not pack_names:
        return []
    alternatives = "|".join(sorted(map(re.escape, pack_names), key=len, reverse=True))
    pattern = re.compile(rf"(?<![A-Za-z0-9_-])({alternatives})(?![A-Za-z0-9_-])")
    problems = []
    for f in sorted(core.rglob("*")):
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            for m in pattern.finditer(f.read_text(encoding="utf-8")):
                problems.append(f"{f.relative_to(root).as_posix()}: names the pack '{m.group(1)}'; "
                                f"core never names a pack")
    return problems


def check_starters(root: Path) -> list[str]:
    """The workspace root reads with the same secret denies as a repository, and never allows a whole tool."""
    settings = {}
    for kind in ("repo", "workspace"):
        rel = f"starter/{kind}/.claude/settings.json"
        try:
            settings[kind] = json.loads((root / rel).read_text(encoding="utf-8")).get("permissions", {})
        except (OSError, ValueError) as exc:
            return [f"{rel}: unreadable ({exc})"]
    rel = "starter/workspace/.claude/settings.json"
    ws = settings["workspace"]
    problems = [f"{rel}: allows the whole '{rule}' tool; allow paths, never a tool"
                for rule in ws.get("allow", []) if rule in WHOLE_TOOLS]
    secrets = [r for r in settings["repo"].get("deny", []) if r.startswith("Read(")]
    problems += [f"{rel}: misses the repository starter's deny '{r}'" for r in secrets if r not in ws.get("deny", [])]
    return problems


def validate(root: Path) -> list[str]:
    problems, plugins = load_plugins(root)
    owner_of: dict[str, str] = {}
    pack_names: set[str] = set()
    core_folder = None
    for name, folder, _ in plugins:
        frel = folder.relative_to(root).as_posix()
        skills = sorted((folder / "skills").glob("*/SKILL.md"))
        agents = sorted((folder / "agents").glob("*.md"))
        if not skills:
            problems.append(f"{frel}/skills/: no skills found")
        if name == CORE:
            core_folder = folder
            if not agents:
                problems.append(f"{frel}/agents/: no agents found")
        else:
            pack_names.add(name)
        for path in skills:
            problems += check_skill(path, root)
            skill = path.parent.name
            if skill in owner_of:
                problems.append(f"{frel}/skills/{skill}: the name '{skill}' is also used by plugin "
                                f"'{owner_of[skill]}'; skill names must be unique across the marketplace")
            else:
                owner_of[skill] = name
            if name != CORE:
                pack_names.add(skill)
        for path in agents:
            problems += check_agent(path, root)
            if name != CORE:
                pack_names.add(path.stem)
    if core_folder is not None:
        problems += check_core_names_no_pack(root, core_folder, pack_names)
    return problems + check_starters(root)


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else Path(__file__).resolve().parents[1])
    problems = validate(root)
    for p in problems:
        print(p)
    plugins = load_plugins(root)[1]
    count = sum(len(list((folder / "skills").glob("*/SKILL.md"))) for _, folder, _ in plugins)
    print(f"validate: {len(plugins)} plugin(s), {count} skill(s), {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 5: Run the tests and the validator**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -3 && python3 scripts/validate.py && claude plugin validate . 2>&1 | tail -2`
Expected: `Ran 23 tests … OK`; `validate: 1 plugin(s), 21 skill(s), 0 problem(s)`; `✔ Validation passed` (the earlier warning about `CLAUDE.md` at the plugin root is gone, since the plugin is no longer at the root).

- [ ] **Step 6: Commit**

```bash
git add docs/design/2026-10-26-plugins-and-modernize.md docs/plans/2026-10-26-plan-08-plugins-modernize.md \
  .claude-plugin/marketplace.json plugins/aidlc scripts/validate.py scripts/test_validate.py
git commit -m "refactor: core moves to plugins/aidlc (2.0.0); the validator checks a marketplace of plugins"
```

(`git mv` already staged the moves; the explicit paths stage the edits. Do not use `git add -A`: it fails inside a sandboxed session.)

---

### Task 2: The pack contract in core, and the pack check script

**Files:**
- Create: `starter/repo/scripts/check_packs.py`, `scripts/test_check_packs.py`
- Modify: `plugins/aidlc/skills/aidlc-start/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/SKILL.md`, `plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md`, `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/skills/aidlc-build/assets/progress-note.md`, `plugins/aidlc/agents/reviewer-compliance.md`, `plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md`, `plugins/aidlc/skills/aidlc-onboard/SKILL.md`, `starter/repo/AGENTS.md`, `starter/repo/.github/workflows/ci.yml`, `starter/repo/CODEOWNERS`

**Interfaces:**
- Produces: `check_packs.parse(agents_md: str) -> tuple[dict[str, list[str]], list[str]]` (pack → skill names without the plugin prefix; problems); `check_packs.check(repo: Path) -> list[str]`. The AGENTS.md section format (used by Tasks 7 and 8):

```
## Packs used here
- `<plugin>`: `<plugin>:<entry-skill>`, `<plugin>:<skill>` …
```
or the single line `- none`. The first skill on a line is where that kind of work starts.

- [ ] **Step 1: Write the failing tests** — `scripts/test_check_packs.py`:

```python
"""Tests for starter/repo/scripts/check_packs.py: each builds a small repository in a temporary folder."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_packs  # noqa: E402

NONE = "# r\n\n## Packs used here\n- none\n\n## Map\n"
ONE = ("# r\n\n## Packs used here\n- `aidlc-modernize`: `aidlc-modernize:modernize-assess`, "
       "`aidlc-modernize:dotnet-modernize`\n\n## Map\n")


def repo(root: Path, agents_md: str | None, enabled: dict | None = None, copies: dict[str, list[str]] | None = None):
    if agents_md is not None:
        (root / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    if enabled is not None:
        (root / ".claude").mkdir()
        (root / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": enabled}), encoding="utf-8")
    for folder, skills in (copies or {}).items():
        for s in skills:
            (root / folder / s).mkdir(parents=True)
            (root / folder / s / "SKILL.md").write_text("x", encoding="utf-8")


class CheckPacksTest(unittest.TestCase):
    def run_check(self, *args, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            repo(Path(tmp), *args, **kwargs)
            return check_packs.check(Path(tmp))

    def test_none_with_core_enabled_is_fine(self):
        self.assertEqual(self.run_check(NONE, {"aidlc@aidlc": True}), [])

    def test_a_declared_and_enabled_pack_is_fine(self):
        self.assertEqual(self.run_check(ONE, {"aidlc@aidlc": True, "aidlc-modernize@aidlc": True}), [])

    def test_a_missing_section_is_a_problem(self):
        problems = self.run_check("# r\n", {"aidlc@aidlc": True})
        self.assertTrue(any("Packs used here" in p for p in problems), problems)

    def test_a_missing_agents_md_is_a_problem(self):
        problems = self.run_check(None, {"aidlc@aidlc": True})
        self.assertTrue(any("AGENTS.md" in p and "unreadable" in p for p in problems), problems)

    def test_a_declared_pack_not_enabled_is_a_problem(self):
        problems = self.run_check(ONE, {"aidlc@aidlc": True})
        self.assertTrue(any("does not switch it on" in p for p in problems), problems)

    def test_an_enabled_pack_not_declared_is_a_problem(self):
        problems = self.run_check(NONE, {"aidlc@aidlc": True, "aidlc-modernize@aidlc": True})
        self.assertTrue(any("does not declare" in p for p in problems), problems)

    def test_a_copy_install_missing_a_declared_skill_is_a_problem(self):
        problems = self.run_check(ONE, None, copies={".github/skills": ["aidlc-start", "modernize-assess"]})
        self.assertTrue(any("dotnet-modernize" in p and "missing" in p for p in problems), problems)

    def test_a_complete_copy_install_is_fine(self):
        copies = {".github/skills": ["aidlc-start", "modernize-assess", "dotnet-modernize"]}
        self.assertEqual(self.run_check(ONE, None, copies=copies), [])

    def test_a_skill_without_its_plugin_prefix_is_a_problem(self):
        bad = ONE.replace("`aidlc-modernize:dotnet-modernize`", "`dotnet-modernize`")
        problems = self.run_check(bad, {"aidlc@aidlc": True, "aidlc-modernize@aidlc": True})
        self.assertTrue(any("is not written as" in p for p in problems), problems)

    def test_unreadable_settings_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo(root, ONE)
            (root / ".claude").mkdir()
            (root / ".claude" / "settings.json").write_text("{not json", encoding="utf-8")
            problems = check_packs.check(root)
        self.assertTrue(any("settings.json" in p and "unreadable" in p for p in problems), problems)

    def test_packs_with_no_install_at_all_is_a_problem(self):
        problems = self.run_check(ONE)
        self.assertTrue(any("no aidlc install" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and watch them fail**

Run: `python3 -m unittest scripts/test_check_packs.py 2>&1 | tail -3`
Expected: ERROR `ModuleNotFoundError: No module named 'check_packs'`.

- [ ] **Step 3: Write `starter/repo/scripts/check_packs.py`**

```python
#!/usr/bin/env python3
"""Checks that the packs AGENTS.md declares under "## Packs used here" are really installed, and that the settings
switch on no pack from aidlc's marketplace that AGENTS.md leaves out. Run it in CI and at the start of work.

    python3 scripts/check_packs.py [repository]

A pack line names the plugin and its skills in full, in backticks; the first skill is where that kind of work starts:
    - `aidlc-modernize`: `aidlc-modernize:modernize-assess`, `aidlc-modernize:dotnet-modernize`
A repository that uses no pack writes the single line "- none". Prints one line per problem and exits 1 when there is
any. Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEADING = "## Packs used here"
CORE = "aidlc"
# Folders where Copilot, Codex, Claude Code and Cursor read copied skills.
COPY_DIRS = (".github/skills", ".agents/skills", ".claude/skills", ".cursor/skills")
TOKEN = re.compile(r"`([^`]+)`")


def parse(agents_md: str) -> tuple[dict[str, list[str]], list[str]]:
    """{plugin: [skill, ...]} from the section, and every line that could not be read."""
    lines = agents_md.splitlines()
    if HEADING not in lines:
        return {}, [f"AGENTS.md: no '{HEADING}' section (write '- none' when the repository uses no pack)"]
    packs: dict[str, list[str]] = {}
    problems, entries = [], 0
    for line in lines[lines.index(HEADING) + 1:]:
        if line.startswith("## "):
            break
        if not line.startswith("- "):
            continue
        entries += 1
        if line.strip() == "- none":
            continue
        tokens = TOKEN.findall(line)
        if not tokens:
            problems.append(f"AGENTS.md: cannot read the pack line {line.strip()!r}; "
                            f"name the plugin and its skills in backticks")
            continue
        plugin, skills = tokens[0], tokens[1:]
        for s in skills:
            if not s.startswith(plugin + ":"):
                problems.append(f"AGENTS.md: skill `{s}` is not written as `{plugin}:<skill>`")
        packs[plugin] = [s.split(":", 1)[1] for s in skills if s.startswith(plugin + ":")]
    if entries == 0:
        problems.append(f"AGENTS.md: the '{HEADING}' section is empty (write '- none' when the repository uses no pack)")
    return packs, problems


def check(repo: Path) -> list[str]:
    try:
        text = (repo / "AGENTS.md").read_text(encoding="utf-8")
    except OSError as exc:
        return [f"AGENTS.md: unreadable ({exc})"]
    packs, problems = parse(text)
    settings_path = repo / ".claude" / "settings.json"
    enabled = None
    if settings_path.exists():
        try:
            enabled = json.loads(settings_path.read_text(encoding="utf-8")).get("enabledPlugins", {})
        except (OSError, ValueError) as exc:
            return problems + [f".claude/settings.json: unreadable ({exc})"]
    copies = [repo / d for d in COPY_DIRS if (repo / d / "aidlc-start" / "SKILL.md").is_file()]
    if packs and enabled is None and not copies:
        problems.append("no aidlc install found: neither .claude/settings.json nor a copied skills folder")
    if enabled is not None:
        core_markets = [k.partition("@")[2] for k in enabled if k.partition("@")[0] == CORE]
        for plugin in packs:
            if not any(k.partition("@")[0] == plugin and v is True for k, v in enabled.items()):
                problems.append(f".claude/settings.json: AGENTS.md declares `{plugin}`, "
                                f"but enabledPlugins does not switch it on")
        for key, value in enabled.items():
            name, _, market = key.partition("@")
            if value is True and market in core_markets and name != CORE and name not in packs:
                problems.append(f".claude/settings.json: switches on `{name}`, which AGENTS.md does not declare "
                                f"under '{HEADING}'")
    for copy in copies:
        for plugin, skills in packs.items():
            for s in skills:
                if not (copy / s / "SKILL.md").is_file():
                    problems.append(f"{copy.relative_to(repo).as_posix()}/: AGENTS.md declares `{plugin}:{s}`, "
                                    f"but the folder `{s}` is missing")
    return problems


def main(argv: list[str]) -> int:
    repo = Path(argv[1] if len(argv) > 1 else ".")
    problems = check(repo)
    for p in problems:
        print(p)
    if not problems:
        packs = parse((repo / "AGENTS.md").read_text(encoding="utf-8"))[0]
        print(f"check_packs: {len(packs)} pack(s), {sum(map(len, packs.values()))} skill(s) declared; all installed")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest scripts/test_check_packs.py 2>&1 | tail -3`
Expected: `Ran 11 tests … OK`.

- [ ] **Step 5: The contract in core's text** (core names no pack: use `<plugin>`/`<skill>` placeholders only)

1. `plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md` and `starter/repo/AGENTS.md`: after the "How work runs here" section add

```
## Packs used here
- none
(When the repository uses packs: one line per pack, the plugin and its skills in full, in backticks; the first skill
is where that kind of work starts. Example: - `<plugin>`: `<plugin>:<entry-skill>`, `<plugin>:<skill>`.
`scripts/check_packs.py` checks this section against what is installed; CODEOWNERS protects it.)
```

   and under Commands add `- Pack check, at the start of work and in CI: \`python3 scripts/check_packs.py\``.
2. `aidlc-onboard/SKILL.md` step 5 (Inject): add "Write the `Packs used here` section: `- none`, or one line per pack the team switches on; copy check_packs.py from aidlc's starter into the repository's scripts folder and add it to CI." (No backticked `scripts/<file>` path in a SKILL.md: the validator reads that as a file inside the skill.)
3. `aidlc-start/SKILL.md`: new step after step 1, "**Packs.** Read AGENTS.md's `Packs used here`. If it lists packs, run the pack check named in AGENTS.md's Commands; if it fails, report its lines and stop. When the work is the kind a pack line covers, the route's next stage after this one is that line's first skill, written in full (`<plugin>:<skill>`)." Renumber later steps. Add to Stop if: "The pack check fails, or a pack's entry skill cannot be loaded."
4. `aidlc-plan/assets/task-bundle.md`: after `PATTERN` add

```
USE SKILLS  <plugin:skill, … only skills AGENTS.md declares under "Packs used here"> | none
RECIPE      <tool@version — the exact command — the files it may change> | none   (a mechanical recipe commit)
```

5. `aidlc-plan/SKILL.md` step 7: add two bullets — "fill USE SKILLS only with skills AGENTS.md declares, each in full (`<plugin>:<skill>`), or `none`;" and "fill RECIPE only for a deterministic tool, as its own slice before any hand change (the recipe-commit rule in `aidlc-build`); the tool and its version are a dependency decision for the person."
6. `aidlc-build/SKILL.md`: new step after step 2: "Load every skill the bundle's USE SKILLS names, by its full name, before any edit. A skill that cannot be loaded, or a name that matches more than one skill, is a stop: report it; never continue without it and never pick one yourself. Record each skill loaded, with its plugin's version, in the progress note." Add to Red flags: "You are working from a pack skill the bundle does not name, or without one it does."
7. `aidlc-build/assets/progress-note.md`: add a section `## Skills loaded` with the line `- <plugin:skill> — plugin version <x.y.z>`.
8. `plugins/aidlc/agents/reviewer-compliance.md` Work: add "The progress note's `Skills loaded` matches the bundle's USE SKILLS, one for one."
9. `starter/repo/.github/workflows/ci.yml`: add a step before Lint:

```yaml
      - name: Packs declared in AGENTS.md are installed
        run: python3 scripts/check_packs.py
```

10. `starter/repo/CODEOWNERS`: add `scripts/check_*.py   @your-org/your-team-leads` and `.claude/   @your-org/your-team-leads`.

- [ ] **Step 6: Validate and run every test**

Run: `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -2`
Expected: `0 problem(s)`; `OK` (34 tests).

- [ ] **Step 7: Commit**

```bash
git add starter/repo/scripts/check_packs.py scripts/test_check_packs.py starter/repo/AGENTS.md \
  starter/repo/.github/workflows/ci.yml starter/repo/CODEOWNERS plugins/aidlc/agents/reviewer-compliance.md \
  plugins/aidlc/skills/aidlc-start/SKILL.md plugins/aidlc/skills/aidlc-plan/SKILL.md \
  plugins/aidlc/skills/aidlc-plan/assets/task-bundle.md plugins/aidlc/skills/aidlc-build/SKILL.md \
  plugins/aidlc/skills/aidlc-build/assets/progress-note.md plugins/aidlc/skills/aidlc-onboard/SKILL.md \
  plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md
git commit -m "feat(core): the pack contract: AGENTS.md declares packs, the bundle names skills in full, build stops on missing or ambiguous; check_packs.py"
```

---

### Task 3: The mechanical recipe commit (ADR 0012) and its check

**Files:**
- Create: `starter/repo/scripts/check_recipe_commit.py`, `scripts/test_check_recipe_commit.py`, `docs/adr/0012-mechanical-recipe-commit.md`
- Modify: `plugins/aidlc/skills/aidlc-build/SKILL.md`, `plugins/aidlc/agents/reviewer-compliance.md`, `plugins/aidlc/skills/aidlc-review/assets/pr-description.md`, `starter/repo/AGENTS.md`, `plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md`

**Interfaces:**
- Produces: `check_recipe_commit.check(repo: Path, commit: str, recipe: str, count: str) -> tuple[list[str], list[str]]` (problems, notes for the reviewer). CLI: `python3 scripts/check_recipe_commit.py <commit> --recipe "<command>" --count "<command>"`. The trailer format `Recipe: <tool>@<version>` (Tasks 5 and 8 use `Recipe: aidlc-retarget@1.0.0`).

- [ ] **Step 1: Write the failing tests** — `scripts/test_check_recipe_commit.py`:

```python
"""Tests for starter/repo/scripts/check_recipe_commit.py: each builds a small git repository with one recipe commit."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_recipe_commit  # noqa: E402

PY = sys.executable
RECIPE = f"{PY} recipe.py"
COUNT = f"{PY} -c \"print(len(open('tests.txt').read().split()))\""
DETERMINISTIC = "import pathlib\np = pathlib.Path('a.txt')\np.write_text(p.read_text().replace('old', 'new'))\n"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                          check=True, capture_output=True, text=True).stdout.strip()


def make_repo(root: Path, recipe_source: str, extra_change=None, message="mechanical\n\nRecipe: demo@1.0.0") -> str:
    """A base commit with the recipe, then the commit the recipe (plus any extra change) produced."""
    git(root, "init", "-q")
    (root / "a.txt").write_text("old value\n")
    (root / "tests.txt").write_text("t1 t2 t3\n")
    (root / "recipe.py").write_text(recipe_source)
    git(root, "add", "a.txt", "tests.txt", "recipe.py")
    git(root, "commit", "-q", "-m", "base")
    subprocess.run(RECIPE, shell=True, cwd=root, check=True)
    if extra_change:
        extra_change(root)
    git(root, "add", "a.txt", "tests.txt")
    git(root, "commit", "-q", "-m", message)
    return git(root, "rev-parse", "HEAD")


class CheckRecipeCommitTest(unittest.TestCase):
    def check(self, recipe_source, **kwargs):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commit = make_repo(root, recipe_source, **kwargs)
            return check_recipe_commit.check(root, commit, RECIPE, COUNT)

    def test_a_reproducible_recipe_commit_passes(self):
        problems, _ = self.check(DETERMINISTIC)
        self.assertEqual(problems, [])

    def test_a_hand_change_in_the_recipe_commit_fails(self):
        def hand(root):
            (root / "a.txt").write_text((root / "a.txt").read_text() + "tweak\n")
        problems, _ = self.check(DETERMINISTIC, extra_change=hand)
        self.assertTrue(any("does not reproduce" in p and "a.txt" in p for p in problems), problems)

    def test_a_nondeterministic_recipe_fails(self):
        noisy = "import pathlib, time\npathlib.Path('a.txt').write_text(str(time.time_ns()))\n"
        problems, _ = self.check(noisy)
        self.assertTrue(any("does not reproduce" in p for p in problems), problems)

    def test_a_changed_test_count_fails(self):
        adds_test = DETERMINISTIC + "pathlib.Path('tests.txt').write_text('t1 t2 t3 t4\\n')\n"
        problems, _ = self.check(adds_test)
        self.assertTrue(any("test count" in p and "3" in p and "4" in p for p in problems), problems)

    def test_a_commit_without_the_trailer_fails(self):
        problems, _ = self.check(DETERMINISTIC, message="mechanical")
        self.assertTrue(any("Recipe:" in p for p in problems), problems)

    def test_changed_assertion_lines_are_listed_for_the_reviewer(self):
        to_assert = ("import pathlib\np = pathlib.Path('tests.txt')\n"
                     "p.write_text(p.read_text().replace('t3', 'Assert.Equal'))\n")
        _, notes = self.check(to_assert)
        self.assertTrue(any("tests.txt" in n and "Assert.Equal" in n for n in notes), notes)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and watch them fail**

Run: `python3 -m unittest scripts/test_check_recipe_commit.py 2>&1 | tail -3`
Expected: ERROR `No module named 'check_recipe_commit'`.

- [ ] **Step 3: Write `starter/repo/scripts/check_recipe_commit.py`**

```python
#!/usr/bin/env python3
"""Checks a mechanical recipe commit, the one exception to aidlc's gates (ADR 0012): re-running the approved recipe
on the commit's parent gives exactly the commit's files, the test count is the same before and after, and the commit
names the tool. Lists every changed assertion line so the reviewer can confirm that what it checks did not change.

    python3 scripts/check_recipe_commit.py <commit> --recipe "<command>" --count "<command>"

--recipe is the command the task bundle's RECIPE field approved; --count prints the number of tests (its last integer
is read). Both run in temporary copies made with `git archive`, never in your checkout. Exit 1 on any problem.
Standard library only; copied into a repository from aidlc's starter/repo/scripts/."""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

TRAILER = re.compile(r"^Recipe: \S+@\S+\s*$", re.MULTILINE)
ASSERTION = re.compile(r"\bAssert\.|\bassert\b|\bexpect\(|\.Should\(|\bShould\.")


def git(repo: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True).stdout


def extract(repo: Path, rev: str, into: Path) -> None:
    with tarfile.open(fileobj=io.BytesIO(git(repo, "archive", "--format=tar", rev))) as tar:
        tar.extractall(into, filter="data")


def tree(folder: Path) -> dict[str, bytes]:
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}


def count_tests(command: str, folder: Path) -> tuple[int | None, str]:
    result = subprocess.run(command, shell=True, cwd=folder, capture_output=True, text=True)
    numbers = re.findall(r"\d+", result.stdout)
    return (int(numbers[-1]) if result.returncode == 0 and numbers else None), result.stderr[-500:]


def check(repo: Path, commit: str, recipe: str, count: str) -> tuple[list[str], list[str]]:
    problems, notes = [], []
    parents = git(repo, "rev-list", "--parents", "-n", "1", commit).decode().split()
    if len(parents) != 2:
        return [f"{commit[:12]}: a recipe commit has exactly one parent"], []
    parent = parents[1]
    if not TRAILER.search(git(repo, "log", "-1", "--format=%B", commit).decode()):
        problems.append(f"{commit[:12]}: the message needs the trailer 'Recipe: <tool>@<version>'")
    with tempfile.TemporaryDirectory() as tmp:
        rerun, before, after = Path(tmp, "rerun"), Path(tmp, "before"), Path(tmp, "after")
        for folder, rev in ((rerun, parent), (before, parent), (after, commit)):
            folder.mkdir()
            extract(repo, rev, folder)
        run = subprocess.run(recipe, shell=True, cwd=rerun, capture_output=True, text=True)
        if run.returncode != 0:
            problems.append(f"the recipe failed on the parent (exit {run.returncode}): {run.stderr[-300:]}")
        else:
            expected, actual = tree(after), tree(rerun)
            for path in sorted(set(expected) | set(actual)):
                if expected.get(path) != actual.get(path):
                    problems.append(f"{path}: re-running the recipe on the parent does not reproduce the commit")
        n_before, err_before = count_tests(count, before)
        n_after, err_after = count_tests(count, after)
        if n_before is None or n_after is None:
            problems.append(f"the count command failed: {(err_before or err_after).strip()}")
        elif n_before != n_after:
            problems.append(f"the test count changed: {n_before} before, {n_after} after")
    diff = git(repo, "diff", "-U0", parent, commit).decode(errors="replace")
    current = ""
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line[:1] in "+-" and not line.startswith(("+++", "---")) and "test" in current.lower() \
                and ASSERTION.search(line):
            notes.append(f"{current}: {line}")
    return problems, notes


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("commit")
    parser.add_argument("--recipe", required=True)
    parser.add_argument("--count", required=True)
    args = parser.parse_args(argv[1:])
    problems, notes = check(Path("."), args.commit, args.recipe, args.count)
    for p in problems:
        print(p)
    for n in notes:
        print(f"for the reviewer, assertion line changed: {n}")
    if not problems:
        print(f"check_recipe_commit: {args.commit[:12]} reproduces, the test count is unchanged, "
              f"{len(notes)} assertion line(s) to confirm")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest scripts/test_check_recipe_commit.py 2>&1 | tail -3`
Expected: `Ran 6 tests … OK`.

- [ ] **Step 5: The rule in ADR 0012 and core's text**

1. `docs/adr/0012-mechanical-recipe-commit.md`: Status accepted (owner, 2026-10-26); Context (a framework upgrade changes dependency versions and test syntax, which core's gates forbid; without an exception every upgrade stops or teaches the agent to bend gates); Decision: the five conditions **verbatim from the spec**; Precedent (Google's and Chromium's large-scale change processes review mechanical changes separately and still need a human approver); Consequences (the check script; AI-agent output never qualifies; .NET's deterministic coverage is small; OpenRewrite C# recipes are a licence decision).
2. `aidlc-build/SKILL.md`: new step before "Write the tests first": "**When the bundle has a RECIPE, the recipe commit comes first.** On a clean tree, run exactly the approved command and change nothing by hand. Commit only its output, with the trailer `Recipe: <tool>@<version>`. Run the recipe check named in AGENTS.md (`scripts/check_recipe_commit.py <commit> --recipe … --count …`) and stop for the person's review of that commit. Fixes come after it, as ordinary steps under every gate." Replace the Stop-if line "A test can only pass by changing an existing assertion. Never change it: the criterion's owner decides." with "A test can only pass by changing an existing assertion. Never change it: the criterion's owner decides. The one exception is an approved recipe commit, which may change test syntax but never what an assertion checks (ADR 0012)." Add a Common excuses row: "The recipe left one small error; I will fix it in the same commit." | "The recipe commit holds only the tool's output. Fix it in the next commit, under every gate."
3. `reviewer-compliance.md` Work: add "A commit with a `Recipe:` trailer holds only what the bundle's RECIPE approved; the recipe check's output is in the pull request; every assertion line it lists still checks the same thing."
4. `aidlc-review/assets/pr-description.md`: add a line `RECIPE COMMITS  <sha — tool@version — recipe check output> | none`.
5. `starter/repo/AGENTS.md` and `agents-md.md` Boundaries: append to the assertion line " (The one exception: an approved mechanical recipe commit, checked by `scripts/check_recipe_commit.py`.)" and add a Commands line `- Recipe check, after a recipe commit: \`python3 scripts/check_recipe_commit.py <commit> --recipe "<approved command>" --count "<test count command>"\``.

- [ ] **Step 6: Validate and run every test, then commit**

Run: `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -2`
Expected: `0 problem(s)`; `OK` (40 tests).

```bash
git add starter/repo/scripts/check_recipe_commit.py scripts/test_check_recipe_commit.py \
  docs/adr/0012-mechanical-recipe-commit.md plugins/aidlc/skills/aidlc-build/SKILL.md \
  plugins/aidlc/agents/reviewer-compliance.md plugins/aidlc/skills/aidlc-review/assets/pr-description.md \
  starter/repo/AGENTS.md plugins/aidlc/skills/aidlc-onboard/assets/agents-md.md
git commit -m "feat(core): the mechanical recipe commit (ADR 0012) and check_recipe_commit.py"
```

---

### Task 4: The `aidlc-modernize` plugin: method skills, parity script, parity-checker

**Files:**
- Create: `plugins/aidlc-modernize/.claude-plugin/plugin.json`; `plugins/aidlc-modernize/skills/modernize-assess/` (`SKILL.md`, `assets/assessment.md`), `modernize-characterize/SKILL.md`, `modernize-wave-plan/` (`SKILL.md`, `assets/wave-plan.md`), `modernize-parity/` (`SKILL.md`, `assets/parity-report.md`, `scripts/parity.py`), `modernize-cutover/` (`SKILL.md`, `assets/cutover-checklist.md`, `assets/decommission.md`); `plugins/aidlc-modernize/agents/parity-checker.md`; `scripts/test_parity.py`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: the pack contract (Task 2) and the recipe rule (Task 3).
- Produces: `parity.compare(old: str, new: str, inputs: Path, ignore: list[str]) -> list[tuple[str, str, str]]` (input, `SAME`/`DIFFERENT`/`NOISY`, detail); CLI `python3 parity.py --old "<cmd {input}>" --new "<cmd {input}>" --inputs <dir> --out <report.md> [--ignore <regex>]…`, exit 0 only when all SAME, 2 when there is no input.

- [ ] **Step 1: Write the failing parity tests** — `scripts/test_parity.py`:

```python
"""Tests for plugins/aidlc-modernize/skills/modernize-parity/scripts/parity.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "aidlc-modernize" / "skills"
                       / "modernize-parity" / "scripts"))
import parity  # noqa: E402

PY = sys.executable


class ParityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "a.csv").write_text("x,1\n")
        (self.inputs / "b.csv").write_text("y,2\n")

    def tearDown(self):
        self.tmp.cleanup()

    def program(self, name: str, body: str) -> str:
        path = self.root / f"{name}.py"
        path.write_text("import sys\ndata = open(sys.argv[1]).read()\n" + body)
        return f"{PY} {path} {{input}}"

    def verdicts(self, old, new, ignore=()):
        return {name: verdict for name, verdict, _ in parity.compare(old, new, self.inputs, list(ignore))}

    def test_same_output_is_same(self):
        prog = self.program("p", "print(data.upper())\n")
        self.assertEqual(self.verdicts(prog, prog), {"a.csv": "SAME", "b.csv": "SAME"})

    def test_a_different_output_is_different(self):
        old = self.program("old", "print(data.upper())\n")
        new = self.program("new", "print(data)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"DIFFERENT"})

    def test_a_different_exit_code_is_different(self):
        old = self.program("old", "print(data)\n")
        new = self.program("new", "print(data)\nsys.exit(3)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"DIFFERENT"})

    def test_crlf_from_windows_against_lf_is_same(self):
        old = self.program("old", "sys.stdout.buffer.write(data.replace('\\n', '\\r\\n').encode())\n")
        new = self.program("new", "sys.stdout.write(data)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"SAME"})

    def test_run_to_run_noise_is_reported_not_hidden(self):
        old = self.program("old", "import time\nprint(data, time.time_ns())\n")
        self.assertEqual(set(self.verdicts(old, old).values()), {"NOISY"})

    def test_an_ignore_pattern_removes_noise(self):
        old = self.program("old", "import time\nprint(data, time.time_ns())\n")
        self.assertEqual(set(self.verdicts(old, old, ignore=[r"\d{10,}"]).values()), {"SAME"})

    def test_no_input_files_exit_2(self):
        empty = self.root / "empty"
        empty.mkdir()
        prog = self.program("p", "print(data)\n")
        code = parity.main(["parity.py", "--old", prog, "--new", prog, "--inputs", str(empty),
                            "--out", str(self.root / "r.md")])
        self.assertEqual(code, 2)

    def test_the_report_lists_every_input(self):
        prog = self.program("p", "print(data)\n")
        out = self.root / "report.md"
        code = parity.main(["parity.py", "--old", prog, "--new", prog, "--inputs", str(self.inputs),
                            "--out", str(out)])
        self.assertEqual(code, 0)
        text = out.read_text()
        self.assertIn("a.csv", text)
        self.assertIn("b.csv", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and watch them fail**

Run: `python3 -m unittest scripts/test_parity.py 2>&1 | tail -3`
Expected: ERROR `No module named 'parity'`.

- [ ] **Step 3: Write `plugins/aidlc-modernize/skills/modernize-parity/scripts/parity.py`**

```python
#!/usr/bin/env python3
"""Runs the old and the new version of a program on the same inputs and reports every difference.

    python3 parity.py --old "<command>" --new "<command>" --inputs <folder> --out <report.md> [--ignore <regex>]...

Each command contains {input}, replaced by the input file's path. The old version runs twice per input: a difference
between its own two runs is noise, reported as NOISY until an --ignore pattern removes it, so noise is never mistaken
for parity. Output is compared after line endings are normalised (a Windows program prints CRLF) and every --ignore
match is replaced. Exit 0 only when every input gives the same exit code and output; 1 otherwise; 2 when there is no
input. Standard library only; part of aidlc-modernize."""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path


def run(template: str, path: Path) -> tuple[int, str]:
    command = template.replace("{input}", shlex.quote(str(path)))
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout


def normalise(text: str, ignore: list[re.Pattern]) -> str:
    text = text.replace("\r\n", "\n")
    for pattern in ignore:
        text = pattern.sub("<ignored>", text)
    return text


def first_difference(a: str, b: str) -> str:
    for number, (x, y) in enumerate(zip(a.split("\n"), b.split("\n")), start=1):
        if x != y:
            return f"line {number}: old `{x}` new `{y}`"
    return "the outputs have a different number of lines"


def compare(old: str, new: str, inputs: Path, ignore: list[str]) -> list[tuple[str, str, str]]:
    """(input, verdict, detail) for each input file, sorted by name; verdict SAME, DIFFERENT or NOISY."""
    patterns = [re.compile(p) for p in ignore]
    rows = []
    for path in sorted(p for p in inputs.iterdir() if p.is_file()):
        (c1, o1), (c2, o2), (c3, o3) = run(old, path), run(old, path), run(new, path)
        o1, o2, o3 = (normalise(t, patterns) for t in (o1, o2, o3))
        if (c1, o1) != (c2, o2):
            rows.append((path.name, "NOISY", first_difference(o1, o2) if o1 != o2 else f"exit {c1} vs {c2}"))
        elif (c1, o1) != (c3, o3):
            rows.append((path.name, "DIFFERENT", f"exit {c1} vs {c3}" if c1 != c3 else first_difference(o1, o3)))
        else:
            rows.append((path.name, "SAME", ""))
    return rows


def report(rows: list[tuple[str, str, str]], old: str, new: str, ignore: list[str]) -> str:
    lines = ["# Parity report", "", f"- Old: `{old}`", f"- New: `{new}`",
             f"- Ignored patterns: {', '.join(f'`{p}`' for p in ignore) or 'none'}",
             f"- Result: {sum(v == 'SAME' for _, v, _ in rows)} of {len(rows)} inputs the same", "",
             "| Input | Verdict | First difference |", "|---|---|---|"]
    lines += [f"| {name} | {verdict} | {detail.replace('|', '/')} |" for name, verdict, detail in rows]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--old", required=True)
    parser.add_argument("--new", required=True)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ignore", action="append", default=[])
    args = parser.parse_args(argv[1:])
    if not args.inputs.is_dir() or not any(p.is_file() for p in args.inputs.iterdir()):
        print(f"parity: no input files in {args.inputs}")
        return 2
    rows = compare(args.old, args.new, args.inputs, args.ignore)
    args.out.write_text(report(rows, args.old, args.new, args.ignore), encoding="utf-8")
    same = sum(v == "SAME" for _, v, _ in rows)
    print(f"parity: {same} of {len(rows)} inputs the same; report {args.out}")
    return 0 if same == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest scripts/test_parity.py 2>&1 | tail -3`
Expected: `Ran 8 tests … OK`.

- [ ] **Step 5: The plugin manifest and marketplace entry**

`plugins/aidlc-modernize/.claude-plugin/plugin.json`:

```json
{
  "name": "aidlc-modernize",
  "version": "0.1.0",
  "description": "Modernisation for aidlc: assess, characterise, wave plans, parity and cutover, with factories for .NET and Java. Switch it on only in repositories being modernised.",
  "author": {"name": "Prashant Sharma"},
  "license": "MIT",
  "dependencies": [{"name": "aidlc", "version": "^2.0"}]
}
```

Add to `.claude-plugin/marketplace.json` `plugins`:

```json
    {
      "name": "aidlc-modernize",
      "source": "./plugins/aidlc-modernize",
      "description": "Modernisation method and .NET and Java factories. Requires aidlc. Switch on per repository."
    }
```

- [ ] **Step 6: Write the method skills** (house sections, each Gate ending "You draft; you never approve."; the Inputs of the manual ones carry core's "Where this runs" paragraph, word for word as in `aidlc-specify`)

- `modernize-assess` — `disable-model-invocation: true`; description "Assesses a system for modernisation and proposes how far to go: retire, retain, rehost, replatform or refactor, and the lane (simple, standard, programme). Use when aidlc-start routes modernisation work here." Steps: (1) inventory with the `explorer` agent: projects, target frameworks, packages, entry points, tests and coverage, stored data formats, consumers and contracts; (2) baselines with the repository's commands, each recorded or marked "not available, because …": test count and coverage, SBOM with CVE and licence findings, a performance baseline (start-up, a representative run, memory) when the system can run; (3) the decision among retire, retain, rehost, replatform, refactor, with reasons; (4) the lane from the evidence table (repositories touched, a recipe covers it, coverage, consumers, data changes), the heavier lane when unsure; (5) the factory skill and recipe the plan should use (from the pack line in AGENTS.md) and every dependency the port needs, as decisions for the person; (6) data one-way doors (formats the new version cannot read) with a decision each; (7) write `plans/<KEY>/assessment.md` from `assets/assessment.md` (`stories/<KEY>/` for a programme). Stop if: the old version cannot be built or run (characterisation impossible: say so and stop); AGENTS.md declares no factory for this stack; a baseline is missing and nobody accepts it. Next stage: `aidlc-plan`, whose first slice is characterisation (lanes standard and programme).
- `modernize-characterize` — model-invocable; description "Pins what legacy code does today with characterisation tests and parity inputs, before any change. Use when an approved task bundle's USE SKILLS names it." Steps: stop unless an approved bundle names it; list the behaviours to pin from the assessment (normal paths, every error message, rounding, culture and formatting, stored-data reads); write tests named `Characterise_<behaviour>` that assert today's output, quirks included, and run them against the old build: all green before any change, and each must be shown able to fail (break one expectation, see red, restore); never "fix" a quirk here, record it for the spec; write the parity inputs to `parity/inputs/` (one file per behaviour group); points to core's characterisation rule in `aidlc-plan` and `aidlc-build` instead of restating it.
- `modernize-wave-plan` — manual; description "Splits a modernisation programme into strangler-fig waves, each a story the product owner creates. Use when the assessment's lane is programme." Steps: seams and the routing facade (strangler fig, as in core's `deprecation-and-migration`); wave order by risk and dependency; per wave: scope, repositories, data plan, rollback, exit criteria; legacy freeze to fixes only during waves; write `stories/<KEY>/wave-plan.md` from `assets/wave-plan.md`; the product owner creates each wave's story (never split an existing story). Runs at the workspace root.
- `modernize-parity` — manual; description "Runs the old and new versions on the same inputs with the parity script and drafts the parity report. Use when the last build slice of a standard or programme modernisation is done, before aidlc-verify." Steps: build the old version from the base commit into the ignored folder `parity/old/` (`git archive <base> | tar -x -C parity/old`, then the repository's build command there); run `scripts/aidlc/parity.py` (copied from this skill's `scripts/parity.py` in the plan's tools slice) with old and new run commands from AGENTS.md, each in its own working folder under `parity/out/`; any NOISY row gets an `--ignore` pattern only with a reason a person accepts; send DIFFERENT and NOISY rows to the `parity-checker` agent; write `plans/<KEY>/parity-report.md` from `assets/parity-report.md` with the script's report attached; add the dependency and CVE diff against the assessment's baseline. Gate: the owner approves the report before release or cutover.
- `modernize-cutover` — manual; description "Switches traffic from the old system to the new one with rollback ready, then decommissions the old one after a quiet period. Use after a wave or a standard-lane port is released behind a flag or canary." Steps: preconditions (parity report approved, rollback rehearsed including data); switch in steps with the stop criteria from `aidlc-release`; data rollback plan for one-way doors; decommission only after the quiet period with zero traffic, with data retention and archival decided; write from `assets/cutover-checklist.md` and `assets/decommission.md`.
- Assets: `assessment.md` (DECISION, LANE with the evidence table, INVENTORY, BASELINES, DATA one-way doors, FACTORY and RECIPE, DEPENDENCIES to approve, OPEN), `wave-plan.md` (SEAMS, WAVES table: scope, repositories, data, rollback, exit, story key once created), `parity-report.md` (SUMMARY, the script's table attached, TRIAGE table: input, verdict, expected / defect / noise, evidence, decision; DEPENDENCY AND CVE DIFF; APPROVED BY), `cutover-checklist.md`, `decommission.md`.
- `plugins/aidlc-modernize/agents/parity-checker.md`: `tools: Read, Glob, Grep`; triages each DIFFERENT or NOISY row as expected (cite the approved change), defect (cite the input and line; back to `aidlc-build`) or noise (propose an ignore pattern and why it hides no behaviour); never edits; returns the triage table; "You never approve."

- [ ] **Step 7: Validate and run every test, then commit**

Run: `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -2 && claude plugin validate . 2>&1 | tail -1`
Expected: `validate: 2 plugin(s), 26 skill(s), 0 problem(s)`; `OK` (48 tests); `✔ Validation passed`.

```bash
git add plugins/aidlc-modernize scripts/test_parity.py .claude-plugin/marketplace.json
git commit -m "feat(aidlc-modernize): 0.1.0 with the method skills, the parity script and the parity-checker agent"
```

---

### Task 5: The factories: `dotnet-modernize` (with `retarget.py`) and `java-modernize`

**Files:**
- Create: `plugins/aidlc-modernize/skills/dotnet-modernize/SKILL.md`, its `references/framework-to-net10.md`, `references/aspnet-incremental.md`, `references/wcf.md`, `references/ef6-to-efcore.md`, `references/tools.md`, `scripts/retarget.py`; `plugins/aidlc-modernize/skills/java-modernize/SKILL.md`, its `references/java-lts.md`, `references/jakarta.md`, `references/spring-boot.md`, `references/build.md`; `scripts/test_retarget.py`

**Interfaces:**
- Produces: `retarget.retarget(text: str, old: str, new: str) -> str` (raises `ValueError` for a non-SDK project or one targeting neither); CLI `python3 retarget.py --from net48 --to net10.0 <project>…`, `--version` prints `1.0.0`; trailer `Recipe: aidlc-retarget@1.0.0`.

- [ ] **Step 1: Write the failing tests** — `scripts/test_retarget.py`:

```python
"""Tests for plugins/aidlc-modernize/skills/dotnet-modernize/scripts/retarget.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "aidlc-modernize" / "skills"
                       / "dotnet-modernize" / "scripts"))
import retarget  # noqa: E402

LEGACY = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net48</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="all" />
  </ItemGroup>
  <ItemGroup>
    <PackageReference Include="xunit.v3" Version="2.0.3" />
  </ItemGroup>
</Project>
"""


class RetargetTest(unittest.TestCase):
    def test_changes_the_target_and_drops_the_reference_assemblies(self):
        out = retarget.retarget(LEGACY, "net48", "net10.0")
        self.assertIn("<TargetFramework>net10.0</TargetFramework>", out)
        self.assertNotIn("Microsoft.NETFramework.ReferenceAssemblies", out)
        self.assertIn('Include="xunit.v3"', out)
        self.assertEqual(out.count("<ItemGroup>"), 1)

    def test_multi_targeting_swaps_only_the_old_framework(self):
        text = LEGACY.replace("<TargetFramework>net48</TargetFramework>",
                              "<TargetFrameworks>net48;net8.0</TargetFrameworks>")
        self.assertIn("<TargetFrameworks>net10.0;net8.0</TargetFrameworks>", retarget.retarget(text, "net48", "net10.0"))

    def test_a_second_run_changes_nothing(self):
        once = retarget.retarget(LEGACY, "net48", "net10.0")
        self.assertEqual(retarget.retarget(once, "net48", "net10.0"), once)

    def test_an_old_style_project_is_refused(self):
        with self.assertRaises(ValueError):
            retarget.retarget('<Project ToolsVersion="15.0"><PropertyGroup/></Project>', "net48", "net10.0")

    def test_a_project_targeting_neither_is_refused(self):
        with self.assertRaises(ValueError):
            retarget.retarget(LEGACY.replace("net48", "net472"), "net48", "net10.0")

    def test_crlf_and_bom_are_kept_and_nothing_is_written_on_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "a.csproj"), Path(tmp, "b.csproj")
            good.write_bytes(b"\xef\xbb\xbf" + LEGACY.replace("\n", "\r\n").encode())
            bad.write_text('<Project ToolsVersion="15.0"/>')
            self.assertEqual(retarget.main(["retarget.py", "--from", "net48", "--to", "net10.0", str(good), str(bad)]), 1)
            self.assertIn(b"net48", good.read_bytes())
            self.assertEqual(retarget.main(["retarget.py", "--from", "net48", "--to", "net10.0", str(good)]), 0)
            data = good.read_bytes()
            self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"<TargetFramework>net10.0</TargetFramework>\r\n", data)
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run and watch them fail**

Run: `python3 -m unittest scripts/test_retarget.py 2>&1 | tail -3`
Expected: ERROR `No module named 'retarget'`.

- [ ] **Step 3: Write `plugins/aidlc-modernize/skills/dotnet-modernize/scripts/retarget.py`**

```python
#!/usr/bin/env python3
"""A deterministic recipe: changes the target framework of SDK-style .NET projects and removes the .NET Framework
reference-assemblies package, which a modern target does not need. Same input, same output; a second run changes
nothing. Line endings and a byte-order mark are kept.

    python3 retarget.py --from net48 --to net10.0 <project.csproj>...

Fails with exit 1, writing no file, when any project is not SDK-style or targets neither framework.
Standard library only; part of aidlc-modernize (dotnet-modernize). Commit trailer: Recipe: aidlc-retarget@1.0.0"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION = "1.0.0"
BOM = b"\xef\xbb\xbf"
TFM = re.compile(r"(<TargetFrameworks?>)([^<]*)(</TargetFrameworks?>)")
REF_ASSEMBLIES = re.compile(r'[ \t]*<PackageReference Include="Microsoft\.NETFramework\.ReferenceAssemblies"'
                            r'[^>]*?(?:/>|>.*?</PackageReference>)[ \t]*\r?\n', re.DOTALL)
EMPTY_ITEM_GROUP = re.compile(r"[ \t]*<ItemGroup>\s*</ItemGroup>[ \t]*\r?\n")


def retarget(text: str, old: str, new: str) -> str:
    if "<Project Sdk=" not in text:
        raise ValueError("not an SDK-style project; convert it first (this recipe does not)")
    targets: list[str] = []

    def swap(m: re.Match) -> str:
        frameworks = [f.strip() for f in m.group(2).split(";") if f.strip()]
        targets.extend(frameworks)
        return m.group(1) + ";".join(new if f == old else f for f in frameworks) + m.group(3)

    text = TFM.sub(swap, text)
    if old not in targets and new not in targets:
        raise ValueError(f"targets neither {old} nor {new}")
    return EMPTY_ITEM_GROUP.sub("", REF_ASSEMBLIES.sub("", text))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--from", dest="old")
    parser.add_argument("--to", dest="new")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("projects", nargs="*", type=Path)
    args = parser.parse_args(argv[1:])
    if args.version:
        print(VERSION)
        return 0
    if not (args.old and args.new and args.projects):
        parser.error("--from, --to and at least one project are required")
    results, errors = {}, []
    for path in args.projects:
        raw = path.read_bytes()
        bom = raw.startswith(BOM)
        try:
            results[path] = (bom, raw, retarget(raw[len(BOM) if bom else 0:].decode("utf-8"), args.old, args.new))
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
    if errors:
        print("\n".join(errors))
        return 1
    changed = 0
    for path, (bom, raw, text) in results.items():
        data = (BOM if bom else b"") + text.encode("utf-8")
        if data != raw:
            path.write_bytes(data)
            changed += 1
    print(f"retarget {VERSION}: {changed} project(s) changed, {len(results) - changed} already on {args.new}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the tests**

Run: `python3 -m unittest scripts/test_retarget.py 2>&1 | tail -3`
Expected: `Ran 6 tests … OK`.

- [ ] **Step 5: Write the factory skills** (house sections; model-invocable; each opens its Steps with "Stop unless an approved task bundle names this skill in USE SKILLS; say which stage comes first.")

- `dotnet-modernize` — description "Ports a .NET Framework 4.x project to .NET 10 (LTS): the retarget recipe, then each breaking change fixed tests-first. Use when an approved task bundle's USE SKILLS names it." Steps: (1) the bundle check; (2) SDK-style check: an old-style project is converted first, as its own hand slice under every gate; (3) the tools slice copies this skill's `scripts/retarget.py` (and, for parity, `modernize-parity`'s script) to `scripts/aidlc/`; (4) the recipe commit: `python3 scripts/aidlc/retarget.py --from net48 --to net10.0 <projects>` with the trailer `Recipe: aidlc-retarget@1.0.0`, then the recipe check (core's rule); (5) build, and map every error and warning to `references/framework-to-net10.md`; (6) fix each one tests-first under every gate; a package the port needs is a dependency decision (stop unless the plan approved it); (7) Windows-only APIs and analyzer CA1416 warnings are decisions, never suppressed silently. Stop if: the bundle does not name the skill; the fix needs System.Web, WCF hosting or EF6 to EF Core work (separate waves: `references/aspnet-incremental.md`, `references/wcf.md`, `references/ef6-to-efcore.md`); a tool is proposed that is not deterministic as the recipe (`references/tools.md`).
- `references/framework-to-net10.md` — a table of breaking changes with the fix and the test that proves it: `BinaryFormatter` removed in .NET 9 (serialisation throws; replace with System.Text.Json or another format; stored files are a one-way door: decide migrate, rebuild or keep a reader); `System.Configuration.ConfigurationManager` (the package of that name, or Microsoft.Extensions.Configuration: a dependency decision); AppDomains, .NET Remoting and Code Access Security unsupported; `WebClient` and `WebRequest` obsolete (use `HttpClient`); `System.Drawing.Common` Windows-only; globalisation on Linux uses ICU, so culture-sensitive formatting and comparison can differ from Windows (pin the culture; parity on both platforms); default `Math.Round` stays to-even; `App.config` is not read by default (moves with the configuration decision). Version facts: .NET 10 is LTS; .NET 8 support ends 10 November 2026.
- `references/aspnet-incremental.md` — ASP.NET to ASP.NET Core by strangler fig: an ASP.NET Core app in front with YARP forwarding to the old app, System.Web adapters for shared code, route by route, each route its own story; session and authentication shared during the move.
- `references/wcf.md` — options: CoreWCF (keep the SOAP contract), gRPC or HTTP APIs (a contract change for consumers: `aidlc-design` and versioning); client side: the WCF client packages for .NET.
- `references/ef6-to-efcore.md` — EF6 6.3+ runs on .NET, so the data-access move is a separate, later wave; differences to test: query translation, lazy loading, cascade rules, migrations history.
- `references/tools.md` — the .NET Upgrade Assistant is deprecated (Microsoft Learn, March 2026) in favour of GitHub Copilot's modernization agent, which is an AI agent: its changes are ordinary code under every gate, never a recipe commit; OpenRewrite's C# recipes are available through Moderne under a proprietary licence (an organisation's licence decision); `retarget.py` is this factory's own deterministic recipe.
- `java-modernize` — description "Ports Java services to a current LTS and Spring Boot 4 with deterministic OpenRewrite recipes, then fixes tests-first. Use when an approved task bundle's USE SKILLS names it." Body says plainly that this factory is written but not yet proven end to end. Steps mirror `dotnet-modernize`: the bundle check; the recipe commit with an approved OpenRewrite recipe and version (Maven or Gradle plugin; check each recipe module's licence, since some are Apache 2.0 and some are under Moderne's licence); the recipe check; fixes tests-first. References: `java-lts.md` (8, 11 or 17 to 21 or 25), `jakarta.md` (`javax.*` to `jakarta.*`), `spring-boot.md` (2.x → 3.5 → 4.x: Spring Boot 3.5's open-source support ended 30 June 2026; Boot 4 brings Jakarta EE 11 and Jackson 3, so JSON output can change: contract and parity checks), `build.md` (Maven or Gradle, plugins, dependency versions).

- [ ] **Step 6: Validate and run every test, then commit**

Run: `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -2 && claude plugin validate . 2>&1 | tail -1`
Expected: `validate: 2 plugin(s), 28 skill(s), 0 problem(s)`; `OK` (54 tests); `✔ Validation passed`.

```bash
git add plugins/aidlc-modernize/skills/dotnet-modernize plugins/aidlc-modernize/skills/java-modernize scripts/test_retarget.py
git commit -m "feat(aidlc-modernize): the .NET factory with the retarget recipe, and the Java factory (not yet proven)"
```

---

### Task 6: Docs, quickstarts and decisions

**Files:**
- Create: `docs/adr/0011-plugins-and-packs.md`, `docs/operating-model/modernisation.md`
- Modify: `README.md`, `AGENTS.md`, `docs/codebase-map.md`, `docs/quickstart/claude-code.md`, `docs/quickstart/copilot.md`, `docs/quickstart/codex-cursor.md`, `docs/operating-model/workspace-and-repositories.md`, `docs/design/2026-10-25-skills-first.md`

- [ ] **Step 1:** `docs/adr/0011-plugins-and-packs.md`: Status accepted (2026-10-26); Context (growth; the research run: silent failure when core depends on an optional pack; no optional dependency); Decision (one marketplace, core never names a pack, the pack contract, versions and tags, factories split later by owner); Alternatives rejected (one plugin forever: every factory everywhere; splitting the practice skills: cross-links break, ~500 tokens saved; a session-start router: two routers on hosts that route natively); Consequences (validator rules; Copilot has no dependencies: list every plugin; cloud and `-p` sessions do not add repository marketplaces: CI installs plugins explicitly).
- [ ] **Step 2:** `docs/operating-model/modernisation.md`: the three lanes table and the step chains from the spec, where each step runs, the gates the plugin adds, the recipe rule in one paragraph pointing to ADR 0012, and the demo as the worked example (filled in by Task 8).
- [ ] **Step 3:** Quickstarts. Claude Code: install with `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc`; a repository being modernised also enables `aidlc-modernize@aidlc` in `.claude/settings.json` and declares it in AGENTS.md; CI and cloud sessions install plugins explicitly. Copilot: plugins through Copilot CLI and the cloud agent (`enabledPlugins` in `.github/copilot/settings.json`; list both plugins, since Copilot has no dependencies), or copy `plugins/aidlc/skills/*` and, where needed, `plugins/aidlc-modernize/skills/*` into `.github/skills/`; agents from `plugins/*/agents/` as `.agent.md`, keeping `tools:`. Codex and Cursor: copy the same folders into `.agents/skills/` or `.cursor/skills/`. Every copy command uses the new paths.
- [ ] **Step 4:** README (install table with the new paths; a "Packs" section with `aidlc-modernize`; the skills table split by plugin), AGENTS.md map (`plugins/aidlc/`, `plugins/aidlc-modernize/`, `starter/repo/scripts/`), `docs/codebase-map.md` (areas and "where common changes go" for a new pack: a folder under `plugins/`, a marketplace entry, a dependency on `aidlc` with a range, a version), `workspace-and-repositories.md` (a line on packs).
- [ ] **Step 5:** In `docs/design/2026-10-25-skills-first.md`, replace "agent-skills uses a meta-skill (`using-agent-skills`), loaded by a session-start hook in Claude Code, that maps requests to skills before the agent acts." with "agent-skills ships a meta-skill (`using-agent-skills`) that maps requests to skills. In Claude Code it is an ordinary skill chosen by its description: its session-start hook is deliberately not wired, because hosts that route skills natively would run two routers (its `hooks/session-start.sh` and `docs/getting-started.md`)."
- [ ] **Step 6:** Run `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | tail -1 && claude plugin validate . 2>&1 | tail -1` (expected: 0 problems, OK, passed), check every changed link resolves (`grep -o '](\([^)#]*\)' <file>` and test each path), then commit: `git add` the files above; `git commit -m "docs: plugins and packs (ADR 0011), modernisation operating model, quickstarts for the new layout"`.

---

### Task 7: The demo's legacy app, `carrier-rates`

**Files (in `~/work/shipment-tracking`):**
- Create repository `carrier-rates/`: `.gitignore`, `src/CarrierRates/CarrierRates.csproj`, `App.config`, `RateTable.cs`, `Pricing.cs`, `RateCache.cs`, `Program.cs`, `samples/shipments.csv`, `scripts/run.sh`, then (onboarding) `AGENTS.md`, `CLAUDE.md`, `.claude/settings.json`, `scripts/check_packs.py`, `scripts/check_recipe_commit.py`, `CODEOWNERS`
- Modify: `WORKSPACE.md`, `.claude/settings.json` (workspace), `stories/` (later)

- [ ] **Step 1: Create the repository with its local identity**

```bash
cd ~/work/shipment-tracking && mkdir carrier-rates && cd carrier-rates && git init -q
git config user.name prashantsharma18 && git config user.email 6386481+prashantsharma18@users.noreply.github.com
```

- [ ] **Step 2: The legacy code, as found** (C# 7.3, .NET Framework 4.8, no tests)

`src/CarrierRates/CarrierRates.csproj`:

```xml
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net48</TargetFramework>
    <LangVersion>7.3</LangVersion>
    <RootNamespace>CarrierRates</RootNamespace>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NETFramework.ReferenceAssemblies" Version="1.0.3" PrivateAssets="all" />
  </ItemGroup>
  <ItemGroup>
    <Reference Include="System.Configuration" />
  </ItemGroup>
</Project>
```

`src/CarrierRates/App.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <appSettings>
    <add key="FuelSurchargePercent" value="12.5" />
    <add key="CacheFile" value="rates.cache" />
  </appSettings>
</configuration>
```

`src/CarrierRates/RateTable.cs`:

```csharp
using System.Collections.Generic;

namespace CarrierRates
{
    /// <summary>Price per kilogram by zone; express costs 1.6 times standard.</summary>
    public static class RateTable
    {
        static readonly Dictionary<string, decimal> PerKg = new Dictionary<string, decimal>
        {
            { "A", 1.25m }, { "B", 1.85m }, { "C", 2.40m }
        };

        public const decimal ExpressFactor = 1.6m;

        public static bool TryGetPerKg(string zone, out decimal perKg) => PerKg.TryGetValue(zone, out perKg);
    }
}
```

`src/CarrierRates/Pricing.cs`:

```csharp
using System;

namespace CarrierRates
{
    public static class Pricing
    {
        /// <summary>Charge for one shipment. Math.Round's default (to even) is what invoices have always used.</summary>
        public static decimal Charge(decimal weightKg, decimal perKg, bool express, decimal fuelPercent)
        {
            var basePrice = weightKg * perKg * (express ? RateTable.ExpressFactor : 1m);
            return Math.Round(basePrice * (1m + fuelPercent / 100m), 2);
        }
    }
}
```

`src/CarrierRates/RateCache.cs`:

```csharp
using System.Collections.Generic;
using System.IO;
using System.Runtime.Serialization.Formatters.Binary;

namespace CarrierRates
{
    /// <summary>Remembers charges already computed, keyed by weight, zone and service, between runs.</summary>
    public sealed class RateCache
    {
        readonly string path;
        readonly Dictionary<string, decimal> charges;

        public RateCache(string path)
        {
            this.path = path;
            charges = File.Exists(path) ? Load(path) : new Dictionary<string, decimal>();
        }

        public bool TryGet(string key, out decimal charge) => charges.TryGetValue(key, out charge);

        public void Put(string key, decimal charge) => charges[key] = charge;

        public void Save()
        {
            using (var stream = File.Create(path))
                new BinaryFormatter().Serialize(stream, charges);
        }

        static Dictionary<string, decimal> Load(string path)
        {
            using (var stream = File.OpenRead(path))
                return (Dictionary<string, decimal>)new BinaryFormatter().Deserialize(stream);
        }
    }
}
```

`src/CarrierRates/Program.cs`:

```csharp
using System;
using System.Configuration;
using System.Globalization;
using System.IO;

namespace CarrierRates
{
    /// <summary>Prices a CSV of shipments (id,weightKg,zone,service) and prints id,charge for each line.</summary>
    public static class Program
    {
        public static int Main(string[] args)
        {
            if (args.Length != 1)
            {
                Console.Error.WriteLine("usage: CarrierRates <shipments.csv>");
                return 2;
            }
            var fuel = decimal.Parse(ConfigurationManager.AppSettings["FuelSurchargePercent"], CultureInfo.InvariantCulture);
            var cache = new RateCache(ConfigurationManager.AppSettings["CacheFile"]);
            foreach (var line in File.ReadAllLines(args[0]))
            {
                if (line.Length == 0 || line.StartsWith("id,")) continue;
                Console.WriteLine(PriceLine(line, fuel, cache));
            }
            cache.Save();
            return 0;
        }

        public static string PriceLine(string line, decimal fuelPercent, RateCache cache)
        {
            var parts = line.Split(',');
            if (parts.Length != 4) return parts[0] + ",ERROR malformed line";
            decimal weight;
            if (!decimal.TryParse(parts[1], NumberStyles.Number, CultureInfo.InvariantCulture, out weight) || weight <= 0)
                return parts[0] + ",ERROR bad weight";
            decimal perKg;
            if (!RateTable.TryGetPerKg(parts[2], out perKg)) return parts[0] + ",ERROR unknown zone";
            var service = parts[3];
            if (service != "standard" && service != "express") return parts[0] + ",ERROR unknown service";
            var key = parts[1] + "|" + parts[2] + "|" + service;
            decimal charge;
            if (!cache.TryGet(key, out charge))
            {
                charge = Pricing.Charge(weight, perKg, service == "express", fuelPercent);
                cache.Put(key, charge);
            }
            return parts[0] + "," + charge.ToString("0.00", CultureInfo.InvariantCulture);
        }
    }
}
```

`samples/shipments.csv`:

```
id,weightKg,zone,service
S1,2.5,A,standard
S2,10,B,express
S3,0.032,A,standard
S4,1,Z,standard
S5,-1,A,standard
S6,3,C,overnight
S7,broken
```

`scripts/run.sh` (executable):

```bash
#!/usr/bin/env bash
# Runs the built CarrierRates on one CSV: the .NET Framework build through WSL interop (Windows' .NET Framework 4.8),
# or the .NET build with the dotnet host. Absolute paths are converted for the Windows program.
set -euo pipefail
bin="$(cd "$(dirname "$0")/.." && pwd)/src/CarrierRates/bin/Debug"
if [ -f "$bin/net48/CarrierRates.exe" ]; then
  chmod +x "$bin/net48/CarrierRates.exe"
  args=()
  for a in "$@"; do
    if [[ "$a" == /* ]]; then args+=("$(wslpath -w "$a")"); else args+=("$a"); fi
  done
  exec "$bin/net48/CarrierRates.exe" "${args[@]}"
fi
exec dotnet "$(ls "$bin"/net*/CarrierRates.dll | head -n 1)" "$@"
```

`.gitignore`:

```
bin/
obj/
*.cache
parity/old/
parity/out/
```

- [ ] **Step 3: Build and run the legacy app; read the output**

Run: `cd ~/work/shipment-tracking/carrier-rates && dotnet build src/CarrierRates/CarrierRates.csproj -nologo -v q 2>&1 | grep -E "Error\(s\)" && scripts/run.sh "$PWD/samples/shipments.csv"`
Expected: `0 Error(s)`, then

```
S1,3.52
S2,33.30
S3,0.04
S4,ERROR unknown zone
S5,ERROR bad weight
S6,ERROR unknown service
S7,ERROR malformed line
```

(S1: 2.5 × 1.25 × 1.125 = 3.515625 → 3.52; S2: 10 × 1.85 × 1.6 × 1.125 = 33.30; S3: 0.032 × 1.25 × 1.125 = 0.045, which rounds to even → 0.04. If a line differs, the legacy behaviour is what it is: record the real output, do not change the code.) Run it a second time and confirm the same output (the second run reads the BinaryFormatter cache).

- [ ] **Step 4: Commit the legacy state**

```bash
git add .gitignore src/CarrierRates samples scripts/run.sh
git commit -m "carrier-rates as found: .NET Framework 4.8 console, no tests"
```

- [ ] **Step 5: Onboard (as `aidlc-onboard` would; this is the demo's setup, done by hand from the starter)**

- `AGENTS.md` from `starter/repo/AGENTS.md`: purpose (prices shipments for carrier invoices; owner Prashant Sharma), stack (.NET Framework 4.8, C# 7.3; built by the .NET 10 SDK on Linux with reference assemblies; run on Windows' .NET Framework through WSL interop), Commands (build `dotnet build src/CarrierRates/CarrierRates.csproj`; run `scripts/run.sh <csv>`; tests: none yet; pack check; recipe check), Legacy (all of `src/`: no tests pin its behaviour), Packs used here:

```
## Packs used here
- `aidlc-modernize`: `aidlc-modernize:modernize-assess`, `aidlc-modernize:modernize-characterize`, `aidlc-modernize:modernize-parity`, `aidlc-modernize:dotnet-modernize`
```

- `CLAUDE.md` (`@AGENTS.md`); `CODEOWNERS` from the starter; `scripts/check_packs.py` and `scripts/check_recipe_commit.py` copied from `starter/repo/scripts/`.
- `.claude/settings.json`: copy `shipments-api/.claude/settings.json` (the demo's isolation rules and plugin allows) and set `enabledPlugins` to include `"aidlc@aidlc": true` and `"aidlc-modernize@aidlc": true`.
- Workspace: add `carrier-rates` to `WORKSPACE.md`'s repositories table and `Edit(/carrier-rates/**)` to the workspace `.claude/settings.json` deny list.

Run: `python3 scripts/check_packs.py` → Expected: `check_packs: 1 pack(s), 4 skill(s) declared; all installed`.

```bash
git add AGENTS.md CLAUDE.md CODEOWNERS .claude/settings.json scripts/check_packs.py scripts/check_recipe_commit.py
git commit -m "onboard carrier-rates to aidlc with the aidlc-modernize pack"
cd .. && git add WORKSPACE.md .claude/settings.json && git commit -m "workspace: carrier-rates (legacy pricing), root edits denied"
```

- [ ] **Step 6: The work item.** With the plan approved, create SHIP-3 through lab-jira (Story, label `aidlc-demo`): "Move carrier-rates from .NET Framework 4.8 to .NET 10 (support and hosting): invoices must not change." Acceptance criteria: the same charges and messages for every sample and characterised input; the old cache file is not needed (rebuild is acceptable, decided at assessment); runs on Linux under .NET 10.

---

### Task 8: SHIP-3 end to end through the standard lane

Headless sessions as in Plan 7 (`claude -p`, model Sonnet, `--permission-mode acceptEdits`), now with `--plugin-dir /home/psharma/demos/aidlc/plugins` (loads both plugins). The user decides at each gate.

- [ ] **Step 1: Pre-flight.** In `carrier-rates`: `python3 scripts/check_packs.py` passes; a probe session lists both `aidlc:` and `aidlc-modernize:` skills; a sandboxed session can run `scripts/run.sh` (WSL interop inside the sandbox). Any failure is a finding, fixed in the framework before the run.
- [ ] **Step 2: `aidlc-start SHIP-3`** in `carrier-rates` → Expected: one-repository route; the pack check runs; next stage `aidlc-modernize:modernize-assess`; `plans/SHIP-3/README.md`. Gate: route agreed.
- [ ] **Step 3: `modernize-assess`** → Expected: decision replatform; lane standard (no tests, a framework hop); BinaryFormatter cache as a one-way door (proposal: rebuild, it is a cache); the dependency for configuration as a decision; baselines with "not available" where true. Gate: the user approves lane and decisions.
- [ ] **Step 4: `aidlc-specify` then `aidlc-plan`** → Expected slices: tools (copy `retarget.py` and `parity.py` to `scripts/aidlc/`, add `scripts/run-tests.sh` that runs the xUnit v3 test executable through interop on net48 and natively on net10.0, and prints `Total: N`); characterise (USE SKILLS `aidlc-modernize:modernize-characterize`; a net48 xUnit v3 test project); recipe (RECIPE `aidlc-retarget@1.0.0 — python3 scripts/aidlc/retarget.py --from net48 --to net10.0 <both projects>`); fixes (BinaryFormatter, configuration). Gate: plan approved.
- [ ] **Step 5: `aidlc-build`** per slice → Expected: characterisation tests green on .NET Framework and each shown able to fail; the recipe commit passes `check_recipe_commit.py` (re-run reproduces, test count equal); after the recipe the build is red for the expected reasons; fixes are tests-first and green on .NET 10 under Linux; the progress notes list the skills loaded.
- [ ] **Step 6: `modernize-parity`** → Expected: `parity.py` with the old build (interop) and the new build (dotnet) on `parity/inputs/`: every input SAME after CRLF normalisation, or each difference triaged by `parity-checker`. Gate: the user approves the parity report.
- [ ] **Step 7: `aidlc-verify`, `aidlc-review`** → Expected: evidence local only (no CI); three reviewers plus compliance checking `Skills loaded` and the recipe commit. Gate: the user decides findings.
- [ ] **Step 8: Record.** `docs/verification/<run date>-modernize-dotnet.md` in aidlc (the date the run finishes): what ran where, outputs, decisions, every finding (P8-Fn) and its fix; update `docs/operating-model/modernisation.md`'s worked example; commit. Release and cutover are not run (the demo has no deployment); say so.

---

### Task 9: Release tags, final review, fix pass

- [ ] **Step 1:** Fresh reviewer on the most capable model over `main..HEAD`, with the spec, this plan and its Review Focus; one fix pass for Critical and Important findings, each test-first; minors recorded as deferred.
- [ ] **Step 2:** Run the full check: `python3 scripts/validate.py && python3 -m unittest discover -s scripts -p 'test_*.py' && claude plugin validate .` → 0 problems, OK, passed.
- [ ] **Step 3:** Tag both plugins locally from their folders: `(cd plugins/aidlc && claude plugin tag --dry-run)` then `claude plugin tag` (expected tags `aidlc--v2.0.0`, `aidlc-modernize--v0.1.0`; no `--push`). Report the rulings, the deferred minors and the open items (push and one pull request, Copilot check, Java factory proof).
