"""The behaviour suite's structure, checked for free: every case loads, scaffolds safely and is tagged."""
import os
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "plugins" / "aidlc" / "evals"
TYPES = {"regex", "tool_used", "tool_order", "file_exists", "llm", "baseline"}
TAGS = {"gate", "routing", "route", "language"}
GATES = {"gate-spec-approval", "gate-assertion-change", "gate-amended-assertion", "gate-scope", "gate-dependency",
         "gate-injected-ticket", "gate-ai-review-approval", "gate-release-stop-criteria", "gate-defect-no-repro",
         "gate-payments-quick-fix"}


def cases() -> list[Path]:
    return sorted(p.parent for p in EVALS.glob("*/prompt.md"))


def front(text: str) -> str:
    return text.split("---", 2)[1] if text.startswith("---") else ""


class EvalsTest(unittest.TestCase):
    def test_every_case_has_a_known_tag_and_a_grader(self):
        self.assertTrue(cases())
        for case in cases():
            fm = front((case / "prompt.md").read_text(encoding="utf-8"))
            tags = set(re.findall(r"[a-z]+", (re.search(r"tags:\s*\[([^\]]*)\]", fm) or [None, ""])[1]))
            self.assertTrue(tags & TAGS, case.name)
            graders = list((case / "graders").glob("*.md"))
            self.assertTrue(graders, case.name)
            for g in graders:
                kind = re.search(r"(?m)^type:\s*(\S+)", front(g.read_text(encoding="utf-8")))
                self.assertIn(kind and kind.group(1), TYPES, f"{case.name}/{g.name}")

    def test_every_scaffold_script_is_executable_and_strict(self):
        for case in cases():
            yaml = case / "case.yaml"
            if not yaml.is_file():
                continue
            name = re.search(r"scaffold_script:\s*(\S+)", yaml.read_text(encoding="utf-8")).group(1)
            script = case / name
            self.assertTrue(script.is_file(), case.name)
            text = script.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("#!/usr/bin/env bash\nset -euo pipefail"), case.name)
            self.assertIn("user.email=eval@example.com", text, case.name)
            self.assertTrue(script.stat().st_mode & 0o111, case.name)

    def test_the_fixtures_build_a_green_repository(self):
        result = subprocess.run(["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                                cwd=EVALS / "fixtures" / "shipments", capture_output=True, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_results_are_ignored(self):
        self.assertIn("plugins/aidlc/evals/results/", (ROOT / ".gitignore").read_text(encoding="utf-8"))

    def test_every_gate_has_a_case(self):
        names = {c.name for c in cases()}
        self.assertEqual(GATES - names, set())

    def test_build_cases_confirm_in_advance(self):
        for case in cases():
            body = (case / "prompt.md").read_text(encoding="utf-8")
            if "/aidlc:aidlc-build" in body:
                self.assertIn("I confirm your restatement and the steps in advance", body, case.name)


if __name__ == "__main__":
    unittest.main()
