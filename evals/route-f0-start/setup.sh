#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
mkdir -p tests
cat > tests/test_labels.py <<'FIXTURE_EOF'
import unittest

from src.shipments.labels import label


class LabelTest(unittest.TestCase):
    def test_label_is_the_code_in_capitals(self):
        self.assertEqual(label("ab12"), "AB12")
FIXTURE_EOF
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "fixture"
