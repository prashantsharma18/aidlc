# 0026 · Decisions by tier, and standard changes

Status: Proposed (2026-11-21). Accepted (2026-11-21; confirmed by the framework owner in the session). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-21-fewer-approvals.md` · Plan: `docs/plans/2026-11-21-plan-24-fewer-approvals.md` ·
Amends: ADR 0012 (the recipe pause for a listed recipe class), ADR 0015 (route S), ADR 0020 (the pull request
approval is the record)
Amended by ADR 0027 (proposed, 2026-11-21): the Ready row also shows the route, which the tech lead owns, and the code
owner reads the AI's decision log at Merge; see ADR 0027.
Amended by ADR 0028 (proposed, 2026-11-22): the AI may push its own feature branch when the team gives it a
credential that cannot push the default branch; see ADR 0028.

## Context
People's decisions are the bottleneck. With parallel lanes (ADR 0025), more lanes make more waits on people. An
inventory of every person stop (2026-11-21) counted 7 for an F0 story at Tier 1, 13 for an F1 story at Tier 1, and
about 21 for an F1 story at Tier 3, plus one per slice. Several were the same decision taken twice: the spec, design
and plan approved on the tracker and again as the pull request that merges them first (ADR 0020); the code owner's
approval in both the verify and the review gates; the plan's restatement and then the build's; the engineer's diff
review before the push and then their decision on each finding of the same diff; the release approval in two
records; and the intent's acceptance next to the spec's approval. On F0 and D1, no person agreed the Tier 1 rating.

## Decision
- One decisions-by-tier table, in the tiers file every stage reads (the six identical `assets/tiers.md` copies, and
  `docs/operating-model/tiers-table.md`), says where a person stops. A stage that is not a decision for its tier
  still runs and still writes its document; it states what it did, in the document and in the session, and goes on.
  A person who disagrees says so, and the stage revises. Each stage whose Gate holds such a decision says so in one
  identical line.
- Tier 1: two blocking decisions, Ready and Merge, and Release only when users see the change. Tier 2: Ready, Design + plan, Merge, and Release only when users
  see the change. Tier 3: the same four, Release always, plus the specialists and the hands-on restatement per slice.
  A change behind a flag that is still off needs no release decision until the flag goes on; turning a flag on is
  the release.
- Ready is the work, its acceptance criteria and its tier. The intent's acceptance and the spec's approval are both
  inside it. On F0, D1 and route S, the engineer who confirms the brief confirms its tier. A change of tier, up or
  down, is a Ready decision at every tier.
- No decision is asked twice. Where a pull request merges an approved document first, the pull request approval is
  the record: the AI writes the work item's entry from it, with how it was confirmed, and asks before posting (ADR
  0023). When the AI cannot read the review tool, the decider confirms in the session. The code owner approves once,
  at Merge. Restatements are stated, not waited on, except at Tier 3 (hands-on, per slice) and at the checkpoints a
  bundle's MODE puts. Once the review runs, deciding the findings is the diff review: there is no separate review of
  the diff before the push. The readiness record's Decision cites the change-management record. At Tier 1, design
  "none needed" is stated in the plan, and the code owner sees it at Merge.
- Kept at every tier, unchanged: a new dependency, a quality-bar exception and an assertion change (the criterion's
  owner decides); checkpoints where the bundle's MODE puts them; the person pushes; every decision in operate,
  feedback and onboard, and every `parallel-lanes` person action; the AI never approves or merges (ADR 0023). A plan
  that marks its slices independent still merges first at every tier (ADR 0025), so at Tier 1 it is the one plan
  its tech lead approves.
- Standard changes. A "Standard changes" section in the team's `AGENTS.md` lists classes of work, each with what
  qualifies, its limits and the evidence it needs. The tech lead approves the list once, in a pull request, as any
  rule. `aidlc-onboard` proposes three: a recipe commit with an approved tool and version; a dependency patch or
  minor bump within the team's policy (no new dependency, never a major version); and a D1 defect fix that stays
  Tier 1.
- Route S. `aidlc-start` checks the work against the list and its limits. A match takes route S: `aidlc-start`
  writes the standard brief, `plans/<KEY>/standard.md`, which names the class and copies its limits, and the
  engineer confirms it with its tier; then build, verify and review. It skips intent, spec, design and plan
  approval. A defect that matches the D1-fix class takes route D1, whose fix brief already carries that class's
  limits and is confirmed the same way. If the work goes past a limit (a major version, a new dependency, a Tier 2
  risk), the AI stops and the work takes its normal route. It never stretches a class.
- What still holds on route S: the code owner reviews and merges the pull request after a non-author PASS. The
  evidence file names the class and shows its limits held. For a listed recipe class, the build's separate
  recipe-review pause is lifted: the evidence file's Recipe commits section shows the re-run, and the code owner reads
  it at Merge.
- This amends ADR 0020: at Tier 2 and 3 the spec merges first in its own pull request, and the design and the plan
  merge first together, in one pull request; each pull request approval is the record. It amends ADR 0015 with route
  S, and ADR 0012's fourth condition: for a recipe class listed in `AGENTS.md`, the person's review of the recipe
  commit is the code owner's, at Merge.
- aidlc still ships no code and needs no code-host feature (ADR 0024).

## Consequences
- At Tier 1 no one approves the plan before the build, so a wrong plan shows at Merge. The stated restatement and
  plan, which the person may correct at any time, limit it; Tier 1 is small and reversible by definition.
- A standard class can be stretched. The limits are written in `AGENTS.md`, the evidence file shows them, the code
  owner checks them at Merge, and the AI stops when a limit is passed.
- A sub-agent lane still builds only a row whose plan a person approved (a confirmed brief counts, ADR 0025). A Tier
  1 row on a full route, whose plan no person approves, is built in a lane a person starts.
- `scripts/test_fewer_approvals.py` holds the structure checks; four behaviour cases under `evals/` hold the
  behaviour, run when a key or token is available. The existing tests that pinned the old wording change only as the
  plan's "Needs the owner's decision" lists.
