#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
# index KEY TITLE STATUS...: a one-repository story index whose stage rows read the given statuses, in order.
index() {
  local key="$1" title="$2" i=0 stage
  shift 2
  local statuses=("$@")
  mkdir -p "plans/$key"
  {
    printf '# %s · %s\n\nSOURCE     %s (pasted work item)\nKIND       new feature\nROUTE      F1\n' "$key" "$title" "$key"
    printf 'LEVEL      repository\nCURRENT    spec v1\n\n| Stage | Runs in | Status |\n|---|---|---|\n'
    for stage in aidlc-intent aidlc-specify aidlc-design aidlc-plan aidlc-build aidlc-verify aidlc-review \
                 aidlc-release merged; do
      printf '| %s | repository | %s |\n' "$stage" "${statuses[$i]}"
      i=$((i + 1))
    done
  } > "plans/$key/README.md"
}
cat > QUEUE.md <<'FIXTURE_EOF'
# Queue

```text
MAX LANES   3
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-70 | . | feat/SHIP-70-returns | none |
FIXTURE_EOF
index SHIP-70 "Return labels and refunds" done done done done done done done done done
index SHIP-71 "Labels for parcels sent back" done done done "done: approved in pull request 11 by Ana, checked in the review tool" \
  "to do" "to do" "to do" "to do" "to do"
printf 'BRANCH     code feat/SHIP-71-labels\n' >> plans/SHIP-71/README.md
cat > plans/SHIP-71/spec.md <<'FIXTURE_EOF'
# SHIP-71 · spec v1

Spec owner: Priya · Tier: 1 · Route: F1 · Version: v1

AC1: a label for a returned parcel starts with "RET-".
Non-goals: printing.

Spec v1 approved by Priya on 2026-11-19, confirmed by Priya in the session.
FIXTURE_EOF
cat > plans/SHIP-71/plan.md <<'FIXTURE_EOF'
# Plan: SHIP-71 · v1            Spec: v1

TIER       1
APPROACH   One slice, tests first.
FILES      src/shipments/labels.py, tests/test_labels.py
BRANCH     feat/SHIP-71-labels
APPROVAL   plan.md v1 approved by Ana (tech lead), 2026-11-21, in pull request 11, checked in the review tool.
FIXTURE_EOF
cat > plans/SHIP-71/bundle-1.md <<'FIXTURE_EOF'
TASK BUNDLE · SHIP-71 · slice 1
GOAL        AC1: the returned-parcel label prefix.
TIER        1
MODE        delegate
DEPENDS ON  none
BRANCH      feat/SHIP-71-labels
MAY CHANGE  src/shipments/labels.py, tests/test_labels.py
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths
FIXTURE_EOF
git init -q -b main
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
g add -A && g commit -q -m "fixture: SHIP-71's plan is merged; the queue lists SHIP-70 only"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
