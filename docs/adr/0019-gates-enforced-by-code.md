# 0019 · The rules hold by code, not only by prose

Status: Superseded by ADR 0024 (proposed, 2026-11-20); ADR 0024 accepted 2026-11-21: aidlc ships no check code; each rule is held by the team's own
project and by a reviewer who did not write the change. (Was: Proposed (2026-11-19). · Decider: Prashant Sharma
(framework owner))
Plan: `docs/plans/2026-11-19-plan-20-gates-that-hold.md` · Change list: A1, A3, A4, A5

## Context
The rules that matter most hold only by the skills' prose and the same model's self-check: edits inside MAY CHANGE,
no changed assertion, no new dependency, the Quality bar, MUST NOT. A review on 2026-11-17 found no hook, no Edit deny
in the repository starter and no CI check for them, and a starter AI review weaker than the framework's own.

## Decision
- `check_slice.py` (starter, standard library) checks a story branch against its approved bundles: scope, MUST NOT,
  removed tests and assertions (outside AMENDED ASSERTIONS and recipe commits), dependency manifests, suppressions and
  skips without `aidlc-exception: reason=...; owner=...; expires=YYYY-MM-DD`, and approved documents (ADR 0020).
- CI runs it as a required job, from the base branch's copy, on the pull request's head commit.
- A Stop hook in the repository starter's `.claude/settings.json` runs it before a Claude Code session stops. The
  plugin root keeps no `hooks` folder (ADR 0018).
- The repository starter denies edits to `.claude/**`, the check scripts, `run_slices.py`, `ai-review.yml` and
  `CODEOWNERS`. `AGENTS.md` and `ci.yml` stay editable (onboard and slice 0 need them); the slice check covers them
  in a build.
- Adopters get the hardened AI review: pinned actions, the key in an approved environment, fail-closed, rules read
  from the base branch, and it loads no settings, hooks or MCP servers the repository controls.

## Consequences
- A branch whose name carries no tracker key is not checked (dependency bots, chores). A person sees that in the PR.
- In Copilot, Codex and Cursor only the CI checks hold; the README says so.
- On GitHub Free the required checks bind only on public repositories.
