#!/usr/bin/env python3
"""A lexical routing check for the skills Claude may start on its own. Claude chooses a skill by matching a request
against skill descriptions; this script approximates that with a stemmed TF-IDF ranking, so a description that lacks
the words people actually use, or two descriptions that read alike, show up before anyone spends a model call.

    python3 scripts/route_check.py [--cases scripts/routing_cases.json] [--min-rank1 0.0]

Prints the rank-1 rate (positives whose skill ranks first), every positive outside its top_k, every negative whose
owner does not outrank the skill, and every pair of descriptions at or above 0.75 similarity. Exits 1 on any of
those, or when the rank-1 rate is below --min-rank1. It cannot judge meaning; behaviour evals do that.
Standard library only."""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate import front_matter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
STOP = set("""a an the and or of to in on for with by is are be this that it as at from your you we our use when do
does how what which can i me my it's its into not no if so there their them then than our us they its also any all""".split())
SUFFIXES = ("ations", "ation", "ings", "ing", "ers", "er", "ies", "es", "ed", "ly", "s", "e")


def stem(word: str) -> str:
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


def auto_skills(skills_dir: Path = SKILLS) -> dict[str, str]:
    found = {}
    for path in sorted(skills_dir.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        fm = front_matter(text) or {}
        if fm.get("disable-model-invocation", "").lower() != "true" and fm.get("description"):
            found[fm.get("name", path.parent.name)] = fm["description"]
    return found


class Index:
    def __init__(self, docs: dict[str, str]):
        self.names = list(docs)
        counts = {name: Counter(tokens(text)) for name, text in docs.items()}
        df = Counter(term for c in counts.values() for term in c)
        n = len(docs)
        self.idf = {term: math.log((n + 1) / (d + 1)) + 1 for term, d in df.items()}
        self.vectors = {name: self._vector(c) for name, c in counts.items()}

    def _vector(self, counts: Counter) -> dict[str, float]:
        v = {t: c * self.idf.get(t, 0.0) for t, c in counts.items() if t in self.idf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        return sum(x * b.get(t, 0.0) for t, x in a.items())

    def rank(self, prompt: str) -> list[tuple[str, float]]:
        q = self._vector(Counter(tokens(prompt)))
        return sorted(((n, self._cosine(q, self.vectors[n])) for n in self.names), key=lambda p: (-p[1], p[0]))

    def similarity(self, a: str, b: str) -> float:
        return self._cosine(self.vectors[a], self.vectors[b])


def check(cases: dict, index: Index) -> dict:
    misses, wrong_owner, firsts, positives = [], [], 0, 0
    for skill, spec in cases.items():
        for case in spec.get("positive", []):
            positives += 1
            order = [n for n, _ in index.rank(case["prompt"])]
            position = order.index(skill) + 1 if skill in order else len(order) + 1
            firsts += position == 1
            if position > case.get("top_k", 3):
                misses.append((skill, case["prompt"], position))
        for case in spec.get("negative", []):
            order = [n for n, _ in index.rank(case["prompt"])]
            if skill in order and case["owner"] in order and order.index(case["owner"]) > order.index(skill):
                wrong_owner.append((skill, case["prompt"], case["owner"]))
    return {"misses": misses, "wrong_owner": wrong_owner, "positives": positives,
            "rank1": firsts / positives if positives else 0.0}


def collisions(index: Index, error: float = 0.75) -> list[tuple[str, str, float]]:
    names = sorted(index.names)
    return [(a, b, s) for i, a in enumerate(names) for b in names[i + 1:]
            if (s := index.similarity(a, b)) >= error]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Lexical routing check for model-invoked skills.")
    parser.add_argument("--cases", default=str(ROOT / "scripts" / "routing_cases.json"))
    parser.add_argument("--min-rank1", type=float, default=0.0)
    args = parser.parse_args(argv)
    index = Index(auto_skills())
    report = check(json.loads(Path(args.cases).read_text(encoding="utf-8")), index)
    pairs = collisions(index)
    print(f"route_check: {report['positives']} positive prompts, rank-1 rate {report['rank1']:.0%}")
    for skill, prompt, pos in report["misses"]:
        print(f"MISS {skill} ranked {pos}: {prompt}")
    for skill, prompt, owner in report["wrong_owner"]:
        print(f"OWNER {owner} does not outrank {skill}: {prompt}")
    for a, b, s in pairs:
        print(f"COLLISION {a} ~ {b}: {s:.2f}")
    failed = report["misses"] or report["wrong_owner"] or pairs or report["rank1"] < args.min_rank1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
