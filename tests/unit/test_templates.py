import tempfile
import unittest
from pathlib import Path

from aidlc.templates import (TemplateError, list_templates, load_template,
                             parse_front_matter, render, write_new)
from tests.helpers import run_cli

EXPECTED_IDS = {
    "intent", "spec", "evidence-pack", "design-note", "decision-frame", "adr", "plan",
    "task-bundle", "progress-note", "pr-description", "evidence-table", "review-record",
    "security-review", "readiness", "change-record", "release-runbook", "runbook",
    "incident", "coordination-plan", "compat-matrix", "workspace", "working-agreement",
    "agents-md", "codebase-map", "explorer-brief",
}


class TemplatesTest(unittest.TestCase):
    def test_all_expected_templates_exist_and_load(self):
        self.assertEqual({t.id for t in list_templates()}, EXPECTED_IDS)

    def test_every_template_names_guide_sections(self):
        for t in list_templates():
            self.assertTrue(t.guide, t.id)

    def test_render_fills_declared_fields(self):
        t = load_template("intent")
        text = render(t, {"KEY": "SHIP-1", "TITLE": "Show delivery window"})
        self.assertIn("SHIP-1", text)
        self.assertNotIn("{{", text)
        self.assertTrue(text.startswith("<!-- aidlc template: intent -->"))

    def test_render_missing_field_errors(self):
        with self.assertRaises(TemplateError):
            render(load_template("intent"), {"KEY": "SHIP-1"})

    def test_write_new_refuses_to_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "intent.md"
            out.write_text("mine\n", encoding="utf-8")
            with self.assertRaises(TemplateError):
                write_new(load_template("intent"), {"KEY": "A-1", "TITLE": "t"}, out)
            self.assertEqual(out.read_text(encoding="utf-8"), "mine\n")

    def test_front_matter_accepts_crlf_and_bom(self):
        meta, body = parse_front_matter("﻿---\r\nid: x\r\n---\r\nbody\r\n", Path("x.md"))
        self.assertEqual(meta, {"id": "x"})
        self.assertEqual(body, "body\n")

    def test_missing_front_matter_errors(self):
        with self.assertRaises(TemplateError):
            parse_front_matter("no front matter\n", Path("x.md"))

    def test_cli_list_and_new(self):
        code, out, _ = run_cli("new", "--list")
        self.assertEqual(code, 0)
        self.assertIn("spec", out)
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "spec.md"
            code, _, err = run_cli("new", "spec", "--out", str(target),
                                   "--set", "KEY=SHIP-1", "--set", "TITLE=Window",
                                   "--set", "OWNER=PO", "--set", "TIER=2")
            self.assertEqual(code, 0, err)
            self.assertIn("SHIP-1", target.read_text(encoding="utf-8"))
