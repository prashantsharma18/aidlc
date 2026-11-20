# The removed check code (tag `checks-v1`)

On 2026-11-20 aidlc stopped shipping scripts and CI workflows to teams (ADR 0024, Plan 22). Nothing is lost: the tag
`checks-v1` (commit `7843f18`) holds the last state with the code, and any file comes back with
`git show checks-v1:<path>` or `git checkout checks-v1 -- <path>`. Push the tag with main: `git push origin checks-v1`.

| What | Where it was | What holds the rule now |
|---|---|---|
| `check_slice.py` (the slice check) and the Stop hook that ran it | `starter/repo/scripts/`, `starter/repo/.claude/settings.json` | The evidence file the session writes with git, read by `reviewer-compliance` and `reviewer-tests` in a fresh context; the code owner |
| `check_plan.py` (the plan check) | `starter/repo/scripts/` | The plan's checklist; the tech lead |
| `check_recipe_commit.py` (the recipe check) | `starter/repo/scripts/` | The git procedure in `aidlc-build`, step 5 |
| `run_slices.py` (the slice runner) | `starter/repo/scripts/` | A person starts one fresh session per slice |
| `check_contract_version.py`, `check_contract_pin.py` | `starter/repo/scripts/` | oasdiff, `sha256sum -c` and `git ls-remote --tags` in the team's own CI (`designing-apis`) |
| `story_status.py` (status, the release check, the `.gitignore` block) | `starter/workspace/scripts/` | `status.md` derived from git; one release row per repository, confirmed by a person; a `.gitignore` line a person adds |
| `ai-review.yml`, `ci.yml`, `contract-check.yml`, `contract-publish.yml` | `starter/repo/.github/workflows/` | The reviewer agents in a fresh session; the team's own CI |
| The deny rules on the scripts and on `ai-review.yml` | both starter `.claude/settings.json` | Nothing: the files they protected are gone |
| `test_check_slice.py`, `test_check_plan.py`, `test_check_recipe_commit.py`, `test_check_contract.py`, `test_run_slices.py`, `test_story_status.py`, and the workflow tests in `test_gates_hold.py` and `test_multirepo.py` | `scripts/` | Removed with the code they tested |
