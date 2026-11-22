---
name: fix-root-causes
description: "Apply when debugging. Trace each symptom back to the first place the system went wrong and fix it there. A guard is a fix only when the state it handles is legitimate."
disable-model-invocation: true
metadata:
  kind: principle
---

# Fix Root Causes

Fix the fault, not the place where it surfaced. The root cause is the first place the system did something it should not do, or failed to handle a state it should handle.

- Reproduce first. Ask "why" until the answer is a wrong decision in the code. When stuck, instrument and read the actual state.
- Ask whether the state that triggered the symptom is legitimate. If it is, handle it where the code broke. If it should never exist, a check there hides the bug, so find what produced it. Guards, retries, swallowed errors, clamped values, and discarded state are the usual ways to hide a bug.
- Fix the pattern, not the instance. Find every place with the same fault.
- If the deciding fact took a deep dig, propose the cheap, always-on signal that would have shown it at first look.

**In aidlc:** Every place inside MAY CHANGE; one outside it is a stop. The always-on signal is a proposal for its owner (`aidlc-feedback`). In production you propose only (`debugging-failures`).

Adapted from pstack's `principle-fix-root-causes` (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan); its notice is in `skills/NOTICE`.

You draft; you never approve.
