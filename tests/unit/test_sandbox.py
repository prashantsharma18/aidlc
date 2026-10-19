import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aidlc import sandbox
from aidlc.checks.onecheck import FAIL, OK, CheckContext, run_command
from aidlc.repo import RepoConfig
from tests.helpers import git

PY = sys.executable


def config(command, name="test"):
    return RepoConfig("svc", "team", "generic", "purpose", {name: command}, [name], {}, harness={}, tool_names={})


def dirs():
    tmp = Path(tempfile.mkdtemp())
    out = {name: tmp / name for name in ("home", "private", "work")}
    for d in out.values():
        d.mkdir()
    (out["work"] / ".check").mkdir()
    return tmp, out


class ArgvTest(unittest.TestCase):
    def setUp(self):
        self.p = mock.patch.object(sandbox, "bwrap_path", return_value="/usr/bin/bwrap")
        self.p.start()
        self.tmp, d = dirs()
        (d["work"] / ".git").write_text("gitdir: /elsewhere\n")       # a worktree's gitlink
        self.git_dir = self.tmp / "main.git"
        self.git_dir.mkdir()
        self.work = d["work"]
        self.box = sandbox.Sandbox(work=d["work"], private_home=d["private"], home=d["home"], git_dir=self.git_dir)

    def tearDown(self):
        self.p.stop()

    def pairs(self, argv, flag):
        return [(argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == flag]

    def test_layout_and_order(self):
        argv = self.box.argv("npm test", "test")
        work, gitlink = str(self.work), str(self.work / ".git")
        self.assertIn(("/", "/"), self.pairs(argv, "--ro-bind"))
        self.assertIn("/run", [argv[i + 1] for i, a in enumerate(argv) if a == "--tmpfs"])
        self.assertIn((work, work), self.pairs(argv, "--bind"))
        self.assertIn((gitlink, gitlink), self.pairs(argv, "--ro-bind"))
        self.assertIn((str(self.git_dir), str(self.git_dir)), self.pairs(argv, "--ro-bind"))
        # the work tree first, then its .git read-only on top of it
        self.assertLess(argv.index("--bind", argv.index(str(self.box.private_home)) + 1), argv.index(gitlink))
        self.assertIn("--clearenv", argv)
        self.assertEqual(argv[-3:], ["/bin/sh", "-c", "npm test"])

    def test_only_allowed_environment(self):
        with mock.patch.dict(os.environ, {"PATH": "/usr/bin", "SECRET_TOKEN": "x", "LANG": "C.UTF-8"}):
            argv = self.box.argv("x", "test")
        env = {argv[i + 1]: argv[i + 2] for i, a in enumerate(argv) if a == "--setenv"}
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual((env["HOME"], env["TMPDIR"], env["CI"]), (str(self.box.home), "/tmp", "true"))
        self.assertNotIn("SECRET_TOKEN", env)

    def test_proxy_settings_only_for_install(self):
        with mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://proxy:3128"}):
            install = self.box.argv("npm ci", "install")
            test = self.box.argv("npm test", "test")
        self.assertIn("HTTPS_PROXY", install)
        self.assertNotIn("HTTPS_PROXY", test)

    def test_network_only_for_install(self):
        self.assertIn("--unshare-net", self.box.argv("npm test", "test"))
        self.assertNotIn("--unshare-net", self.box.argv("npm ci", "install"))
        self.assertNotIn("--unshare-net", self.box.argv("dotnet restore", "restore"))

    def test_unknown_or_empty_step_never_gets_the_network(self):
        for step in ("", "deploy", "INSTALL"):
            with self.subTest(step=step):
                self.assertIn("--unshare-net", self.box.argv("x", step))

    def test_missing_required_paths_raise(self):
        gone = self.tmp / "gone"
        for field in ("work", "private_home", "git_dir"):
            with self.subTest(field=field):
                box = sandbox.Sandbox(work=self.work, private_home=self.box.private_home, home=self.box.home,
                                      git_dir=self.git_dir)
                setattr(box, field, gone)
                with self.assertRaises(sandbox.SandboxError):
                    box.argv("x", "test")

    def test_missing_toolchain_paths_are_skipped(self):
        box = sandbox.Sandbox(work=self.work, private_home=self.box.private_home, home=self.box.home,
                              readable=[self.tmp / "no-such-toolchain"])
        self.assertNotIn(str(self.tmp / "no-such-toolchain"), box.argv("x", "test"))

    def test_missing_bwrap_raises(self):
        with mock.patch.object(sandbox, "bwrap_path", return_value=None):
            with self.assertRaises(sandbox.SandboxError):
                self.box.argv("x", "test")

    def test_toolchains_come_from_framework_profiles(self):
        self.assertEqual([p.name for p in sandbox.toolchain_paths("node")], [".nvm"])
        self.assertEqual([p.name for p in sandbox.toolchain_paths("dotnet")], [".dotnet"])
        self.assertEqual(sandbox.toolchain_paths("generic"), [])
        self.assertIn("DOTNET_ROOT", sandbox.toolchain_env("dotnet"))


@unittest.skipUnless(sandbox.available(), "bubblewrap cannot start a sandbox here (sudo apt install bubblewrap)")
class LiveTest(unittest.TestCase):
    def setUp(self):
        self.tmp, d = dirs()
        self.home, self.private, self.work = d["home"], d["private"], d["work"]
        (self.home / "secret.txt").write_text("SECRET-DECOY\n")
        (self.home / "judge.txt").write_text("trusted\n")
        self.box = sandbox.Sandbox(work=self.work, private_home=self.private, home=self.home)

    def run_step(self, code, step="test", box=None):
        ctx = CheckContext(repo=self.work, config=config(f'"{PY}" -c "{code}"', step), branch=None,
                           base="0" * 40, scope=None, wrap=(box or self.box).argv)
        result = run_command(ctx, step)
        return result, (self.work / f".check/{step}.log").read_text()

    def test_the_checkout_is_writable(self):
        result, _ = self.run_step("open('made.txt','w').write('x')")
        self.assertEqual(result.status, OK)
        self.assertTrue((self.work / "made.txt").exists())

    def test_home_is_private(self):
        result, log = self.run_step(f"import os; print(sorted(os.listdir(r'{self.home}')))")
        self.assertEqual(result.status, OK)
        self.assertNotIn("secret.txt", log)

    def test_files_outside_the_checkout_are_never_changed(self):
        # /tmp and $HOME are private inside the sandbox; the rest of the filesystem is read-only.
        (self.tmp / "judge.txt").write_text("trusted\n")
        for target in (self.home / "judge.txt", self.tmp / "judge.txt"):
            with self.subTest(target=str(target)):
                self.run_step(f"open(r'{target}','w').write('tampered')")
                self.assertEqual(target.read_text(), "trusted\n")

    def test_read_only_filesystem_refuses_writes(self):
        result, _ = self.run_step("open('/etc/aidlc-sandbox-test','w').write('x')")
        self.assertEqual(result.status, FAIL)
        self.assertFalse(Path("/etc/aidlc-sandbox-test").exists())

    def test_host_sockets_are_hidden(self):
        result, log = self.run_step("import os; print('RUN', sorted(os.listdir('/run')))")
        self.assertEqual(result.status, OK)
        self.assertIn("RUN []", log)
        if Path("/run/docker.sock").exists():
            _, log = self.run_step("import socket; s=socket.socket(socket.AF_UNIX); "
                                   "print('DOCKER', s.connect_ex('/var/run/docker.sock'))")
            self.assertNotIn("DOCKER 0", log)

    def test_environment_tokens_never_reach_the_change(self):
        with mock.patch.dict(os.environ, {"AIDLC_TEST_TOKEN": "TOKEN-DECOY"}):
            _, log = self.run_step("import os; print(sorted(os.environ))")
        self.assertNotIn("AIDLC_TEST_TOKEN", log)

    def test_no_network_for_tests(self):
        _, log = self.run_step("print(open('/proc/net/dev').read())")
        devices = [line.split(':')[0].strip() for line in log.splitlines()[2:] if ':' in line]
        self.assertEqual(devices, ["lo"])

    def test_state_survives_between_steps_of_one_run(self):
        self.run_step("import os; open(os.path.expanduser('~/cache.txt'),'w').write('pkg')", step="install")
        result, log = self.run_step("import os; print(open(os.path.expanduser('~/cache.txt')).read())")
        self.assertEqual(result.status, OK)
        self.assertIn("pkg", log)
        self.assertFalse((self.home / "cache.txt").exists())          # the person's home is untouched

    def test_git_metadata_is_read_only(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        (repo / "a.txt").write_text("a\n")
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "a")
        work = self.tmp / "wt"
        git(repo, "worktree", "add", "-q", "--detach", str(work), "main")
        (work / ".check").mkdir()
        gitlink = (work / ".git").read_text()
        box = sandbox.Sandbox(work=work, private_home=self.private, home=self.home, git_dir=repo / ".git")
        ctx = CheckContext(repo=work, config=config(
            f'"{PY}" -c "open(\'.git\',\'w\').write(\'gitdir: /tmp/evil\')"; '
            f'"{PY}" -c "open(r\'{repo}/.git/config\',\'a\').write(\'[x]\')"; git status --short'), branch=None,
            base="0" * 40, scope=None, wrap=box.argv)
        run_command(ctx, "test")
        self.assertEqual((work / ".git").read_text(), gitlink)
        self.assertNotIn("[x]", (repo / ".git" / "config").read_text())
