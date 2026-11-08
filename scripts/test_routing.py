"""The routing check over the real skills: every model-invoked skill draws its prompts, and no two read alike."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_check  # noqa: E402

CASES = json.loads((Path(__file__).resolve().parent / "routing_cases.json").read_text(encoding="utf-8"))
FLOOR = 0.85  # in-sample: measured 86% (49 of 57) on 2026-11-08, on the prompts the descriptions were tuned to;
              # one lost rank-1 prompt fails CI on purpose (a ratchet). Raise it, never lower it.
HOLDOUT = json.loads((Path(__file__).resolve().parent / "routing_holdout.json").read_text(encoding="utf-8"))["cases"]
HOLDOUT_FLOOR = 0.70  # out-of-sample: 7 of 10 within top 3 on 2026-11-08; descriptions are never tuned to these prompts
CEILING = 0.45  # the most similar real pair was 0.33 on 2026-11-08


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.skills = route_check.auto_skills()
        self.index = route_check.Index(self.skills)

    def test_every_model_invoked_skill_has_cases(self):
        self.assertEqual(sorted(CASES), sorted(self.skills))
        for skill, spec in CASES.items():
            self.assertGreaterEqual(len(spec["positive"]), 3, skill)
            self.assertGreaterEqual(len(spec["negative"]), 2, skill)
            for case in spec["negative"]:
                self.assertIn(case["owner"], self.skills, (skill, case["owner"]))

    def test_every_positive_ranks_within_its_top_k(self):
        self.assertEqual(route_check.check(CASES, self.index)["misses"], [])

    def test_every_negative_owner_outranks_the_skill(self):
        self.assertEqual(route_check.check(CASES, self.index)["wrong_owner"], [])

    def test_the_rank_1_rate_holds_its_floor(self):
        self.assertGreaterEqual(route_check.check(CASES, self.index)["rank1"], FLOOR)

    def test_no_two_descriptions_collide(self):
        self.assertEqual(route_check.collisions(self.index, error=CEILING), [])

    def test_no_positive_prompt_copies_its_description(self):
        for skill, spec in CASES.items():
            for case in spec["positive"]:
                self.assertNotIn(case["prompt"].lower().rstrip("?."), self.skills[skill].lower(), (skill, case["prompt"]))


    def test_held_out_prompts_hold_their_floor(self):
        hits = sum(1 for case in HOLDOUT
                   if [n for n, _ in self.index.rank(case["prompt"])].index(case["skill"]) < case["top_k"])
        self.assertGreaterEqual(hits / len(HOLDOUT), HOLDOUT_FLOOR)

    def test_held_out_prompts_are_not_in_the_tuned_cases(self):
        tuned = {c["prompt"] for spec in CASES.values() for c in spec["positive"] + spec["negative"]}
        self.assertEqual({c["prompt"] for c in HOLDOUT} & tuned, set())

if __name__ == "__main__":
    unittest.main()
