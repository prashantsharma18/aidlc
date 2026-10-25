# How work runs: the workspace and its repositories

One rule: **story things at the workspace root, code things in the repository that owns the code.**

A *workspace* is a folder (its own small git repository) that holds the repositories a product area needs, plus
`WORKSPACE.md`. A *story* is one tracker item; it is never split into more items. When it changes several
repositories, each repository's share is a *part*, a row in the story's coordination plan.

## Start: `aidlc-start`

Every piece of work starts with `aidlc-start`, at the workspace root (or in a lone repository). It decides two things.

**The kind of work**

| Kind | What it needs | Route |
|---|---|---|
| New feature | No story: an interview, then a story the product owner creates. A story: a clear problem, outcome and acceptance criteria | intent (if needed), specify, discover and design when the tier or a contract asks, then each part, then release |
| Defect | How to reproduce it, expected and actual behaviour, evidence (missing: ask and stop) | intent in defect mode, a short plan, build with the reproducing test first, verify, review, release |
| Change request | The original story and its documents (not found: ask and stop) | In progress: specify in amendment mode; the affected parts are marked "re-plan". Released: new work with its own key, whose criteria include "the original's criteria still hold" |
| Incident follow-up | The incident record | As a defect, with the incident as the evidence |

**The scope.** One explorer per repository answers "would this work change you?". One repository: everything runs there,
documents in its `plans/<KEY>/`. Several, or unsure: the workspace flow.

## The two levels

| Level | Runs in | Skills | Documents |
|---|---|---|---|
| Story (once) | the workspace root | intent, specify, discover, design, release; operate and feedback when needed | `stories/<KEY>/` in the workspace repository |
| Part (once per repository) | inside that repository | plan, build, verify, review | `plans/<KEY>/` in that repository, on branch `feat/<KEY>-<part>` |

```text
Jira story SHIP-1
   │
workspace root ── aidlc-start ─► specify ─► discover ─► design + coordination plan (stories/SHIP-1/)
   │                                                     │ one row per part
   ├── shipments-api ── plan ─► build ─► verify ─► review ─► PR "[SHIP-1] part 1 of 3"
   ├── notifications ── plan ─► build ─► verify ─► review ─► PR "[SHIP-1] part 2 of 3"
   └── customer-portal ─ plan ─► build ─► verify ─► review ─► PR "[SHIP-1] part 3 of 3"
   │
workspace root ── release (flags on in the plan's order) ─► the story is Done
```

## How work breaks down and is tracked

| Level | Defined by | Tracked by |
|---|---|---|
| Story | the tracker | its status; its development panel lists every branch and PR named with its key |
| Part | a row of `stories/<KEY>/coordination-plan.md` | the row's status: waiting, planned, building, in review, merged, released, re-plan |
| Slice | a task bundle `plans/<KEY>/bundle-<slice>.md` from `aidlc-plan` | its approval in the pull request; its commits |
| Step | the numbered checklist `aidlc-build` proposes | one commit per green step |

## The feedback loops

| Loop | Speed | How it works | What stops a runaway |
|---|---|---|---|
| Build | minutes | `aidlc-build`: a failing test, the code, the repository's tests; on a failure, name the cause and make one targeted fix | Three attempts at the same failure, then stop and report |
| Pull request | hours | CI runs; `aidlc-verify` maps every criterion to its test; a red run goes back to `aidlc-build` | CI stays red; nothing merges |
| Review | hours to days | `aidlc-review` sends the change to three reviewer agents; the code owner decides each finding; fixes go back through `aidlc-build` | The code owner's approval; branch protection |
| Production | days | `aidlc-operate`, then `aidlc-feedback` turns each lesson into a test, a rule, a skill change or an eval case | People decide containment and where each lesson goes |

## Who decides

Agents draft; people decide. The product owner owns the story and its criteria; the tech lead approves designs and
plans; each repository's code owner approves its pull request; a release approver turns flags on. AI review is evidence
for the reviewer, never the approval.
