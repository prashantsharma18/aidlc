# Playbook: feature

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `feature`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The behaviour the criteria name, proved on the surface users reach. The design and the plan are
decided already; you build what they say.

**Typical route.** F0, F1, F2, C, and route G's criteria after slice 0.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `building-user-interfaces` and `testing-in-browser` for a
screen; `designing-apis` for an API or a module boundary; `migrating-safely` for a data change.

**Steps.**
1. Trace the code the slice changes before you write any: its callers, its data, and the tests that cover it (the
   bundle's LOAD FIRST and PATTERN).
2. Name the data shape first: the structure the slice adds, chosen before the logic. A state machine, not scattered
   booleans; a table, not a chain of branches; a typed model, not the same assumption about a shape in many files.
3. One criterion at a time: its failing test, the least code that turns it green, then the whole suite. A criterion
   whose test is impractical follows ADR 0029, as `aidlc-build` step 6 says.
4. A change to a shared helper reaches every caller: find each one, and check it. A caller outside MAY CHANGE is a
   stop, as `aidlc-build`'s Stop if says.
5. Prove it on the surface users reach: a page in a browser, a request to the endpoint, a command in a terminal. A
   result from another surface, or an inconclusive one, is not a pass: say so.
6. Commit small ordered steps, each green.

**Its proof.** Each criterion's test, named with its ID, failing first, then passing; the bundle's DONE WHEN checks,
each a command and what it showed; for a criterion users see, the check on that surface and what passed.

**Hand back.** What you built, each choice you made and why (the decision log), and what stays unproven.
