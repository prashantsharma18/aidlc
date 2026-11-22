#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
mkdir -p plans/SHIP-70
cat > plans/SHIP-70/README.md <<'FIXTURE_EOF'
# SHIP-70 · Return labels

SOURCE     SHIP-70 (pasted work item)
KIND       new feature
ROUTE      F1   (new feature; Tier 1; one repository; criteria written by owner)
LEVEL      repository
BRANCH     code feat/SHIP-70-return-labels
CURRENT    none yet

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | to do |
| aidlc-design | repository | to do |
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| merged | repository | to do |
| aidlc-release | repository | to do |
FIXTURE_EOF
cat > plans/SHIP-70/intent.md <<'FIXTURE_EOF'
# SHIP-70 · intent v1

Problem: support agents cannot make a return label for a parcel, so customers wait for a manual one.
Outcome: an agent gets a return label for a parcel's code in one call.
Kind: new feature · Provisional tier: 1
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-70 has its intent" && g switch -q -c feat/SHIP-70-return-labels
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
