# The recipe commit and its check

Sent here from `aidlc-build` step 5, a bundle with a RECIPE; this skill's Gate, Stop if and Rules still apply.

Then run the recipe check, with git, from the repository root (`cd "$(git rev-parse --show-toplevel)"`). Make a
temporary worktree at the commit's parent (`git worktree add <folder> <commit>^`). In it, run the repository's test
command (named in `AGENTS.md`) there first, for the parent's count, because the recipe then changes the worktree, and
then `git -C <folder> clean -fd`. Run the approved command, stage everything (`git -C <folder> add -A`), and `git -C
<folder> diff --cached --stat <commit>` must print nothing. Then run the test command again, for the commit's count: the
test count must be the same at the parent and at the commit; record both counts. Also keep `git diff <commit>^ <commit>
-- ':(top)<test path>'` (one quoted pattern per test path), so the changed assertion lines are on record. Remove the
worktree (`git worktree remove --force <folder>`) and keep the result for the Recipe commits section of the evidence
file (step 9).
