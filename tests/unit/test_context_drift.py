import unittest
from datetime import date

from aidlc.checks.context_drift import check_context_drift
from tests.helpers import TempRepo, git, run_cli

TODAY = date(2026, 10, 18)


def files(map_date="2026-10-10", commit=None, agents_extra=""):
    agents = ("# svc: agent guide\n"
              "- Map: `docs/codebase-map.md`; code in `src/` and `src/app/**/*.ts`\n"
              "- Check: `npm run check` and `make test` and `aidlc check`\n"
              "- Placeholders: `src/auth/<feature>/`, `req.ip`, `config.get()`, `flags.isEnabled`\n"
              + agents_extra)
    cmap = (f"# svc: codebase map\nOwner: team · Last verified: {map_date}, against commit "
            f"{commit or 'HEAD_PLACEHOLDER'}\n")
    return {"AGENTS.md": agents.replace("\n", "\r\n"), "docs/codebase-map.md": cmap,
            "src/app/main.ts": "x\n", "package.json": '{"scripts": {"check": "x"}}\n',
            "Makefile": "test:\n\techo ok\n"}


def with_real_commit(root, map_date="2026-10-10"):
    sha = git(root, "rev-parse", "--short", "HEAD")
    (root / "docs/codebase-map.md").write_text(
        f"# svc: codebase map\nOwner: team · Last verified: {map_date}, against commit {sha}\n",
        encoding="utf-8")


class ContextDriftTest(unittest.TestCase):
    def test_clean_repo_has_no_fail(self):
        with TempRepo(files()) as root:
            with_real_commit(root)
            findings = check_context_drift(root, TODAY)
            self.assertEqual([f for f in findings if f.level == "FAIL"], [], findings)

    def test_stale_path_fails(self):
        with TempRepo(files(agents_extra="- Old: `src/legacy/old.ts`\n")) as root:
            with_real_commit(root)
            msgs = [str(f) for f in check_context_drift(root, TODAY)]
            self.assertTrue(any("src/legacy/old.ts" in m and m.startswith("FAIL") for m in msgs))

    def test_missing_npm_script_and_make_target_fail(self):
        extra = "- `npm run nope` and `make nope` and `aidlc nope`\n"
        with TempRepo(files(agents_extra=extra)) as root:
            with_real_commit(root)
            msgs = " ".join(str(f) for f in check_context_drift(root, TODAY))
            self.assertIn("npm script 'nope'", msgs)
            self.assertIn("make target 'nope'", msgs)
            self.assertIn("aidlc subcommand 'nope'", msgs)

    def test_old_map_warns_and_unknown_commit_fails(self):
        with TempRepo(files(map_date="2026-01-01", commit="deadbee")) as root:
            findings = check_context_drift(root, TODAY)
            self.assertTrue(any(f.level == "WARN" and "older than" in f.message for f in findings))
            self.assertTrue(any(f.level == "FAIL" and "deadbee" in f.message for f in findings))

    def test_long_agents_md_fails(self):
        with TempRepo(files(agents_extra="- line\n" * 210)) as root:
            with_real_commit(root)
            self.assertTrue(any(f.level == "FAIL" and "lines" in f.message
                                for f in check_context_drift(root, TODAY)))

    def test_cli_exit_codes_and_subdirectory(self):
        with TempRepo(files(agents_extra="- `missing/file.md`\n")) as root:
            with_real_commit(root)
            code, out, _ = run_cli("check", "context-drift", cwd=root / "src")
            self.assertEqual(code, 1, out)
            self.assertIn("context-drift:", out)
            self.assertIn("missing/file.md", out)  # proves the root, not src/, was checked
