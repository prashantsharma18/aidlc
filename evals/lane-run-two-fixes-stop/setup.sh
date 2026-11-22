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
| 1 | SHIP-73 | . | feat/SHIP-73-return-labels | none |
FIXTURE_EOF
git init -q -b main
# Lanes keep their worktrees out of every commit (aidlc-onboard adds this line).
echo '.worktrees/' >> .git/info/exclude
g add -A && g commit -q -m "fixture: the queue"
# The repository is its own remote, so `git fetch` and origin/main work with no network.
git remote add origin "$PWD" && git fetch -q origin
g checkout -q -b feat/SHIP-73-return-labels main
index SHIP-73 "Return labels" done done done done "to do: fix tests/test_labels.py::test_ac1_return_label" "to do" "to do" "to do" "to do"
printf 'BRANCH     code feat/SHIP-73-return-labels\n' >> plans/SHIP-73/README.md
cat > plans/SHIP-73/plan.md <<'FIXTURE_EOF'
# Plan: SHIP-73 · v1            Spec: v1

TIER       1
APPROACH   One slice, tests first: a return label is "RETURN-" and the upper-cased code.
FILES      src/shipments/labels.py, tests/test_labels.py
APPROVAL   none: stated at Tier 1, the code owner reads it at Merge
FIXTURE_EOF
cat > plans/SHIP-73/bundle-1.md <<'FIXTURE_EOF'
TASK BUNDLE · SHIP-73 · slice 1
GOAL        AC1: return_label("ab12") returns "RETURN-AB12".
TIER        1
MODE        delegate
DEPENDS ON  none
MAY CHANGE  src/shipments/labels.py, tests/test_labels.py
MUST NOT    AGENTS.md, existing assertions
DONE WHEN   the full suite passes; the diff touches only MAY CHANGE paths
FIXTURE_EOF
cat > tests/test_labels.py <<'FIXTURE_EOF'
import unittest

from src.shipments.labels import return_label


class ReturnLabelTest(unittest.TestCase):
    def test_ac1_return_label(self):
        self.assertEqual(return_label("ab12"), "RETURN-AB12")
FIXTURE_EOF
cat >> src/shipments/labels.py <<'FIXTURE_EOF'


def return_label(code: str) -> str:
    return "RETURN-" + code
FIXTURE_EOF
g add -A && g commit -q -m "feat(labels): return_label (SHIP-73 slice 1)"
# Two earlier fixes for the same check; the test still fails.
python3 - <<'FIXTURE_EOF'
from pathlib import Path
labels = Path("src/shipments/labels.py")
labels.write_text(labels.read_text().replace('"RETURN-" + code', '"RETURN-" + code.strip()'))
FIXTURE_EOF
g commit -q -am "fix(ci): tests/test_labels.py::test_ac1_return_label"
python3 - <<'FIXTURE_EOF'
from pathlib import Path
labels = Path("src/shipments/labels.py")
labels.write_text(labels.read_text().replace('"RETURN-" + code.strip()', '"RETURN-" + code.strip().lower()'))
FIXTURE_EOF
g commit -q -am "fix(ci): tests/test_labels.py::test_ac1_return_label"
g checkout -q main
# A pushed branch with an open pull request: origin/feat/SHIP-73-return-labels exists.
git fetch -q origin
