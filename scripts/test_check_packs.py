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

    def test_an_undeclared_pack_is_found_when_core_is_enabled_elsewhere(self):
        problems = self.run_check(NONE, {"aidlc-modernize@aidlc": True})
        self.assertTrue(any("does not declare" in p for p in problems), problems)

    def test_local_settings_are_read_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo(root, NONE, {"aidlc@aidlc": True})
            (root / ".claude" / "settings.local.json").write_text(json.dumps({"enabledPlugins": {"aidlc-modernize@aidlc": True}}))
            problems = check_packs.check(root)
        self.assertTrue(any("settings.local.json" in p and "does not declare" in p for p in problems), problems)

    def test_copilot_settings_count_as_an_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo(root, ONE)
            (root / ".github" / "copilot").mkdir(parents=True)
            (root / ".github" / "copilot" / "settings.json").write_text(
                json.dumps({"enabledPlugins": {"aidlc@aidlc": True, "aidlc-modernize@aidlc": True}}))
            self.assertEqual(check_packs.check(root), [])
            (root / ".github" / "copilot" / "settings.json").write_text(json.dumps({"enabledPlugins": {"aidlc@aidlc": True}}))
            problems = check_packs.check(root)
        self.assertTrue(any(".github/copilot/settings.json" in p and "does not switch it on" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
