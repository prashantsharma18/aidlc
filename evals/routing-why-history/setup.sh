#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
git init -q -b main && g add -A && g commit -q -m "fixture: shipments"
cat > src/shipments/eta.py <<'FIXTURE_EOF'
"""Delivery estimates."""
import math

ETA_CAP_HOURS = 72


def eta_days(distance_km: float) -> int:
    """Whole days to deliver: one day per started 500 km, at least one, never above the cap."""
    if distance_km < 0:
        raise ValueError("distance must not be negative")
    return min(max(1, math.ceil(distance_km / 500)), ETA_CAP_HOURS // 24)
FIXTURE_EOF
g add -A && g commit -q -F - <<'MSG_EOF'
fix(eta): cap the ETA at 72 hours

The carrier contract CARRIER-9 promises delivery within three days. Above 72 hours the carrier pays no penalty, so a longer ETA misleads the customer.
MSG_EOF
