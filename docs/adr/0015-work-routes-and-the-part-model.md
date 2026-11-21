# 0015 · Work routes and the part model

Status: Accepted (2026-11-08). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-08-aidlc-4-routes-and-roadmap.md`

Amended by ADR 0024 (2026-11-20): see the last section.
Amended by ADR 0025 (proposed, 2026-11-21): one pull request per independent slice, when the plan marks its slices
independent; see ADR 0025. ADR 0025 was accepted on 2026-11-21.
Amended by ADR 0026 (proposed, 2026-11-21): route S, for the standard changes a team lists in its `AGENTS.md`; see ADR
0026.

## Context
The stages worked one at a time but did not fit together end to end. Stages disagreed about the pull request (one per
slice or one per repository part) and about whether design always runs. Five stages produced their output only in the
reply, so the next session could not read it. Story documents on the code branch tripped the build's scope check.
Tracking was written once and never updated. An incident needed a story that only existed after the incident. A
contract change found in one part reached no other part. Nothing said what happens to merged code when a criterion
changes. Every defect took six stages. Two agents, `implementer` and `planner`, let Claude delegate around the gates.

## Decision
- `aidlc-start` chooses one route: F1 (a feature in one repository), F2 (a feature across several), C (a change request
  while the story is in progress), D1 (a defect on the fast path), D2 (a defect on the full route), or I (an incident,
  which starts at the alert). Route G, a new system, follows in aidlc 4.1.
- Several repositories: the workspace root holds the story and tracks every part. One repository: everything happens
  in that repository, and nothing is written at the root.
- One branch and one pull request per repository part, holding all of its slices. The story's documents travel on that
  branch, exempt from the scope check; each approval before code is recorded on the work item with the document's
  version and commit.
- Design always runs; only discover is optional. Every stage writes its output to a file.
- Each stage marks its row in the index. At the workspace root, `story_status.py` derives every part's status from the
  repositories' own indexes; no session writes into another repository.
- Contracts carry a version. Only `aidlc-design`, in amendment mode, changes one, with its consumers' approval. Each
  bundle pins the spec, plan and contract versions it builds on; a stale pin marks the part "re-plan".
- A criterion amended after code exists revises each part by its state. An assertion listed under AMENDED ASSERTIONS,
  citing the approved amendment, is the second exception to "never change an existing assertion", beside ADR 0012's
  recipe commit.
- A Tier 1 defect with a reproduction and written expected behaviour takes the fast path: `aidlc-plan` in brief mode
  writes `fix.md`, the engineer confirms it, and the code owner approves brief and fix together.
- Operate and feedback need no story; they write to `incidents/<ID>/` and `feedback/<YYYY-MM-DD>-<topic>/`.
- The `implementer` and `planner` agents are removed. Delegated building returns as a mode of `aidlc-build`.

## Consequences
- aidlc 4.0.0 is a breaking release. In-flight 3.x stories finish on 3.x, or re-enter through `aidlc-start`.
- The pointer index that ADR 0009 kept at the workspace root for a one-repository story is gone.
- `scripts/test_routes.py` and `scripts/test_story_status.py` hold the checks.
- The enforcement layer (hooks and CI scripts) stays parked; these rules hold through the stages' text, the compliance
  reviewer and people.

## Amended by ADR 0024 (2026-11-20)
- `story_status.py` is removed. The AI at the workspace root derives `status.md` from each part's index on its
  repository's default branch, read with git. At release, `aidlc-release` fills one checklist row per repository,
  and a person confirms each row.
- `scripts/test_story_status.py` is removed with the script.
