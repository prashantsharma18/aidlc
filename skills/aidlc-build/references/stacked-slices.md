# Slices on their own branch: siblings and stacks

Sent here from `aidlc-build` Inputs or step 1, a slice on its own branch; this skill's Gate, Stop if and Rules still apply.

**Inputs.** A slice that the plan gave its own branch (`<branch>-s<n>`, ADR 0025) is its own pull request: it keeps its
index, its evidence file and its pull request's documents in `plans/<KEY>/slice-<n>/`, and its progress note stays
`plans/<KEY>/progress-<n>.md`. It edits only its own row, its own progress note and its own evidence file, so sibling
pull requests never edit the same file.

**Step 1.** A stacked slice (its `DEPENDS ON` names a slice on its own branch) whose parent merged, or whose parent's
branch gained commits, is moved first, as `parallel-lanes` says under "A stacked slice after its parent merges" (read
its `SKILL.md`, in the folder beside this skill's): its own commits only, with `git rebase --onto`, never by merging the
default branch into it.
