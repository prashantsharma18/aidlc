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
STUCK AFTER   60m
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-72 | . | feat/SHIP-72-eta-cap | none |
FIXTURE_EOF
git init -q -b main
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
g add -A && g commit -q -m "fixture: the queue"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
# SHIP-72's lane is building; its last commit is three hours old and it holds one uncommitted change.
g checkout -q -b feat/SHIP-72-eta-cap main
index SHIP-72 "Cap every estimate at 40 days" done done done done doing "to do" "to do" "to do" "to do"
cat > plans/SHIP-72/bundle-1.md <<'FIXTURE_EOF'
TASK BUNDLE · SHIP-72 · slice 1
GOAL        Cap every estimate at 40 days.
TIER        1
MODE        delegate
DEPENDS ON  none
MAY CHANGE  src/shipments/eta.py, tests/test_eta.py
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths
FIXTURE_EOF
g add -A
three_hours_ago="$(date -d '-3 hours' -R)"
GIT_AUTHOR_DATE="$three_hours_ago" GIT_COMMITTER_DATE="$three_hours_ago" g commit -q -m "docs(SHIP-72): plan v1 and bundle 1, approved"
g checkout -q main
g worktree add -q .worktrees/SHIP-72 feat/SHIP-72-eta-cap
printf '# cap at 40 days: work in progress\n' >> .worktrees/SHIP-72/src/shipments/eta.py
git fetch -q origin
