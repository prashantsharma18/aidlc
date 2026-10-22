<!-- aidlc template: adr -->
# 0004 · AI gates use Anthropic's GitHub Action and GitHub's own rules

Status: Accepted (2026-10-22). Amends design §8. · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (adds required checks and a workflow write permission)

## Context

Design §8 planned two framework commands:

- `aidlc eval`: a custom runner, case format and profiles;
- `aidlc review`: three passes and a custom gate that every finding is dispositioned.

On 2026-10-22 the owner chose official tools and GitHub's own rules instead, so the framework does
not build a review or eval engine. What exists:

- **`anthropics/claude-code-action`.** Anthropic's GitHub Action. Its documented review workflow
  runs Anthropic's `code-review` plugin and posts each finding as an inline comment
  (<https://code.claude.com/docs/en/github-actions>).
- **Managed Code Review.** It needs a Team or Enterprise plan, and Anthropic says it "never approves
  or blocks the pull request", so it cannot be a gate.
- **`claude plugin eval`.** Anthropic's eval tool. It loads only a plugin's skills, agents and hooks,
  never a project's `CLAUDE.md` or `.claude/` settings. So it fits skills (Plan 5), not the
  harness or a repository's own configuration.
- **The live attack suite** (`tests/harness_live/run_attacks.py`). It already runs real Claude Code
  sessions against a rendered repository, and checks which control stopped each attack.

## Decision

1. **Review.** `anthropics/claude-code-action`, pinned to
   `6fed3ca145920b639991cb756090506e1bcaf515` (v1.0.245, released 2026-10-07). It is the newest
   release at least 14 days old, the dependency policy's minimum release age; the moving `v1` tag
   pointed at a release published the same day. Anthropic's `code-review` plugin runs the bug and
   compliance passes (`CLAUDE.md`, `AGENTS.md`), and a short prompt runs the security pass.
   Findings are inline comments.
2. **Disposition gate.** GitHub's "Require conversation resolution before merging". You answer
   each comment "Fixed: <commit>" or "Dismissed: <reason>", then resolve it. GitHub cannot check
   that a reason was written; that stays a team rule, as the guide treats it (11.4).
3. **Harness evals.** The live attack suite runs as the required job `agent-config-evals` whenever
   a change touches anything outside `docs/`. The harness is built from much of `cli/` and `core/`,
   so a narrower path list missed real changes. The suite (`tests/harness_live/`, `tests/helpers.py`,
   `tests/__init__.py`) is restored exactly from the base commit, so a change cannot weaken its own
   exam (guide 10.8 step 6). It runs with `python3 -I`, and it appends the repository to `sys.path`,
   so a file the change adds cannot replace a standard module.
4. **Skill evals** come in Plan 5, with `claude plugin eval`. **Repository evals** come in Plan 6.
   They will generalise the attack suite's headless runner, because `claude plugin eval` does not
   load project configuration.
5. **The `ai-gates` environment.** A person approves every run. The `ANTHROPIC_API_KEY` exists only
   as that environment's secret, from a dedicated Console workspace (`aidlc-ci`) with a spend limit.
   It is not a subscription token.

## The security exception

`core/policy-as-code/rego/workflows.rego` denied every job-level write. It now allows exactly one:
`pull-requests: write`, for a job that meets all of these:

- it runs in the `ai-gates` environment;
- it has at least one step;
- it uses only `actions/checkout` and `anthropics/claude-code-action`, each pinned to a full SHA;
- its only shell steps are two fixed setup commands: `sudo apt-get update -q && sudo apt-get install
  -y -q bubblewrap`, and the `kernel.apparmor_restrict_unprivileged_userns=0` sysctl. Each has no
  `env:`, `shell:` or other key. The key scrubbing (`CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`) needs
  bubblewrap, which the first live run showed: without it, the review step stopped.

Every other write, `id-token: write` included, stays denied.

**Why this token.** By default the Action posts as the Claude GitHub App, which needs
`id-token: write` and an installation whose rights include Contents, Workflows and Actions write.
The workflow's own `GITHUB_TOKEN`, limited to `pull-requests: write`, is narrower:

- it cannot push, because `contents` stays read;
- it cannot approve, because the repository's `can_approve_pull_request_reviews` setting is
  `false` (checked 2026-10-22, and again in the live proof);
- the security pass may only read files inside the repository, run one exact `git diff` command,
  and post inline comments;
- both review steps set `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1`, which removes the key from every
  subprocess's environment.

If the token cannot post live, the owner decides between installing the Claude GitHub App (another
narrow exception, for `id-token: write`) and keeping only what the token can do. The outcome is
recorded here.

## Accepted risks

- **The plugin is not pinned.** The marketplace
  (`https://github.com/anthropics/claude-code.git`) is a Git URL that the Action fetches at run
  time. The `code-review` plugin's prompts can change without a commit in this repository. The
  mitigations: it is Anthropic's repository; the job holds no write but comments; a person
  approves every run.
- **The `code-review` plugin grants itself more tools.** Its command allows `gh pr view`,
  `gh pr diff`, `gh pr comment`, `gh search` and `gh issue` commands. A prompt injection in the
  diff could, in principle, make it post a local file with `gh pr comment --body-file`, and comments
  here are public. The mitigations:
  - the key is scrubbed from subprocesses;
  - a person approves every run;
  - the key sits in its own workspace with a spend limit.

  If a comment ever shows the key, rotate the key at once.
- **The token can resolve review threads.** The Action writes the job token into the checkout's git
  configuration, and `pull-requests: write` can resolve review threads through GitHub's API. The
  disposition gate therefore relies on the reviewer having no `gh api` or GraphQL tool, which
  neither step grants.
- **The judge runs in the same process as the code under test.** The attack suite imports the
  change's `cli/aidlc` in the same process, and the sessions run the change's hooks with the key in
  their environment. A deliberately malicious change from someone with write access could read the
  key. The control is the person who approves the run: they read the diff first.
- **The compliance pass reads the change's own rules.** The Action restores `.claude/`, `.mcp.json`
  and `CLAUDE.md` from the base branch, but this repository's `CLAUDE.md` only imports `AGENTS.md`,
  which comes from the change.
- **Fork pull requests are not reviewed.** GitHub withholds secrets from them, so `ai-review`
  fails, and so does `agent-config-evals` unless the change touches only `docs/`. A maintainer
  re-creates the change on a branch here.
- **Every run waits for a person's approval.** That costs attention, and it buys spend control and a
  human in the loop.

## Consequences

- `aidlc eval` and `aidlc review` are not built.
- `core/policy/branch-protection.yaml` names the required check `ai-review` (formerly
  `ai-review-dispositioned`).
- Installed repositories get the review workflow in Plan 6, when it is proven on the demo
  repositories.
- Operation is described in [docs/checks/ai-gates.md](../checks/ai-gates.md).
