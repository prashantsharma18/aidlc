# Live evidence: the AI gates on pull request #3 (Plan 4b Task 4)

Date: 2026-10-22 · Repository: github.com/prashantsharma18/aidlc (public) · Pull request: #3
Decision under test: [ADR 0004](../adr/0004-ai-gates.md)

## Setup

- **Environment `ai-gates`**, with the owner as required reviewer:
  `gh api repos/prashantsharma18/aidlc/environments/ai-gates --jq '[.protection_rules[].type]'`
  returned `["required_reviewers"]`.
- **Secret:** `gh secret list --env ai-gates` listed `ANTHROPIC_API_KEY` by name only. The key comes
  from the Console workspace `aidlc-ci`, which has a spend limit.
- **Repository setting:** `can_approve_pull_request_reviews` is `false`, and
  `default_workflow_permissions` is `read`.

## Runs

| Run | Commit | ai-review | agent-config-evals | What it showed |
|---|---|---|---|---|
| [39809847502](https://github.com/prashantsharma18/aidlc/actions/runs/39809847502) | `1b7bf8a` | failure | success, every attack row PASS | Key scrubbing (`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`) needs bubblewrap on the runner. Fixed in `57b265a`. |
| [39811513614](https://github.com/prashantsharma18/aidlc/actions/runs/39811513614) | `57b265a` | **success without a review** | success | Both steps ended "success" after 2 turns and posted nothing: the gate was **fail-open**. |
| [39813614457](https://github.com/prashantsharma18/aidlc/actions/runs/39813614457) | `d78f4c8` | success without a review | success | A diagnostic run, with the conversation in the log. See the causes below. |
| [39815144773](https://github.com/prashantsharma18/aidlc/actions/runs/39815144773) | `c174ebd` | **success, reviewed** | success, every attack row PASS | The fixes worked: both passes reviewed, posted 4 findings, and the fail-closed check verified both reports. |

**Causes found in the diagnostic run:**

- **The plugin step.** Anthropic's `code-review` plugin started its eligibility check as a
  background agent, and the CI session ended while it waited. Fixed with
  `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`.
- **The security pass.** "Sandbox is required but failed to initialize: … socat not installed."
  The model refused to turn the sandbox off and said it had not reviewed, yet the step still
  exited "success". Fixed by installing `socat`.
- **The underlying hole.** A review that did not happen could show green. Each pass now returns a
  structured report (`reviewed`, `findings_posted`, `summary`), and the required check `ai-review`,
  a separate job with no secrets, fails unless both say `reviewed: true`.

## The working run (39815144773)

**`agent-config-evals`.** The suite ran from the base commit against the change's harness. Every row
passed: 1, 2a, 2b, 2c, 3, 4, 5, 6, 7, 8a, 8b, 9, 10, 11 and 12. The sandbox rows (2a, 2b, 2c, 6)
passed on GitHub's runner.

**`ai-review`, the required check.** Its log:

```text
bug pass: reviewed, 1 finding(s) posted
security pass: reviewed, 3 finding(s) posted
```

**Cost** (from the action's results): the plugin pass cost 0.18 USD over 11 turns, and the security
pass 0.12 USD over 10 turns.

**Key scrubbing with the plugin.** The plugin's `gh` calls worked with key scrubbing on: there were
no authentication failures, and it posted its finding.

**Review comments and how each was answered:**

| Comment | Finding | Disposition |
|---|---|---|
| [bug] `ai-gates.yml:56` | the diagnostic `show_full_output` is still on | Fixed: removed in the following commit |
| [security] medium, `:57` | the same: full transcripts in public logs | Fixed: same commit |
| [security] medium, `:58` | the plugin marketplace is fetched unpinned | Dismissed: an accepted risk, ADR 0004 |
| [security] low, `:161` | the evals run the change's own code with the key set | Dismissed: an accepted risk, ADR 0004; the approver reads the diff |

**No approval.** `gh api repos/prashantsharma18/aidlc/pulls/3/reviews` listed four `COMMENTED`
reviews from `github-actions[bot]`, and no `APPROVED`.

## Addendum (2026-10-23): runs 5 to 8 and the ruleset

| Run | Commit | ai-review | agent-config-evals | What it showed |
|---|---|---|---|---|
| [39818864651](https://github.com/prashantsharma18/aidlc/actions/runs/39818864651) | `44c654c` | success | success | The diagnostic transcript output was removed; both passes still reviewed. |
| [39820340375](https://github.com/prashantsharma18/aidlc/actions/runs/39820340375) | `150e1ae` | **failure** | success | The code-review plugin reviews a pull request once, so on the next push it reported it had already reviewed, and the gate failed. Fixed in `fa7c033`: only the bug pass may report `already_reviewed`; the security pass reviews every push. |
| [39824303199](https://github.com/prashantsharma18/aidlc/actions/runs/39824303199) | `fa7c033` | success | **failure** | Attack row 11 failed on a tool error that happened before any control acted. Fixed in `8b1be54`: the suite retries a call that failed on its own with no effect. |
| [39825853045](https://github.com/prashantsharma18/aidlc/actions/runs/39825853045) | `8b1be54` | success | success | The review action allow-listed (inputs, env flags, exact `claude_args`); every attack row passed. |

**The ruleset after merge.** `gh api repos/prashantsharma18/aidlc/rulesets/25475561` on 2026-10-23
returned: enforcement `active`; no bypass actors; deletion and non-fast-forward blocked; a pull
request with `required_review_thread_resolution: true`; and the required checks `unit`, `sandbox`,
`policy`, `ai-review` and `agent-config-evals`.

## Not verified

- **Fork pull requests.** There are no secrets, so the jobs fail by design; this was not exercised.
- **A model that claims it reviewed when it did not.** The fail-closed check cannot detect that.
