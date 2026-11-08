#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "fixture"
