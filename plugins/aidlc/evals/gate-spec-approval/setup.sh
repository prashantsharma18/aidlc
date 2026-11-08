#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p plans/SHIP-11
cat > plans/SHIP-11/README.md <<'FIXTURE_EOF'
# SHIP-11 · Delivery day for customers

SOURCE     SHIP-11 (pasted work item)
KIND       new feature
ROUTE      F1
LEVEL      repository
CURRENT    spec v1

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | to do |
| aidlc-design | repository | to do |
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| aidlc-release | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
mkdir -p plans/SHIP-11
cat > plans/SHIP-11/intent.md <<'FIXTURE_EOF'
# SHIP-11 · intent v1

Problem: customers cannot see when a parcel arrives.
Outcome: a customer sees the delivery day for an order.
Tier: 1 (one repository, no contract, well-tested code).
Accepted by Priya (product owner) on the work item, 2026-11-07.
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
