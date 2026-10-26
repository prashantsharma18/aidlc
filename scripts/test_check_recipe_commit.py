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
