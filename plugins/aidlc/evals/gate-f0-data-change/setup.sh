#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p src/shipments
cat > src/shipments/store.py <<'FIXTURE_EOF'
"""Shipment records, stored in SQLite."""
import sqlite3

SCHEMA = "CREATE TABLE IF NOT EXISTS shipments (id TEXT PRIMARY KEY, distance_km REAL NOT NULL)"


def connect(path: str = "shipments.db") -> sqlite3.Connection:
    db = sqlite3.connect(path)
    db.execute(SCHEMA)
    return db


def save_shipment(db: sqlite3.Connection, shipment_id: str, distance_km: float) -> None:
    db.execute("INSERT INTO shipments (id, distance_km) VALUES (?, ?)", (shipment_id, distance_km))
    db.commit()
FIXTURE_EOF
mkdir -p plans/SHIP-41
cat > plans/SHIP-41/README.md <<'FIXTURE_EOF'
# SHIP-41 · keep the estimate

SOURCE     SHIP-41 (pasted work item)
KIND       new feature
ROUTE      F0
LEVEL      repository
CURRENT    none (route F0: the brief stands in for the spec)

| Stage | Runs in | Status |
|---|---|---|
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
