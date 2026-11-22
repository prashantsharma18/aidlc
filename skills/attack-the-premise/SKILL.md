---
name: attack-the-premise
description: "Apply when two or more fixes that share one premise have failed the same gate. Write the premise down and test it directly before you write another fix that assumes it."
disable-model-invocation: true
metadata:
  kind: principle
---

# Attack the Premise

When two or more fixes that share one premise have failed the same gate, suspect the premise, not the fixes.

- Write the premise down: the one sentence every failed fix assumed.
- Test it before the next fix. Find an observation that would come out differently if the premise were false, and make it. Look at how the failures are distributed, not only at how large they are.
- If the evidence contradicts the premise, look for what the failures share that it did not predict. If one part always lands on the losing side, change what puts it there instead of adding a mechanism that cleans up after it.

Do not start the next fix before the premise is written down and tested.

**In aidlc:** A second fix that fails the same way is a stop (`aidlc-build`'s Stop if): write the shared premise and the observation that tests it in the stop's report. Testing the premise is diagnosis, not another attempt.

Adapted from pstack's `principle-attack-the-premise` (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan); its notice is in `skills/NOTICE`.

You draft; you never approve.
