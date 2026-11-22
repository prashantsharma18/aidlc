#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
mkdir -p plans/SHIP-71
cat > plans/SHIP-71/README.md <<'FIXTURE_EOF'
# SHIP-71 · Return labels

SOURCE     SHIP-71 (pasted work item)
KIND       new feature
ROUTE      F1   (new feature; Tier 1; one repository; criteria written by owner)
LEVEL      repository
BRANCH     code feat/SHIP-71-return-labels
CURRENT    spec v1

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | done |
| aidlc-design | repository | to do |
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| merged | repository | to do |
| aidlc-release | repository | to do |
FIXTURE_EOF
cat > plans/SHIP-71/spec.md <<'FIXTURE_EOF'
# SHIP-71 · spec v1

Spec owner: Priya · Tier: 1 (one repository, one owner, no contract change, well-tested code) · Route: F1 · Version: v1

AC1: return_label("ab12") returns "RETURN-AB12".
AC2: return_label("") raises ValueError.
Non-goals: printing; carrier codes.

Spec v1 approved by Priya on 2026-11-21, confirmed by Priya in the session · route F1 (shown; the tech lead owns it).
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-71 is Ready" && g switch -q -c feat/SHIP-71-return-labels
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
