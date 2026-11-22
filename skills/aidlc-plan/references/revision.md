# Revisions and re-plans

Sent here from `aidlc-plan` step 5 or step 8, a re-plan or a revision; this skill's Gate, Stop if and Rules still apply.

**Step 5.** A part already merged when its spec changed gets a revision: branch `<type>/<KEY>-<part>-r<n>`, pull request
title `[<KEY>] part <n> of <m>, revision <r>: <what>`, and a bundle pinned to the new spec that covers only the change
between the two versions.

**Step 8.** For a re-plan or a revision, raise the version, say what changed, and reset the `aidlc-build`,
`aidlc-verify`, `aidlc-review` and `merged` rows of the part index to "to do".
