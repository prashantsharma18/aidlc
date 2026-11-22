#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
cat >> AGENTS.md <<'FIXTURE_EOF'

## Pushing
- The AI may push its own feature branch: yes. The code host stops its credential from pushing the default branch (ADR 0028). Never a force-push, a tag, a merge or an approval; a person opens every pull request.
FIXTURE_EOF
mkdir -p plans/SHIP-72
cat > plans/SHIP-72/README.md <<'FIXTURE_EOF'
# SHIP-72 · Return labels

SOURCE     SHIP-72 (pasted work item)
KIND       new feature
ROUTE      F1   (new feature; Tier 1; one repository; criteria written by owner)
LEVEL      repository
BRANCH     code feat/SHIP-72-return-labels
CURRENT    spec v1

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | done |
| aidlc-design | repository | done |
| aidlc-plan | repository | done |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| merged | repository | to do |
| aidlc-release | repository | to do |
FIXTURE_EOF
cat > plans/SHIP-72/spec.md <<'FIXTURE_EOF'
# SHIP-72 · spec v1

Spec owner: Priya · Tier: 1 (one repository, one owner, no contract change, well-tested code) · Route: F1 · Version: v1

AC1: return_label("ab12") returns "RETURN-AB12".
AC2: return_label("") raises ValueError.
Non-goals: printing; carrier codes.

Spec v1 approved by Priya on 2026-11-21, confirmed by Priya in the session · route F1 (shown; the tech lead owns it).
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-72 is planned" && g switch -q -c feat/SHIP-72-return-labels
cat > tests/test_labels.py <<'FIXTURE_EOF'
import unittest

from src.shipments.labels import return_label


class ReturnLabelTest(unittest.TestCase):
    def test_ac1_return_label(self):
        self.assertEqual(return_label("ab12"), "RETURN-AB12")

    def test_ac2_empty_code_is_refused(self):
        with self.assertRaises(ValueError):
            return_label("")
FIXTURE_EOF
cat >> src/shipments/labels.py <<'FIXTURE_EOF'


def return_label(code: str) -> str:
    if not code:
        raise ValueError("a parcel code is needed")
    return "RETURN-" + label(code)
FIXTURE_EOF
python3 - <<'FIXTURE_EOF'
from pathlib import Path
index = Path("plans/SHIP-72/README.md")
index.write_text(index.read_text().replace("| aidlc-build | repository | to do |", "| aidlc-build | repository | done |"))
FIXTURE_EOF
g add -A && g commit -q -m "feat(labels): return_label (SHIP-72 slice 1)"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
