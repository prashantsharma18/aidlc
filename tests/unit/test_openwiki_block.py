import unittest

from aidlc.checks.openwiki_block import check_openwiki
from aidlc.paths import framework_root
from tests.helpers import TempRepo, run_cli

BASELINE = (framework_root() / "core/context/openwiki/openwikiignore.baseline").read_text(
    encoding="utf-8")
GOOD_BLOCK = ("<!-- OPENWIKI:START -->\n## Generated wiki (derived; verify against code)\n"
              "- Start at [openwiki/quickstart.md](openwiki/quickstart.md)\n<!-- OPENWIKI:END -->\n")


def repo(agents_block=GOOD_BLOCK, claude="@AGENTS.md\n", ignore=BASELINE, wiki=True):
    files = {"AGENTS.md": "# x\n" + agents_block, "CLAUDE.md": claude}
    if ignore is not None:
        files[".openwikiignore"] = ignore
    if wiki:
        files["openwiki/quickstart.md"] = "# q\n"
    return files


class OpenWikiTest(unittest.TestCase):
    def fails(self, files):
        with TempRepo(files) as root:
            return [str(f) for f in check_openwiki(root) if f.level == "FAIL"]

    def test_good_repo_passes(self):
        self.assertEqual(self.fails(repo()), [])

    def test_oversized_block_fails(self):
        block = "<!-- OPENWIKI:START -->\n" + "- see openwiki/a.md\n" * 16 + "<!-- OPENWIKI:END -->\n"
        self.assertTrue(any("16 lines" in m for m in self.fails(repo(agents_block=block))))

    def test_non_pointer_content_fails(self):
        block = "<!-- OPENWIKI:START -->\nThe service uses Redis for sessions.\n<!-- OPENWIKI:END -->\n"
        self.assertTrue(any("not a pointer" in m for m in self.fails(repo(agents_block=block))))

    def test_block_in_claude_md_fails(self):
        self.assertTrue(any("CLAUDE.md" in m for m in self.fails(repo(claude="@AGENTS.md\n" + GOOD_BLOCK))))

    def test_unpaired_markers_fail(self):
        self.assertTrue(self.fails(repo(agents_block="<!-- OPENWIKI:START -->\n- openwiki/x.md\n")))

    def test_missing_ignore_baseline_line_fails(self):
        trimmed = BASELINE.replace(".env.*\n", "")
        self.assertTrue(any(".env.*" in m for m in self.fails(repo(ignore=trimmed))))

    def test_no_wiki_no_block_is_fine(self):
        self.assertEqual(self.fails(repo(agents_block="", ignore=None, wiki=False)), [])

    def test_cli(self):
        with TempRepo(repo()) as root:
            code, out, _ = run_cli("check", "openwiki", str(root))
            self.assertEqual(code, 0, out)
