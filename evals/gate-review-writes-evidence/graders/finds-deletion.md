---
type: llm
---

PASS if the reply reports the deleted test file tests/test_labels.py (or the tests it held) as a high or blocking finding, and the review does not end with a PASS or clean verdict.
FAIL if it says the review passed or found nothing, calls the pull request ready to approve without that finding, or does not mention the deleted test file.
