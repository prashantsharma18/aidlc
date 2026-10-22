# AI gates: AI review and harness evals

Two required checks run in `.github/workflows/ai-gates.yml`: `ai-review` and `agent-config-evals`.
Both use Anthropic's official GitHub Action or Claude Code itself. Neither is a framework engine
([ADR 0004](../adr/0004-ai-gates.md)).

## What runs, and when

Both jobs run on every pull request: when it is opened, gets new commits, is reopened, or is
marked ready for review.

- **`ai-review`** runs two review steps:
  - Anthropic's `code-review` plugin, for the bug and compliance passes (`CLAUDE.md`, `AGENTS.md`);
  - a security pass.

  Each finding is an inline comment. A draft pull request is not reviewed until you mark it ready.
- **`agent-config-evals`** first checks whether the change touches the harness. If it does, it runs
  the live attack suite.

Both jobs run in the `ai-gates` environment, so each run waits for your approval.

## Approving a run

On the pull request, choose **Review deployments**, tick `ai-gates`, and approve. One approval
covers both jobs. A new commit starts new runs, which need approval again.

## Answering review findings

The reviewer never approves, and nothing it says counts as approval: a person approves. A clean
review posts nothing; the job's success means only that the review ran.

For each comment:

1. Fix it (a test first, in a new commit), or decide it does not apply.
2. Reply `Fixed: <commit>` or `Dismissed: <reason>`, for example
   `Dismissed: intended, the spec allows an empty list`.
3. Choose **Resolve conversation**.

The `main` ruleset sets **Require conversation resolution before merging**, so a pull request with
an open comment cannot merge. GitHub cannot check that you wrote a reason; the team does.

## Harness evals

`agent-config-evals` runs the suite when the change touches any of these:

- `core/hooks/`
- `core/policy/`
- `cli/aidlc/adapters/`
- `cli/aidlc/harness.py`
- `cli/aidlc/hookbridge.py`
- `tests/harness_live/`
- `.github/workflows/ai-gates.yml`

Otherwise it passes without running. If it cannot tell whether the harness changed, it fails.

**How the run works:**

1. The suite (`tests/harness_live/`) comes from the base commit, so a change cannot weaken its own
   exam.
2. The suite runs about 16 short Haiku sessions against the change's harness.
3. The job passes only when every row passes.
4. The report is the `harness-attacks` artifact of the run.

Run the same suite on your machine with `make harness-live`. It uses your own Claude login.

## On your machine

- **Review:** `/code-review` in a Claude Code session.
- **Harness evals:** `make harness-live`.

Neither counts toward a merge. Only the GitHub runs do (ADR 0002).

## Setup (the owner's steps)

1. **Create the key.** In the Claude Console, create a workspace `aidlc-ci` with a monthly spend
   limit, and an API key in it.
2. **Create the environment.** In the repository's Settings, Environments, create `ai-gates` with
   yourself as the required reviewer.
3. **Store the key.** Run `gh secret set ANTHROPIC_API_KEY --env ai-gates -R <owner/repo>`, and paste
   the key at the prompt. Never paste it anywhere else.
4. **Check that Actions cannot approve.** In Settings, Actions, General, "Allow GitHub Actions to
   create and approve pull requests" must be off.
5. **Require the gates.** In the `main` ruleset, require the status checks `ai-review` and
   `agent-config-evals`, and turn on **Require conversation resolution before merging**.

## Forks

GitHub gives pull requests from forks no secrets, so both jobs fail on them. A maintainer
re-creates the change on a branch in this repository.

## Cost

Each run approved costs:

- about one Sonnet review;
- when the harness changed, about 16 short Haiku sessions.

Read the real figures in the `aidlc-ci` Console workspace.

## Other evals

- **Skills and agents:** evals come with them in Plan 5, as `claude plugin eval` suites.
- **Each project repository:** its own small set of real tasks comes in Plan 6.
