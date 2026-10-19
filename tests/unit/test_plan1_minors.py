"""Deferred minor findings m1-m15 from the Plan 1 and Plan 2 task reviews. One test each."""
import json
import os
import re
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import jsonschema
import yaml

from aidlc.adapters.base import write_rendered
from aidlc.adapters.claude_code import ClaudeCodeAdapter
from aidlc.checks.context_drift import check_context_drift
from aidlc.checks.openwiki_block import check_openwiki
from aidlc.harness import HarnessError, effective_permissions, load_narrowing
from aidlc.paths import framework_root
from aidlc.policy import load_policy
from aidlc.repo import init_repo, load_config
from aidlc.scope import ScopeError, approved_ref, parse_may_change
from tests.helpers import TempRepo, git, run_cli

TODAY = date(2026, 10, 18)
GOOD_MAP = "# m\nOwner: team · Last verified: 2026-10-10, against commit {sha}\n"


def drift_repo(files):
    """A committed repository with a valid codebase map; `files` override or add to it."""
    base = {"AGENTS.md": "# svc\n", "docs/codebase-map.md": GOOD_MAP.format(sha="0000000")}
    base.update(files)
    return TempRepo(base)


def drift_fails(root):
    sha = git(root, "rev-parse", "--short", "HEAD")
    cmap = root / "docs/codebase-map.md"
    text = cmap.read_text(encoding="utf-8")
    cmap.write_text(re.sub(r"commit [0-9a-f]+", f"commit {sha}", text), encoding="utf-8")
    return [str(f) for f in check_context_drift(root, TODAY) if f.level == "FAIL"]


def scaffold(root, profile="node"):
    init_repo(root, "svc", "team", profile, "purpose", date(2026, 10, 19))


class M1DriftNeverTracebacks(unittest.TestCase):
    def test_m1_invalid_glob_names_the_file(self):
        with drift_repo({"AGENTS.md": "# svc\n- see `src/**.ts`\n"}) as root:
            self.assertTrue(any("AGENTS.md" in m and "src/**.ts" in m for m in drift_fails(root)))

    def test_m1_invalid_package_json_names_the_file(self):
        with drift_repo({"AGENTS.md": "# svc\n- run `npm run check`\n", "package.json": "{nope"}) as root:
            self.assertTrue(any("package.json" in m for m in drift_fails(root)))

    def test_m1_impossible_map_date_names_the_map(self):
        cmap = "# m\nOwner: team · Last verified: 2026-13-45, against commit 0000000\n"
        with drift_repo({"docs/codebase-map.md": cmap}) as root:
            sha = git(root, "rev-parse", "--short", "HEAD")
            (root / "docs/codebase-map.md").write_text(cmap.replace("0000000", sha), encoding="utf-8")
            fails = [str(f) for f in check_context_drift(root, TODAY) if f.level == "FAIL"]
            self.assertTrue(any("docs/codebase-map.md" in m and "2026-13-45" in m for m in fails), fails)

    def test_m1_malformed_config_names_the_file(self):
        with drift_repo({".aidlc/config.yaml": "name: [unclosed\n"}) as root:
            self.assertTrue(any(".aidlc/config.yaml" in m for m in drift_fails(root)))

    def test_m1_non_utf8_rules_file_names_the_file(self):
        with drift_repo({}) as root:
            bad = root / ".aidlc/rules/api.md"
            bad.parent.mkdir(parents=True)
            bad.write_bytes(b"# rules \xff\xfe\n")
            self.assertTrue(any(".aidlc/rules/api.md" in m for m in drift_fails(root)))


class M2OutsideRepository(unittest.TestCase):
    def test_m2_path_resolving_outside_the_repository_fails(self):
        with drift_repo({"AGENTS.md": "# svc\n- see `../aidlc-m2-outside/AGENTS.md`\n"}) as root:
            outside = root.parent / "aidlc-m2-outside"
            outside.mkdir()
            try:
                (outside / "AGENTS.md").write_text("x\n", encoding="utf-8")
                fails = drift_fails(root)
            finally:
                shutil.rmtree(outside)
            self.assertTrue(any("../aidlc-m2-outside/AGENTS.md" in m and "outside" in m
                                for m in fails), fails)


class M3FolderRuleQuoting(unittest.TestCase):
    def test_m3_glob_with_quote_renders_valid_yaml(self):
        glob = 'src/a"b/**'
        rule = "---\npaths:\n  - 'src/a\"b/**'\n---\n# rule\n"
        with TempRepo({"AGENTS.md": "# x\n", ".aidlc/rules/api.md": rule}) as root:
            (out,) = ClaudeCodeAdapter().render_folder_rules(root)
            front = out.content.split("---\n")[1]
            self.assertEqual(yaml.safe_load(front), {"paths": [glob]})


class M4MayChangeParsing(unittest.TestCase):
    def test_m4_leading_colon_is_stripped(self):
        self.assertEqual(parse_may_change("MAY CHANGE: src/a.ts\n"), ["src/a.ts"])

    def test_m4_unfilled_placeholder_is_refused(self):
        for text in ("MAY CHANGE <glob>\n", "MAY CHANGE src/(new\n", "MAY CHANGE src/a)\n"):
            with self.subTest(text=text), self.assertRaises(ScopeError):
                parse_may_change(text)


class FixRound1(unittest.TestCase):
    def test_i1_bad_context_values_are_findings_not_tracebacks(self):
        for ctx in ("{rules_file: 5}", "{map: [a]}", "{rules_file: ../x.md}", "{rules_file: /etc/hosts}",
                    "{map: '~/m.md'}", "{rules_file: ''}"):
            with self.subTest(ctx=ctx), drift_repo({".aidlc/config.yaml": (
                    f"name: s\nowner: o\nprofile: node\ncontext: {ctx}\n")}) as root:
                fails = drift_fails(root)
                self.assertTrue(any(".aidlc/config.yaml" in m and
                                    ("rules_file" in m or "map" in m) for m in fails), fails)

    def test_m1_parentheses_inside_a_glob_are_refused(self):
        with self.assertRaises(ScopeError) as ctx:
            parse_may_change("MAY CHANGE: src/(group)/**\n")
        self.assertIn("src/(group)/**", str(ctx.exception))
        self.assertIn("parentheses in a glob are not supported", str(ctx.exception))
        self.assertEqual(parse_may_change("MAY CHANGE: src/** (the API)\n"), ["src/**"])

    def test_m2_non_mapping_context_and_commands_are_clear_errors(self):
        for key in ("context", "commands"):
            with self.subTest(key=key), TempRepo() as root:
                scaffold(root)
                path = root / ".aidlc/config.yaml"
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                data[key] = [1, 2]
                path.write_text(yaml.safe_dump(data), encoding="utf-8")
                with self.assertRaises(ValueError) as ctx:
                    load_config(root)
                self.assertIn(".aidlc/config.yaml", str(ctx.exception))

    def test_m3_drift_ignores_exported_git_variables(self):
        with drift_repo({"AGENTS.md": "# svc\n- see `dist/out.js` and `docs/codebase-map.md`\n",
                         ".gitignore": "dist/\n"}) as root:
            sha = git(root, "rev-parse", "--short", "HEAD")
            (root / "docs/codebase-map.md").write_text(GOOD_MAP.format(sha=sha), encoding="utf-8")
            with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent"}):
                fails = [f for f in check_context_drift(root, TODAY) if f.level == "FAIL"]
            self.assertEqual(fails, [])


class M5TraceRefusesHandWrittenDoc(unittest.TestCase):
    def test_m5_unmarked_generated_doc_is_not_overwritten(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            copy = tmp / "fw"
            shutil.copytree(framework_root(), copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            doc = copy / "docs" / "traceability.md"
            doc.write_text("# my own notes\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"AIDLC_HOME": str(copy)}):
                code, out, err = run_cli("trace")
            self.assertEqual(code, 1, out + err)
            self.assertEqual(doc.read_text(encoding="utf-8"), "# my own notes\n")
            self.assertIn("traceability.md", out + err)
        finally:
            shutil.rmtree(tmp)


class M6RefusalNamesSource(unittest.TestCase):
    def test_m6_refusals_name_the_exact_source(self):
        files = {"AGENTS.md": "# x\n", "CLAUDE.md": "mine\n", ".claude/rules/api.md": "mine\n",
                 ".claude/settings.json": "{}\n",
                 ".aidlc/rules/api.md": "---\npaths:\n  - 'src/**'\n---\n# r\n"}
        with TempRepo(files) as root:
            scaffold_files = {p: (root / p).read_text(encoding="utf-8") for p in files}
            scaffold(root)
            for p, text in scaffold_files.items():
                (root / p).write_text(text, encoding="utf-8")
            adapter = ClaudeCodeAdapter()
            rendered = (adapter.render_rules(root) + adapter.render_folder_rules(root)
                        + adapter.render_permissions(root))
            problems = write_rendered(root, rendered, check=False)
            joined = "\n".join(problems)
            for rel, sources in (("CLAUDE.md", [".aidlc/claude.md"]),
                                 (".claude/rules/api.md", [".aidlc/rules/api.md"]),
                                 (".claude/settings.json", ["core/policy/permissions.yaml",
                                                            ".aidlc/permissions.yaml"])):
                line = next((p for p in problems if p.startswith(rel + ":")), "")
                for source in sources:
                    self.assertIn(source, line, joined)


class M7UsageErrors(unittest.TestCase):
    def test_m7_scope_without_repository_exits_2_on_stderr(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as out_dir:
            code, out, err = run_cli("scope", "--repo", tmp, "--branch", "feat/x",
                                     "--out", str(Path(out_dir) / "scope"))
            self.assertEqual(code, 2, out + err)
            self.assertEqual(out, "")
            self.assertIn("aidlc scope", err)

    def test_m7_scope_malformed_approval_line_exits_2_on_stderr(self):
        approvals = "feat/x HEAD:plans/b.md lead 2026-10-18\n"
        with TempRepo({"plans/approved-bundles.txt": approvals}) as root, \
                tempfile.TemporaryDirectory() as out_dir:
            code, out, err = run_cli("scope", "--repo", str(root), "--branch", "feat/x",
                                     "--out", str(Path(out_dir) / "scope"))
            self.assertEqual(code, 2, out + err)
            self.assertEqual(out, "")
            self.assertIn("pin a commit sha", err)

    def test_m7_scope_unapproved_branch_stays_exit_1_on_stderr(self):
        with TempRepo({"plans/approved-bundles.txt": "# none\n"}) as root, \
                tempfile.TemporaryDirectory() as out_dir:
            code, out, err = run_cli("scope", "--repo", str(root), "--branch", "feat/x",
                                     "--out", str(Path(out_dir) / "scope"))
            self.assertEqual(code, 1)
            self.assertEqual(out, "")
            self.assertIn("refusing to start", err)

    def test_m7_init_repo_profiles_come_from_profiles_yaml(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            copy = tmp / "fw"
            shutil.copytree(framework_root() / "core", copy / "core")
            profiles = copy / "core/context/profiles.yaml"
            data = yaml.safe_load(profiles.read_text(encoding="utf-8"))
            data["golang"] = data["generic"]
            profiles.write_text(yaml.safe_dump(data), encoding="utf-8")
            with mock.patch.dict(os.environ, {"AIDLC_HOME": str(copy)}), TempRepo() as root:
                code, out, err = run_cli("init-repo", str(root), "--name", "x", "--owner", "o",
                                         "--profile", "golang", "--purpose", "p")
            self.assertEqual(code, 0, out + err)
        finally:
            shutil.rmtree(tmp)


class M8MakeTargets(unittest.TestCase):
    def test_m8_multi_target_line_and_lowercase_makefile(self):
        for name in ("Makefile", "GNUmakefile", "makefile"):
            with self.subTest(name=name), drift_repo(
                    {"AGENTS.md": "# svc\n- run `make test` and `make lint`\n",
                     name: "lint test:\n\techo ok\n"}) as root:
                self.assertEqual([m for m in drift_fails(root) if "make target" in m], [])

    def test_m8_missing_target_still_fails(self):
        with drift_repo({"AGENTS.md": "# svc\n- run `make nope`\n",
                         "Makefile": ".PHONY: test\ntest:\n\techo ok\n"}) as root:
            self.assertTrue(any("make target 'nope'" in m for m in drift_fails(root)))


OW_IGNORE = (framework_root() / "core/context/openwiki/openwikiignore.baseline").read_text(
    encoding="utf-8")


class M9OpenWikiPointers(unittest.TestCase):
    def test_m9_prose_mentioning_openwiki_is_not_a_pointer(self):
        block = ("<!-- OPENWIKI:START -->\n- see the openwiki/ folder for everything\n"
                 "<!-- OPENWIKI:END -->\n")
        with TempRepo({"AGENTS.md": "# x\n" + block, ".openwikiignore": OW_IGNORE,
                       "openwiki/q.md": "# q\n"}) as root:
            self.assertTrue([f for f in check_openwiki(root) if f.level == "FAIL"])

    def test_m9_no_pointer_warn_is_emitted_alongside_a_fail(self):
        files = {"AGENTS.md": "# x\n", "CLAUDE.md": "<!-- OPENWIKI:START -->\n", "openwiki/q.md": "# q\n"}
        with TempRepo(files) as root:
            levels = [(f.level, f.file) for f in check_openwiki(root)]
            self.assertIn(("FAIL", "CLAUDE.md"), levels)
            self.assertIn(("WARN", "AGENTS.md"), levels)


class M10GitEnvironment(unittest.TestCase):
    def test_m10_exported_git_variables_do_not_leak(self):
        approvals = "feat/x aaa111:plans/b.md lead 2026-10-18\n"
        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent", "GIT_WORK_TREE": "/nonexistent",
                                          "GIT_INDEX_FILE": "/nonexistent/index"}):
            with TempRepo({"plans/approved-bundles.txt": approvals}) as root:
                self.assertEqual(approved_ref(root, "feat/x"), "aaa111:plans/b.md")


class M11InterfaceDoc(unittest.TestCase):
    def test_m11_wire_classes_are_listed_exactly(self):
        text = (framework_root() / "docs/adapters/interface.md").read_text(encoding="utf-8")
        line = next(l for l in text.splitlines() if l.startswith("- Tool classes"))
        classes = re.findall(r"`([a-z]+(?: \| [a-z]+)+)`", line)
        self.assertEqual(classes[0].split(" | "), ["read", "edit", "shell", "mcp", "external"])
        self.assertIn("unknown-tool", text)
        self.assertNotIn("analyse", text)


class M12NarrowingNeverDropsBaselineDeny(unittest.TestCase):
    def test_m12_every_baseline_entry_survives_every_narrowing_key(self):
        base = load_policy("permissions")
        kinds = ("read", "edit", "shell", "tools")
        every = {k: sorted({*base["deny"].get(k, []), *base["ask"].get(k, [])}) for k in kinds}
        narrowing = {
            "allow_remove": every,
            "deny_add": {k: list(v) for k, v in every.items()},
            "ask_add": {k: list(v) for k, v in every.items() if k != "read"},
            "allow_add": [{"kind": k, "pattern": p, "reason": "r", "owner": "o"}
                          for k, v in every.items() for p in v],
            "secret_paths_add": list(base["secret_paths"]),
            "protected_paths_add": list(base["protected_paths"]),
        }
        with TempRepo() as root:
            (root / ".aidlc").mkdir()
            (root / ".aidlc/permissions.yaml").write_text(yaml.safe_dump(narrowing), encoding="utf-8")
            eff = effective_permissions(root)
        for section in ("deny", "ask"):
            for kind, entries in base.get(section, {}).items():
                for entry in entries:
                    self.assertIn(entry, eff[section][kind], f"{section}.{kind}: {entry}")
        for key in ("protected_paths", "secret_paths"):
            for entry in base[key]:
                self.assertIn(entry, eff[key], key)


class M13ConfigShape(unittest.TestCase):
    def test_m13_non_mapping_sections_are_a_clear_error(self):
        for key, value in (("harness", "5"), ("harness", "[a, b]"), ("tool_names", "x")):
            with self.subTest(key=key, value=value), TempRepo() as root:
                scaffold(root)
                path = root / ".aidlc/config.yaml"
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                data[key] = yaml.safe_load(value)
                path.write_text(yaml.safe_dump(data), encoding="utf-8")
                with self.assertRaises(ValueError) as ctx:
                    load_config(root)
                self.assertIn(".aidlc/config.yaml", str(ctx.exception))
                self.assertIn(key, str(ctx.exception))


class M14SymlinkedNarrowing(unittest.TestCase):
    def test_m14_symlinked_permissions_file_is_refused(self):
        with TempRepo() as root, tempfile.TemporaryDirectory() as other:
            real = Path(other) / "perm.yaml"
            real.write_text("deny_add: {shell: ['docker *']}\n", encoding="utf-8")
            (root / ".aidlc").mkdir()
            (root / ".aidlc/permissions.yaml").symlink_to(real)
            with self.assertRaises(HarnessError) as ctx:
                load_narrowing(root)
            self.assertIn("symlink", str(ctx.exception))


class M15AskAddRejectsRead(unittest.TestCase):
    def test_m15_ask_add_read_is_rejected_by_the_schema(self):
        schema = json.loads((framework_root() / "core/schemas/repo-permissions.schema.json")
                            .read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        self.assertTrue(list(validator.iter_errors({"ask_add": {"read": ["x/**"]}})))
        self.assertEqual(list(validator.iter_errors({"ask_add": {"edit": ["x/**"]}})), [])

    def test_m15_load_narrowing_raises_for_ask_add_read(self):
        with TempRepo() as root:
            (root / ".aidlc").mkdir()
            (root / ".aidlc/permissions.yaml").write_text("ask_add: {read: ['x/**']}\n", encoding="utf-8")
            with self.assertRaises(HarnessError):
                load_narrowing(root)


if __name__ == "__main__":
    unittest.main()
