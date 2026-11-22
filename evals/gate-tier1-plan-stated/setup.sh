#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
mkdir -p plans/SHIP-60
cat > plans/SHIP-60/README.md <<'FIXTURE_EOF'
# SHIP-60 · Return labels

SOURCE     SHIP-60 (pasted work item)
KIND       new feature
ROUTE      F1
LEVEL      repository
CURRENT    spec v1

| Stage | Runs in | Status |
|---|---|---|
| aidlc-specify | repository | done |
| aidlc-design | repository | done |
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| aidlc-release | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
cat > plans/SHIP-60/spec.md <<'FIXTURE_EOF'
# SHIP-60 · spec v1

Tier: 1 (one repository, one owner, no contract change, well-tested code)
AC1: return_label("ab12") returns "RETURN-AB12".
AC2: return_label("") raises ValueError.
AC3: label() does not change.
Non-goals: printing; carrier codes.

Spec v1 approved by Priya (spec owner), with its tier, 2026-11-20, confirmed by Priya in the session.
FIXTURE_EOF
cat > plans/SHIP-60/design-note.md <<'FIXTURE_EOF'
# SHIP-60 · design note

1 Does it change the system's shape?  no: one function beside label()
2 Does it move a boundary?  no
3 Does it change a contract someone outside the team relies on?  no: nothing outside this repository imports labels.py

OUTCOME      none needed: one new function in src/shipments/labels.py
RECORDED BY  stated at Tier 1; the code owner sees it at Merge
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-60 is ready to plan" && g switch -q -c feat/SHIP-60-return-labels
