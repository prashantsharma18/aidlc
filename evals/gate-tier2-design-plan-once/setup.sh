#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
mkdir -p plans/SHIP-80
# index STATUS...: the index's stage rows, in order: specify, design, plan, build, verify, review, release, merged.
index() {
  local i=0 stage
  local statuses=("$@")
  {
    printf '# SHIP-80 · Carrier prefix on labels\n\nSOURCE     SHIP-80 (pasted work item)\nKIND       new feature\n'
    printf 'ROUTE      F1\nLEVEL      repository\nCURRENT    spec v1\n\n| Stage | Runs in | Status |\n|---|---|---|\n'
    for stage in aidlc-specify aidlc-design aidlc-plan aidlc-build aidlc-verify aidlc-review aidlc-release merged; do
      printf '| %s | repository | %s |\n' "$stage" "${statuses[$i]}"
      i=$((i + 1))
    done
  } > plans/SHIP-80/README.md
}
index done "to do" "to do" "to do" "to do" "to do" "to do" "to do"
cat > plans/SHIP-80/spec.md <<'FIXTURE_EOF'
# SHIP-80 · spec v1

Tier: 2 (labels.py is a shared module the portal team imports; the label format is a contract they rely on)
AC1: label("ab12", carrier="DX") returns "DX-AB12".
AC2: label("ab12") still returns "AB12".
Non-goals: printing.

Spec v1 approved by priya on pull request 7, checked in the review tool, 2026-11-19; it merged first (ADR 0020).
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: SHIP-80 spec v1, merged first"
g switch -q -c docs/SHIP-80-design-plan
index done done "to do" "to do" "to do" "to do" "to do" "to do"
cat > plans/SHIP-80/design-note.md <<'FIXTURE_EOF'
# SHIP-80 · design note

1 Does it change the system's shape?  no
2 Does it move a boundary?  no
3 Does it change a contract someone outside the team relies on?  yes: the portal team parses the label format

OUTCOME      one decision: an optional carrier prefix, added so the old format stays valid -> SHIP-80-adr-1.md
APPROVED     (pending: the tech lead approves design and plan in one pull request)
FIXTURE_EOF
cat > plans/SHIP-80/SHIP-80-adr-1.md <<'FIXTURE_EOF'
# SHIP-80-adr-1 · An optional carrier prefix on labels

Status: Proposed. Decider: Ana (tech lead). Consumers who must agree: the portal team.

Decision: label() takes an optional carrier code and prefixes it; without one, the label is unchanged.
FIXTURE_EOF
g add -A && g commit -q -m "docs: SHIP-80 design note and ADR draft"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
