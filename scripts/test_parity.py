"""Tests for plugins/aidlc-modernize/skills/modernize-parity/scripts/parity.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins" / "aidlc-modernize" / "skills"
                       / "modernize-parity" / "scripts"))
import parity  # noqa: E402

PY = sys.executable


class ParityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        (self.inputs / "a.csv").write_text("x,1\n")
        (self.inputs / "b.csv").write_text("y,2\n")

    def tearDown(self):
        self.tmp.cleanup()

    def program(self, name: str, body: str) -> str:
        path = self.root / f"{name}.py"
        path.write_text("import sys\ndata = open(sys.argv[1]).read()\n" + body)
        return f"{PY} {path} {{input}}"

    def verdicts(self, old, new, ignore=()):
        return {name: verdict for name, verdict, _ in parity.compare(old, new, self.inputs, list(ignore))}

    def test_same_output_is_same(self):
        prog = self.program("p", "print(data.upper())\n")
        self.assertEqual(self.verdicts(prog, prog), {"a.csv": "SAME", "b.csv": "SAME"})

    def test_a_different_output_is_different(self):
        old = self.program("old", "print(data.upper())\n")
        new = self.program("new", "print(data)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"DIFFERENT"})

    def test_a_different_exit_code_is_different(self):
        old = self.program("old", "print(data)\n")
        new = self.program("new", "print(data)\nsys.exit(3)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"DIFFERENT"})

    def test_crlf_from_windows_against_lf_is_same(self):
        old = self.program("old", "sys.stdout.buffer.write(data.replace('\\n', '\\r\\n').encode())\n")
        new = self.program("new", "sys.stdout.write(data)\n")
        self.assertEqual(set(self.verdicts(old, new).values()), {"SAME"})

    def test_run_to_run_noise_is_reported_not_hidden(self):
        old = self.program("old", "import time\nprint(data, time.time_ns())\n")
        self.assertEqual(set(self.verdicts(old, old).values()), {"NOISY"})

    def test_an_ignore_pattern_removes_noise(self):
        old = self.program("old", "import time\nprint(data, time.time_ns())\n")
        self.assertEqual(set(self.verdicts(old, old, ignore=[r"\d{10,}"]).values()), {"SAME"})

    def test_output_that_is_not_utf8_is_compared_as_bytes(self):
        cp437 = self.program("cp437", "sys.stdout.buffer.write(b'Zo\\x89-1,3.52\\r\\n')\n")
        same = self.program("same", "sys.stdout.buffer.write(b'Zo\\x89-1,3.52\\n')\n")
        other = self.program("other", "sys.stdout.buffer.write(b'Zo\\x8a-1,3.52\\n')\n")
        self.assertEqual(set(self.verdicts(cp437, same).values()), {"SAME"})
        self.assertEqual(set(self.verdicts(cp437, other).values()), {"DIFFERENT"})

    def test_two_broken_commands_are_not_parity(self):
        broken = "/nonexistent/program {input}"
        self.assertEqual(set(self.verdicts(broken, broken).values()), {"BROKEN"})
        code = parity.main(["parity.py", "--old", broken, "--new", broken, "--inputs", str(self.inputs),
                            "--out", str(self.root / "r.md")])
        self.assertEqual(code, 1)

    def test_a_failure_with_output_is_still_compared(self):
        prog = self.program("p", "print(data)\nsys.exit(4)\n")
        self.assertEqual(set(self.verdicts(prog, prog).values()), {"SAME"})

    def test_no_input_files_exit_2(self):
        empty = self.root / "empty"
        empty.mkdir()
        prog = self.program("p", "print(data)\n")
        code = parity.main(["parity.py", "--old", prog, "--new", prog, "--inputs", str(empty),
                            "--out", str(self.root / "r.md")])
        self.assertEqual(code, 2)

    def test_the_report_lists_every_input(self):
        prog = self.program("p", "print(data)\n")
        out = self.root / "report.md"
        code = parity.main(["parity.py", "--old", prog, "--new", prog, "--inputs", str(self.inputs),
                            "--out", str(out)])
        self.assertEqual(code, 0)
        text = out.read_text()
        self.assertIn("a.csv", text)
        self.assertIn("b.csv", text)


if __name__ == "__main__":
    unittest.main()
