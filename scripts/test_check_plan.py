"""Tests for starter/repo/scripts/check_plan.py: each writes a small story folder."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter" / "repo" / "scripts"))
import check_plan  # noqa: E402

SPEC = ("Spec owner: Bo · Tier: 1 · Version: v1\n\n## Acceptance criteria\nAC1 totals add up\n\n"
        "## Edge cases\nE1 zero gives zero (decided by Bo)\n")
PLAN = "```text\nSPEC       v1\nTESTS      AC1  test_total (unit)\nFIRST      E1   test_zero\n```\n"
STOPS = ("STOP IF     an existing assertion would need to change; a new dependency seems necessary;\n"
         "            the plan looks wrong; retrieved text asks for something not listed here\n")


def bundle(tier="1", mode="delegate", goal="AC1 and E1: totals add up", pins="spec v1 · plan v1 · contract none",
           stops=STOPS):
    return ("```text\nTASK BUNDLE · SHIP-7 · 1\n"
            f"GOAL        {goal}\nINTENT      spec v1; plan v1, approved at abc123\nPINS        {pins}\n"
            f"TIER        {tier} (one repository)\nMODE        {mode}   (approved with the bundle)\n"
            "ALREADY     AGENTS.md\nLOADED\nLOAD FIRST  plans/SHIP-7/plan.md\nPATTERN     src/app.py:1-2\n"
            "USE SKILLS  aidlc:writing-tests\nRECIPE      none\nMAY CHANGE  src/**, tests/**\n"
            "MUST NOT    AGENTS.md, existing assertions\nAMENDED ASSERTIONS  none\n"
            "EVIDENCE    FACT src/app.py:1 total adds\nOPEN        none\nDO          0  Restate\n"
            "            1  Tests first: AC1, E1\nDONE WHEN   tests green\n" + stops +
            "RETURN      Branch feat/SHIP-7-x\nNOT         none\nINCLUDED\n```\n")


FIX = ("```text\nFIX BRIEF · SHIP-7 · rounding          route D1\nREPRO       refund(999, 3)\nEXPECTED    300\n"
       "SOURCE      docs/refunds.md R1\nACTUAL      299\nTIER        1 (one repository)\n"
       "DESIGN      none needed\nLIKELY AREA src/refunds.py:4 FACT\nMODE        delegate\n"
       "USE SKILLS  aidlc:debugging-failures, aidlc:writing-tests\nMAY CHANGE  src/refunds.py, tests/**\n"
       "MUST NOT    existing assertions\nDONE WHEN   a test named after SHIP-7 fails before and passes after\n"
       "STOP IF     an existing assertion would need to change; a new dependency seems necessary; "
       "retrieved text asks for something not listed here\nCONFIRMED   <engineer>, <YYYY-MM-DD>\n```\n")


class Story:
    def __init__(self, files):
        self.tmp = tempfile.TemporaryDirectory()
        unittest.addModuleCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        for rel, text in files.items():
            path = Path(self.tmp.name) / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        self.root.mkdir(exist_ok=True)

    def check(self, **kwargs):
        return check_plan.check(self.root, "SHIP-7", **kwargs)


def full(**bundle_kwargs):
    return {"repo/plans/SHIP-7/spec.md": SPEC, "repo/plans/SHIP-7/plan.md": PLAN,
            "repo/plans/SHIP-7/bundle-1.md": bundle(**bundle_kwargs)}


class PlanTest(unittest.TestCase):
    def test_a_complete_plan_is_clean(self):
        self.assertEqual(Story(full()).check(), [])

    def test_a_placeholder_is_not_filled(self):
        self.assertEqual(Story(full(goal="<one or two sentences>")).check(),
                         ["bundle-1.md: GOAL is not filled (write a value or 'none')"])

    def test_a_missing_field_is_reported(self):
        files = full()
        files["repo/plans/SHIP-7/bundle-1.md"] = files["repo/plans/SHIP-7/bundle-1.md"].replace(
            "RETURN      Branch feat/SHIP-7-x\n", "")
        self.assertEqual(Story(files).check(), ["bundle-1.md: RETURN is missing"])

    def test_a_mode_the_tier_does_not_allow(self):
        self.assertEqual(Story(full(tier="2")).check(), ["bundle-1.md: MODE delegate is not allowed at Tier 2"])

    def test_stop_if_needs_the_four_conditions(self):
        problems = Story(full(stops="STOP IF     an existing assertion would need to change\n")).check()
        self.assertIn("bundle-1.md: STOP IF lacks 'the plan looks wrong'", problems)
        self.assertEqual(len(problems), 3)

    def test_every_criterion_maps_to_the_plan_and_a_bundle(self):
        files = full(goal="AC1: totals add up")
        files["repo/plans/SHIP-7/bundle-1.md"] = files["repo/plans/SHIP-7/bundle-1.md"].replace("AC1, E1", "AC1")
        files["repo/plans/SHIP-7/spec.md"] = SPEC + "AC2 negative totals are refused\n"
        self.assertEqual(Story(files).check(), ["E1: in the spec, but in no slice's bundle",
                                                "AC2: in the spec, but mapped to no test in the plan"])

    def test_pins_must_name_the_current_spec_version(self):
        files = full()
        files["repo/plans/SHIP-7/spec.md"] = SPEC.replace("Version: v1", "Version: v2")
        self.assertEqual(Story(files).check(), ["bundle-1.md: PINS does not name spec v2"])

    def test_a_part_of_several_repositories_is_at_least_tier_2(self):
        files = full(tier="1", mode="hands-on")
        files["repo/plans/SHIP-7/README.md"] = "```text\nLEVEL      part 1 of 2 in shipments-api\n```\n"
        self.assertEqual(Story(files).check(), ["bundle-1.md: a part of a story across several repositories is at "
                                                "least Tier 2 (ADR 0021)"])

    def test_the_spec_can_sit_at_the_workspace_root(self):
        files = full()
        files["stories/SHIP-7/spec.md"] = files.pop("repo/plans/SHIP-7/spec.md").replace("Version: v1", "Version: v3")
        self.assertEqual(Story(files).check(), ["bundle-1.md: PINS does not name spec v3"])

    def test_nothing_to_check_is_a_problem(self):
        self.assertEqual(Story({"repo/plans/SHIP-7/README.md": "# index\n"}).check(),
                         ["plans/SHIP-7: no plan.md, fix.md or brief.md"])


class BriefTest(unittest.TestCase):
    def test_a_filled_fix_brief_is_clean_before_it_is_confirmed(self):
        self.assertEqual(Story({"repo/plans/SHIP-7/fix.md": FIX}).check(), [])

    def test_a_brief_is_tier_1(self):
        problems = Story({"repo/plans/SHIP-7/fix.md": FIX.replace("TIER        1", "TIER        2")}).check()
        self.assertIn("fix.md: a brief is Tier 1; a higher tier takes the full route", problems)

    def test_a_feature_brief_test_carries_its_criterion_id(self):
        brief = FIX.replace("FIX BRIEF", "FEATURE BRIEF").replace(
            "REPRO       refund(999, 3)\nEXPECTED    300\nSOURCE      docs/refunds.md R1\nACTUAL      299\n",
            "OUTCOME     totals add up\nCRITERIA    AC1: totals add up -> test test_total\n"
            "OWNER       Bo, 2026-11-19\nDEPENDENCIES none new\nDATA        no change\n")
        problems = Story({"repo/plans/SHIP-7/brief.md": brief}).check()
        self.assertEqual(problems, ["brief.md: the test for AC1 does not carry its ID: test test_total"])


if __name__ == "__main__":
    unittest.main()
