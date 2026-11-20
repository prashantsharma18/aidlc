"""Plan 17: aidlc is one plugin at the repository root, with no pack and no pack contract."""
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ("docs/plans/", "docs/design/", "docs/verification/", "docs/archive/", "docs/adr/")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if (ROOT / p).is_file()]


def live(paths: list[str]) -> list[str]:
    """Files that describe the kit as it is today: not history (decision records included), not this test."""
    keep = []
    for p in paths:
        if p.startswith(HISTORY) or p == "scripts/test_one_plugin.py":
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

    def test_no_live_document_names_the_pack(self):
        docs = [p for p in live(tracked()) if not p.endswith(".py")]
        hits = [p for p in docs if re.search(r"aidlc-modernize|modernize-|dotnet-modernize|java-modernize", read(p))]
        self.assertEqual(hits, [])

    def test_the_marketplace_lists_one_plugin(self):
        market = json.loads(read(".claude-plugin/marketplace.json"))
        self.assertEqual([p["name"] for p in market["plugins"]], ["aidlc"])

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
        docs = [p for p in live(tracked()) if not p.endswith(".py")]
        hits = [p for p in docs if "plugins/aidlc" in read(p)]
        self.assertEqual(hits, [])


    def test_no_live_code_names_the_pack(self):
        code = [p for p in live(tracked()) if p.endswith(".py")]
        hits = [p for p in code if re.search(r"aidlc-modernize|modernize-|dotnet-modernize|java-modernize", read(p))]
        self.assertEqual(hits, [])

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

    def test_adr_0011_is_superseded(self):
        self.assertIn("Superseded by ADR 0018", read("docs/adr/0011-plugins-and-packs.md"))

    def test_the_decision_is_recorded_and_released(self):
        self.assertTrue((ROOT / "docs/adr/0018-one-plugin-at-the-root.md").is_file())
        self.assertEqual(json.loads(read(".claude-plugin/plugin.json"))["version"], "6.0.0")


class ReviewFixesTest(unittest.TestCase):
    """Plan 17 final review: each test was seen failing before its fix."""

    def test_i1_ci_fetches_the_tags_the_archive_test_reads(self):
        self.assertIn("fetch-depth: 0", read(".github/workflows/validate.yml"))
        self.assertIn("git push origin aidlc-modernize-archive", read("docs/archive/aidlc-modernize.md"))

    def test_m1_teammates_get_an_upgrade_note(self):
        adr = read("docs/adr/0018-one-plugin-at-the-root.md")
        self.assertIn("## Upgrading a repository onboarded with aidlc 4", adr)
        self.assertIn("`aidlc-modernize@aidlc`", adr)

    def test_m5_both_starters_keep_the_install_and_the_cache_paths(self):
        for kind in ("repo", "workspace"):
            settings = json.loads(read(f"starter/{kind}/.claude/settings.json"))
            self.assertTrue(settings["enabledPlugins"]["aidlc@aidlc"], kind)
            self.assertIn("aidlc", settings["extraKnownMarketplaces"], kind)
            self.assertIn("Read(~/.claude/plugins/cache/aidlc/**)", settings["permissions"]["allow"], kind)

    def test_m6_m7_no_stale_wording(self):
        self.assertNotIn("the marketplace check", read("docs/codebase-map.md"))
        self.assertNotIn("Raise a plugin's version", read("docs/codebase-map.md") + read("README.md"))
        agents_map = read("AGENTS.md").split("## Map", 1)[1].split("\n## ", 1)[0]
        self.assertEqual(agents_map.count(".claude-plugin"), 1)

if __name__ == "__main__":
    unittest.main()
