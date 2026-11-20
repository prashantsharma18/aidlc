# 0024 · Instructions first; checks live in the team's project

Status: Proposed (2026-11-20). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-20-instructions-first.md` · Plan: `docs/plans/2026-11-20-plan-22-instructions-first.md` ·
Supersedes: ADR 0019 · Amends: ADRs 0012, 0015, 0016, 0017, 0020, 0021, 0022, 0023

## Context
ADR 0010 removed the Python harness: it slowed every change, it served mostly one AI tool, and it was hard to adopt.
Plans 20 and 21 brought code back: seven starter scripts, four starter workflows, a Stop hook, and hundreds of tests
of their own. One rule then lived in a skill, a script and two kinds of test, and Plan 21 needed many fix rounds on
the scripts alone. The scripts could block a merge only through GitHub's required checks and branch protection, which
on GitHub Free work only on public repositories. Without them every check, coded or not, is advice.

The leading frameworks (superpowers, Spec Kit, OpenSpec, BMAD-METHOD, pstack) ship no gate code. The vendors put hard
rules in the project's own tests, linters, CI and tool settings. The evidence says agents do cheat around tests, that
self-review is weak, and that an outside reviewer helps. The design records the sources.

## Decision
- aidlc is instructions: skills, agents, templates and `AGENTS.md`. It ships no scripts and no CI workflows to teams.
- A rule that must hold every time lives in the team's project: its tests, linters, type checks, CI, and its AI
  tool's settings. aidlc tells the agent to build and maintain those checks; the team owns them.
- When a mistake repeats, `aidlc-feedback` adds a check to the team's project at the highest level that works, proves
  it fails on the real past mistake, and adds a row to the "Rules and what enforces them" table of the team's
  `AGENTS.md`.
- A verdict that a change is done or passes counts only from someone who did not write it: a reviewer agent in a
  fresh context, or a person. It names the commit it judged; a later commit that changes a path outside
  `plans/<KEY>/` voids it.
- The reviewer agents read an evidence file the session writes with plain git commands,
  `plans/<KEY>/review-evidence.md`. They keep Read, Grep and Glob, and never run a command.
- A person decides at each gate, from evidence that git can confirm, not from claims.
- aidlc depends on git and on no code-host feature, other than a pull request (a review request). A team that has branch protection or required checks may use
  them; aidlc never needs them. "Pull request" stays the common word for a pull or merge request, defined once in
  `using-aidlc`. "Change request" stays the name of route C, so it never means a pull request.
- A skill may name plain git commands and the standard tools this table names (oasdiff, sha256sum); it never names a
  script of its own.

The checks, rule by rule:

| Rule | Was enforced by | Now enforced by |
|---|---|---|
| No deleted test, no changed assertion (ADR 0019's central concern) | `check_slice.py` in CI | The `reviewer-tests` agent reads the test-file diff from an evidence file the session writes (`git diff <base> -- <test paths>`); the evidence table shows the changed test files and the test count before and after; the code owner reads both. The team may add its own CI check. |
| Edit only inside MAY CHANGE; MUST NOT untouched | `check_slice.py` | The `reviewer-compliance` agent compares `git diff --name-only <base>` (in the evidence file) with the bundle |
| No new suppression or skip without an exception | `check_slice.py` (12 syntaxes) | The team's linters' own rules (`skills/aidlc-onboard/references/suppression-rules.md`), plus the reviewer reading added `aidlc-exception` lines |
| No new dependency without asking | `check_slice.py` | The reviewer reads manifest changes in the evidence file; the person approves |
| Approved documents unchanged in a code change (ADR 0020) | `check_slice.py` | The reviewer reads `git diff <base> -- plans/<KEY>`; the code owner approves |
| Plan complete before approval | `check_plan.py` | The plan template's checklist; the tech lead approves |
| Recipe commit is mechanical (ADR 0012) | `check_recipe_commit.py` | `aidlc-build` step 5 and the evidence file's Recipe commits section: re-run the recipe on the parent commit and `git diff` against the commit; the reviewer reads the result |
| Run approved slices one by one | `run_slices.py` | The person starts one fresh session per slice; `aidlc-build` states the stops |
| Story status across repositories, drift, merge state | `story_status.py` | A release checklist row per repository, filled from git by the agent and confirmed by the person |
| Contract version raised; breaking change raises MAJOR | `check_contract_version.py` + workflows | The provider team runs `oasdiff breaking` and a version comparison in its own CI; `designing-apis` gives the commands |
| Consumer copy matches the pinned version | `check_contract_pin.py` | `sha256sum -c` and `git ls-remote --tags` in the consumer's release checklist |
| Independent AI review of a change request | `ai-review.yml` (GitHub, Claude-only) | The `reviewer-*` agents run in a fresh session; the team may add any AI review its host offers |
| Secrets never read; push asks first | starter `.claude/settings.json` | Kept as an optional example settings file a team copies; not a gate of aidlc |

## Consequences
- Removed: `starter/repo/scripts/`, `starter/workspace/scripts/`, `starter/repo/.github/workflows/`, the Stop hook,
  the deny rules that protected them, and their tests. The code stays recoverable under the tag `checks-v1`
  (`docs/archive/checks-v1.md`).
- The starter's `.claude/settings.json` stays as an optional example: the secret-read denies, the sandbox, "ask before
  push or install", and the denies on `.claude/**` and `CODEOWNERS`, so a session cannot loosen its own settings.
- A deleted test or a weakened assertion is now caught by a reviewer agent and a person, not by code. A reviewer
  agent can be lenient. A team that wants a hard block adds one to its own CI.
- A story across several repositories relies on a release checklist again: one row per repository, filled from git
  by the agent and confirmed by a person.
- aidlc's own validator and its own CI stay: they check aidlc, not a team's project.
- ADRs 0012, 0015, 0016, 0017, 0020, 0021, 0022 and 0023 keep their decisions; each carries a dated note saying which
  of its enforcement lines no longer hold. ADR 0019 is superseded.
- The session writes the evidence file the reviewers read, so the evidence is only as honest as that session; the code owner can re-run any command in it against git.
