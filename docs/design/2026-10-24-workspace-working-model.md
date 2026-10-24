# Design: the workspace working model (Plan 6b)

Status: draft for review (2026-10-24) · Owner: Prashant Sharma (framework owner)
Builds on: Plan 6 (the shipment-tracking demo), its findings, and the user's decisions of 2026-10-24.

## Why

The SHIP-1 demo worked, but people could not tell where to start or where each step runs. Three causes:

1. The story's shared documents were kept in one team's repository (`shipments-api`), a "lead repository" someone
   had to guess.
2. Every skill writes to `plans/<KEY>/` in whatever folder it runs in, so a story spread across repositories had no
   single home.
3. Nothing told a person which skill to run first, or whether a skill was being run in the right place.

## Decisions already made (user, 2026-10-24)

| Decision | Choice |
|---|---|
| The rule | Story things at the workspace root; code things in the repository that owns the code |
| Where a story that may span repositories starts | Always at the workspace root; a one-repository story starts in that repository |
| Home of a multi-repository story's documents | The workspace repository, `stories/<KEY>/`; the Jira story links to it |
| An existing user story | Stays one story. It is never split into more tracker issues |
| Tracking the parts | One row per repository part in the coordination plan (the "job sheet"); every branch and pull request carries the story key |
| The harness | Unchanged: guard, sandbox, permissions, protected paths, scope, retry limit, `aidlc check`, trusted CI |

## The model

### Two ways in, one router

```text
A new requirement (no story yet)          An existing user story (SHIP-1 in Jira)
            │                                            │
            └──────────── /aidlc:aidlc-start ────────────┘
                     (run at the workspace root)
                               │
          reads the story or interviews for the requirement,
          sends an explorer into each repository, and decides:
                               │
         ┌─────────────────────┴──────────────────────┐
   one repository                              several repositories (or unsure)
   "open <repo>; run the stages there"         "stay at the root; stories/<KEY>/ is the home"
   documents: <repo>/plans/<KEY>/              documents: stories/<KEY>/ + each repo's plans/<KEY>/
```

`aidlc-start` is a new, small skill: the single answer to "where do I start?". It never writes code.

- **No story yet:** it runs the intent interview (one question at a time) and drafts the story's title, description
  and acceptance criteria. The product owner creates the story in Jira (or approves the agent creating it, which the
  policy already makes an "ask"). Then `aidlc-start <KEY>` routes it.
- **The story exists:** it reads the story, checks it (a clear problem, an observable outcome, testable acceptance
  criteria) and lists questions for the product owner. It does not redraft a story that is already good.
- **Routing:** an explorer per repository answers "would this story change you?". One repository: route there.
  Several, or unsure: route to the workspace flow. It drafts the story's index, `stories/<KEY>/README.md`.

### The two levels

| Level | Runs in | Skills | Documents |
|---|---|---|---|
| Story (once) | the workspace root (read-only for agents) | start, intent, specify, discover, design, release, operate, feedback | `stories/<KEY>/` in the workspace repository |
| Part (once per repository) | inside that repository | plan, build-slice, verify, review | `plans/<KEY>/` in that repository, on branch `feat/<KEY>-<part>` |

A one-repository story keeps today's behaviour exactly: everything runs in that repository and lives in its
`plans/<KEY>/`.

### The story's home

```text
stories/SHIP-1/                     (workspace repository)
  README.md               index: source (Jira link), route, stage checklist with where each runs and its status
  intent.md               only when the story was new, or the intent needed rewriting
  spec.md                 criteria AC1..n, each naming the repository that proves it
  evidence-pack.md        from discover
  design-note.md          from design (ADRs live in the repository each one governs)
  coordination-plan.md    the job sheet: one row per part, with status
  release-runbook.md, readiness.md, change-record.md      from release
  incident-NN.md, feedback.md                             only when needed
```

Agents at the root still write nothing. Each skill gives its draft in the reply and a person saves it, as in every
repository today.

### The job sheet

The coordination plan template's `SLICES` line becomes a `PARTS` table:

```text
PARTS      #  Repository       Owner      Change                        Flag                  Waits for      Undo      Status
           1  shipments-api    Logistics  contract 1.7; send window      eta-in-api            -              flag off  merged
           2  notifications    Messaging  window in the email           eta-in-email          api-v1.7.0     flag off  building
           3  customer-portal  Web        window on the page            show-delivery-window  api-v1.7.0     flag off  in review
TRACKING   branch feat/<KEY>-<part> in each repository; pull request title "[<KEY>] part n of m: …"
```

Status values: waiting, planned, building, in review, merged, released.

### Skills know where they belong

Each stage skill states its level and checks where it was started, using markers that already exist: a
`WORKSPACE.md` means the workspace root; a `.aidlc/config.yaml` means a repository.

- A story-level skill started inside a repository, for a story that has a `stories/<KEY>/` folder, says "this stage
  belongs at the workspace root" and stops.
- A part-level skill started at the root says which repository to open and stops.
- Part-level skills read the job sheet from the workspace (`../stories/<KEY>/coordination-plan.md`, read-only) and use
  the branch and pull-request naming above.

### Seeing progress

`aidlc story status <KEY>`, run at the workspace root, reads the job sheet and, for each part's repository, the local
git state: the story branch, its approved bundles (`plans/approved-bundles.txt` on `main`), its last commit and any
release tag. It prints one line per part. Read-only, standard library only, fails closed on a missing or malformed job
sheet. The Jira story's development panel shows the pull requests as well.

### The workspace itself

`WORKSPACE.md` describes the workspace, not one story: its repositories, owners, the rules, and where stories live.
`aidlc workspace init` therefore takes the workspace's name and purpose instead of a story key, creates
`stories/README.md`, and requires the folder to be a git repository (the workspace repository).

## Out of scope (separate decisions)

- AI review in the repositories' CI template (a small, additive harness change; needs an API key per repository or
  organisation).
- F15, anchoring the rendered protected-path rules (narrows a deny rule).
- Lightening the stages by size (the research's "issue in, PR out" for small work); the tier rules already allow a
  "none needed" design and a short plan.

## Success criteria

- One command answers "where do I start?" for both a new requirement and an existing story.
- Running a stage skill in the wrong place stops with the right place named.
- A multi-repository story's documents all live in `stories/<KEY>/`; no story document lives in another team's repository.
- `aidlc story status SHIP-1` shows every part on one screen.
- SHIP-1 is moved to the new layout and the clean-harness probe still passes.
