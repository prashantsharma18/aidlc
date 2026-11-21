#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
# slice_index N STATUS...: the index of slice N, which the plan gave its own branch; rows build, verify, review, merged.
slice_index() {
  local n="$1" i=0 stage
  shift
  local statuses=("$@")
  mkdir -p "plans/SHIP-40/slice-$n"
  {
    printf '# SHIP-40 · slice %s · Refuse impossible distances\n\n' "$n"
    printf 'SOURCE     SHIP-40 (pasted work item)\nKIND       new feature\nROUTE      F1\nLEVEL      repository\n\n'
    printf '| Stage | Runs in | Status |\n|---|---|---|\n'
    for stage in aidlc-build aidlc-verify aidlc-review merged; do
      printf '| %s | repository | %s |\n' "$stage" "${statuses[$i]}"
      i=$((i + 1))
    done
  } > "plans/SHIP-40/slice-$n/README.md"
}
mkdir -p plans/SHIP-40
cat > QUEUE.md <<'FIXTURE_EOF'
# Queue

```text
MAX LANES   3
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-40 slice 3 | . | feat/SHIP-40-eta-limit-s3 | SHIP-40 slice 2 |
FIXTURE_EOF
cat > plans/SHIP-40/README.md <<'FIXTURE_EOF'
# SHIP-40 · Refuse impossible distances

SOURCE     SHIP-40 (pasted work item)
KIND       new feature
ROUTE      F1
LEVEL      repository
CURRENT    spec v1

Slices 2 and 3 have their own branches and indexes: plans/SHIP-40/slice-2/README.md and slice-3/README.md.

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | done |
| aidlc-design | repository | done |
| aidlc-plan | repository | done |
| aidlc-build | repository | done |
| aidlc-verify | repository | done |
| aidlc-review | repository | done |
| aidlc-release | repository | to do |
| merged | repository | done |
FIXTURE_EOF
cat > plans/SHIP-40/plan.md <<'FIXTURE_EOF'
# Plan: SHIP-40 · v1            Spec: v1

APPROACH   Slice 1 documents the limit; slice 2 refuses a distance above 20000 km; slice 3 prints the refusal on the label.
ORDER      1 (part branch, merged) · 2 DEPENDS ON none (feat/SHIP-40-eta-limit-s2) · 3 DEPENDS ON slice 2 (feat/SHIP-40-eta-limit-s3, stacked on slice 2)
APPROVAL   plan.md v1 (commit fixture) approved by Ana (tech lead), 2026-11-19, in the session; merged on main first.
FIXTURE_EOF
cat > plans/SHIP-40/bundle-2.md <<'FIXTURE_EOF'
TASK BUNDLE · SHIP-40 · slice 2
GOAL        AC2: refuse a distance above 20000 km.
TIER        1
MODE        hands-on
DEPENDS ON  none
MAY CHANGE  src/shipments/eta.py, tests/test_eta.py
MUST NOT    src/shipments/labels.py, AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
FIXTURE_EOF
cat > plans/SHIP-40/bundle-3.md <<'FIXTURE_EOF'
TASK BUNDLE · SHIP-40 · slice 3
GOAL        AC3: a refused parcel's label names the limit.
TIER        1
MODE        hands-on
DEPENDS ON  slice 2
MAY CHANGE  src/shipments/eta.py, tests/test_eta.py, src/shipments/labels.py, tests/test_labels.py
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths (`plans/<KEY>/**` is exempt from this check)
FIXTURE_EOF
slice_index 2 "to do" "to do" "to do" "to do"
slice_index 3 "to do" "to do" "to do" "to do"
git init -q -b main && g add -A && g commit -q -m "docs(SHIP-40): plan v1 with independent slices, approved and merged first"
g checkout -q -b feat/SHIP-40-eta-limit-s2
cat > src/shipments/eta.py <<'FIXTURE_EOF'
"""Delivery estimates."""
import math


def eta_days(distance_km: float) -> int:
    """Whole days to deliver: one day per started 500 km, at least one."""
    if distance_km < 0:
        raise ValueError("distance must not be negative")
    if distance_km > 20000:
        raise ValueError("distance above 20000 km")
    return max(1, math.ceil(distance_km / 500))
FIXTURE_EOF
cat >> tests/test_eta.py <<'FIXTURE_EOF'

    def test_ac2_refuses_above_20000_km(self):
        with self.assertRaises(ValueError):
            eta_days(20001)
FIXTURE_EOF
g add -A && g commit -q -m "feat(eta): refuse distances above 20000 km (SHIP-40 slice 2)"
cat > src/shipments/eta.py <<'FIXTURE_EOF'
"""Delivery estimates."""
import math

MAX_DISTANCE_KM = 20000


def eta_days(distance_km: float) -> int:
    """Whole days to deliver: one day per started 500 km, at least one."""
    if distance_km < 0:
        raise ValueError("distance must not be negative")
    if distance_km > MAX_DISTANCE_KM:
        raise ValueError(f"distance above {MAX_DISTANCE_KM} km")
    return max(1, math.ceil(distance_km / 500))
FIXTURE_EOF
g add -A && g commit -q -m "refactor(eta): name the distance limit (SHIP-40 slice 2)"
printf '# Progress · SHIP-40 · 2\n\nSTATUS      done\nMODE        hands-on\n' > plans/SHIP-40/progress-2.md
slice_index 2 done "to do" "to do" "to do"
g add -A && g commit -q -m "docs(SHIP-40): slice 2 built"
# Slice 3 starts from slice 2's branch once slice 2's build is done.
g checkout -q -b feat/SHIP-40-eta-limit-s3
cat > src/shipments/labels.py <<'FIXTURE_EOF'
"""Shipping labels."""
from src.shipments.eta import MAX_DISTANCE_KM


def label(code: str) -> str:
    return code.upper()


def refused_label(code: str) -> str:
    """The label of a parcel refused for its distance."""
    return f"{code.upper()} REFUSED: over {MAX_DISTANCE_KM} km"
FIXTURE_EOF
cat > tests/test_labels.py <<'FIXTURE_EOF'
import unittest

from src.shipments.labels import refused_label


class LabelsTest(unittest.TestCase):
    def test_ac3_a_refused_label_names_the_limit(self):
        self.assertEqual(refused_label("ab12"), "AB12 REFUSED: over 20000 km")
FIXTURE_EOF
g add -A && g commit -q -m "feat(labels): a refused parcel's label names the limit (SHIP-40 slice 3)"
head="$(git rev-parse --short HEAD)"
printf '# Progress · SHIP-40 · 3\n\nSTATUS      done\nMODE        hands-on\n' > plans/SHIP-40/progress-3.md
cat > plans/SHIP-40/slice-3/evidence.md <<FIXTURE_EOF
SHIP-40 · slice 3 · evidence at ${head}
AC3  test_ac3_a_refused_label_names_the_limit  pass  pass
TOTAL 4 tests (4 passed, 0 failed, 0 skipped in CI)
UNPROVED  none
FIXTURE_EOF
slice_index 3 done done "to do" "to do"
g add -A && g commit -q -m "docs(SHIP-40): slice 3 built and verified at ${head}"
# Slice 2 goes on through review; Ana approved its pull request, and the merged row was marked in its last commit.
g checkout -q feat/SHIP-40-eta-limit-s2
slice_index 2 done done done done
g add -A && g commit -q -m "docs(SHIP-40): slice 2 reviewed; merged row marked after Ana's approval, checked in the review tool"
# The code host squashed slice 2 into one commit on main, and kept its branch. Someone else's work landed after it.
g checkout -q main
g merge -q --squash feat/SHIP-40-eta-limit-s2 && g commit -q -m "SHIP-40 slice 2: refuse distances above 20000 km (#21)"
printf 'Rule D3: the depot accepts parcels until 18:00.\n' >> docs/delivery.md
g add -A && g commit -q -m "docs: the depot's closing time"
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
