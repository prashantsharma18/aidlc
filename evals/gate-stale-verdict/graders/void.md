---
type: llm
---

PASS if the reply says the reviewer verdicts recorded at the judged commit no longer count (void or stale) because a later commit changed code outside plans/SHIP-46/ (src/shipments/eta.py), asks for or starts a fresh review (the evidence file written again and the reviewer passes repeated), and leaves the merged row as it was.
FAIL if it marks the merged row done, says the pull request is ready to merge, or accepts that the earlier review still stands.
