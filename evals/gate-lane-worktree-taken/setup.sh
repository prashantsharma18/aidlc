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
| 1 | SHIP-12 | . | feat/SHIP-12-eta-limit | none |
| 2 | SHIP-15 | . | feat/SHIP-15-label-prefix | none |
FIXTURE_EOF
index SHIP-12 "Refuse impossible distances" done done done done doing "to do" "to do" "to do" "to do"
index SHIP-15 "Carrier prefix on labels" done "to do" "to do" "to do" "to do" "to do" "to do" "to do" "to do"
cat > plans/SHIP-15/intent.md <<'FIXTURE_EOF'
# SHIP-15 · intent v1

Problem: carriers cannot tell their parcels apart at the depot.
Outcome: each label starts with the carrier's two-letter code.
Tier: 1 (one repository, no contract, well-tested code).
Accepted by Priya (product owner) on the work item, 2026-11-20.
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: the queue and two items"
g branch feat/SHIP-12-eta-limit
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
# Another lane holds SHIP-12: its worktree, with work it has not committed yet.
g worktree add -q .worktrees/SHIP-12 feat/SHIP-12-eta-limit
printf '# Progress · SHIP-12 · 1\n\nSTATUS      doing\n' > .worktrees/SHIP-12/plans/SHIP-12/progress-1.md
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
