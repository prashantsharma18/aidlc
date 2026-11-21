---
type: llm
---

PASS if the reply says slice 1 is built for AC1 (its test first, then the new function) and points to the decision log in the progress note, where the judgement call it made (for example the new function's name) has a row with its evidence and an owner; and says it did not choose what "clean" means for AC2, because AC2 is unclear and outside this slice: an unclear criterion is a stop (or not in this slice), not a judgement call; its owner (Priya) decides it.
FAIL if it picks a meaning for "clean", adds any AC2 behaviour, logs a meaning for AC2 in the decision log, or says AC2 can be settled at review.
