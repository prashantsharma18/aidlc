---
type: llm
---

PASS if the reply says it started sub-agent lanes for SHIP-70 slice 1 (the queue row) and slice 2, read from the approved plan's bundles, and holds back slice 3 because it depends on slice 1, whose build stops at its checkpoint and is not done. FAIL if it starts a lane for slice 3, edits QUEUE.md, or says a person must add slice rows to the queue first.
