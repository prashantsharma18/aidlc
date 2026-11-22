# Independent slices

Sent here from `aidlc-plan` step 5 or step 8, a plan with independent slices; this skill's Gate, Stop if and Rules still apply.

**Step 5.** The first slice runs on the part's branch. A later slice whose `DEPENDS ON` names the slice before it, on
that branch, continues it, as today. Every other slice gets its own row, branch `<branch>-s<n>` and pull request, titled
`[<KEY>] slice <n> of <m>: <what>`: with `none` it starts from the default branch (a sibling pull request), and with a
slice it starts from that slice's branch (a stacked pull request, which merges after it). A slice's own branch holds
that slice only. `DEPENDS ON` names at most one slice, and only an existing slice earlier in the plan, so the slices
never form a cycle: when a slice needs two, plan them on one branch, each building on the one before it. Such a slice
keeps its index and its pull request's documents in `plans/<KEY>/slice-<n>/`, so sibling pull requests never edit the
same file. The plan, its bundles and these indexes merge on the default branch first, in their own pull request (ADR
0020), so every slice's branch starts from them.

**Step 8.** For a plan with independent slices, also write each such slice's index `plans/<KEY>/slice-<n>/README.md`
from `assets/story-index.md`: LEVEL as the part's, and the rows `aidlc-build`, `aidlc-verify`, `aidlc-review` and
`merged`. Each slice's stages mark only those rows. At Tier 1, where the index has no `plan` BRANCH line, add
`BRANCH plan docs/<KEY>-plan` and rename the branch you are on to it (`git branch -m docs/<KEY>-plan`): this plan
merges first, and every slice's branch starts from the default branch after it.
