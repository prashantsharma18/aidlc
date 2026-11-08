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

    def test_no_live_document_names_the_pack(self):
        docs = [p for p in live(tracked()) if not p.endswith(".py")]
        hits = [p for p in docs if re.search(r"aidlc-modernize|modernize-|dotnet-modernize|java-modernize", read(p))]
        self.assertEqual(hits, [])

    def test_the_marketplace_lists_one_plugin(self):
        market = json.loads(read(".claude-plugin/marketplace.json"))
        self.assertEqual([p["name"] for p in market["plugins"]], ["aidlc"])


if __name__ == "__main__":
    unittest.main()
