"""Tests for starter/repo/scripts/check_contract_version.py (the provider) and check_contract_pin.py (the consumer).
A fake oasdiff stands in for the real one: it reports a breaking change when a path of the base is gone."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_contract_pin  # noqa: E402
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


class FailClosedTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.provider = Provider(self.tmp)

    def clone(self, *options: str) -> Path:
        self.provider.commit(contract("1.0.0", ("/shipments/{id}", "/shipments")))
        target = self.tmp / "clone"
        subprocess.run(["git", "clone", "-q", *options, f"file://{self.provider.root}", str(target)],
                       check=True, capture_output=True)
        return target

    def test_a_shallow_clone_without_tags_is_a_problem(self):
        root = self.clone("--depth", "1")
        problems, _ = check_contract_version.check(root, "openapi.yaml", str(self.provider.oasdiff))
        self.assertEqual(len(problems), 1)
        self.assertIn("fetch-depth: 0", problems[0])
        tag, problems = check_contract_version.publish_tag(root, "openapi.yaml")
        self.assertIsNone(tag)
        self.assertIn("fetch-depth: 0", problems[0])

    def test_a_full_clone_without_tags_is_the_first_version(self):
        root = self.clone("--no-tags")
        problems, notes = check_contract_version.check(root, "openapi.yaml", str(self.provider.oasdiff))
        self.assertEqual(problems, [])
        self.assertIn("becomes the first published version", notes[0])

    def test_a_git_failure_is_a_problem(self):
        problems, _ = check_contract_version.check(self.tmp, "openapi.yaml", str(self.provider.oasdiff))
        self.assertEqual(problems, [])  # no file, no tags: nothing to check
        (self.tmp / "openapi.yaml").write_text(contract("1.0.0"), encoding="utf-8")
        problems, _ = check_contract_version.check(self.tmp, "openapi.yaml", str(self.provider.oasdiff))
        self.assertIn("fetch-depth: 0", problems[0])

    def test_a_deleted_published_contract_is_a_problem(self):
        (self.provider.root / "openapi.yaml").unlink()
        problems, _ = self.provider.check()
        self.assertEqual(problems, ["the published contract openapi.yaml is missing; deleting a published contract "
                                    "is a breaking change"])

    def test_no_contract_and_no_tags_is_a_note(self):
        git(self.provider.root, "tag", "-d", "api-v1.0.0")
        (self.provider.root / "openapi.yaml").unlink()
        self.assertEqual(self.provider.check(), ([], ["no contract at openapi.yaml; nothing to check"]))

    def test_versions_order_numerically_and_prereleases_are_ignored(self):
        for tag in ("api-v1.9.0", "api-v1.10.0", "api-v2.0.0-rc.1", "api-v01.0.0"):
            git(self.provider.root, "tag", tag)
        self.assertEqual([name for _, name in check_contract_version.published(self.provider.root)],
                         ["api-v1.0.0", "api-v1.9.0", "api-v1.10.0"])
        (self.provider.root / "openapi.yaml").write_text(contract("1.10.1", ("/shipments/{id}", "/x")),
                                                         encoding="utf-8")
        self.assertEqual(self.provider.check()[0], [])
        self.assertIn("api-v1.10.0", self.provider.check()[1][0])

    def test_a_missing_version_says_what_is_read(self):
        (self.provider.root / "openapi.yaml").write_text("openapi: 3.0.3\ninfo:\n  title: x\n", encoding="utf-8")
        self.assertEqual(self.provider.check()[0], ["info.version not found in openapi.yaml (only block-style YAML "
                                                    "or JSON is read)"])

    def test_a_missing_oasdiff_says_how_to_install_it(self):
        (self.provider.root / "openapi.yaml").write_text(contract("1.1.0", ("/shipments",)), encoding="utf-8")
        _, notes = check_contract_version.check(self.provider.root, "openapi.yaml", str(self.tmp / "none"))
        self.assertTrue(any("pinned oasdiff" in n and "--oasdiff" in n for n in notes))


class ConsumerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = Provider(Path(tmp.name))
        self.root = Path(tmp.name) / "web-portal"
        self.root.mkdir()
        self.folder = self.root / "contracts" / "shipments-api"

    def main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = check_contract_pin.main([*argv, "--root", str(self.root)])
        return code, out.getvalue() + err.getvalue()

    def vendor(self, tag="api-v1.0.0"):
        return self.main("--update", "shipments-api", tag, "--repository", str(self.provider.root),
                         "--path", "openapi.yaml")

    def test_no_contracts_is_clean(self):
        self.assertEqual(self.main(), (0, "check_contract_pin: no vendored contracts\n"))

    def test_update_writes_the_copy_and_its_source(self):
        code, out = self.vendor()
        self.assertEqual(code, 0, out)
        source = check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))
        self.assertEqual(source["tag"], "api-v1.0.0")
        self.assertEqual(source["commit"], git(self.provider.root, "rev-parse", "api-v1.0.0^{commit}"))
        self.assertEqual((self.folder / "openapi.yaml").read_text(encoding="utf-8"), contract("1.0.0"))
        self.assertEqual(self.main()[0], 0)
        self.assertEqual(self.main("--online")[0], 0)

    def test_an_edited_copy_is_a_problem(self):
        self.vendor()
        (self.folder / "openapi.yaml").write_text(contract("1.0.0", ("/shipments",)), encoding="utf-8")
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("contracts/shipments-api/openapi.yaml: differs from the copy SOURCE names (sha256)", out)

    def test_a_source_missing_a_field_is_a_problem(self):
        self.vendor()
        text = (self.folder / "SOURCE").read_text(encoding="utf-8")
        (self.folder / "SOURCE").write_text("\n".join(line for line in text.splitlines() if not line.startswith("commit:")),
                                            encoding="utf-8")
        self.assertIn("contracts/shipments-api/SOURCE: commit missing", self.main()[1])

    def test_a_copy_whose_version_is_not_the_tags_is_a_problem(self):
        self.vendor()
        text = contract("1.1.0")
        (self.folder / "openapi.yaml").write_text(text, encoding="utf-8")
        source = (self.folder / "SOURCE").read_text(encoding="utf-8")
        old = check_contract_pin.read_source(source)["sha256"]
        (self.folder / "SOURCE").write_text(source.replace(old, check_contract_pin.sha256(text.encode())),
                                            encoding="utf-8")
        self.assertIn("info.version is '1.1.0', but SOURCE pins api-v1.0.0", self.main()[1])

    def test_a_moved_tag_is_found_online(self):
        self.vendor()
        self.provider.commit(contract("1.0.0", ("/moved",)))
        git(self.provider.root, "tag", "-f", "api-v1.0.0")
        code, out = self.main("--online")
        self.assertEqual(code, 1)
        self.assertIn("a published version moved; ask the provider", out)

    def test_update_moves_the_pin_to_a_named_version(self):
        self.vendor()
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        git(self.provider.root, "tag", "api-v1.1.0")
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.1.0")[0], 0)
        self.assertEqual(check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))["tag"],
                         "api-v1.1.0")
        self.assertEqual(self.main("--online")[0], 0)

    def test_update_never_follows_latest(self):
        code, out = self.main("--update", "shipments-api", "latest", "--repository", str(self.provider.root),
                              "--path", "openapi.yaml")
        self.assertEqual(code, 2)
        self.assertIn("never latest", out)

    def test_an_unpublished_tag_cannot_be_fetched(self):
        code, out = self.vendor("api-v9.0.0")
        self.assertEqual(code, 1)
        self.assertIn("cannot fetch api-v9.0.0", out)


class ConsumerFailClosedTest(unittest.TestCase):
    """A check never passes silently: a missing, unreadable or malformed pin, or an unreachable provider, is a problem."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.provider = Provider(Path(tmp.name))
        self.root = Path(tmp.name) / "web-portal"
        self.root.mkdir()
        self.folder = self.root / "contracts" / "shipments-api"

    main = ConsumerTest.main
    vendor = ConsumerTest.vendor

    def source_edit(self, old: str, new: str):
        text = (self.folder / "SOURCE").read_text(encoding="utf-8")
        (self.folder / "SOURCE").write_text(text.replace(old, new), encoding="utf-8")

    def test_a_folder_without_a_source_is_a_problem(self):
        self.folder.mkdir(parents=True)
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("contracts/shipments-api: no SOURCE", out)

    def test_a_source_that_cannot_be_read_is_a_problem(self):
        self.folder.mkdir(parents=True)
        (self.folder / "SOURCE").write_bytes(b"\xff\xfe\x00 not utf-8")
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("contracts/shipments-api/SOURCE: cannot be read", out)

    def test_a_missing_copy_is_a_problem(self):
        self.vendor()
        (self.folder / "openapi.yaml").unlink()
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("no openapi.yaml beside SOURCE", out)

    def test_a_tag_that_is_not_strict_semver_is_a_problem(self):
        self.vendor()
        for bad in ("api-v01.0.0", "api-v1.0", "latest", "api-v1.0.0-rc1"):
            self.source_edit("api-v1.0.0", bad)
            code, out = self.main()
            self.assertEqual(code, 1, bad)
            self.assertIn("is not a published version", out)
            self.source_edit(bad, "api-v1.0.0")

    def test_an_abbreviated_commit_is_a_problem(self):
        self.vendor()
        commit = check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))["commit"]
        self.source_edit(commit, commit[:12])
        self.assertIn("commit must be the full 40-character commit", self.main()[1])

    def test_online_with_an_unreachable_provider_is_a_problem(self):
        self.vendor()
        repository = check_contract_pin.read_source((self.folder / "SOURCE").read_text(encoding="utf-8"))["repository"]
        self.source_edit(repository, str(self.root / "no-such-repository"))
        self.assertEqual(self.main()[0], 0)
        code, out = self.main("--online")
        self.assertEqual(code, 1)
        self.assertIn("cannot fetch api-v1.0.0", out)

    def test_online_when_the_tag_no_longer_has_the_path_is_a_problem(self):
        self.vendor()
        self.source_edit("openapi.yaml", "docs/openapi.yaml")
        code, out = self.main("--online")
        self.assertEqual(code, 1)

    def test_update_needs_a_repository_and_path_the_first_time(self):
        code, out = self.main("--update", "shipments-api", "api-v1.0.0")
        self.assertEqual(code, 2)
        self.assertIn("pass --repository and --path", out)

    def test_update_refuses_a_tag_that_is_not_strict_semver(self):
        for bad in ("api-v01.0.0", "api-v1.0", "api-v1.0.0\n"):
            code, out = self.main("--update", "shipments-api", bad, "--repository", str(self.provider.root),
                                  "--path", "openapi.yaml")
            self.assertEqual(code, 2, repr(bad))
        self.assertFalse(self.folder.exists())

    def test_update_refuses_a_provider_name_that_leaves_contracts(self):
        code, _ = self.main("--update", "../escape", "api-v1.0.0", "--repository", str(self.provider.root),
                            "--path", "openapi.yaml")
        self.assertEqual(code, 2)

    def test_update_refuses_a_copy_whose_version_is_not_the_tags(self):
        self.provider.commit(contract("2.0.0"))
        git(self.provider.root, "tag", "api-v1.5.0")
        code, out = self.main("--update", "shipments-api", "api-v1.5.0", "--repository", str(self.provider.root),
                              "--path", "openapi.yaml")
        self.assertEqual(code, 1)
        self.assertIn("info.version is '2.0.0', but the tag is api-v1.5.0", out)
        self.assertFalse(self.folder.exists())

    def test_update_refuses_a_path_with_no_file_name(self):
        code, _ = self.main("--update", "shipments-api", "api-v1.0.0", "--repository", str(self.provider.root),
                            "--path", "docs/")
        self.assertEqual(code, 2)


class ConsumerSecurityTest(unittest.TestCase):
    """The repository value is external input: it is never an option, a helper command or a transport git runs."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.provider = Provider(self.tmp)
        self.root = self.tmp / "web-portal"
        self.root.mkdir()
        self.folder = self.root / "contracts" / "shipments-api"
        self.marker = self.tmp / "pwned"

    main = ConsumerTest.main
    vendor = ConsumerTest.vendor

    def evil(self):
        return [f"--upload-pack=touch {self.marker};", f"--upload-pack=touch {self.marker}",
                f"ext::sh -c touch% {self.marker}", "-oProxyCommand=x", "git@-host:path", "ftp://host/x",
                "relative/path", "https://host/a b", "https://host/a\tb", "git@host:-x", "file:///tmp/x"]

    def test_update_refuses_an_unsafe_repository_and_runs_nothing(self):
        for repository in self.evil():
            code, out = self.main("--update", "shipments-api", "api-v1.0.0", f"--repository={repository}",
                                  "--path", "openapi.yaml")
            self.assertEqual(code, 2, repository)
            self.assertIn("repository", out)
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.folder.exists())

    def test_an_edited_source_with_an_unsafe_repository_is_refused_offline_and_online(self):
        ConsumerTest.vendor(self)
        source = (self.folder / "SOURCE").read_text(encoding="utf-8")
        good = check_contract_pin.read_source(source)["repository"]
        for repository in self.evil():
            (self.folder / "SOURCE").write_text(source.replace(good, repository), encoding="utf-8")
            for flag in ((), ("--online",)):
                code, out = self.main(*flag)
                self.assertEqual(code, 1, (repository, flag))
                self.assertIn("SOURCE: repository", out)
        self.assertFalse(self.marker.exists())

    def test_safe_repository_forms_are_accepted(self):
        for repository in (str(self.provider.root), "https://example.com/org/shipments-api.git",
                           "ssh://git@example.com/org/shipments-api.git", "git@example.com:org/shipments-api.git"):
            self.assertIsNone(check_contract_pin.repository_problem(repository), repository)

    def test_git_gets_a_locked_down_environment_and_the_separator(self):
        calls = []

        def fake(cmd, **kwargs):
            calls.append((cmd, kwargs))
            return subprocess.CompletedProcess(cmd, 1, "", "no")
        with mock.patch.object(check_contract_pin, "run_process", fake):
            check_contract_pin.fetch(str(self.provider.root), "api-v1.0.0", "openapi.yaml")
        self.assertTrue(calls)
        for cmd, kwargs in calls:
            self.assertEqual(kwargs["env"]["GIT_TERMINAL_PROMPT"], "0")
            self.assertEqual(kwargs["env"]["GIT_ALLOW_PROTOCOL"], "https:ssh:file")
            self.assertLessEqual(kwargs["timeout"], 120)
        fetch = next(cmd for cmd, _ in calls if "fetch" in cmd)
        self.assertEqual(fetch[fetch.index("--") + 1], str(self.provider.root))

    def test_one_deadline_covers_every_git_call_of_a_run(self):
        timeouts = []

        def fake(cmd, **kwargs):
            timeouts.append(kwargs["timeout"])
            return subprocess.CompletedProcess(cmd, 0, "", "")
        with mock.patch.object(check_contract_pin, "run_process", fake):
            result = check_contract_pin.fetch(str(self.provider.root), "api-v1.0.0", "openapi.yaml",
                                              deadline=time.monotonic() - 1)
        self.assertIsInstance(result, str)
        self.assertIn("timed out", result)
        self.assertEqual(timeouts, [])

    def test_a_failure_between_the_writes_leaves_the_previous_copy_and_source(self):
        ConsumerTest.vendor(self)
        before = {n: (self.folder / n).read_bytes() for n in ("openapi.yaml", "SOURCE")}
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        git(self.provider.root, "tag", "api-v1.1.0")
        real, count = os.replace, []

        def flaky(src, dst):
            count.append(dst)
            if len(count) == 2:
                raise OSError("disk full")
            return real(src, dst)
        with mock.patch.object(check_contract_pin.os, "replace", flaky):
            code, out = self.main("--update", "shipments-api", "api-v1.1.0")
        self.assertEqual(code, 1, out)
        self.assertEqual({n: (self.folder / n).read_bytes() for n in before}, before)
        self.assertEqual(sorted(p.name for p in self.folder.iterdir()), ["SOURCE", "openapi.yaml"])

    def test_a_duplicate_key_in_source_is_a_problem(self):
        ConsumerTest.vendor(self)
        with (self.folder / "SOURCE").open("a", encoding="utf-8") as handle:
            handle.write("tag:        api-v0.0.1\n")
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("SOURCE: tag appears twice", out)


class ConsumerHardeningTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.provider = Provider(self.tmp)
        self.root = self.tmp / "web-portal"
        self.root.mkdir()

    main = ConsumerTest.main

    def test_git_variables_that_redirect_the_repository_are_not_passed_on(self):
        victim = self.tmp / "victim"
        victim.mkdir()
        git(victim, "init", "-q")
        before = git(victim, "for-each-ref")
        env = {"GIT_DIR": str(victim / ".git"), "GIT_WORK_TREE": str(victim), "GIT_INDEX_FILE": "x",
               "GIT_OBJECT_DIRECTORY": str(victim / "o"), "GIT_ALTERNATE_OBJECT_DIRECTORIES": "y",
               "GIT_CONFIG_PARAMETERS": "'core.x=1'", "GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "a",
               "GIT_CONFIG_VALUE_0": "b", "GIT_SSH_COMMAND": "ssh -q"}
        with mock.patch.dict(os.environ, env):
            clean = check_contract_pin.git_env()
            result = check_contract_pin.fetch(str(self.provider.root), "api-v1.0.0", "openapi.yaml")
        self.assertIsInstance(result, tuple, result)
        self.assertEqual(git(victim, "for-each-ref"), before)
        self.assertFalse((victim / ".git" / "FETCH_HEAD").exists())
        self.assertEqual([k for k in clean if k in env], ["GIT_SSH_COMMAND"])

    def test_a_timeout_kills_the_whole_process_group(self):
        pidfile = self.tmp / "child.pid"
        script = f"sleep 300 & echo $! > {pidfile}; wait"
        with self.assertRaises(subprocess.TimeoutExpired):
            check_contract_pin.run_process(["sh", "-c", script], env=dict(os.environ), timeout=1, text=True)
        pid = int(pidfile.read_text())
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, 9)
            self.fail("the grandchild outlived the timeout")

    def test_a_path_named_source_is_refused_and_never_deleted(self):
        code, out = self.main("--update", "shipments-api", "api-v1.0.0", "--repository", str(self.provider.root),
                              "--path", "d/SOURCE")
        self.assertEqual(code, 2)
        self.assertIn("SOURCE", out)
        self.assertFalse((self.root / "contracts").exists())
        ConsumerTest.vendor(self)
        folder = self.root / "contracts" / "shipments-api"
        text = (folder / "SOURCE").read_text(encoding="utf-8")
        (folder / "SOURCE").write_text(text.replace("openapi.yaml", "d/SOURCE"), encoding="utf-8")
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.0.0")[0], 2)
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.0.0", "--path", "openapi.yaml")[0], 0)
        self.assertTrue((folder / "SOURCE").is_file())
        self.assertEqual(self.main("--online")[0], 0)


class OasdiffIsolationTest(unittest.TestCase):
    """The pull request's own config must not reach oasdiff: it could lower the severity of a breaking change."""

    def run_it(self):
        seen = {}

        def fake(cmd, **kwargs):
            seen["cmd"], seen["kwargs"] = cmd, kwargs
            seen["cwd_files"] = sorted(p.name for p in Path(kwargs["cwd"]).iterdir()) if kwargs.get("cwd") else None
            seen["config_text"] = Path(cmd[cmd.index("--config") + 1]).read_text() if "--config" in cmd else None
            return subprocess.CompletedProcess(cmd, 0, "", "")
        with tempfile.TemporaryDirectory() as caller, mock.patch.dict(os.environ, {"OASDIFF_CONFIG": "/evil.yaml"}):
            (Path(caller) / ".oasdiff.yaml").write_text("severity-levels: x\n")
            old = os.getcwd()
            os.chdir(caller)
            try:
                with mock.patch.object(check_contract_version.subprocess, "run", fake):
                    check_contract_version.run_oasdiff("oasdiff", "a", "b", ".yaml")
            finally:
                os.chdir(old)
            seen["caller"] = os.path.realpath(caller)
        return seen

    def test_oasdiff_gets_an_empty_config_and_a_private_cwd(self):
        seen = self.run_it()
        self.assertIn("--config", seen["cmd"])
        self.assertEqual(seen["config_text"], "")
        self.assertIsNotNone(seen["kwargs"].get("cwd"))
        self.assertNotEqual(os.path.realpath(seen["kwargs"]["cwd"]), seen["caller"])
        self.assertNotIn(".oasdiff.yaml", seen["cwd_files"])

    def test_oasdiff_does_not_inherit_the_config_variable(self):
        seen = self.run_it()
        self.assertNotIn("OASDIFF_CONFIG", seen["kwargs"]["env"])


class FinalReviewTest(unittest.TestCase):
    """The final review of Plan 21: a shallow clone with tags, more git variables, the copy's name in any case, a
    grandchild that leaves the process group, and credentials in a repository URL."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.provider = Provider(self.tmp)
        self.root = self.tmp / "web-portal"
        self.root.mkdir()
        self.folder = self.root / "contracts" / "shipments-api"

    main = ConsumerTest.main
    vendor = ConsumerTest.vendor

    def test_a_shallow_clone_with_some_tags_is_a_problem(self):
        self.provider.commit(contract("1.1.0", ("/shipments/{id}", "/shipments")))
        clone = self.tmp / "clone"
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{self.provider.root}", str(clone)],
                       check=True, capture_output=True)
        git(clone, "tag", "api-v0.1.0")
        self.assertTrue(check_contract_version.published(clone))
        problems, _ = check_contract_version.check(clone, "openapi.yaml", str(self.provider.oasdiff))
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("fetch-depth: 0", problems[0])
        tag, problems = check_contract_version.publish_tag(clone, "openapi.yaml")
        self.assertIsNone(tag)
        self.assertIn("fetch-depth: 0", problems[0])

    def test_the_common_dir_and_namespace_variables_are_not_passed_on(self):
        env = {"GIT_COMMON_DIR": str(self.tmp / "elsewhere"), "GIT_NAMESPACE": "other"}
        with mock.patch.dict(os.environ, env):
            clean = check_contract_pin.git_env()
            result = check_contract_pin.fetch(str(self.provider.root), "api-v1.0.0", "openapi.yaml")
        self.assertEqual([key for key in env if key in clean], [])
        self.assertIsInstance(result, tuple, result)

    def test_a_copy_named_source_in_any_case_is_refused_and_never_deleted(self):
        for path in ("d/source", "d/Source"):
            code, out = self.main("--update", "shipments-api", "api-v1.0.0", "--repository",
                                  str(self.provider.root), "--path", path)
            self.assertEqual(code, 2, (path, out))
        self.assertFalse((self.root / "contracts").exists())
        self.vendor()
        text = (self.folder / "SOURCE").read_text(encoding="utf-8")
        (self.folder / "SOURCE").write_text(text.replace("openapi.yaml", "d/source"), encoding="utf-8")
        code, out = self.main()
        self.assertEqual(code, 1)
        self.assertIn("names SOURCE itself", out)
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.0.0")[0], 2)
        keep = self.folder / "source"
        keep.write_text("not a contract\n", encoding="utf-8")
        self.assertEqual(self.main("--update", "shipments-api", "api-v1.0.0", "--path", "openapi.yaml")[0], 0)
        self.assertTrue(keep.is_file())
        self.assertTrue((self.folder / "SOURCE").is_file())

    @unittest.skipUnless(shutil.which("setsid"), "needs setsid")
    def test_a_grandchild_that_leaves_the_group_cannot_hold_the_call(self):
        pidfile = self.tmp / "child.pid"
        script = f"setsid sleep 20 & echo $! > {pidfile}; wait"
        started = time.monotonic()
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                check_contract_pin.run_process(["sh", "-c", script], env=dict(os.environ), timeout=1, text=True)
            self.assertLess(time.monotonic() - started, 10)
        finally:
            try:
                os.kill(int(pidfile.read_text()), 9)
            except (OSError, ValueError):
                pass

    def test_a_repository_with_credentials_is_refused(self):
        for repository in ("https://user:s3cr3t@example.com/org/shipments-api.git",
                           "https://ghp_s3cr3t@example.com/org/shipments-api.git",
                           "ssh://git:s3cr3t@example.com/org/shipments-api.git"):
            problem = check_contract_pin.repository_problem(repository)
            self.assertIsNotNone(problem, repository)
            self.assertNotIn("s3cr3t", problem)
            code, out = self.main("--update", "shipments-api", "api-v1.0.0", f"--repository={repository}",
                                  "--path", "openapi.yaml")
            self.assertEqual(code, 2, repository)
        self.assertFalse(self.folder.exists())
        for repository in ("ssh://git@example.com/org/shipments-api.git", "ssh://git@example.com:2222/org/x.git",
                           "git@example.com:org/shipments-api.git", "https://example.com/org/shipments-api.git"):
            self.assertIsNone(check_contract_pin.repository_problem(repository), repository)

    def test_a_malformed_repository_with_credentials_never_echoes_them(self):
        for repository in ("https://user:s3cr3t@example.com/org/x?y", "https://user:s3cr3t@example.com/org/x y",
                           "-https://ghp_s3cr3t@example.com/org/x"):
            problem = check_contract_pin.repository_problem(repository)
            self.assertIsNotNone(problem, repository)
            self.assertNotIn("s3cr3t", problem, repository)


if __name__ == "__main__":
    unittest.main()
