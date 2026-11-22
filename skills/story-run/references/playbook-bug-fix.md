# Playbook: bug fix

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `bug-fix`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The evidence that the bug is gone. Every line you ship traces to evidence. A change that "might
help" is a guess, and it does not ship: the smallest change the evidence supports ships, nothing more.

**Typical route.** D1, D2, and an incident's follow-up (it enters at `aidlc-start`).

**USE SKILLS** (`aidlc-plan` names them in the bundle): none beyond what `aidlc-build` loads; its step 8 loads
`debugging-failures` for a failing check.

**Steps.**
1. Reproduce it yourself, on the surface where it fails, locally or in a test environment: a person acts on
   production (`aidlc-operate`). Ask a person only with a stated reason that surface cannot be reached from here.
   When it will not fire, build the trigger: narrow the conditions, or add logging, until it does.
2. Write the competing causes down, each with the observation that would rule it out. Seed them from the code and
   from the area's history (`git log -L`, and the pull requests that changed it). Each pass, run the check that rules
   out the most causes, write what it showed, and cross out the causes it ruled out. Never guess.
3. Confirm the mechanism with a run before you write the fix, and name that run.
4. The reproduction comes first: the failing test, or, when a test is impractical, the command or live check that
   shows the failure (ADR 0029). Its commit comes before the fix's in git history.
5. Make the smallest fix the evidence supports. Before another attempt, back the last one out in full, so the diff
   holds only what the evidence supports. The limit on attempts is `aidlc-build`'s, as its Stop if says.
6. Run the reproduction again, on the same surface: it passes now. A unit test shows how a branch behaves, not that
   the bug is gone; an inconclusive result is not a pass.

**Its proof.** The reproduction, failing before the fix and passing after, with both outputs; the competing causes,
each with the run that ruled it in or out; nothing in the diff that the evidence did not call for.

**Hand back.** What was broken, its cause and the run that proved it, the fix, and the failing-then-passing output,
word for word.
