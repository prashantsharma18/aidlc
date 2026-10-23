# AI gates: AI review and harness evals

Two required checks run in `.github/workflows/ai-gates.yml`: `ai-review` and `agent-config-evals`.
Both use Anthropic's official GitHub Action or Claude Code itself. Neither is a framework engine
([ADR 0004](../adr/0004-ai-gates.md)).

## What runs, and when

Both jobs run on every pull request: when it is opened, gets new commits, is reopened, or is
marked ready for review.

- **`ai-review-passes`** runs two review steps:
  - Anthropic's `code-review` plugin, for the bug and compliance passes (`CLAUDE.md`, `AGENTS.md`);
  - a security pass.

  Each finding is an inline comment. Each step ends with a short structured report saying whether
  it really reviewed the change. A draft pull request is not reviewed until you mark it ready.
- **`ai-review`** is the required check. It holds no secrets. It passes only when the review job
  succeeded and both steps report they reviewed the change. The one exception: the bug pass may
  report that it already reviewed this pull request. A step that could not read the diff
  therefore fails the check, instead of showing green. It cannot catch a model that falsely claims
  it reviewed.
- **`agent-config-evals`** first checks whether the change touches anything outside `docs/`. If it
  does, it runs the live attack suite.

Both jobs run in the `ai-gates` environment, so each run waits for your approval.

**Changing the base branch does not re-run the gates.** Re-running on the `edited` event was
considered and rejected: an edit to the title or description would skip the review, and GitHub
counts a skipped required check as passed, so that newer "pass" would hide a failed review (and the
edit would cancel a review in progress). If you retarget a pull request, push a commit or re-run
the jobs.

**The review job's policy is an allow-list** (`workflows.rego`): its checkout may set only
`fetch-depth`, and must set `persist-credentials: false`; it may not name another repository or
ref, or add an environment.

## Approving a run

On the pull request, choose **Review deployments**, tick `ai-gates`, and approve. One approval
covers both jobs. A new commit starts new runs, which need approval again.

**Approving runs the pull request's code with the API key set**, on a runner with network access:
the evals execute its `cli/`, `core/` and hooks. Read the diff before you approve, above all
changes to `cli/`, `core/hooks/`, `tests/` and `.github/`.

## Answering review findings

The reviewer never approves, and nothing it says counts as approval: a person approves. The job's
success means only that the review steps ran.

**What a green `ai-review` means.**
- **The security pass reviewed this push.** Its own report must say so.
- **The bug and compliance pass reviewed this push, or an earlier push of the same pull request.**
  Anthropic's `code-review` plugin reviews once per pull request: after its first comment, it skips
  later pushes and reports `skipped_reason: already_reviewed`. The check accepts only that skip.
  Any other skip fails the check, including one where the plugin judged the change trivial.

For a large change after the first review, open a new pull request, or run `/code-review`
yourself.

For each comment:

1. Fix it (a test first, in a new commit), or decide it does not apply.
2. Reply `Fixed: <commit>` or `Dismissed: <reason>`, for example
   `Dismissed: intended, the spec allows an empty list`.
3. Choose **Resolve conversation**.

The `main` ruleset sets **Require conversation resolution before merging**, so a pull request with
an open comment cannot merge. GitHub cannot check that you wrote a reason; the team does.

## Harness evals

`agent-config-evals` runs the suite unless the change touches only `docs/`. The harness is built
from much of `cli/` and `core/`, so any code change runs it. A change to only `docs/` passes
without running. If the job cannot tell what changed, it fails.

**How the run works:**

1. The suite (`tests/harness_live/`, `tests/helpers.py`, `tests/__init__.py`) is restored exactly
   from the base commit, so a change cannot weaken its own exam.
2. The suite runs about 16 short Haiku sessions against the change's harness. The job allows 60
   minutes: 17 sessions at the 180-second session timeout is about 51 minutes before any retry.
3. The job passes only when every row passes.
4. The report is the `harness-attacks` artifact of the run. It is uploaded only when it does not
   contain the API key.

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

GitHub gives pull requests from forks no secrets. So `ai-review` fails on them, and so does
`agent-config-evals` unless the change touches only `docs/`. A maintainer re-creates the change on
a branch in this repository.

## Cost

Each run approved costs:

- the review. The `code-review` plugin starts several subagents (Haiku, Sonnet and Opus); `--model`
  sets only the main session;
- one Sonnet security pass;
- unless the change touches only `docs/`, about 16 short Haiku sessions.

Read the real figures in the `aidlc-ci` Console workspace.

## Other evals

- **Skills and agents:** evals come with them in Plan 5, as `claude plugin eval` suites.
- **Each project repository:** its own small set of real tasks comes in Plan 6.

## If the key leaks

If a comment, a log or an artifact ever shows the key, rotate the key at once:

1. Delete the key in the `aidlc-ci` Console workspace.
2. Create a new key.
3. Run `gh secret set` again.
4. Delete the comment.
