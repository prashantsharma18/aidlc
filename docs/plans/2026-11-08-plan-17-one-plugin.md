# aidlc as one plugin Implementation Plan (Plan 17, aidlc 5.0.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The repository is one Claude Code plugin, `aidlc`, at its root: the modernise pack is archived and the pack contract is gone, so a teammate installs one plugin with two commands and nothing else to understand.

**Architecture:** `skills/`, `agents/` and `evals/` move from `plugins/aidlc/` to the repository root, and `.claude-plugin/` holds both `plugin.json` and `marketplace.json`, whose one entry has `"source": "./"`. The validator checks that layout. Every pack mechanism leaves the skills, the starter files, the validator and the docs. A new test file, `scripts/test_one_plugin.py`, pins the result; its tests are written first and seen failing.

**Tech Stack:** Markdown, JSON, Python 3.12 standard library (`unittest`), git, Claude Code (`claude plugin validate .`).

**Spec:** the owner's decisions of 2026-11-08, recorded below; ADR 0018 (Task 4) records them. Builds on `main` at f8e093c (aidlc 4.3.0).

Branch: `docs/plan-17-one-plugin`. The owner has already deleted `plugins/aidlc-modernize/` in the working tree (25 files, uncommitted).

## The owner's decisions (2026-11-08)

| Question | Decision |
|---|---|
| Focus | aidlc only. The modernise pack is not worked on now |
| The modernise pack | Removed from the repository (the owner deleted the folder); kept in git for later |
| Where the plugin lives | At the repository root, like a one-plugin repository: `skills/`, `agents/`, `evals/` at the root |
| The pack contract | Removed too: `Packs used here`, `check_packs.py`, start's pack step, "pack skills" in USE SKILLS, the "core never names a pack" check |

What the root layout costs, accepted by the owner: an install copies the whole repository into the plugin cache (`docs/`, `starter/`, `scripts/`), about 5 MB today instead of 2.8 MB; `claude plugin validate` warns that a `CLAUDE.md` at a plugin root is not loaded as project context (the root `CLAUDE.md` is for contributors, and stays).

## Decisions this plan makes

| Question | Decision | Why |
|---|---|---|
| Backup of the pack | A tag, `aidlc-modernize-archive`, on f8e093c (the last commit that holds it), and `docs/archive/aidlc-modernize.md` saying what it held and how to restore it | The tag `aidlc-modernize--v0.1.1` misses two later edits; the harness was parked the same way (`harness-v1`) |
| Install commands | Unchanged: `/plugin marketplace add prashantsharma18/aidlc`, then `/plugin install aidlc@aidlc`. The marketplace and the plugin keep the name `aidlc` | Teammates who installed already keep working after an update |
| Historical documents | Plans, designs, verification records and ADRs before this one keep their paths and pack wording; ADR 0011 is marked "Superseded by ADR 0018" | They record what was true then |
| The recipe commit (ADR 0012) | Stays: it serves any deterministic tool, not only the pack | Removing it would weaken a gate |
| Version | aidlc 5.0.0 | The skills' contract changes (no pack step, no pack skills in bundles), and the layout changes |
| Move method | One mechanical commit (`git mv` and path rewrites only) whose test count and results match the commit before it | A reviewer can trust a pure move without reading every line |

## Test changes the owner approves with this plan

`AGENTS.md` says never to change an existing test assertion to make a test pass. These changes remove or reverse assertions because the owner removed the feature they pin, not to make a test pass. Each is listed so the owner approves it explicitly:

| Test | Change | Why |
|---|---|---|
| `scripts/test_parity.py` (11 tests), `scripts/test_retarget.py` (8) | Deleted | They test the pack's scripts, which the owner deleted; they move to the archive tag with the code |
| `scripts/test_check_packs.py` (14) | Deleted, with `starter/repo/scripts/check_packs.py` | The pack check is removed |
| `test_validate.py`: `test_a_core_and_pack_marketplace_has_no_problems`, `test_skill_names_are_unique_across_plugins`, `test_core_never_names_a_pack`, `test_core_requires_nothing`, `test_pack_stage_skills_keep_the_house_sections` | Deleted | They pin pack rules that no longer exist |
| `test_validate.py`: `test_a_plugin_source_outside_plugins_is_a_problem` | Replaced by `test_the_plugin_source_must_be_the_root`, which asserts the opposite | The owner chose the root layout |
| Every test file that names `plugins/aidlc/` | The path only (`plugins/aidlc/skills/x` becomes `skills/x`) | The files moved; what each assertion checks is unchanged |

## Global Constraints

- One plugin, named `aidlc`, at the repository root. The marketplace, also named `aidlc`, lists it with `"source": "./"`.
- Nothing names `aidlc-modernize`, a pack, `Packs used here` or `check_packs` outside historical documents (`docs/plans/`, `docs/design/`, `docs/verification/`, `docs/archive/`, and ADRs 0001 to 0017).
- No gate is weakened: tests first, MAY CHANGE, the assertion rule and its two exceptions (recipe commits, AMENDED ASSERTIONS), stop conditions, "You draft; you never approve."
- Every test not listed above keeps passing unchanged in meaning. `scripts/test_loads.py`'s `LOADS` table stays as it is (path changes only if it names one).
- Short sentences, British spelling. No new dependency. Commits use the noreply identity and end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.

## Review Focus

- A teammate who installed `aidlc@aidlc` before the move updates the plugin. They expect it to keep working under the same name; Task 2 adds `test_the_install_id_is_unchanged`, and Task 4 records an install from a local checkout.
- A component Claude Code would load from the new plugin root by accident: a `settings.json`, `.mcp.json`, `hooks/`, `bin/`, `commands/`, `monitors/`, `output-styles/`, `themes/` or `workflows/` at the repository root. A person expects only the skills and agents to load; Task 2 adds `test_nothing_else_at_the_root_loads_as_a_component`.
- A stage skill that still sends someone to a pack step or a pack check (for example start's step numbers after its pack step goes). A person expects the steps to read in order; Task 3 adds `test_start_steps_are_numbered_in_order`.
- A starter repository that still runs `check_packs.py` in CI after the script is gone. A person expects CI to stay green; Task 3 adds `test_the_starter_ci_runs_no_pack_check`.
- A live document that still tells a Copilot or Codex user to copy `plugins/aidlc/skills/*`. Task 2 adds `test_no_live_document_names_the_old_path`.

---

### Task 1: Archive the modernise pack

**Files:**
- Delete (already deleted by the owner, committed here): `plugins/aidlc-modernize/**`; delete `scripts/test_parity.py`, `scripts/test_retarget.py`, `docs/operating-model/modernisation.md`
- Modify: `.claude-plugin/marketplace.json`, `README.md`, `AGENTS.md`, `docs/codebase-map.md`, `docs/quickstart/claude-code.md`, `docs/quickstart/copilot.md`, `docs/quickstart/codex-cursor.md`, `docs/operating-model/workspace-and-repositories.md`
- Create: `docs/archive/aidlc-modernize.md`, `scripts/test_one_plugin.py`

**Interfaces:**
- Produces: `scripts/test_one_plugin.py` with `read(rel)`, `LIVE` (the live documents) and `class OnePluginTest`; later tasks append inside it.

- [ ] **Step 1: Tag the backup.** `git tag aidlc-modernize-archive f8e093c`. Check: `git ls-tree -r --name-only aidlc-modernize-archive -- plugins/aidlc-modernize | wc -l` prints 25 or more.

- [ ] **Step 2: Write the failing tests.** Create `scripts/test_one_plugin.py`:

```python
"""Plan 17: aidlc is one plugin at the repository root, with no pack and no pack contract."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ("docs/plans/", "docs/design/", "docs/verification/", "docs/archive/")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if (ROOT / p).is_file()]


def live(paths: list[str]) -> list[str]:
    """Files that describe the kit as it is today: not history, not an ADR before 0018, not this test."""
    keep = []
    for p in paths:
        if p.startswith(HISTORY) or p == "scripts/test_one_plugin.py":
            continue
        adr = re.match(r"docs/adr/(\d{4})-", p)
        if adr and int(adr.group(1)) < 18:
            continue
        if p.endswith((".md", ".py", ".json", ".yml", ".yaml", ".sh")):
            keep.append(p)
    return keep


class OnePluginTest(unittest.TestCase):
    def test_the_modernise_pack_is_archived(self):
        self.assertFalse((ROOT / "plugins/aidlc-modernize").exists())
        tag = subprocess.run(["git", "rev-parse", "--verify", "--quiet", "aidlc-modernize-archive"], cwd=ROOT,
                             capture_output=True, text=True)
        self.assertEqual(tag.returncode, 0)
        note = read("docs/archive/aidlc-modernize.md")
        self.assertIn("git checkout aidlc-modernize-archive -- plugins/aidlc-modernize", note)

    def test_nothing_live_names_the_pack(self):
        hits = [p for p in live(tracked()) if re.search(r"aidlc-modernize|modernize-|dotnet-modernize|java-modernize",
                                                        read(p))]
        self.assertEqual(hits, [])

    def test_the_marketplace_lists_one_plugin(self):
        market = json.loads(read(".claude-plugin/marketplace.json"))
        self.assertEqual([p["name"] for p in market["plugins"]], ["aidlc"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run them and watch them fail.** Run: `python3 -m unittest scripts.test_one_plugin 2>&1 | tail -1`. Expected: `FAILED` (2 failures: live files name the pack; the marketplace lists two). The archive test fails until Step 5.

- [ ] **Step 4: Remove the pack's references.**
  - `git rm -q --cached -r plugins/aidlc-modernize` (records the owner's deletion), `git rm -q scripts/test_parity.py scripts/test_retarget.py docs/operating-model/modernisation.md`.
  - `.claude-plugin/marketplace.json`: delete the `aidlc-modernize` entry; set `"description"` to "aidlc: skills for AI-assisted software delivery, from a requirement to a verified, reviewed change." (Task 2 rewrites the remaining entry.)
  - `README.md`: in the first paragraph after the title, replace the sentence beginning "One marketplace, two plugins:" with "One plugin, **`aidlc`**." and keep the next sentence about the tools; delete the `aidlc-modernize` paragraph at the end of "## Skills" (it begins "`aidlc-modernize` (`plugins/aidlc-modernize/`)"); in "## Packs", delete the line beginning "- **`aidlc-modernize`**" (Task 3 removes the section).
  - `AGENTS.md`: delete the map line "- `plugins/aidlc-modernize/` the modernisation pack: …"; in the first line of the Map, replace "the modernisation pack" wording if any remains.
  - `docs/codebase-map.md`: delete the `plugins/aidlc-modernize/` entry (two lines).
  - Quickstarts: in `claude-code.md` delete the "**Packs.**" paragraph; in `copilot.md` delete the sentence "In a repository being modernised, also copy `plugins/aidlc-modernize/skills/*`, and declare the pack in AGENTS.md's `Packs used here`."; in `codex-cursor.md` delete "(and `plugins/aidlc-modernize/skills/*` in a repository being modernised)" or its equivalent, and the sentence "Declare any pack in AGENTS.md's `Packs used here`; `python3 scripts/check_packs.py` checks the copied folders against it."
  - `workspace-and-repositories.md`: in "## Packs", replace "(for example `aidlc-modernize`)" with nothing and remove "See [modernisation.md](modernisation.md) and" (Task 3 removes the section).
  - `grep -rn "aidlc-modernize\|modernize-\|modernisation.md" $(git ls-files | grep -v "^docs/plans/\|^docs/design/\|^docs/verification/\|^docs/archive/\|^docs/adr/00[01]")` lists anything left; remove each the same way.

- [ ] **Step 5: Write `docs/archive/aidlc-modernize.md`:**

```markdown
# Archived: the aidlc-modernize pack

Archived on 2026-11-08 by the owner, Prashant Sharma, to focus on aidlc. Not deleted: it is in git under the tag
`aidlc-modernize-archive` (commit f8e093c), and the earlier releases under `aidlc-modernize--v0.1.0` and
`aidlc-modernize--v0.1.1`.

## What it held
- Method skills: `modernize-assess`, `modernize-characterize`, `modernize-wave-plan`, `modernize-parity`,
  `modernize-cutover`.
- Factories: `dotnet-modernize` (with `scripts/retarget.py`), proven end to end on SHIP-3 (a .NET Framework 4.8
  service ported to .NET 10, 70 tests, parity 14/14; `docs/verification/2026-10-26-modernize-dotnet.md`), and
  `java-modernize`, written but not proven.
- The `parity-checker` agent and `modernize-parity/scripts/parity.py`.
- It plugged into core through the pack contract (ADR 0011), which Plan 17 removed with it (ADR 0018).

## How to restore it
1. `git checkout aidlc-modernize-archive -- plugins/aidlc-modernize`, and the tests from the same tag:
   `git checkout aidlc-modernize-archive -- scripts/test_parity.py scripts/test_retarget.py`.
2. Decide how it plugs in again: as a second plugin (a marketplace entry and a plugin folder of its own, since aidlc
   now sits at the repository root), or as skills inside aidlc. Either needs a design change, recorded as an ADR.
```

- [ ] **Step 6: Run all tests and the validator.**

Run: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | grep -E "^Ran|^OK|^FAILED"; python3 scripts/validate.py | tail -1`
Expected: `OK` (287 − 19 deleted + 3 new = 271); `validate: 1 plugin(s), 30 skill(s), 0 problem(s)`.

- [ ] **Step 7: Commit.**

```bash
git add -A .claude-plugin README.md AGENTS.md docs scripts plugins
git commit -m "chore!: archive the aidlc-modernize pack (tag aidlc-modernize-archive)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Move aidlc to the repository root

**Files:**
- Move: `plugins/aidlc/skills` → `skills`, `plugins/aidlc/agents` → `agents`, `plugins/aidlc/evals` → `evals`, `plugins/aidlc/.claude-plugin/plugin.json` → `.claude-plugin/plugin.json`
- Modify: `.claude-plugin/marketplace.json`, `scripts/validate.py`, `scripts/route_check.py`, every `scripts/test_*.py` that names the old path, `.gitignore` (the eval results path), `README.md`, `AGENTS.md`, `docs/codebase-map.md`, the quickstarts, `evals/README.md`
- Test: `scripts/test_one_plugin.py`, `scripts/test_validate.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class OnePluginTest`:

```python
    def test_the_plugin_is_the_repository_root(self):
        for folder in ("skills", "agents", "evals"):
            self.assertTrue((ROOT / folder).is_dir(), folder)
        self.assertFalse((ROOT / "plugins").exists())
        manifest = json.loads(read(".claude-plugin/plugin.json"))
        self.assertEqual(manifest["name"], "aidlc")
        market = json.loads(read(".claude-plugin/marketplace.json"))
        self.assertEqual(market["plugins"][0]["source"], "./")

    def test_the_install_id_is_unchanged(self):
        market = json.loads(read(".claude-plugin/marketplace.json"))
        self.assertEqual((market["name"], market["plugins"][0]["name"]), ("aidlc", "aidlc"))
        self.assertIn('"aidlc@aidlc": true', read("starter/repo/.claude/settings.json"))

    def test_nothing_else_at_the_root_loads_as_a_component(self):
        for name in ("settings.json", ".mcp.json", ".lsp.json", "hooks", "bin", "commands", "monitors",
                     "output-styles", "themes", "workflows"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_no_live_document_names_the_old_path(self):
        hits = [p for p in live(tracked()) if "plugins/aidlc" in read(p)]
        self.assertEqual(hits, [])
```

And in `scripts/test_validate.py`, replace `test_a_plugin_source_outside_plugins_is_a_problem` (owner-approved, see the table above) with:

```python
    def test_the_plugin_source_must_be_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package(root, {"aidlc-plan": skill("aidlc-plan")})
            (root / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({"name": "aidlc", "plugins": [{"name": "aidlc", "source": "./plugins/aidlc"}]}))
            self.assertTrue(any("source" in p and "'./'" in p for p in validate.validate(root)))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: the four new `OnePluginTest` tests fail, and `test_the_plugin_source_must_be_the_root` fails.

- [ ] **Step 3: The mechanical move (its own commit).**

```bash
git mv plugins/aidlc/skills skills
git mv plugins/aidlc/agents agents
git mv plugins/aidlc/evals evals
git mv plugins/aidlc/.claude-plugin/plugin.json .claude-plugin/plugin.json
rmdir plugins/aidlc/.claude-plugin plugins/aidlc plugins
```

Then rewrite paths, and only paths, in the scripts and tests: in every `scripts/*.py`, replace the string `plugins/aidlc/` with nothing, and the path expression `"plugins" / "aidlc" / ` with nothing (for example `ROOT / "plugins" / "aidlc" / "skills"` becomes `ROOT / "skills"`). In `.gitignore`, replace `plugins/aidlc/evals/results/` with `evals/results/`. List what changed with `git diff --stat` and read each hunk: only paths.

Before the move, record the suite's count: `python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | grep "^Ran"`. After the move and the path rewrite, the same count must pass, except the tests this task added in Step 1, and the validator tests that need Step 4.

- [ ] **Step 4: The validator reads one plugin at the root.** In `scripts/validate.py`:
  - Replace `load_plugins` with:

```python
def load_plugin(root: Path) -> tuple[list[str], dict | None]:
    """The one plugin, at the repository root: its manifest, and every problem found in the two manifests."""
    rel = ".claude-plugin/marketplace.json"
    try:
        market = json.loads((root / rel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{rel}: unreadable ({exc})"], None
    problems = []
    entries = market.get("plugins", [])
    if [e.get("name") for e in entries] != [CORE]:
        problems.append(f"{rel}: lists {[e.get('name') for e in entries]}; it lists one plugin, '{CORE}'")
    for entry in entries:
        if entry.get("source") != "./":
            problems.append(f"{rel}: plugin '{entry.get('name')}' must have the source './' "
                            f"(got {entry.get('source')!r}); the repository root is the plugin")
    mrel = ".claude-plugin/plugin.json"
    try:
        manifest = json.loads((root / mrel).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return problems + [f"{mrel}: unreadable ({exc})"], None
    if manifest.get("name") != CORE:
        problems.append(f"{mrel}: name '{manifest.get('name')}' must be '{CORE}'")
    if not SEMVER.fullmatch(str(manifest.get("version", ""))):
        problems.append(f"{mrel}: needs a semantic version such as 1.0.0")
    if manifest.get("dependencies"):
        problems.append(f"{mrel}: requires nothing")
    return problems, manifest
```

  - Delete `check_core_names_no_pack`.
  - Replace `validate` with:

```python
def validate(root: Path) -> list[str]:
    problems, _ = load_plugin(root)
    skills = sorted((root / "skills").glob("*/SKILL.md"))
    agents = sorted((root / "agents").glob("*.md"))
    if not skills:
        problems.append("skills/: no skills found")
    if not agents:
        problems.append("agents/: no agents found")
    for path in skills:
        problems += check_skill(path, root)
    for path in agents:
        problems += check_agent(path, root)
    return problems + check_starters(root)
```

  - In `main`, replace the two lines that compute `plugins` and `count` with `count = len(list((root / "skills").glob("*/SKILL.md")))`, and the print with `print(f"validate: 1 plugin, {count} skill(s), {len(problems)} problem(s)")`.
  - Set `HOUSE_PREFIXES = ("aidlc-",)`, and in the module docstring replace "the aidlc marketplace and every plugin it lists" with "the aidlc plugin at the repository root and its marketplace entry", and "skill names unique across plugins, core never naming a pack, plugin versions and dependencies" with "the plugin's version".
  - In `scripts/test_validate.py`, change only the fixture builder: `write_plugin(root, "aidlc", …)` writes `skills/`, `agents/` and `.claude-plugin/plugin.json` at `root` instead of `root / "plugins" / "aidlc"`; `package` writes one marketplace entry `{"name": "aidlc", "source": "./"}` and drops its `packs` parameter. Delete the five owner-approved pack tests listed above, and the `PACK` fixture and `pack` helper if nothing else uses them.

- [ ] **Step 5: The marketplace and the live docs.**
  - `.claude-plugin/marketplace.json`: the one entry becomes `{"name": "aidlc", "source": "./", "description": "Stage skills (start to feedback, onboard), engineering-practice skills and agent roles. Each stage stops at its human gate."}`.
  - `README.md`: replace `plugins/aidlc/skills/*` with `skills/*` (Install table, twice); in "## Skills", replace "Core (`plugins/aidlc/`):" with "The skills (`skills/`):", and "(in `plugins/aidlc/agents/`)" with "(in `agents/`)".
  - `AGENTS.md`: replace the map line "- `plugins/aidlc/` the core plugin: `skills/` (…) and `agents/`." with "- `skills/` the `aidlc-*` stage skills and the engineering-practice skills (`skills/NOTICE` holds the third-party licence for parts of the eight earlier practices); `agents/` the agent roles; `evals/` the behaviour evals; `.claude-plugin/` the plugin and its marketplace entry: the repository root is the plugin."; replace "every release raises the plugin's version (`plugins/<name>/.claude-plugin/plugin.json`)" with "every release raises the plugin's version (`.claude-plugin/plugin.json`)".
  - `docs/codebase-map.md`, the three quickstarts and `evals/README.md`: replace `plugins/aidlc/` paths with root paths, and `claude plugin eval plugins/aidlc` with `claude plugin eval .`.
  - Run `grep -rn "plugins/aidlc" $(git ls-files)` and fix every live hit the same way.

- [ ] **Step 6: Run every check.**

```bash
python3 -m unittest discover -s scripts -p 'test_*.py' 2>&1 | grep -E "^Ran|^OK|^FAILED"
python3 scripts/validate.py | tail -1
python3 scripts/route_check.py | tail -1
claude plugin validate .
```

Expected: `OK`; `validate: 1 plugin, 30 skill(s), 0 problem(s)`; rank-1 unchanged (86%); `Validation passed`, with at most the warning about the root `CLAUDE.md`. If `claude plugin validate` rejects `"source": "./"`, stop and report: the fallback (a `github` source that names this repository, as one-plugin repositories do) is a decision for the owner.

- [ ] **Step 7: Install from a local checkout** (no cost, no push): in a scratch `HOME` so the owner's settings are untouched, `HOME=<scratchpad>/home claude plugin marketplace add <repository>` then `HOME=<scratchpad>/home claude plugin install aidlc@aidlc`, then `HOME=<scratchpad>/home claude plugin details aidlc`. Expected: 30 skills and 6 agents in the component inventory. Record the output for Task 4. If the CLI cannot run with a scratch `HOME` here, record that and skip; the owner runs it once.

- [ ] **Step 8: Commit** in two commits: the mechanical move (Step 3), then the validator, tests and docs (Steps 1, 4, 5).

```bash
git commit -m "refactor!: move aidlc to the repository root (git mv and path rewrites only)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git commit -m "feat(validate)!: one plugin at the root; the marketplace entry's source is ./

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Remove the pack contract

**Files:**
- Modify: `skills/aidlc-start/SKILL.md`, `skills/aidlc-plan/SKILL.md`, `skills/aidlc-plan/assets/task-bundle.md`, `skills/aidlc-build/SKILL.md`, `skills/aidlc-onboard/SKILL.md`, `skills/aidlc-onboard/assets/agents-md.md`, `starter/repo/AGENTS.md`, `starter/repo/.github/workflows/ci.yml`, the eval fixtures' `AGENTS.md` (`evals/fixtures/shipments/AGENTS.md`, `evals/fixtures/workspace/shipments-api/AGENTS.md`, `evals/fixtures/workspace/web-portal/AGENTS.md`), `AGENTS.md`, `README.md`, `docs/codebase-map.md`, `docs/operating-model/workspace-and-repositories.md`, `docs/adr/0011-plugins-and-packs.md` (status line only)
- Delete: `starter/repo/scripts/check_packs.py`, `scripts/test_check_packs.py` (owner-approved)
- Test: `scripts/test_one_plugin.py`

- [ ] **Step 1: Write the failing tests.** Append inside `class OnePluginTest`:

```python
    def test_no_live_file_keeps_the_pack_contract(self):
        pattern = re.compile(r"Packs used here|check_packs|pack skill|pack check|names a pack|core never names", re.I)
        hits = [p for p in live(tracked()) if pattern.search(read(p))]
        self.assertEqual(hits, [])
        self.assertFalse((ROOT / "starter/repo/scripts/check_packs.py").exists())

    def test_start_steps_are_numbered_in_order(self):
        steps = read("skills/aidlc-start/SKILL.md").split("## Steps", 1)[1].split("\n## ", 1)[0]
        numbers = [int(n) for n in re.findall(r"(?m)^(\d+)\. ", steps)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertNotIn("**Packs.**", steps)

    def test_the_starter_ci_runs_no_pack_check(self):
        self.assertNotIn("check_packs", read("starter/repo/.github/workflows/ci.yml"))

    def test_adr_0011_is_superseded(self):
        self.assertIn("Superseded by ADR 0018", read("docs/adr/0011-plugins-and-packs.md"))
```

- [ ] **Step 2: Run them and watch them fail.** Expected: 4 FAIL.

- [ ] **Step 3: Edit the skills.**
  - `aidlc-start`: delete step 2 (the paragraph beginning "2. **Packs.**", through "Write it first in the index's stage checklist."); renumber steps 3 to 9 as 2 to 8, and every reference to them inside the skill ("chosen in step 7" becomes "chosen in step 6"; check each "step <n>"). Delete the Stop if line "- The pack check fails, or a pack's entry skill cannot be loaded."
  - `aidlc-plan` step 7: replace "fill USE SKILLS with the pack skills AGENTS.md declares and the core practices the slice needs, each in full (`<plugin>:<skill>`), or `none`." with "fill USE SKILLS with the practices the slice needs, each in full (`aidlc:<skill>`), or `none`."
  - `task-bundle.md`: replace `USE SKILLS  <plugin:skill, … pack skills AGENTS.md declares and core practices from the `using-aidlc` practice map> | none` with `USE SKILLS  <aidlc:skill, … practices from the `using-aidlc` practice map> | none`.
  - `aidlc-build` Red flags: delete "- You are working from a pack skill the bundle does not name, or without one it does." If step 3 or the Inputs name packs, keep the rule ("Load every skill the bundle's USE SKILLS names, by its full name") and drop only the pack wording.
  - `aidlc-onboard`: in the new-mode prepare list, replace "and `check_packs.py`, `check_recipe_commit.py` and `run_slices.py` into the" with "and `check_recipe_commit.py` and `run_slices.py` into the"; delete "`Packs used here` as `- none`;" from the same paragraph. In `assets/agents-md.md`, delete the "## Packs used here" section (heading, `- none`, and its parenthesised note) and the Commands line "- Pack check, at the start of work and in CI: `python3 scripts/check_packs.py`".
- [ ] **Step 4: Edit the starters, fixtures and docs.**
  - `starter/repo/AGENTS.md`: the same two deletions as `agents-md.md`. `starter/repo/.github/workflows/ci.yml`: delete the step named "Packs declared in AGENTS.md are installed" and its `run` line. `git rm starter/repo/scripts/check_packs.py scripts/test_check_packs.py`.
  - The three eval fixtures' `AGENTS.md`: delete their "## Packs used here" section.
  - Repository `AGENTS.md` Standards: replace "- Core never names a pack, a pack skill or a pack agent; skill names are unique across the marketplace; every release raises the plugin's version (`.claude-plugin/plugin.json`)." with "- Every release raises the plugin's version (`.claude-plugin/plugin.json`)."; in the Standards line about house sections, replace "Stage, method and recipe skills (`aidlc-`, `modernize-`, `dotnet-`, `java-`)" with "Stage skills (`aidlc-`)".
  - `README.md`: delete the "## Packs" section.
  - `docs/codebase-map.md`: delete the "A new pack:" recipe (two lines) and "Core never names a pack; the validator fails if it does."; replace "holds `check_packs.py`, `check_recipe_commit.py` and `run_slices.py`" with "holds `check_recipe_commit.py` and `run_slices.py`".
  - `workspace-and-repositories.md`: delete the "## Packs" section.
  - `docs/adr/0011-plugins-and-packs.md`: change its status line to "Status: Superseded by ADR 0018 (2026-11-08): one plugin at the repository root; no packs."
  - Run `grep -rn -i "packs used here\|check_packs\|pack skill\|pack check" $(git ls-files)` and remove every live hit.

- [ ] **Step 5: Run every check.** Expected: `OK`; 0 problems; `Validation passed`.

- [ ] **Step 6: Commit.**

```bash
git add -A skills starter evals AGENTS.md README.md docs scripts
git commit -m "feat!: remove the pack contract: start's pack step, pack skills in bundles, check_packs.py

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: ADR 0018, release aidlc 5.0.0 and the verification record

**Files:**
- Create: `docs/adr/0018-one-plugin-at-the-root.md`, `docs/verification/2026-11-08-plan-17-one-plugin.md`
- Modify: `.claude-plugin/plugin.json`, `scripts/test_one_plugin.py`

- [ ] **Step 1: Write the failing test.** Append inside `class OnePluginTest`:

```python
    def test_the_decision_is_recorded_and_released(self):
        self.assertTrue((ROOT / "docs/adr/0018-one-plugin-at-the-root.md").is_file())
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "5.0.0")
```

- [ ] **Step 2: Run it and watch it fail.** Expected: 1 FAIL.

- [ ] **Step 3: Write ADR 0018** in ADR 0016's layout: Status "Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)". Context: two plugins, a pack contract and two factories were more than teammates need; the goal is aidlc itself, installed as one plugin. Decision: the four owner decisions in the table above; the tag `aidlc-modernize-archive`; install commands unchanged; the recipe commit stays. Consequences: aidlc 5.0.0; an install copies the whole repository; the root `CLAUDE.md` draws a validate warning and stays for contributors; ADR 0011 superseded; restoring the pack is a design change.

- [ ] **Step 4: Version.** In `.claude-plugin/plugin.json`, replace `"version": "4.3.0"` with `"version": "5.0.0"`.

- [ ] **Step 5: Run every check** (Task 2 Step 6's four commands). Expected: all green.

- [ ] **Step 6: Commit.** `git add docs/adr .claude-plugin scripts/test_one_plugin.py`; message "chore(release): aidlc 5.0.0, one plugin at the root; ADR 0018" with the co-author line.

- [ ] **Step 7: Final review.** A fresh reviewer on the most capable model reads the branch against this plan's decisions, the owner-approved test changes and the Review Focus. It checks that no gate weakened, no live file names a pack or the old path, the moved files are byte-identical apart from path strings, and Claude Code would load nothing unintended from the root. Fix critical, important and cheap real low findings test-first; dismiss other lows with a reason.

- [ ] **Step 8: Write the verification record** in Plan 15's layout: the checks (test counts before and after, with the 35 deleted tests named), the local install result, the Review Focus cases with their tests, the review's findings and fixes, and the decisions. Commit it with the fix pass.
