#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
mkdir -p plans/SHIP-21
cat > QUEUE.md <<'FIXTURE_EOF'
# Queue

```text
MAX LANES   3
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-21 | . | feat/SHIP-21-weekend-days | none |
FIXTURE_EOF
cat > plans/SHIP-21/README.md <<'FIXTURE_EOF'
# SHIP-21 · No delivery on weekends

SOURCE     SHIP-21 (pasted work item)
KIND       new feature
ROUTE      F1
LEVEL      repository
CURRENT    spec v1

| Stage | Runs in | Status |
|---|---|---|
| aidlc-intent | repository | done |
| aidlc-specify | repository | done |
| aidlc-design | repository | done |
| aidlc-plan | repository | to do |
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| aidlc-release | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
cat > plans/SHIP-21/spec.md <<'FIXTURE_EOF'
# SHIP-21 · spec v1

AC1: an estimate whose last day falls on a Saturday or a Sunday moves to the Monday after it.
AC2: an estimate whose last day falls on a weekday is unchanged.
E1: 0 km sent on a Friday arrives on the Monday (decided by Priya, product owner).

Spec v1 approved by Priya (spec owner), 2026-11-20, checked on the work item.
FIXTURE_EOF
cat > plans/SHIP-21/design-note.md <<'FIXTURE_EOF'
# SHIP-21 · design note

DESIGN        none needed: one function in src/shipments/eta.py, no contract, no data change.
RECORDED BY   Ana (tech lead), 2026-11-20, confirmed by Ana in the session
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-21 is ready to plan"
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
