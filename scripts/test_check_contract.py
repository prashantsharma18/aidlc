"""Tests for starter/repo/scripts/check_contract_version.py (the provider) and check_contract_pin.py (the consumer).
A fake oasdiff stands in for the real one: it reports a breaking change when a path of the base is gone."""
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_contract_version  # noqa: E402

GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null", "-c", "tag.gpgsign=false"]
FAKE_OASDIFF = """#!{python}
import pathlib, sys
pathlib.Path(sys.argv[0] + ".args").write_text("\\n".join(sys.argv[1:]))
base, revision = (pathlib.Path(p).read_text().splitlines() for p in sys.argv[-2:])
gone = [line for line in base if line.startswith("  /") and line not in revision]
if gone:
    print("error [api-path-removed-without-deprecation] " + gone[0].strip())
    sys.exit(1)
"""


def contract(version: str = "1.0.0", paths: tuple[str, ...] = ("/shipments/{id}",)) -> str:
    body = "".join(f"  {p}:\n    get:\n      responses:\n        '200':\n          description: ok\n" for p in paths)
    return f"openapi: 3.0.3\ninfo:\n  title: Shipments\n  version: {version}\n  contact:\n    name: core\npaths:\n{body}"


def git(root: Path, *args: str) -> str:
    return subprocess.run(GIT + ["-C", str(root), *args], check=True, capture_output=True, text=True).stdout.strip()


class Provider:
    """A provider repository whose main published api-v1.0.0."""

    def __init__(self, tmp: Path):
        self.root = tmp / "shipments-api"
        self.root.mkdir()
        git(self.root, "init", "-q", "-b", "main")
        self.commit(contract("1.0.0"))
        git(self.root, "tag", "api-v1.0.0")
        self.oasdiff = tmp / "oasdiff"
        self.oasdiff.write_text(FAKE_OASDIFF.format(python=sys.executable), encoding="utf-8")
        self.oasdiff.chmod(0o755)

    def commit(self, text: str) -> str:
        (self.root / "openapi.yaml").write_text(text, encoding="utf-8")
        git(self.root, "add", "openapi.yaml")
        git(self.root, "commit", "-q", "-m", "contract")
        return git(self.root, "rev-parse", "HEAD")

    def check(self) -> tuple[list[str], list[str]]:
        return check_contract_version.check(self.root, "openapi.yaml", str(self.oasdiff))


class InfoVersionTest(unittest.TestCase):
    def test_yaml_json_and_quotes(self):
        v = check_contract_version.info_version
        self.assertEqual(v(contract("2.1.0")), "2.1.0")
        self.assertEqual(v("openapi: 3.1.0\ninfo:\n  title: x\n  version: '3.0.1'  # pinned\n"), "3.0.1")
        self.assertEqual(v('{"openapi": "3.1.0", "info": {"title": "x", "version": "1.2.3"}}'), "1.2.3")

    def test_a_nested_version_is_not_info_version(self):
        text = "info:\n  title: x\n  contact:\n    version: 9.9.9\npaths: {}\nversion: 8.8.8\n"
        self.assertIsNone(check_contract_version.info_version(text))


class ProviderTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = Provider(Path(tmp.name))

    def test_the_first_version_needs_no_tag(self):
        git(self.provider.root, "tag", "-d", "api-v1.0.0")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertIn("becomes the first published version", notes[0])

    def test_an_unchanged_contract_is_clean(self):
        self.assertEqual(self.provider.check(), ([], ["openapi.yaml is unchanged since api-v1.0.0"]))

    def test_an_additive_change_with_a_new_minor_is_clean(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/shipments/{id}", "/shipments")),
                                                         encoding="utf-8")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertEqual(notes, ["no breaking change since api-v1.0.0"])
        args = Path(str(self.provider.oasdiff) + ".args").read_text().splitlines()
        self.assertEqual(args[:4], ["breaking", "--fail-on", "ERR", "--allow-external-refs=false"])

    def test_a_change_without_a_new_version_is_a_problem(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.0.0", ("/shipments/{id}", "/shipments")),
                                                         encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["openapi.yaml changed since api-v1.0.0, but info.version 1.0.0 "
                                                    "is not above 1.0.0: raise it"])

    def test_a_breaking_change_needs_a_new_major(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/parcels/{id}",)), encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["a breaking change since api-v1.0.0 without a new MAJOR version: "
                                                    "make it additive, or raise MAJOR with the consumers' agreement "
                                                    "(expand and contract)"])

    def test_a_breaking_change_with_a_new_major_asks_for_the_agreement(self):
        (self.provider.root / "openapi.yaml").write_text(contract("2.0.0", ("/parcels/{id}",)), encoding="utf-8")
        problems, notes = self.provider.check()
        self.assertEqual(problems, [])
        self.assertIn("records each consumer's agreement", notes[0])
        self.assertIn("api-path-removed", notes[1])

    def test_a_missing_oasdiff_fails_closed(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/shipments",)), encoding="utf-8")
        problems, _ = check_contract_version.check(self.provider.root, "openapi.yaml",
                                                   str(self.provider.root / "no-such-oasdiff"))
        self.assertEqual(problems, ["oasdiff could not compare the contracts (exit 127)"])

    def test_a_bad_version_is_a_problem(self):
        (self.provider.root / "openapi.yaml").write_text(contract("v2"), encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["openapi.yaml: info.version must be MAJOR.MINOR.PATCH, not 'v2'"])

    def test_publish_names_a_new_version_only(self):
        publish = check_contract_version.publish_tag
        self.assertEqual(publish(self.provider.root, "openapi.yaml"), (None, []))
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        self.assertEqual(publish(self.provider.root, "openapi.yaml"), ("api-v1.1.0", []))

    def test_publish_refuses_a_lower_or_a_changed_published_version(self):
        publish = check_contract_version.publish_tag
        git(self.provider.root, "tag", "api-v1.2.0")
        self.provider.commit(contract("1.1.0"))
        self.assertEqual(publish(self.provider.root, "openapi.yaml")[1],
                         ["openapi.yaml 1.1.0 is not above the published api-v1.2.0"])
        self.provider.commit(contract("1.0.0", ("/other",)))
        self.assertIn("a published version never changes", publish(self.provider.root, "openapi.yaml")[1][0])

    def test_the_command_prints_only_the_tag(self):
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_contract_version.main(["--contract", "openapi.yaml", "--publish-tag",
                                                "--root", str(self.provider.root)])
        self.assertEqual((code, out.getvalue()), (0, "api-v1.1.0\n"))


if __name__ == "__main__":
    unittest.main()
