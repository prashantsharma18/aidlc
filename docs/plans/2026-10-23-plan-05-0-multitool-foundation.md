# Plan 5.0: Multi-tool foundation. Implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adding a second tool (Copilot, then Cursor or Codex) becomes mostly data plus one small writer, never a rewrite. Rendering a second tool can never delete or disturb the first tool's files. This plan builds no second tool: Claude Code stays the only supported one.

**Architecture:** Five changes, all behind today's behaviour for Claude Code.
1. **Ownership.** The generated-file manifest records which tool owns each file. A render can only clean up its own files, and two tools can never claim one path.
2. **The full adapter contract.** The adapter contract gains the design's two missing functions, `render_skills` and `render_agents`. One function, `render_outputs`, lists everything an adapter renders, and replaces the three duplicated call lists.
3. **Capabilities as data.** Each tool's capabilities are a small YAML file in `core/adapters/`, validated by a schema:
   - file locations and formats;
   - tool names;
   - hook dialect and failure behaviour;
   - permission and MCP locations;
   - which paths are its agent configuration.

   A generated document compares the tools. The trusted CI judge uses these files to catch unmanaged agent configuration from **any** tool.
4. **A shim with dialects.** The hook shim splits into a tool-neutral flow and a Claude "dialect". A second tool's hook becomes a second dialect.
5. **Docs.** ADR 0006 records the decision, and the out-of-date Copilot notes are rewritten from today's official docs.

**Tech Stack:** Python 3.12 (stdlib, PyYAML, jsonschema). The hooks stay stdlib only.

**Spec:**
- design §4.3 (the adapter interface: six render functions and a runtime shim);
- ADR 0001 (policy as code), ADR 0002-tool-classes and ADR 0005 (planned in Plan 5a);
- the user's decisions of 2026-10-23: do this foundation before Plan 5a; legacy gets its own plan; read-only skills may start automatically;
- the research of 2026-10-23: the aidlc gap map, and the official Copilot, Cursor and Codex docs, cited in the descriptors.

**Why now:** Plan 5a adds a new kind of generated output, the plugin. Plan 6 adds repositories. Each of the five changes is small today and expensive after them.

## Facts this plan relies on (verified 2026-10-23)

**The orphan bug.**
- `cli/aidlc/adapters/base.py` `write_rendered` keeps one manifest (`.aidlc/generated.json`, `{"files": {path: sha256}}`).
- It deletes, or reports as "orphaned", every recorded file the current render did not produce.
- So a render for tool B would delete tool A's files, and the CI judge's per-tool pass would report them.
- Tests in `tests/unit/test_manifest.py` read `manifest["files"]` as a path-to-hash map. That format must not change.

**The contract today.**
- The `Adapter` Protocol has `render_rules`, `render_folder_rules`, `render_permissions` and `render_hooks`.
- The same four-call list is repeated in `cli/aidlc/commands/render_cmd.py`, `cli/aidlc/checks/doctor.py` (`check_d1`) and `cli/aidlc/checks/conftest_check.py` (`judge_generated`).
- `render_ci` (`cli/aidlc/ci_templates.py`) is rendered with every tool. Its output is `paths.CI_WORKFLOW`.

**Agent-config detection.** `conftest_check._is_agent_config` treats as agent configuration only:
- `.claude` path parts;
- `.mcp.json` and `claude.local.md`;
- `.aidlc/hooks/` and `.aidlc/rules/`.

Another tool's configuration (Copilot, Cursor, Codex) is never judged.

**The shim.** `core/hooks/claude_shim.py` holds:
- the tool-name table (`CLASSES`);
- `to_generic` (the Claude payload to the generic event);
- `main`, which runs the guard or post-check and encodes Claude's output: `hookSpecificOutput.permissionDecision` for pre, and `{"decision": "block"}` for post. It exits 2 on any error.

Its tests call `to_generic` and `main`. The hook-file set (`HOOK_FILES`) is pinned by `tests/unit/test_claude_settings.py`, so this plan keeps the shim in one file.

**What the other tools do (from the official docs, read 2026-10-23):**

| | Copilot | Cursor | Codex |
|---|---|---|---|
| Reads `AGENTS.md` | yes | yes | yes |
| Skill folders it reads | `.github/skills`, `.claude/skills`, `.agents/skills` | `.cursor/skills`, `.agents/skills`, `.claude/skills` | `.agents/skills` |
| Agent format | `.github/agents/*.agent.md`, with tool aliases `read`, `edit`, `execute`, `search` | `.cursor/agents/*.md`, with a `readonly` flag and no tool list | `.codex/agents/*.toml`, with no per-agent tool limits |
| Pre-tool hook | `.github/hooks/*.json` `preToolUse` | `.cursor/hooks.json` `preToolUse` | `.codex/hooks.json` `PreToolUse`, in trusted projects only |
| When the hook errors | fails closed (denies) | fails open, unless the hook sets `failClosed: true` | fails open |
| When the hook times out | **fails open** | fails open, unless `failClosed: true` | fails open |
| Reads Claude's hook settings | yes (`.claude/settings.json`) | yes (imports `.claude/settings.json`) | no |

The sources are listed in each descriptor (Task 3).

## Global Constraints

- **Claude Code behaviour is unchanged.** It renders the same files, and the same tests pass. The only new outputs are the `owners` map in `.aidlc/generated.json`, the capability descriptors, and their generated document.
- **Dependencies.** No new dependency. Hooks stay stdlib only. `HOOK_FILES` is unchanged.
- **Tests.**
  - Never change an assertion in a test older than this plan.
  - `make test` stays model-free.
  - The live attack suite runs in CI (`agent-config-evals`) on this pull request, because the shim changes.
- **Fail closed.**
  - An unreadable manifest or a malformed descriptor is an error.
  - A path claimed by two tools is an error.
  - Unmanaged agent configuration from any known tool FAILs the trusted CI judge, as `.claude/` content already does.
- **Commits, pushes and approvals** follow the established rules: the noreply identity, explicit paths, a pre-push scan, and the user's go-ahead for each push, run approval and merge.
- **Run before every commit:**
  - `make test`;
  - `bin/aidlc trace --check`;
  - `bin/aidlc check context-drift .`;
  - `bin/aidlc policy validate`;
  - `bin/aidlc render --tool claude-code --check .`;
  - `make policy-test` with `AIDLC_TOOLS_DIR` set.

## Review Focus

1. **A repository rendered for two tools, one after the other, and then checked for each.** Neither render deletes or reports the other's files. Pinned by Task 1 `test_rendering_another_tool_keeps_the_first_tools_files`.
2. **A manifest written before this plan, with no `owners`.** It is read as Claude Code's (the CI workflow as shared), and keeps working. Pinned by Task 1 `test_a_manifest_without_owners_is_read_as_claude_code`.
3. **A Cursor, Copilot or Codex file committed by hand into an aidlc repository.** The trusted CI judge FAILs it as unmanaged agent configuration. Pinned by Task 3 `test_every_known_tools_config_is_agent_config`.
4. **The shim's flow with another dialect.** A fake second dialect gets the same guard decisions and the same fail-closed exit on error. Pinned by Task 4 `test_a_second_dialect_uses_the_same_flow`.
5. **A descriptor that claims a tool fails closed when its docs say it fails open.** Each descriptor states its error and timeout behaviour, and the generated comparison shows it. Pinned by Task 3 `test_failure_behaviour_is_declared_for_every_tool`.

---

### Task 1: The manifest records an owner per file

**Files:**
- Modify:
  - `cli/aidlc/adapters/base.py` (`RenderedFile.shared`, `write_rendered(..., owner=...)`, the owners map);
  - `cli/aidlc/ci_templates.py` (`render_ci` marks its file `shared=True`).
- Test: `tests/unit/test_manifest_owners.py`

**Interfaces:**
- `RenderedFile(path, content, source="", shared=False)`.
- `write_rendered(repo, files, check, managed_dirs=(), owner="claude-code") -> list[str]`.
- The manifest format is `{"files": {path: sha256}, "owners": {path: tool-name | "shared"}}`.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_manifest_owners.py
import hashlib
import json
import unittest

from aidlc.adapters.base import MANIFEST, RenderedFile, write_rendered
from aidlc.paths import CI_WORKFLOW
from tests.helpers import TempRepo

GEN = "<!-- Generated by aidlc test -->\n"


def manifest(root):
    return json.loads((root / MANIFEST).read_text(encoding="utf-8"))


class ManifestOwnersTest(unittest.TestCase):
    def test_rendering_another_tool_keeps_the_first_tools_files(self):
        with TempRepo() as root:
            claude = [RenderedFile("CLAUDE.md", GEN + "claude\n")]
            copilot = [RenderedFile(".github/copilot-instructions.md", GEN + "copilot\n")]
            self.assertEqual(write_rendered(root, claude, check=False, owner="claude-code"), [])
            self.assertEqual(write_rendered(root, copilot, check=False, owner="copilot"), [])
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertEqual(write_rendered(root, claude, check=True, owner="claude-code"), [])
            self.assertEqual(write_rendered(root, copilot, check=True, owner="copilot"), [])
            self.assertEqual(manifest(root)["owners"], {"CLAUDE.md": "claude-code",
                                                        ".github/copilot-instructions.md": "copilot"})

    def test_a_tools_own_orphans_are_still_removed(self):
        with TempRepo() as root:
            write_rendered(root, [RenderedFile("CLAUDE.md", GEN), RenderedFile(".claude/rules/x.md", GEN)],
                           check=False, owner="claude-code")
            self.assertEqual(write_rendered(root, [RenderedFile("CLAUDE.md", GEN)], check=False,
                                            owner="claude-code"), [])
            self.assertFalse((root / ".claude/rules/x.md").exists())

    def test_shared_files_are_kept_by_every_tool(self):
        with TempRepo() as root:
            ci = RenderedFile(CI_WORKFLOW, "# Generated by aidlc test\n", shared=True)
            write_rendered(root, [RenderedFile("CLAUDE.md", GEN), ci], check=False, owner="claude-code")
            self.assertEqual(write_rendered(root, [RenderedFile("a.md", GEN), ci], check=False, owner="copilot"), [])
            self.assertEqual(manifest(root)["owners"][CI_WORKFLOW], "shared")
            self.assertEqual(write_rendered(root, [RenderedFile("CLAUDE.md", GEN), ci], check=True,
                                            owner="claude-code"), [])

    def test_two_tools_cannot_claim_one_path(self):
        with TempRepo() as root:
            write_rendered(root, [RenderedFile("AGENTS-x.md", GEN + "a\n")], check=False, owner="claude-code")
            problems = write_rendered(root, [RenderedFile("AGENTS-x.md", GEN + "b\n")], check=False, owner="copilot")
            self.assertEqual(problems, ["AGENTS-x.md: generated for claude-code; another tool cannot render the "
                                        "same path"])
            self.assertEqual((root / "AGENTS-x.md").read_text(encoding="utf-8"), GEN + "a\n")

    def test_a_manifest_without_owners_is_read_as_claude_code(self):
        with TempRepo() as root:
            (root / "CLAUDE.md").write_text(GEN, encoding="utf-8")
            sha = hashlib.sha256(GEN.encode()).hexdigest()
            (root / ".aidlc").mkdir()
            (root / MANIFEST).write_text(json.dumps({"files": {"CLAUDE.md": sha}}), encoding="utf-8")
            self.assertEqual(write_rendered(root, [RenderedFile("b.md", GEN)], check=False, owner="copilot"), [])
            self.assertTrue((root / "CLAUDE.md").is_file())
            self.assertEqual(manifest(root)["owners"]["CLAUDE.md"], "claude-code")

    def test_a_malformed_owners_map_fails_closed(self):
        with TempRepo() as root:
            (root / ".aidlc").mkdir()
            (root / MANIFEST).write_text(json.dumps({"files": {}, "owners": ["x"]}), encoding="utf-8")
            problems = write_rendered(root, [RenderedFile("a.md", GEN)], check=False, owner="copilot")
            self.assertEqual(problems, [f"{MANIFEST} is malformed; restore it from git"])
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_manifest_owners -v`. Expected: `TypeError` (no `owner` or `shared` parameter).
- [ ] **Step 3: Implement.** In `base.py`:
  - **`RenderedFile`:** add the field `shared: bool = False`, with the comment "rendered identically by every tool (the CI workflow); owned by 'shared'".
  - **`_load_owners(repo, files) -> dict[str, str]`:**
    - It reads the same JSON as `_load_manifest`.
    - A missing `owners` key gives `{path: "shared" if path == CI_WORKFLOW else "claude-code" for path in files}`. Before this plan only Claude Code rendered.
    - An `owners` value that is not a dict of strings raises `ValueError(f"{MANIFEST} is malformed; restore it from git")`.
    - Entries for paths missing from `files` are dropped.
  - **`_save_manifest(repo, manifest, owners)`:** writes `{"files": …, "owners": dict(sorted(owners.items()))}`. Callers in tests that mock it are unaffected.
  - **`write_rendered(..., owner="claude-code")`:**
    1. Load the owners right after the manifest.
    2. For each file, set `mine = "shared" if f.shared else owner`. If `owners.get(f.path)` is a different tool name (not `mine`, and not `"shared"` when the file is shared), add the problem `f"{f.path}: generated for {owners[f.path]}; another tool cannot render the same path"` and `continue`, before any write.
    3. After a file is accepted, set `owners[f.path] = mine`.
    4. In the orphan loop, skip `rel` unless `owners.get(rel) in (owner, "shared")`. When an orphan is removed, also `owners.pop(rel, None)`.
    5. Save when the manifest or the owners changed.

  In `ci_templates.render_ci`, return `RenderedFile(OUTPUT, text, source=TEMPLATE, shared=True)`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_manifest tests.unit.test_adapters -v` and `make test`. Expected: everything passes, and the existing manifest tests are unchanged.
- [ ] **Step 5: Commit.** Commit with `fix(render): the generated-file manifest records an owner per file; a tool's render never removes another tool's files`.

### Task 2: The full adapter contract, and one list of outputs

**Files:**
- Modify:
  - `cli/aidlc/adapters/base.py` (Protocol, plus `render_outputs`);
  - `cli/aidlc/adapters/claude_code.py` (`render_skills` and `render_agents` return `[]`);
  - `cli/aidlc/adapters/copilot.py` (both raise `AdapterNotImplemented`);
  - `cli/aidlc/commands/render_cmd.py`, `cli/aidlc/checks/doctor.py` (`check_d1`), `cli/aidlc/checks/conftest_check.py` (`judge_generated`): call `render_outputs`, and pass `owner=adapter.name`.
- Test: `tests/unit/test_adapter_contract.py`

**Interfaces:**
- `render_outputs(adapter, repo) -> list[RenderedFile]` returns, in order:
  - rules;
  - folder rules;
  - permissions;
  - hooks;
  - skills;
  - agents.

  The CI workflow is appended by callers, as today.
- Plan 5a's plugin delivers Claude Code's skills and agents, so the Claude adapter renders none into a repository.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_adapter_contract.py
import unittest
from datetime import date
from unittest import mock

from aidlc.adapters import adapter_names, get_adapter
from aidlc.adapters.base import AdapterNotImplemented, RenderedFile, render_outputs
from aidlc.adapters.claude_code import ClaudeCodeAdapter
from aidlc.repo import init_repo
from tests.helpers import TempRepo, run_cli

SIX = ("render_rules", "render_folder_rules", "render_permissions", "render_hooks", "render_skills",
       "render_agents")


class AdapterContractTest(unittest.TestCase):
    def test_every_adapter_has_the_six_render_functions(self):
        for name in adapter_names():
            with self.subTest(adapter=name):
                adapter = get_adapter(name)
                for fn in SIX:
                    self.assertTrue(callable(getattr(adapter, fn)))

    def test_claude_code_renders_no_skills_or_agents_into_a_repository(self):
        with TempRepo() as root:
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            adapter = get_adapter("claude-code")
            self.assertEqual(adapter.render_skills(root), [])
            self.assertEqual(adapter.render_agents(root), [])

    def test_copilot_skills_and_agents_are_not_built_yet(self):
        with TempRepo() as root:
            for fn in ("render_skills", "render_agents"):
                with self.subTest(fn=fn), self.assertRaises(AdapterNotImplemented):
                    getattr(get_adapter("copilot"), fn)(root)

    def test_render_doctor_and_the_ci_judge_use_render_outputs(self):
        extra = RenderedFile(".claude/agents/probe.md", "<!-- Generated by aidlc test -->\nx\n")
        with TempRepo() as root, mock.patch.object(ClaudeCodeAdapter, "render_agents", return_value=[extra]):
            init_repo(root, "svc", "team", "generic", "purpose", date(2026, 10, 23))
            code, out, err = run_cli("render", "--tool", "claude-code", str(root))
            self.assertEqual(code, 0, out + err)
            self.assertTrue((root / ".claude/agents/probe.md").is_file())
            self.assertIn(extra, render_outputs(get_adapter("claude-code"), root))
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_adapter_contract -v`. Expected: `ImportError` (no `render_outputs`).
- [ ] **Step 3: Implement.**
  - **In `base.py`:** add both methods to the `Adapter` Protocol, and:

```python
def render_outputs(adapter: Adapter, repo: Path) -> list[RenderedFile]:
    """Everything an adapter renders into a repository. aidlc render, doctor D1 and the trusted CI judge
    all use this list, so a new render function reaches all three at once."""
    return (adapter.render_rules(repo) + adapter.render_folder_rules(repo) + adapter.render_permissions(repo)
            + adapter.render_hooks(repo) + adapter.render_skills(repo) + adapter.render_agents(repo))
```

  - **`ClaudeCodeAdapter`:** add `render_skills` and `render_agents`, each returning `[]`, with the docstring "Claude Code gets skills and agents from the aidlc plugin (ADR 0005), not from the repository".
  - **`CopilotAdapter`:** add both, raising `AdapterNotImplemented` with the existing message.
  - **The three call sites:** replace each four-call list with `render_outputs(adapter, repo)`, or `render_outputs(adapter, head)` in the judge, keeping the CI append. Pass `owner=adapter.name` to every `write_rendered` call.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, `make test`, and `AIDLC_TOOLS_DIR=… make policy-test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `refactor(adapters): the six render functions of design 4.3, and one render_outputs list for render, doctor and the CI judge`.

### Task 3: Capability descriptors, the generated comparison, and every tool's agent config judged

**Files:**
- Create:
  - `core/adapters/claude-code.yaml`, `copilot.yaml`, `cursor.yaml`, `codex.yaml`;
  - `core/schemas/adapter.schema.json`;
  - `cli/aidlc/adapters/capabilities.py`;
  - `tests/unit/test_capabilities.py`.
- Modify:
  - `cli/aidlc/trace.py`: collect `core/adapters/*.yaml` with kind `adapter`, and add `docs/adapters/capabilities.md` to `generated_docs`;
  - `cli/aidlc/checks/conftest_check.py`: `_is_agent_config` uses every descriptor's `agent_config`;
  - `docs/traceability.md` (regenerated).

**Interfaces:**
- `load_capabilities(root=None) -> dict[str, dict]`, keyed by `tool`, validated.
- `capabilities_doc(root=None) -> str`.
- `agent_config_markers(root=None) -> tuple[frozenset, frozenset, tuple]`: directory names, file names and path prefixes, all case-folded.
- Plan 5a's plugin build reads `load_capabilities()["claude-code"]["agents"]["tool_names"]` instead of its own constant.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_capabilities.py
import unittest

from aidlc.adapters import adapter_names
from aidlc.adapters.capabilities import agent_config_markers, capabilities_doc, load_capabilities
from aidlc.checks.conftest_check import _fold, _is_agent_config
from tests.helpers import run_cli


class CapabilitiesTest(unittest.TestCase):
    def test_every_tool_has_a_valid_descriptor(self):
        caps = load_capabilities()
        self.assertEqual(set(caps), {"claude-code", "copilot", "cursor", "codex"})
        self.assertEqual(caps["claude-code"]["status"], "supported")
        for name in ("copilot", "cursor", "codex"):
            self.assertEqual(caps[name]["status"], "planned")
        self.assertLessEqual(set(adapter_names()), set(caps))

    def test_failure_behaviour_is_declared_for_every_tool(self):
        caps = load_capabilities()
        expected = {"claude-code": ("fail-closed", "fail-closed"), "copilot": ("fail-closed", "fail-open"),
                    "cursor": ("configurable", "configurable"), "codex": ("fail-open", "fail-open")}
        for name, (error, timeout) in expected.items():
            with self.subTest(tool=name):
                self.assertEqual(caps[name]["hooks"]["on_error"], error)
                self.assertEqual(caps[name]["hooks"]["on_timeout"], timeout)

    def test_claude_code_tool_names_match_the_shim(self):
        from tests.hook_loader import load_hook
        shim = load_hook("claude_shim")
        names = load_capabilities()["claude-code"]["agents"]["tool_names"]
        for cls, tools in names.items():
            for tool in tools:
                with self.subTest(tool=tool):
                    self.assertEqual(shim.CLASSES[tool], cls)

    def test_every_known_tools_config_is_agent_config(self):
        for path in (".cursor/rules/a.mdc", ".github/copilot-instructions.md", ".github/instructions/x.instructions.md",
                     ".github/agents/r.agent.md", ".github/hooks/h.json", ".codex/hooks.json", ".agents/skills/s/SKILL.md",
                     ".claude/settings.json", ".mcp.json", ".cursorrules", "sub/.CURSOR/x"):
            with self.subTest(path=path):
                self.assertTrue(_is_agent_config(_fold(path)))
        for path in (".github/workflows/ci.yml", "src/app.py", "docs/agents/readme.md", "AGENTS.md", "README.md"):
            with self.subTest(path=path):
                self.assertFalse(_is_agent_config(_fold(path)))

    def test_markers_are_case_folded(self):
        dirs, files, prefixes = agent_config_markers()
        self.assertIn(".cursor", dirs)
        self.assertIn("copilot-instructions.md", files)
        self.assertTrue(all(p == p.casefold() for p in prefixes))

    def test_the_comparison_doc_is_generated_and_current(self):
        doc = capabilities_doc()
        for needle in ("claude-code", "copilot", "cursor", "codex", "fail-open", ".agents/skills"):
            self.assertIn(needle, doc)
        code, out, _ = run_cli("trace", "--check")
        self.assertEqual(code, 0, out)
```

- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_capabilities -v`. Expected: `ImportError`.
- [ ] **Step 3: Write the schema, the four descriptors, the loader, the generated doc and the judge change.**

`core/schemas/adapter.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "adapter capabilities",
  "type": "object",
  "additionalProperties": false,
  "required": ["meta", "tool", "status", "verified", "sources", "surfaces", "rules", "skills", "agents", "hooks",
               "permissions", "sandbox", "mcp", "agent_config"],
  "properties": {
    "meta": {"type": "object"},
    "tool": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
    "status": {"enum": ["supported", "planned"]},
    "verified": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}$"},
    "sources": {"type": "array", "minItems": 1, "items": {"type": "string", "pattern": "^https://"}},
    "surfaces": {"type": "array", "minItems": 1, "items": {"type": "string"}},
    "rules": {"type": "object", "additionalProperties": false, "required": ["files", "agents_md", "path_scoped"],
              "properties": {"files": {"type": "array", "items": {"type": "string"}},
                             "agents_md": {"enum": ["native", "import", "fallback", "none"]},
                             "path_scoped": {"type": "object", "additionalProperties": false, "required": ["location", "scope_key"],
                                             "properties": {"location": {"type": "string"}, "scope_key": {"type": "string"}}}}},
    "skills": {"type": "object", "additionalProperties": false, "required": ["dirs", "delivery"],
               "properties": {"dirs": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                              "delivery": {"enum": ["plugin", "repository", "repository-or-plugin"]}}},
    "agents": {"type": "object", "additionalProperties": false, "required": ["location", "tool_limits"],
               "properties": {"location": {"type": "string"},
                              "tool_limits": {"enum": ["classes", "readonly-flag", "none"]},
                              "tool_names": {"type": "object", "propertyNames": {"enum": ["read", "edit", "shell"]},
                                             "additionalProperties": {"type": "array", "items": {"type": "string"}}}}},
    "hooks": {"type": "object", "additionalProperties": false,
              "required": ["location", "pre_tool_event", "deny", "on_error", "on_timeout", "also_runs"],
              "properties": {"location": {"type": "string"}, "pre_tool_event": {"type": "string"}, "deny": {"type": "string"},
                             "on_error": {"enum": ["fail-closed", "fail-open", "configurable"]},
                             "on_timeout": {"enum": ["fail-closed", "fail-open", "configurable"]},
                             "also_runs": {"type": "array", "items": {"type": "string"}}}},
    "permissions": {"type": "object", "additionalProperties": false, "required": ["location", "declarative"],
                    "properties": {"location": {"type": "string"}, "declarative": {"type": "boolean"}}},
    "sandbox": {"type": "object", "additionalProperties": false, "required": ["available", "notes"],
                "properties": {"available": {"type": "boolean"}, "notes": {"type": "string"}}},
    "mcp": {"type": "object", "additionalProperties": false, "required": ["location"],
            "properties": {"location": {"type": "string"}}},
    "agent_config": {"type": "object", "additionalProperties": false, "required": ["dir_names", "file_names", "prefixes"],
                     "properties": {"dir_names": {"type": "array", "items": {"type": "string"}},
                                    "file_names": {"type": "array", "items": {"type": "string"}},
                                    "prefixes": {"type": "array", "items": {"type": "string"}}}}
  }
}
```

`core/adapters/claude-code.yaml`:

```yaml
meta: {id: adapter-claude-code, owner: "@harness-owners", review_by: "2027-04-23", guide: ["2.6", "3.4", "3.6"]}
tool: claude-code
status: supported
verified: "2026-10-23"
sources: ["https://code.claude.com/docs/en/settings", "https://code.claude.com/docs/en/hooks",
          "https://code.claude.com/docs/en/skills", "https://code.claude.com/docs/en/sub-agents"]
surfaces: [cli, ide, desktop, headless]
rules: {files: [CLAUDE.md], agents_md: import, path_scoped: {location: ".claude/rules/*.md", scope_key: paths}}
skills: {dirs: [".claude/skills"], delivery: plugin}
agents: {location: ".claude/agents/*.md (plugin agents/)", tool_limits: classes,
         tool_names: {read: [Read, Glob, Grep], edit: [Edit, Write], shell: [Bash]}}
hooks: {location: ".claude/settings.json", pre_tool_event: PreToolUse,
        deny: "exit 2, or hookSpecificOutput.permissionDecision deny", on_error: fail-closed, on_timeout: fail-closed,
        also_runs: []}
permissions: {location: ".claude/settings.json (project); managed-settings.json (organisation)", declarative: true}
sandbox: {available: true, notes: "bubblewrap and socat on Linux; seatbelt on macOS"}
mcp: {location: ".mcp.json"}
agent_config: {dir_names: [".claude"], file_names: [".mcp.json", "claude.local.md"], prefixes: []}
```

`core/adapters/copilot.yaml`:

```yaml
meta: {id: adapter-copilot, owner: "@harness-owners", review_by: "2027-01-23", guide: ["2.6", "3.4", "3.6"]}
tool: copilot
status: planned
verified: "2026-10-23"
sources: ["https://docs.github.com/en/copilot/reference/hooks-configuration",
          "https://docs.github.com/en/copilot/reference/custom-agents-configuration",
          "https://docs.github.com/en/copilot/concepts/agents/about-agent-skills",
          "https://docs.github.com/en/copilot/reference/enterprise-administrators/enterprise-managed-settings",
          "https://code.visualstudio.com/docs/copilot/customization/hooks",
          "https://code.visualstudio.com/docs/agents/run/agent-sandboxing",
          "https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference"]
surfaces: [vscode-copilot-harness, vscode-local, cli, cloud-agent]
rules: {files: [".github/copilot-instructions.md", AGENTS.md], agents_md: native,
        path_scoped: {location: ".github/instructions/*.instructions.md", scope_key: applyTo}}
skills: {dirs: [".github/skills", ".claude/skills", ".agents/skills"], delivery: repository-or-plugin}
agents: {location: ".github/agents/*.agent.md", tool_limits: classes,
         tool_names: {read: [read, search], edit: [edit], shell: [execute]}}
hooks: {location: ".github/hooks/*.json (the cloud agent reads only these)", pre_tool_event: preToolUse,
        deny: "permissionDecision deny on stdout, or exit 2; ask becomes deny in the cloud agent",
        on_error: fail-closed, on_timeout: fail-open, also_runs: [".claude/settings.json"]}
permissions: {location: "managed-settings.json permissions (deny > ask > allow); CLI --deny-tool", declarative: true}
sandbox: {available: true, notes: "VS Code chat.agent.sandbox and CLI --sandbox (bubblewrap on Linux); the cloud agent runs in an Actions VM with a firewall"}
mcp: {location: ".mcp.json (Copilot harness, CLI); .vscode/mcp.json (VS Code Local); repository settings (cloud agent)"}
agent_config: {dir_names: [".agents"], file_names: ["copilot-instructions.md"],
               prefixes: [".github/instructions/", ".github/agents/", ".github/hooks/", ".github/skills/",
                          ".github/prompts/", ".github/copilot/", ".vscode/mcp.json"]}
```

`core/adapters/cursor.yaml`:

```yaml
meta: {id: adapter-cursor, owner: "@harness-owners", review_by: "2027-01-23", guide: ["2.6", "3.4", "3.6"]}
tool: cursor
status: planned
verified: "2026-10-23"
sources: ["https://cursor.com/docs/context/rules", "https://cursor.com/docs/context/skills",
          "https://cursor.com/docs/context/subagents", "https://cursor.com/docs/agent/hooks",
          "https://cursor.com/docs/reference/third-party-hooks", "https://cursor.com/docs/cli/reference/permissions"]
surfaces: [ide, cli, cloud-agent]
rules: {files: [AGENTS.md], agents_md: native, path_scoped: {location: ".cursor/rules/*.mdc", scope_key: globs}}
skills: {dirs: [".cursor/skills", ".agents/skills", ".claude/skills"], delivery: repository-or-plugin}
agents: {location: ".cursor/agents/*.md", tool_limits: readonly-flag}
hooks: {location: ".cursor/hooks.json", pre_tool_event: preToolUse,
        deny: "permission deny on stdout, or exit 2; set failClosed true",
        on_error: configurable, on_timeout: configurable, also_runs: [".claude/settings.json"]}
permissions: {location: ".cursor/permissions.json; .cursor/cli.json permissions (deny wins)", declarative: true}
sandbox: {available: true, notes: "seatbelt on macOS; Landlock and seccomp on Linux 6.2 or later"}
mcp: {location: ".cursor/mcp.json"}
agent_config: {dir_names: [".cursor"], file_names: [".cursorrules"], prefixes: []}
```

`core/adapters/codex.yaml`:

```yaml
meta: {id: adapter-codex, owner: "@harness-owners", review_by: "2027-01-23", guide: ["2.6", "3.4", "3.6"]}
tool: codex
status: planned
verified: "2026-10-23"
sources: ["https://learn.chatgpt.com/docs/agent-configuration/agents-md", "https://learn.chatgpt.com/docs/build-skills",
          "https://learn.chatgpt.com/docs/agent-configuration/subagents", "https://learn.chatgpt.com/docs/hooks",
          "https://learn.chatgpt.com/docs/agent-approvals-security", "https://learn.chatgpt.com/docs/enterprise/managed-configuration"]
surfaces: [cli, ide, desktop, exec, cloud]
rules: {files: [AGENTS.md], agents_md: native, path_scoped: {location: "nested AGENTS.md (32 KiB in total)", scope_key: directory}}
skills: {dirs: [".agents/skills"], delivery: repository-or-plugin}
agents: {location: ".codex/agents/*.toml", tool_limits: none}
hooks: {location: ".codex/hooks.json or .codex/config.toml [hooks] (trusted projects only)", pre_tool_event: PreToolUse,
        deny: "hookSpecificOutput.permissionDecision deny, or exit 2", on_error: fail-open, on_timeout: fail-open,
        also_runs: []}
permissions: {location: ".codex/config.toml sandbox_mode and approval_policy; .codex/rules/*.rules; requirements.toml (organisation)", declarative: true}
sandbox: {available: true, notes: "seatbelt on macOS; bubblewrap and seccomp on Linux"}
mcp: {location: ".codex/config.toml [mcp_servers]"}
agent_config: {dir_names: [".codex", ".agents"], file_names: ["agents.override.md"], prefixes: []}
```

`cli/aidlc/adapters/capabilities.py`:

```python
"""Tool capabilities as data (ADR 0006): core/adapters/<tool>.yaml, validated by
core/schemas/adapter.schema.json. An adapter reads its own descriptor; the trusted CI judge reads all of
them to recognise any tool's agent configuration; trace renders the comparison."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from ..paths import framework_root
from ..policy import PolicyError, _errors, _schema, load_yaml


def load_capabilities(root: Path | None = None) -> dict[str, dict]:
    return dict(_load(str((root or framework_root()).resolve())))


@lru_cache(maxsize=4)
def _load(root_text: str) -> tuple:
    root = Path(root_text)
    schema = _schema(root, "adapter")
    out = {}
    for path in sorted((root / "core" / "adapters").glob("*.yaml")):
        data = load_yaml(path)
        problems = _errors(schema, data, str(path.relative_to(root)))
        if problems:
            raise PolicyError("; ".join(problems))
        if data["tool"] != path.stem:
            raise PolicyError(f"{path.relative_to(root)}: tool '{data['tool']}' must match the file name")
        out[data["tool"]] = data
    if not out:
        raise PolicyError("no adapter descriptors in core/adapters")
    return tuple(out.items())


def agent_config_markers(root: Path | None = None) -> tuple[frozenset, frozenset, tuple]:
    dirs, files, prefixes = set(), set(), set()
    for data in load_capabilities(root).values():
        config = data["agent_config"]
        dirs |= {d.casefold() for d in config["dir_names"]}
        files |= {f.casefold() for f in config["file_names"]}
        prefixes |= {p.casefold() for p in config["prefixes"]}
    return frozenset(dirs), frozenset(files), tuple(sorted(prefixes))


def capabilities_doc(root: Path | None = None) -> str:
    caps = load_capabilities(root)
    tools = list(caps)
    rows = [
        ("Status", lambda d: f"{d['status']} (verified {d['verified']})"),
        ("Surfaces", lambda d: ", ".join(d["surfaces"])),
        ("Rules", lambda d: ", ".join(d["rules"]["files"]) + f"; AGENTS.md {d['rules']['agents_md']}"),
        ("Path-scoped rules", lambda d: f"{d['rules']['path_scoped']['location']} ({d['rules']['path_scoped']['scope_key']})"),
        ("Skills", lambda d: ", ".join(d["skills"]["dirs"]) + f" ({d['skills']['delivery']})"),
        ("Agents", lambda d: f"{d['agents']['location']}; tool limits: {d['agents']['tool_limits']}"),
        ("Pre-tool hook", lambda d: f"{d['hooks']['location']}: {d['hooks']['pre_tool_event']}"),
        ("Hook error / timeout", lambda d: f"{d['hooks']['on_error']} / {d['hooks']['on_timeout']}"),
        ("Also runs", lambda d: ", ".join(d["hooks"]["also_runs"]) or "none"),
        ("Permissions", lambda d: d["permissions"]["location"]),
        ("Sandbox", lambda d: ("yes: " if d["sandbox"]["available"] else "no: ") + d["sandbox"]["notes"]),
        ("MCP", lambda d: d["mcp"]["location"]),
    ]
    lines = ["<!-- Generated by aidlc trace from core/adapters/*.yaml. Do not edit: run `bin/aidlc trace`. -->",
             "# Tool capabilities (generated)", "",
             "What each AI coding tool reads and enforces, from its official docs (sources in each descriptor). "
             "Only `supported` tools are rendered today (ADR 0006).", "",
             "| | " + " | ".join(tools) + " |", "|---|" + "---|" * len(tools)]
    for label, cell in rows:
        lines.append(f"| {label} | " + " | ".join(cell(caps[t]).replace("|", "\\|") for t in tools) + " |")
    return "\n".join(lines) + "\n"
```

The judge and the trace:
- **In `conftest_check._is_agent_config`:**

```python
def _is_agent_config(folded: str) -> bool:
    dirs, files, prefixes = agent_config_markers()
    parts = folded.split("/")
    return (any(part in dirs for part in parts) or parts[-1] in files or folded.startswith(prefixes)
            or folded.startswith((".aidlc/hooks/", ".aidlc/rules/")))
```

  with `from ..adapters.capabilities import agent_config_markers`.
- **In `trace.collect`:** add `core/adapters/*.yaml` with kind `adapter`, mirroring the `core/observability` block.
- **In `trace.generated_docs`:** add `root / "docs" / "adapters" / "capabilities.md": capabilities_doc(root)`. Import it locally inside the function to avoid an import cycle.
- Run `bin/aidlc trace`.
- [ ] **Step 4: Run the tests and watch them pass.** Run the Step 2 command, then `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_conftest_check -v`, `bin/aidlc trace --check`, `make test`, and `AIDLC_TOOLS_DIR=… make policy-test`. Expected: everything passes. If an existing test repository fixture holds another tool's file and now FAILs, that is a real finding: stop and report, and do not change the fixture's assertion.
- [ ] **Step 5: Commit.** Commit with `feat(adapters): capability descriptors for claude-code (supported), copilot, cursor and codex (planned); the CI judge recognises every tool's agent configuration`.

### Task 4: The hook shim's tool-neutral flow and its Claude dialect

**Files:**
- Modify: `core/hooks/claude_shim.py`
- Test: `tests/unit/test_shim_dialects.py`

**Interfaces:**
- `claude_shim.run(argv, dialect) -> int` is the tool-neutral flow.
- `claude_shim.CLAUDE` is the dialect: `phases`, `to_generic`, `encode_pre(result, redact)` and `encode_post(result, redact)`, each returning stdout text or `None`, plus `error_exit` (2).
- `main(argv)` is `run(argv, CLAUDE)`.
- `to_generic` and `CLASSES` stay at module level, unchanged.
- A later tool adds a dialect file that imports `run`, and is listed in that adapter's hook files.

- [ ] **Step 1: Write the failing tests.**

```python
# tests/unit/test_shim_dialects.py
import contextlib
import io
import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

from tests.hook_loader import load_hook
from tests.unit.test_guard import GuardEnv

shim = load_hook("claude_shim")


def fake_dialect():
    """A Copilot-like dialect: camelCase payload, top-level permissionDecision."""
    def to_generic(payload, phase):
        return {"session": payload.get("sessionId"), "call": None, "tool": payload["toolName"],
                "args": payload.get("toolArgs") or {}, "cwd": payload.get("cwd") or os.getcwd()}

    def encode_pre(result, redact):
        if result["decision"] in ("ask", "deny"):
            return json.dumps({"permissionDecision": result["decision"],
                               "permissionDecisionReason": redact(f"[aidlc {result['rule']}] {result['reason']}")})
        return None

    return SimpleNamespace(phases=("pre",), to_generic=to_generic, encode_pre=encode_pre,
                           encode_post=lambda result, redact: None, error_exit=2)


def run(dialect, argv, stdin):
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin)), contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(io.StringIO()):
        code = shim.run(argv, dialect)
    return code, out.getvalue()


class ShimDialectTest(unittest.TestCase):
    def test_claude_is_a_dialect_of_the_same_flow(self):
        self.assertEqual(shim.CLAUDE.phases, ("pre", "post", "post-failure"))
        self.assertIs(shim.CLAUDE.to_generic, shim.to_generic)
        self.assertEqual(shim.CLAUDE.error_exit, 2)

    def test_a_second_dialect_uses_the_same_flow(self):
        with GuardEnv():
            code, out = run(fake_dialect(), ["x", "pre"],
                            json.dumps({"sessionId": "s", "toolName": "shell", "toolArgs": {"command": "git push"}}))
        self.assertEqual(code, 0)
        body = json.loads(out)
        self.assertEqual(body["permissionDecision"], "deny")
        self.assertIn("[aidlc shell-deny]", body["permissionDecisionReason"])

    def test_a_second_dialect_fails_closed_on_bad_input(self):
        with GuardEnv():
            code, out = run(fake_dialect(), ["x", "pre"], "not json")
        self.assertEqual((code, out), (2, ""))

    def test_a_phase_the_dialect_lacks_fails_closed(self):
        with GuardEnv():
            code, _ = run(fake_dialect(), ["x", "post"], "{}")
        self.assertEqual(code, 2)
```

  If `GuardEnv`'s rules name the deny rule differently from `shell-deny` for `git push`, use the rule the existing `tests/unit/test_claude_shim.py` deny test uses, and record a ruling. The assertion's intent (the guard's deny reaches the dialect's output) stays the same.
- [ ] **Step 2: Run them and watch them fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_shim_dialects -v`. Expected: `AttributeError` (no `CLAUDE` or `run`).
- [ ] **Step 3: Restructure `claude_shim.py`, without changing its behaviour.**
  1. Rename `main`'s body to `run(argv, dialect)`.
  2. Replace `("pre", "post", "post-failure")` with `dialect.phases`. The error message names the dialect's phases.
  3. Replace `to_generic(payload, phase)` with `dialect.to_generic(payload, phase)`.
  4. Replace the pre-phase `print(json.dumps({"hookSpecificOutput": …}))` with `text = dialect.encode_pre(result, guard._redact)`, then `if text: print(text)`.
  5. Replace the post-phase `print(json.dumps({"decision": "block", …}))` with `text = dialect.encode_post(result, guard._redact)`, then `if text: print(text)`.
  6. Make every `return 2` `return dialect.error_exit`.
  7. Define `_claude_pre(result, redact)`, which returns the existing `hookSpecificOutput` JSON for ask or deny, else `None`. Define `_claude_post(result, redact)`, which returns the existing `{"decision": "block", …}` JSON for flag, else `None`.
  8. Define `CLAUDE = SimpleNamespace(phases=("pre", "post", "post-failure"), to_generic=to_generic, encode_pre=_claude_pre, encode_post=_claude_post, error_exit=2)`.
  9. Set `def main(argv): return run(argv, CLAUDE)`.
  10. Update the docstring: "the tool-neutral flow is `run`; Claude Code is the `CLAUDE` dialect".
- [ ] **Step 4: Run the tests and watch them pass.**
  - Run the Step 2 command;
  - run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_claude_shim tests.unit.test_hook_record_ids tests.unit.test_attacks_direct tests.unit.test_retry_limit -v`;
  - run `make test`;
  - run `bin/aidlc render --tool claude-code --check .`.

  Expected: everything passes. The rendered hook files are byte-identical apart from the shim, and the shim's behaviour is pinned by the unchanged tests.
- [ ] **Step 5: Commit.** Commit with `refactor(hooks): the shim's tool-neutral flow (run) and its Claude dialect; a second tool adds a dialect`.

### Task 5: ADR 0006, the rewritten Copilot notes, and the interface docs

**Files:**
- Create: `docs/adr/0006-multi-tool-foundation.md`
- Modify:
  - `docs/adapters/copilot.md` (rewritten);
  - `docs/adapters/interface.md` (six functions, `render_outputs`, owners, descriptors);
  - the design: a dated note under §4.3;
  - `docs/codebase-map.md` (areas `core/adapters/` and `cli/aidlc/adapters/capabilities.py`; a "Where common changes go" line for a new tool);
  - `README.md` (link).
- Test: `tests/unit/test_multitool_docs.py`

- [ ] **Step 1: Write the failing test.**

```python
# tests/unit/test_multitool_docs.py
import unittest

from aidlc.paths import framework_root

ROOT = framework_root()


class MultiToolDocsTest(unittest.TestCase):
    def test_adr_records_the_foundation(self):
        text = (ROOT / "docs/adr/0006-multi-tool-foundation.md").read_text(encoding="utf-8")
        for needle in ("owner", "render_outputs", "core/adapters", "dialect", "fail-open", "also_runs"):
            self.assertIn(needle, text)

    def test_copilot_notes_are_current(self):
        text = (ROOT / "docs/adapters/copilot.md").read_text(encoding="utf-8")
        for needle in (".agent.md", "managed-settings.json", "chat.agent.sandbox", "cloud agent", "Local",
                       ".claude/settings.json", "fail open", "capabilities.md"):
            self.assertIn(needle, text)
        self.assertNotIn("no direct permissions.yaml equivalent", text)

    def test_interface_lists_six_functions(self):
        text = (ROOT / "docs/adapters/interface.md").read_text(encoding="utf-8")
        for needle in ("render_skills", "render_agents", "render_outputs", "core/adapters"):
            self.assertIn(needle, text)
```

- [ ] **Step 2: Run it and watch it fail.** Run `PYTHONPATH=cli:. python3 -m unittest tests.unit.test_multitool_docs -v`. Expected: FAIL.
- [ ] **Step 3: Write the docs.** Use short sentences, British spelling, and "you".

**1. ADR 0006, "A multi-tool foundation before the second tool".** Status: accepted, 2026-10-23.
- **Context:** the orphan bug; four of six functions; Claude-only judging of agent configuration; the shim's Claude coupling; and the official docs showing the tools converging (AGENTS.md, `.agents/skills`, Claude-shaped hooks) yet differing on failure behaviour.
- **Decision:**
  - manifest owners;
  - the six functions and `render_outputs`;
  - capability descriptors as data, with a generated comparison;
  - every known tool's configuration is agent configuration for the judge;
  - the shim split into flow and dialect.
- **Rules for adding a tool:**
  1. Write its descriptor first.
  2. Make its hooks fail closed where the tool allows it (Cursor `failClosed: true`), and back them with its declarative deny rules where it does not (Copilot timeouts, Codex).
  3. Each tool reads only its own rendered files. A tool that also runs Claude's hooks (`also_runs`) needs a test proving the guard does not run twice.
  4. Run the shared hook fixtures through its dialect.
- **Consequences:**
  - adding Copilot means a descriptor (done), a renderer set, a dialect, and doctor checks;
  - repositories with hand-written Cursor, Copilot or Codex files now fail the CI judge until those files are imported (the Adoption plan).

**2. `docs/adapters/copilot.md`,** rewritten. It covers:
- the three surfaces: the VS Code Copilot harness (shared with the CLI), VS Code **Local**, and the **cloud agent**, and which files each reads;
- the corrected facts:
  - agents are `.agent.md`;
  - permissions are real: `managed-settings.json` deny > ask > allow, and the CLI's `--deny-tool`;
  - the OS sandbox: `chat.agent.sandbox` and CLI `--sandbox`;
  - hooks: a non-zero exit denies; timeouts **fail open**; "ask" becomes "deny" in the cloud agent;
  - cross-reads: Copilot runs `.claude/settings.json` hooks too;
  - organisation-managed settings turn off the Claude and Codex harnesses in VS Code;
- the implementation outline, a renderer per surface;
- a link to `docs/adapters/capabilities.md`.

  Remove the sentence "there is no direct permissions.yaml equivalent".

**3. `docs/adapters/interface.md`:** the six functions; `render_outputs`; owners in the manifest; descriptors; dialects. Remove "Copilot Plan 5".

**4. The design §4.3 note, the codebase map and the README** as listed.
- [ ] **Step 4: Run the tests and the checks, and watch them pass.** Run the Step 2 command, `bin/aidlc trace --check`, `bin/aidlc check context-drift .` and `make test`. Expected: everything passes.
- [ ] **Step 5: Commit.** Commit with `docs(adapters): ADR 0006 multi-tool foundation; Copilot notes rewritten from today's official docs; interface updated`.

### Task 6: The pull request (controller, with the user's go-ahead)

- [ ] **Step 1: The final review.** A fresh reviewer on the most capable model reviews the whole branch, with the Review Focus above. Fix findings under the stop rule.
- [ ] **Step 2: Push and open the pull request.** Run the pre-push scan, then push and open the pull request with the user's go-ahead. The user approves the `ai-gates` runs. `agent-config-evals` runs the attack suite, because the shim changed. Answer the review comments.
- [ ] **Step 3: Merge.** After the user merges, revise Plan 5a (see below) on its branch, rebased on `main`.

---

## After this plan: the changes to Plan 5a (already agreed)

- **The plugin build becomes the Claude adapter's distribution output.** `aidlc plugin build` stays the command. It takes Claude's tool names from `core/adapters/claude-code.yaml` (`agents.tool_names`), not from its own constant.
- **Skills declare how they start.**
  - A neutral `metadata.invocation: auto | manual`.
  - **`manual`** for the gated stages: intent, specify, plan, build-slice. Claude gets `disable-model-invocation: true`.
  - **`auto`** for the read-only ones: context-setup's survey, and verify.
- **The ideas from agent-skills:**
  - "fires" and "stays quiet" eval pairs;
  - one pressure case per skill;
  - a "Common excuses" table and a "Red flags" section in every skill, enforced by the format test.

## Self-review notes

- **Design §4.3:** six functions (Task 2) and a runtime shim with dialects (Task 4). "Adding Copilot later means one shim and six renderers": now one dialect, a renderer set, and a descriptor.
- **Research gaps closed:**
  - A1 the orphan bug (Task 1);
  - A2 the missing functions and the duplicated lists (Task 2);
  - A4 other tools' configuration is never judged (Task 3);
  - the shim's coupling (Task 4);
  - the out-of-date Copilot notes (Task 5).
- **Deliberately later:**
  - a per-tool `tool_names` map in the repository config;
  - per-adapter doctor checks and Rego;
  - the `context_drift` `CLAUDE.md` rule;
  - telemetry, evals and AI review for other tools;
  - the Copilot renderers.

  Each is tied to building that tool, and the descriptors now make the gap visible.
- **Placeholder scan:** none. Task 4's rule name is checked against the existing deny test.
- **Type consistency:** `owner` names are adapter names (`claude-code`, `copilot`), equal to the descriptors' `tool` and to `adapter_names()`.
