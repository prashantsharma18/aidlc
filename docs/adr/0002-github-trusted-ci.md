<!-- aidlc template: adr -->
# 0002 · GitHub is the trusted CI; local `aidlc ci` is a preview

Status: Accepted (2026-10-20). Amends design D3. · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (affects every installed repository's controls)

## Context

The guide's central rule is that the agent's own checks are never the final word. Something the
agent cannot touch must re-run the gates before a change counts (guide 3 step 6, 9.5–9.7). Design D3
had no Git host, so it put that "something" on the developer's machine: `aidlc ci`, a local runner
labelled `simulated-ci`.

Plan 3 built it and reviewed it adversarially. The reviews kept finding the same class of hole: a
trusted runner that shares the agent's machine, user account and `.git` folder can be steered by the
agent. The clearest case was a one-line shell write into `.git/refs/heads/main` that made local CI
report "merge-ready yes". Each fix added code:

- a trusted base record;
- a pinned base;
- a re-scope confirmation (`--accept-base`);
- a local merge-approval file.

Together that was about 300 lines plus their tests, none of which has any value once a real host
exists.

## Decision

- **Trusted CI is GitHub Actions**, on public repositories under `github.com/prashantsharma18`. The
  rendered workflow (`core/ci/github/aidlc-verify.yml`) runs `aidlc ci` in GitHub mode. The
  framework repository has its own workflow (`.github/workflows/framework-ci.yml`).
- **Merge readiness belongs to GitHub.** A ruleset on `main` requires a pull request and the status
  checks (`compile`, `check`, `scans` in an installed repository). The framework repository requires
  `unit`, `sandbox` and `policy`. No local tool claims "merge-ready".
- **Local `aidlc ci` is a preview.** It still runs the change's code only in the bubblewrap sandbox,
  because that protects the person's machine. It takes its base from the working copy and labels its
  record `local-preview`. It is never evidence.
- **Removed:**
  - the trusted base record and `aidlc render --trusted-base`;
  - local CI's pinned-base check;
  - `aidlc scope --accept-base` and its deny rule;
  - `plans/approved-merges.txt`.
- **Kept:**
  - every gate and judge;
  - the sandbox and the hooks;
  - GitHub mode's checks (fresh records directory, head SHA, `--sandbox auto` for `scans` only);
  - the generated-file judge;
  - full-SHA approvals.

## Consequences

- **The agent never holds a push credential** for these repositories. Pushing and merging are a
  person's steps.
- **Every commit uses the noreply identity**
  `prashantsharma18 <6386481+prashantsharma18@users.noreply.github.com>`, set per repository. The
  repositories are public, so nothing secret may be committed. A pre-push scan for identities and
  secrets is mandatory, and GitHub secret-scanning push protection is on.
- **A forged local base now misleads only the local preview** and the local guard's scope. GitHub's
  scope step reads approvals from the pull request's base commit, which the agent cannot move.
- **Branch protection is real**, through rulesets. Code-owner review cannot be required while the
  repositories have a single owner: GitHub does not let you approve your own pull request. CODEOWNERS
  is in place for when a second reviewer joins.
- **Changes to the framework reach `main` only through pull requests.**
- **Plans 4 and 6 add their jobs to the same workflows.** Nothing more is hardened locally.
