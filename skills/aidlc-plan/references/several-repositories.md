# Several repositories: a part's documents

Sent here from `aidlc-plan` step 7 or step 8, a part of a story across several repositories; this skill's Gate, Stop if and Rules still apply.

**Step 7.** For a part of a story across several repositories, the spec pin also names the home repository's commit
where the approved spec merged: `spec v<n> @ <commit>`. Once a part pins it, nothing under `stories/<KEY>/` is moved or
renamed; a change is a new version (ADR 0022).

**Step 8.** For a part of a story across several repositories, also write the part index `plans/<KEY>/README.md` from
`assets/story-index.md`: LEVEL `part <n> of <m> in <repository>`, the BRANCH lines `code feat/<KEY>-<part>` and
`plan docs/<KEY>-<part>-plan` (this plan's own pull request, which merges first), the PINS line of the latest bundle,
and the rows
`aidlc-plan`, `aidlc-build`, `aidlc-verify`, `aidlc-review` and `merged`. Beside it, write `plans/<KEY>/criteria.md`
from `assets/criteria.md`: the part's own criteria, edge cases and non-goals, copied word for word from the spec at the
pinned commit, under a SOURCE line naming the home repository, the spec's path and that commit. The copy is read-only:
the part's CI and reviewers read it instead of the home repository, and `aidlc-release` compares it with the spec at its
commit before release (ADR 0022).
