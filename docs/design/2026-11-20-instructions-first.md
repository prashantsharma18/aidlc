# Instructions first: aidlc ships no check code and needs no code-host feature

Date: 2026-11-20 · Owner: framework owner (Prashant Sharma) · Status: agreed in the session, 2026-11-20
Replaces: the "gates by code" direction of ADR 0019 and phases 2b to 6 of `2026-11-19-aidlc-6-change-list.md`
where they add shipped code or depend on GitHub features. The code is kept, recoverable, under the tag `checks-v1`.

## For the reviewer
- Who decides: the framework owner. Recorded in the new ADR 0024 and in Plan 22's approval.
- Tier and main risk: a framework change. The main risk is that an agent deletes a test or weakens an assertion to
  reach green, and no code catches it. Section "The checks, rule by rule" says what catches it instead.
- What changed: aidlc stops shipping scripts and CI workflows. The method stays. Hard checks move into each team's
  own project, which the team owns and runs.

## Why
1. The old Python harness (about 12,000 lines) was removed in ADR 0010: it slowed every change, it was built mostly
   for one AI tool, and it was hard to adopt. Plans 20 and 21 brought code back (about 2,740 lines of starter
   scripts, 4 starter workflows, 375 tests of their own). The same costs returned: one rule lived in a skill, a script
   and two kinds of test, and Plan 21 needed many fix rounds on the scripts alone.
2. The code could only block a merge through GitHub's required checks and branch protection. On GitHub Free those
   work only on public repositories. Without them every check, coded or not, is advice. The owner does not want aidlc
   tied to one code host.
3. The leading frameworks are prose-first and host-neutral: obra/superpowers, github/spec-kit, OpenSpec, BMAD-METHOD,
   cursor/plugins pstack. None enforces its own rules with shipped code. pstack's workflow has no hooks and no gate
   scripts; it teaches the agent to add checks inside the user's project when a mistake repeats.
4. The vendors agree on where hard rules belong. Anthropic: "If something has to happen every time, make it a hook, a
   deny rule, or a managed setting" and "Keep the enforced set small"
   (https://code.claude.com/docs/en/best-practices). OpenAI: "Tests and linters work well for checks you can express
   deterministically … Keep formatting and other mechanical checks in CI"
   (https://developers.openai.com/blog/custom-code-review-rules-for-codex). GitHub: custom instructions "do not
   guarantee that generated content will comply with a policy"
   (https://docs.github.com/en/copilot/concepts/prompting/response-customization). In every case the hard check is
   the project's own tests, linters, CI and tool settings, not a framework's script.
5. The evidence says agents do cheat around tests (METR 2025, https://metr.org/blog/2025-06-05-recent-reward-hacking;
   ImpossibleBench, https://arxiv.org/abs/2510.20270), that self-review is weak and an outside reviewer helps
   (Anthropic, https://www.anthropic.com/engineering/harness-design-long-running-apps), and that long rule lists lower
   compliance (https://arxiv.org/abs/2602.11988). So the plan below keeps rules short, uses a reviewer that did not
   write the change, and asks a person to read evidence that git can confirm.

## The principle
- aidlc is instructions: skills, agents, templates, `AGENTS.md`. It ships no scripts and no CI workflows.
- A rule that must hold every time lives in the team's project: its tests, linters, type checks, CI, and its AI
  tool's settings. aidlc tells the agent to build and maintain those checks; the team owns them.
- When a mistake repeats, the agent adds a check to the team's project at the highest level that works (the design
  makes the mistake impossible; then a type; then a lint rule whose message names the fix; then a test; prose last),
  proves the check fails on the real past mistake, and adds a row to the "Rules and what enforces them" table in the
  team's `AGENTS.md`.
- A verdict of "done" counts only from someone who did not write the change: a reviewer agent in a fresh context, or
  a person. It names the commit it judged; a later change to the diff voids it.
- A person decides at each gate, from evidence that git can confirm, not from claims.
- aidlc depends on git and on no code-host feature. Words are host-neutral: "change request" (a pull or merge
  request), "the review tool", "the code owner", "the team's CI". A team that has branch protection or required
  checks may use them; aidlc never needs them.

## The checks, rule by rule

| Rule | Was enforced by | Now enforced by |
|---|---|---|
| No deleted test, no changed assertion (ADR 0019's central concern) | `check_slice.py` in CI | The `reviewer-tests` agent reads the test-file diff from an evidence file the session writes (`git diff <base> -- <test paths>`); the evidence table shows the changed test files and the test count before and after; the code owner reads both. The team may add its own CI check. |
| Edit only inside MAY CHANGE; MUST NOT untouched | `check_slice.py` | The `reviewer-compliance` agent compares `git diff --name-only <base>` (in the evidence file) with the bundle |
| No new suppression or skip without an exception | `check_slice.py` (12 syntaxes) | The team's linters' own rules (`skills/aidlc-onboard/references/suppression-rules.md`), plus the reviewer reading added `aidlc-exception` lines |
| No new dependency without asking | `check_slice.py` | The reviewer reads manifest changes in the evidence file; the person approves |
| Approved documents unchanged in a code change (ADR 0020) | `check_slice.py` | The reviewer reads `git diff <base> -- plans/<KEY>`; the code owner approves |
| Plan complete before approval | `check_plan.py` | The plan template's checklist; the tech lead approves |
| Recipe commit is mechanical (ADR 0012) | `check_recipe_commit.py` | The bundle's DONE WHEN: re-run the recipe on the parent commit and `git diff` against the commit; the reviewer reads the result |
| Run approved slices one by one | `run_slices.py` | The person starts one fresh session per slice; `aidlc-build` states the stops |
| Story status across repositories, drift, merge state | `story_status.py` | A release checklist row per repository, filled from git by the agent and confirmed by the person |
| Contract version raised; breaking change raises MAJOR | `check_contract_version.py` + workflows | The provider team runs `oasdiff breaking` and a version comparison in its own CI; `designing-apis` gives the commands |
| Consumer copy matches the pinned version | `check_contract_pin.py` | `sha256sum -c` and `git ls-remote --tags` in the consumer's release checklist |
| Independent AI review of a change request | `ai-review.yml` (GitHub, Claude-only) | The `reviewer-*` agents run in a fresh session; the team may add any AI review its host offers |
| Secrets never read; push asks first | starter `.claude/settings.json` | Kept as an optional example settings file a team copies; not a gate of aidlc |

## What stays, what goes, what is added
- Stays: every skill, agent, template and route; ADRs 0020 to 0023 as process rules; the evals; aidlc's own
  validator and the tests of skills and documents.
- Goes: `starter/repo/scripts/`, `starter/workspace/scripts/`, `starter/repo/.github/workflows/`, the Stop hook and
  the deny rules that protect them, and the tests of that code; the GitHub-only wording.
- Added: the non-author verdict tied to a commit; the evidence file the reviewers read; the "encode lessons in
  structure" step in `aidlc-feedback`; host-neutral wording; ADR 0024 superseding ADR 0019.

## Out of scope (later plans)
- Adapters for GitHub Copilot and OpenAI Codex (generated agent files, `.agents/skills`); the skills' `metadata` list
  values. This plan only removes what blocks them and corrects the portability claim in `plugin.json`.
- Running the behaviour evals as a baseline (they need a working eval environment).

## Risks and what we accept
- A deleted test or weakened assertion is now caught by a reviewer agent and a person, not by code. A reviewer agent
  can be lenient. We accept this: the code only blocked with paid code-host features, and teams that want a hard
  block add one to their own CI.
- A multi-repository release relies on a checklist again (the risk that motivated `story_status.py`, P7).
