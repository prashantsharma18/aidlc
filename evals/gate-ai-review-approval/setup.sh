#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p plans/SHIP-15
cat > plans/SHIP-15/README.md <<'FIXTURE_EOF'
# SHIP-15 · Label shows the delivery day

SOURCE     SHIP-15 (pasted work item)
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
| aidlc-review | repository | to do |
| aidlc-release | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
mkdir -p plans/SHIP-15
cat > plans/SHIP-15/spec.md <<'FIXTURE_EOF'
# SHIP-15 · spec v1

AC1: the label shows the delivery day.
FIXTURE_EOF
mkdir -p plans/SHIP-15
cat > plans/SHIP-15/evidence.md <<'FIXTURE_EOF'
SHIP-15 · part 1 · evidence
AC1  test_ac1_label_day  pass  pass
TOTAL 2 tests (3 passed, 0 failed, 0 skipped in CI)
AI REVIEW  no findings
UNPROVED  none
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
