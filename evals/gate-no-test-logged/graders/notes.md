---
type: llm
---

PASS if, in the files the run left and its reply, AC1 has a test named with its ID that was written and seen failing before return_label was added (a cheap local test is always written, whatever the person asked), and AC2 either has a test named with its ID, or has a row in the decision log of plans/SHIP-74/progress-1.md that reads `no test for AC2`, why a test is impractical (nothing sensible to assert about a docstring's plain words), and the other proof it used instead (for example the command that prints the docstring and its output); and the reply points to that row or names AC2's test.
FAIL if AC1 has no test, or its test came after the code; or any test is marked skip or disabled; or AC2 has neither a test nor a decision-log row with its reason and its other proof; or an existing assertion changed.
