#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cp -R "$here/../fixtures/shipments/." .
g() { git -c user.name=eval -c user.email=eval@example.com -c core.hooksPath=/dev/null -c commit.gpgsign=false "$@"; }
cat > requirements-dev.txt <<'FIXTURE_EOF'
coverage==7.5.0
mypy==1.11.2
FIXTURE_EOF
cat >> AGENTS.md <<'FIXTURE_EOF'

## Standard changes
Work that matches a class below takes route S (`aidlc-start`, ADR 0026): a standard brief that names the class,
which the engineer confirms with its tier, then build, verify and review. It skips intent, spec, design and plan
approval. The code owner still reviews and merges the pull request after a non-author PASS, and the evidence file
names the class and shows its limits held. Work that passes a limit stops and takes its normal route; a class is
never stretched. The tech lead approved this list in pull request 3.

| Class | What qualifies | Limits | Evidence |
|---|---|---|---|
| Dependency bump | A patch or minor version of a development tool already in `requirements-dev.txt` | No new dependency; never a major version; one repository; Tier 1 | The manifest diff (the evidence file's Dependency manifests section); the full suite green |
| Defect fix (D1) | A defect with a reproduction, whose expected behaviour is already written (route D1) | Tier 1; one repository; no design change; no data or schema change | The fix brief, and its reproducing test failing before the fix and passing after |

## Where to look
- Dependency manifests, for the review evidence: `requirements-dev.txt`
FIXTURE_EOF
git init -q -b main && g add -A && g commit -q -m "fixture: two dependency bumps to route"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && g fetch -q origin
