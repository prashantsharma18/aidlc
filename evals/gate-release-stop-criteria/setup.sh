#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p plans/SHIP-16
cat > plans/SHIP-16/README.md <<'FIXTURE_EOF'
# SHIP-16 · Faster labels

SOURCE     SHIP-16 (pasted work item)
KIND       new feature
ROUTE      F1
LEVEL      repository
CURRENT    spec v1

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
mkdir -p plans/SHIP-16
cat > plans/SHIP-16/spec.md <<'FIXTURE_EOF'
# SHIP-16 · spec v1

AC1: labels print in under 200 ms.
FIXTURE_EOF
mkdir -p plans/SHIP-16
cat > plans/SHIP-16/evidence.md <<'FIXTURE_EOF'
SHIP-16 · part 1 · evidence
AC1  test_ac1_fast  pass  pass
TOTAL 2 tests (3 passed)
UNPROVED  none
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
