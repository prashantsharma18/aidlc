#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/workspace/." .
for r in shipments-api web-portal; do (cd "$r" && git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "fixture"); done
git init -q -b main && git add -A && git -c user.name=eval -c user.email=eval@example.com commit -q -m "fixture"
