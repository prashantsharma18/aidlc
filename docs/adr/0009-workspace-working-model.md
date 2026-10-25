# 0009 · The workspace working model

Status: Accepted (2026-10-25). · Decider: Prashant Sharma (framework owner)

## Context
In the SHIP-1 demo nobody could tell where work starts or where each step runs. The story's shared documents sat in one
team's repository (a "lead repository" someone had to guess), and stories that already exist must not be split.

## Decision
- Story things at the workspace root, code things in the repository that owns the code.
- `aidlc-start` routes every piece of work by kind (new feature, defect, change request, incident follow-up) and by
  scope (one repository, or several; unsure counts as several).
- A multi-repository story's documents live in the workspace repository's `stories/<KEY>/`; each repository keeps its
  part's plan, bundles, evidence and review in `plans/<KEY>/`.
- The coordination plan is the job sheet: one row per repository part, with status. Every branch and pull request
  carries the story key. The story is never split into more tracker items.
- Every stage skill says where it runs and stops in the wrong place.

## Rejected
A lead repository (guesswork with many repositories); tracker sub-issues per part (the user's stories stay whole);
one agent session across all repositories (one session would bypass each repository's own rules); the tracker as the
home of the documents (not versioned or reviewed with code).
