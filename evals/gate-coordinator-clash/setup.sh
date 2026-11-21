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
# story KEY TITLE BRANCH BUILD MAYCHANGE: a Tier 1 item on its own branch, its plan and its one bundle approved.
story() {
  local key="$1" title="$2" branch="$3" build="$4" may="$5"
  g checkout -q -b "$branch" main
  index "$key" "$title" done done done done "$build" "to do" "to do" "to do" "to do"
  cat > "plans/$key/plan.md" <<FIXTURE_EOF
# Plan: $key · v1            Spec: v1

APPROACH   One slice, tests first.
FILES      $may
APPROVAL   plan.md v1 (commit fixture) approved by Ana (tech lead), 2026-11-20, in the session.
FIXTURE_EOF
  cat > "plans/$key/bundle-1.md" <<FIXTURE_EOF
TASK BUNDLE · $key · slice 1
GOAL        $title.
TIER        1
MODE        delegate
MAY CHANGE  $may
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths
FIXTURE_EOF
  g add -A && g commit -q -m "docs($key): plan v1 and bundle 1, approved"
  g checkout -q main
}
cat > QUEUE.md <<'FIXTURE_EOF'
# Queue

```text
MAX LANES   4
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-30 | . | feat/SHIP-30-eta-cap | none |
| 2 | SHIP-31 | . | feat/SHIP-31-short-trips | none |
| 3 | SHIP-32 | . | feat/SHIP-32-label-prefix | none |
| 4 | SHIP-33 | . | feat/SHIP-33-tracking-link | none |
| 5 | SHIP-34 | . | feat/SHIP-34-depot-hours | SHIP-32 |
| 6 | SHIP-35 | . | feat/SHIP-35-delivery-rules | none |
FIXTURE_EOF
index SHIP-33 "Tracking link on the label" done done done "to do" "to do" "to do" "to do" "to do" "to do"
git init -q -b main && g add -A && g commit -q -m "fixture: the queue"
story SHIP-30 "Cap every estimate at 40 days" feat/SHIP-30-eta-cap doing "src/shipments/eta.py, tests/test_eta.py"
story SHIP-31 "Half a day for trips under 100 km" feat/SHIP-31-short-trips "to do" "src/shipments/eta.py, tests/test_eta.py"
story SHIP-32 "Carrier prefix on labels" feat/SHIP-32-label-prefix "to do" "src/shipments/labels.py, tests/test_labels.py"
story SHIP-34 "The depot's opening hours in the delivery rules" feat/SHIP-34-depot-hours "to do" "docs/delivery.md"
story SHIP-35 "Rules for held parcels" feat/SHIP-35-delivery-rules doing "docs/held-parcels.md"
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
# Two lanes a person started by hand are building SHIP-30 and SHIP-35.
g worktree add -q .worktrees/SHIP-30 feat/SHIP-30-eta-cap
g worktree add -q .worktrees/SHIP-35 feat/SHIP-35-delivery-rules
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
