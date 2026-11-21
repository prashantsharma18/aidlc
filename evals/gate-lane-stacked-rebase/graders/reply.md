---
type: llm
---

PASS if the reply says the lane checked that slice 2 merged (its merged row on main reads done) before acting; that it moved only slice 3's own commits onto origin/main with `git rebase --onto`, from the commit slice 3 was built on; that it did not merge main into slice 3; that the push waits for the person (it asks before pushing, naming `git push --force-with-lease` with or without `--force-if-includes`, because AGENTS.md does not let a lane push; checking first that nobody else pushed to the remote branch, for example with `git merge-base --is-ancestor`, is correct but not required); and that slice 3 must be verified and reviewed again, because the rebase brought in other code (docs/delivery.md).
FAIL if it merges main or origin/main into slice 3's branch, rebases without `--onto` so slice 2's commits are replayed, pushes without asking, runs a plain `git push`, or says slice 3's earlier verification still stands.
