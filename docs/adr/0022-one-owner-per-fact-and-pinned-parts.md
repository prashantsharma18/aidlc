# 0022 · A story's facts have one owner; parts pin by version and commit

Status: Proposed (2026-11-20). · Decider: Prashant Sharma (framework owner)
Plan: `docs/plans/2026-11-20-plan-21-multirepo-foundations.md` · Change list: F1–F6, F9, F11, F13, F14; D5, D9 ·
Amends: ADR 0015 (where a story's documents live; how parts pin), ADR 0020 (Decision 2 across repositories)

## Context
A story across several repositories kept its shared documents at the workspace root and each part in its repository,
but nothing said which copy of a fact was the original. Child bundles cited `plans/SHIP-1/spec.md` after the spec
moved (P9). Part status came from rows people marked by hand, and the release check read whatever branch each clone
had checked out (P7). The contract was pinned by a code comment, and a tag was cut before review (P8). A child's CI
and AI review could not see the criteria, which lived in another repository (P10, P12).

## Decision
- Code that ships together goes in one repository. A workspace is for repositories that must stay separate:
  different owners, release cycles or runtimes.
- Each fact has one owner, and only the owner changes it. The home repository (the workspace root, under git) holds
  the story's index, intent, spec, design note, ADR drafts, contract draft, coordination plan, status, release records
  and incidents. Each part's repository holds its plan, bundles, criteria copy, progress notes, evidence, pull request
  description, review record, its own ADRs and its code. The provider holds the published contract.
- ADRs by scope. One that governs one repository moves to that repository's `docs/adr/`. One across repositories stays
  in the home repository's `docs/adr/`, and each affected repository gets a one-line ADR that links it at a commit.
  Drafts are named `<KEY>-adr-<n>.md`.
- A part pins the spec by version and by home commit: `spec v<n> @ <commit>`. Nothing under `stories/<KEY>/` is
  moved or renamed once a part pins it.
- Each part keeps a read-only copy of its own criteria, edge cases and non-goals in `plans/<KEY>/criteria.md`, under a
  SOURCE line naming the home repository, the spec's path and the commit. Its CI and its reviewers read the copy.
- `story_status.py` takes a part's merge state from its newest code pull request on GitHub when it can, else from the
  default branch's copy of the part index, and reports a hand-marked merged row that disagrees. It reports "re-plan"
  for a pin older than the story's spec, by version or by home commit, and reports a criteria copy that differs from
  the spec at its commit.
- A contract is a versioned artifact (the Spec Kit rule, D5). The provider owns the OpenAPI file its AGENTS.md names,
  and its default branch publishes each version as the tag `api-v<info.version>`. Its pull requests fail when the
  contract changed without a new version, or broke compatibility (oasdiff, D9) without a new MAJOR. Each consumer
  keeps a read-only copy with a SOURCE file (repository, tag, commit, path, sha256), checked offline in its CI, and
  moves it only to a named, published tag, in a planned slice.
- Decision 2 across repositories is the home design pull request, then each part's plan pull request.
- Tracker links are GitHub permalinks at a commit.
- The home repository's CODEOWNERS gives `stories/**` to the leads, and the runtime environment (compose files, flags)
  to its named owner. Its `.gitignore` is generated from the repository table in `WORKSPACE.md`.

## Consequences
- The merged row stays, marked by hand in the part's final commit (ADR 0015). The status command now checks it
  against the real merge state instead of trusting it.
- `git merge-base --is-ancestor` on the part's branch is not the merge signal: a branch with no commits of its own is
  an ancestor, and a squash or rebase merge never is. The default branch's copy of the part index holds for every merge
  method; the same check confirms that a pinned home commit is on the home repository's default branch.
- The home-commit and criteria checks run only when the workspace root is a git repository. A plain folder keeps
  today's version checks.
- A consumer's copy is a file in its own repository: its CI never needs the provider or the home repository.
- Not yet: a required story-gate status on child pull requests, the integration check before the last part merges,
  and GitHub App tokens per role (change list F7, F8, F10: phase 2b).
- Protecting `api-v*` tags needs a ruleset: a public repository on GitHub Free, or a paid plan. The ruleset
  restricts creation, updates and deletions, and only the identity the publish job pushes with bypasses it. Without
  it, anyone with write access can create a version that consumers will pin, from a commit that was never reviewed.
  The consumers' online pin check still reports a tag that moved.
