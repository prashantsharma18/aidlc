# Slice 0: route G

Sent here from `aidlc-build` step 1, slice 0 of route G; this skill's Gate, Stop if and Rules still apply.

**Step 1.** On slice 0 of route G there is no code yet and the commands in `AGENTS.md` read `(not yet run)`: skip this
step; the scaffold recipe commit comes first, and step 8 is the first full run.

**Step 5.** A `(scaffold)` recipe in slice 0 is not checked by the recipe check, because generators are not reproducible
(fresh identifiers, current package versions). Its commit holds only the generators' output, its trailer reads `Recipe:
<tool>@<version> (scaffold)`, and the person reviews it as generated code. That review is this skill's recipe pause,
step 5.
