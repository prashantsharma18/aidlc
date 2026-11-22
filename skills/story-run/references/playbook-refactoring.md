# Playbook: refactoring

Read from `aidlc-build` and `aidlc-verify` when the bundle's `PLAYBOOK` line names `refactoring`; the stage's Gate, Stop if and Rules still apply, and this playbook lifts none of them.

**What you own.** The contract. The structure changes; the behaviour does not.

**Typical route.** F1 (a refactoring slice), S (a recipe class), or the last slice of a feature.

**USE SKILLS** (`aidlc-plan` names them in the bundle): `simplifying-code`.

**Steps.**
1. Pin today's behaviour before any structure moves: a characterisation test, a snapshot, or a script that runs the
   old and the new code on the same inputs and compares the outputs. A type check or a lint run is not a pin.
2. Name the structure the code is missing (a state machine, a table, a typed model). The new shape removes branches
   or invalid states; it does not add a layer.
3. Subtract before you add: delete dead code, fold wrappers that have one caller and remove orphan references, in a
   commit of their own, before the reshape.
4. Move in small steps, each keeping the pin green. For an internal API with no users outside the repository, move
   every caller and delete the old one in the same slice; then search for the old name in strings, docs,
   configuration and tests. A caller outside MAY CHANGE is a stop, as `aidlc-build`'s Stop if says. A published API
   is a contract: changing it is a stop too, as `aidlc-build`'s Stop if says for a contract change, and it follows
   `migrating-safely`'s steps in its own plan.
5. Show that the new code is equivalent: the pin green, and, for a large reshape, the comparison script's output.
6. Name what got simpler: fewer layers to trace, or less state to hold. When nothing did, stop and report, as `aidlc-build`'s Stop if says for a plan that looks wrong.
7. A bug found on the way is its own work item, which the person raises at `aidlc-start`; the structural change ships
   first, against the pin.

**Its proof.** The pin, green before and after; the equivalence check's output; what got simpler; no test deleted and
no assertion changed, which `aidlc-build`'s Stop if holds.

**Hand back.** The structure that changed, the pin it held against, the equivalence proof, and what got simpler.
