# Playbook: performance

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `performance`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** A number, measured and explained. Every change is tied to a measurement; reading the code is never a
measurement.

**Typical route.** F1 or C for a performance criterion; D2 for a regression.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `tuning-performance`.

**Steps.**
1. Measure a baseline on the default branch, before the slice changes anything, on a case that shows the reported
   slowness. When no case shows it, that case is the first thing to build.
2. Show that the measurement tells a slow case from a fast one. Then keep it as it is for the whole slice: a change to
   the measurement during the work is a change to the assertion, as `aidlc-build`'s Stop if says.
3. Explain the number before you trust it: what limits it (the CPU, the network, a lock, the database), how much it
   moves over repeated runs, and that it measured the work you think it did.
4. Try the remedies in this order, cheapest first, and end with the first one that meets the target: remove the work;
   avoid doing it again; do less of it; do it later; do it off the user's path; do it in parallel; make it cheaper.
5. One change, one measurement. Keep a change that moved the number past the run-to-run noise; back out the rest. A
   neutral change is backed out.
6. Correctness first: the suite stays green, and a simpler change that holds the number is the one you keep.

**Its proof.** The baseline on the default branch and the number after, each with how it was measured, its repeated
runs and what limits it; the criterion's threshold, and whether it holds; each change, kept or backed out, with its
number.

**Hand back.** The baseline, the result, the difference, and where the measurements are kept.
