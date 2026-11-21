# aidlc behaviour evals

Behaviour cases for `claude plugin eval`: each case runs the plugin on a realistic prompt in an isolated session and
grades what it did. They spend model calls on your account, so they run on demand and before each release,
never on pull requests.
The free routing check (`scripts/route_check.py`) runs in CI instead.

| Tag | What it proves |
|---|---|
| `gate` | A gate holds when someone pushes against it |
| `routing` | A practice starts when it should, and stays quiet when it should not |
| `route` | A route's stages write the right files on a fixture repository |
| `language` | A practice's principles hold in Java and .NET |

Stage cases start a person-only stage by its slash command. The stage's text does not appear in the run's trace, so
these cases grade behaviour: files written, tools called, the reply. Cases that need a repository copy one from
`fixtures/` in their `setup.sh`.

## In CI

The `evals` workflow runs the release baseline in a clean container, where the Bash cases can run: Actions → evals →
Run workflow, then approve the run in the `ai-gates` environment. It writes a pass-rate table to the run's summary.
Run it before each release, and after any change to a stage skill.

## Run

From the repository root:

```bash
# Smoke: every case once, no baseline arm
claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit "Bash(python3 *)" "Bash(git *)" \
  --no-publish --runs 1 --ablation none --max-cost-usd 10

# Release baseline: three runs, with and without the plugin
claude plugin eval . --trust-plugin --scaffold --allow-tools Write Edit "Bash(python3 *)" "Bash(git *)" \
  --no-publish --runs 3 --threshold 0.67 --max-cost-usd 60 --model claude-sonnet-5-5 \
  --json evals/results/release.json

# Release routing pass: under the baseline arm, "skill fired" graders are indicators only, so score them on their own
claude plugin eval . --trust-plugin --no-publish --tag routing language --runs 3 --ablation none \
  --model claude-sonnet-5-5 --max-cost-usd 15
```

Pin `--model` for any run you compare over time. A run costs about $0.10 to $0.60; there are 40 cases.
Scaffold commits ignore your global git hooks and signing (`-c core.hooksPath=/dev/null -c commit.gpgsign=false`).
Cases that need Bash (the build stage, and the review stage that writes the evidence file) cannot run where the Bash
sandbox refuses, for example when `~/.docker/contexts` is a symbolic link; run those in CI or in the local container
(`container/README.md`). The Bash cases are `gate-assertion-change`, `gate-amended-assertion`, `gate-scope`,
`gate-dependency`, `gate-delegate-tier2`, `gate-stale-verdict`, `gate-review-writes-evidence`, `route-d1-build`,
`gate-restatement-tier3`, `route-s-dependency-bump`, and the four lane cases, `gate-lane-worktree-taken`,
`gate-lane-plan-approval`, `gate-coordinator-clash` and `gate-lane-stacked-rebase`. The lane cases make git worktrees inside the scaffold, so they expect to run in the folder
the scaffold was built in.
The four cases for decisions by tier and standard changes (ADR 0026) are `gate-tier1-plan-stated`,
`route-s-dependency-bump`, `gate-tier2-design-plan-once` and `gate-restatement-tier3`.
Results go to `results/`, which git ignores. Add `--case <name>` to run one case. A low score is a finding about the
kit: record it; never weaken a grader to make it pass.
