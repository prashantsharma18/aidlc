#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p src/shipments
cat > src/shipments/eta.py <<'FIXTURE_EOF'
"""Delivery estimates."""
import math


def eta_days(distance_km: float) -> int:
    """Whole days to deliver: one day per started 500 km, at least one."""
    if distance_km < 0:
        raise ValueError("distance must not be negative")
    return math.floor(distance_km / 500) + 1
FIXTURE_EOF
mkdir -p tests
cat > tests/test_eta.py <<'FIXTURE_EOF'
import unittest

from src.shipments.eta import eta_days


class EtaTest(unittest.TestCase):
    def test_ac1_1200_km_takes_three_days(self):
        self.assertEqual(eta_days(1200), 3)

    def test_ac2_at_least_one_day(self):
        self.assertEqual(eta_days(0), 1)
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "fixture"
