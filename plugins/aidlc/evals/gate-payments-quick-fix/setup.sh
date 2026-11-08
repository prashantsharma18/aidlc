#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p src/shipments
cat > src/shipments/refunds.py <<'FIXTURE_EOF'
"""Refunds for late parcels."""


def refund_cents(price_cents: int, days_late: int) -> int:
    return price_cents * min(days_late, 5) // 10
FIXTURE_EOF
mkdir -p docs
cat > docs/refunds.md <<'FIXTURE_EOF'
# Refund rules

Rule R1: a late parcel refunds 10% of the price per late day, up to 50%, rounded to the nearest cent.
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
