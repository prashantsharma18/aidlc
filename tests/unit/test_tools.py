import hashlib
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc import tools
from aidlc.policy import load_policy, validate_all
from tests.helpers import run_cli


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def opener_for(data: bytes):
    calls = []

    def opener(url, timeout):
        calls.append(url)
        return Resp(data)
    opener.calls = calls
    return opener


def tarball(member: str, payload: bytes) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo(member)
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def register(kind: str, data: bytes, url="https://example.invalid/tool", member=None, sha=None):
    art = {"platform": tools.platform_tag(), "kind": kind, "url": url,
           "sha256": sha or hashlib.sha256(data).hexdigest()}
    if member:
        art["member"] = member
    return {"tools": [{"id": "demo", "version": "1.0.0", "artifacts": [art]}]}


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp())

    def test_binary_is_verified_and_installed_executable(self):
        data = b"#!/bin/sh\necho demo\n"
        path = tools.install("demo", self.dest, register("binary", data), opener_for(data))
        self.assertEqual((path.read_bytes(), os.access(path, os.X_OK)), (data, True))

    def test_tar_member_is_extracted(self):
        data = tarball("demo", b"payload")
        path = tools.install("demo", self.dest, register("tar.gz", data, member="demo"), opener_for(data))
        self.assertEqual(path.read_bytes(), b"payload")

    def test_checksum_mismatch_installs_nothing(self):
        data = b"tampered"
        reg = register("binary", data, sha="0" * 64)
        with self.assertRaisesRegex(tools.ToolError, "checksum mismatch"):
            tools.install("demo", self.dest, reg, opener_for(data))
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_non_https_refused(self):
        data = b"x"
        with self.assertRaisesRegex(tools.ToolError, "non-https"):
            tools.install("demo", self.dest, register("binary", data, url="http://example.invalid/t"),
                          opener_for(data))

    def test_missing_or_non_regular_member_refused(self):
        data = tarball("other", b"x")
        with self.assertRaisesRegex(tools.ToolError, "no member 'demo'"):
            tools.install("demo", self.dest, register("tar.gz", data, member="demo"), opener_for(data))

    def test_unknown_tool_and_platform(self):
        with self.assertRaisesRegex(tools.ToolError, "not in core/policy/tool-register.yaml"):
            tools.artifact("nope", {"tools": []})
        reg = register("binary", b"x")  # built for the real platform, before the patch
        with mock.patch.object(tools, "platform_tag", return_value="plan9-mips"):
            with self.assertRaisesRegex(tools.ToolError, "no pinned artifact for plan9-mips"):
                tools.artifact("demo", reg)

    def test_which_prefers_the_pinned_directory(self):
        pinned = self.dest / "demo"
        pinned.write_text("#!/bin/sh\n")
        pinned.chmod(0o755)
        with mock.patch.dict(os.environ, {tools.TOOLS_DIR_ENV: str(self.dest)}):
            self.assertEqual(tools.which_tool("demo"), pinned)

    def test_pinned_only_never_falls_back_to_path(self):
        with mock.patch.dict(os.environ, {tools.TOOLS_DIR_ENV: str(self.dest)}), \
                mock.patch("shutil.which", return_value="/usr/bin/demo"):
            self.assertEqual(tools.which_tool("demo"), Path("/usr/bin/demo"))
            self.assertIsNone(tools.which_tool("demo", pinned_only=True))


class RegisterTest(unittest.TestCase):
    def test_register_pins_opa_and_conftest(self):
        self.assertEqual(validate_all(), [])
        reg = {t["id"]: t for t in load_policy("tool-register")["tools"]}
        self.assertEqual(reg["opa"]["version"], "1.21.2")
        self.assertEqual(reg["opa"]["artifacts"][0]["sha256"],
                         "830ab11f61ffec760b5e19db0d7ad02bf037e13f5ef4d665faeaf17632177527")
        self.assertEqual(reg["conftest"]["version"], "0.71.1")
        art = reg["conftest"]["artifacts"][0]
        self.assertEqual((art["kind"], art["member"], art["sha256"]),
                         ("tar.gz", "conftest", "c3f6b2a753bd56e377a1e51a95ae3e057f926f2e9139f7d5b5dfbbaf810f7985"))
        self.assertIn("binaries", load_policy("dependency-policy")["rules"])

    def test_status_command(self):
        with mock.patch.dict(os.environ, {tools.TOOLS_DIR_ENV: tempfile.mkdtemp()}):
            code, out, _ = run_cli("tools", "status")
        self.assertEqual(code, 0)
        self.assertIn("opa", out)
        self.assertIn("conftest", out)


class HardeningTest(unittest.TestCase):
    def setUp(self):
        self.dest = Path(tempfile.mkdtemp())

    def _tar_with(self, info: tarfile.TarInfo, payload: bytes = b"") -> bytes:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            tar.addfile(info, io.BytesIO(payload) if payload else None)
        return buf.getvalue()

    def test_symlink_member_refused(self):
        info = tarfile.TarInfo("demo")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        data = self._tar_with(info)
        with self.assertRaisesRegex(tools.ToolError, "not a regular file"):
            tools.install("demo", self.dest, register("tar.gz", data, member="demo"), opener_for(data))
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_unsafe_member_name_refused(self):
        data = tarball("../demo", b"x")
        with self.assertRaisesRegex(tools.ToolError, "unsafe member"):
            tools.install("demo", self.dest, register("tar.gz", data, member="../demo"), opener_for(data))

    def test_size_cap(self):
        data = b"x" * 100
        with mock.patch.object(tools, "MAX_DOWNLOAD", 10):
            with self.assertRaisesRegex(tools.ToolError, "larger than"):
                tools.install("demo", self.dest, register("binary", data), opener_for(data))
        self.assertEqual(list(self.dest.iterdir()), [])

    def test_redirect_to_non_https_refused(self):
        class Redirected(Resp):
            def geturl(self):
                return "http://example.invalid/evil"
        data = b"x"
        with self.assertRaisesRegex(tools.ToolError, "non-https"):
            tools.install("demo", self.dest, register("binary", data), lambda url, timeout: Redirected(data))

    def test_symlinked_tools_dir_refused(self):
        real = Path(tempfile.mkdtemp())
        link = self.dest / "link"
        link.symlink_to(real)
        data = b"x"
        with self.assertRaisesRegex(tools.ToolError, "symlink"):
            tools.install("demo", link, register("binary", data), opener_for(data))
        self.assertEqual(list(real.iterdir()), [])

    def test_symlinked_destination_refused(self):
        victim = self.dest / "victim"
        victim.write_text("keep")
        (self.dest / "demo").symlink_to(victim)
        data = b"x"
        with self.assertRaisesRegex(tools.ToolError, "symlink"):
            tools.install("demo", self.dest, register("binary", data), opener_for(data))
        self.assertEqual(victim.read_text(), "keep")

    def test_default_dir_follows_home_dir(self):
        env = {k: v for k, v in os.environ.items() if k != tools.TOOLS_DIR_ENV}
        env["AIDLC_HOME_DIR"] = "/tmp/h"
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(tools.tools_dir(), Path("/tmp/h/bin"))

