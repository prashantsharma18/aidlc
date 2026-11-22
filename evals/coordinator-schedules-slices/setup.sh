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
index SHIP-70 "Return labels and refunds" done done done "done: approved in pull request 9 by Ana, checked in the review tool" \
  "to do" "to do" "to do" "to do" "to do"
cat > plans/SHIP-70/plan.md <<'FIXTURE_EOF'
# Plan: SHIP-70 · v1            Spec: v1

TIER       1
APPROACH   Three slices, tests first: returns, refunds, then the returns endpoint on top of slice 1.
FILES      src/shipments/returns.py, src/shipments/refunds.py, src/shipments/returns_api.py
BRANCH     docs/SHIP-70-plan
APPROVAL   plan.md v1 approved by Ana (tech lead), 2026-11-20, in pull request 9, checked in the review tool.
FIXTURE_EOF
bundle() {
  local n="$1" deps="$2" may="$3"
  cat > "plans/SHIP-70/bundle-$n.md" <<FIXTURE_EOF
TASK BUNDLE · SHIP-70 · slice $n
GOAL        Slice $n of the return labels and refunds.
TIER        1
MODE        delegate
DEPENDS ON  $deps
MAY CHANGE  $may
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths
FIXTURE_EOF
}
bundle 1 none src/shipments/returns.py
bundle 2 none src/shipments/refunds.py
bundle 3 "slice 1" src/shipments/returns_api.py
for n in 2 3; do
  mkdir -p "plans/SHIP-70/slice-$n"
  cat > "plans/SHIP-70/slice-$n/README.md" <<FIXTURE_EOF
# SHIP-70 · slice $n

| Stage | Runs in | Status |
|---|---|---|
| aidlc-build | repository | to do |
| aidlc-verify | repository | to do |
| aidlc-review | repository | to do |
| merged | repository | to do |
FIXTURE_EOF
done
git init -q -b main
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
g add -A && g commit -q -m "fixture: SHIP-70 is planned in three slices"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
