# 0028 · story-run, the AI's push, and every hand-off defined

Status: Proposed (2026-11-22). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-22-connect-the-flow.md` · Plan: `docs/plans/2026-11-22-plan-27-connect-the-flow.md` ·
Research: `docs/research/2026-11-22-pstack-review/` · Amends: ADR 0026 (the kept rule "the person pushes"), ADR 0025
(a lane's push, and a person's start as the go-ahead)

## Context
aidlc is well connected inside a stage and disconnected between stages. At Tier 1 a person decides Ready and Merge,
and Release only when users see the change (a plan with independent slices is still approved), but a person types
about ten commands, and six stages end without saying what runs next. Several hand-offs are undefined: no stage names
the story's branch (G1), a document pull request has no push step (G2), an approval given in a pull request has no
writer once the document has merged (G3), most routes have no `merged` row (G4), and a red CI run or an accepted
review finding has no way back to build (G6). No stage says which tracker move fits now (G10, G11). The route table
is written in several places, which drift.

pstack (`cursor/plugins`, folder `pstack`, MIT, Lauren Tan) runs a task from one start through playbooks, and stops
only for a person's call. Its stops and its autonomy differ from aidlc's fixed decisions; the research lists each
conflict (report 2, section 5).

## Decision
- **`story-run`.** A workflow skill (ADR 0025's kind) that only a person starts, with a story's key. It reads the
  story's index, takes the first row that is not done, reads that stage's `SKILL.md` by path, with every reference
  whose condition holds, and follows it in full. Every gate of the stage holds as it is. When the stage marks its row
  done (a person's decision leaves it `waiting:`), it goes on to the next row. It stops wherever a stage stops, after
  it pushes a branch whose pull request is not open yet, and at Merge. Before a stop it writes the wait into the row
  the index's rule names, commits, and gives the stage's hand-off, so the next start, in this session or a new one,
  goes on from the index. It runs one slice at a time; slices at the same time are a later plan.
- **The start is the go-ahead.** Every stage keeps `disable-model-invocation: true`. A person's start of `story-run` is
  the go-ahead for the stages up to the next person's decision, as a person's start of a lane is (ADR 0025).
- **The AI's push.** The AI may push its own feature branch: the story's code branch, a slice's branch, or a document
  pull request's branch, as the index's BRANCH lines name them. It never force-pushes, never pushes the default branch
  or a tag, and never merges, approves, or opens or closes a pull request. It needs a credential the team gives it that
  can push feature branches and cannot push the default branch (the code host's own rules), and the team's `AGENTS.md`
  says so. Without both, the person pushes, as before, and `story-run` stops at the push. It pushes only a branch whose
  pull request is the next person's action (after build's last slice, or a document's pull request at G2) and
  review's final commit, never to pause (pstack's `pause-safely`: "No PR and no push unless you already had one
  out"). Moving a stacked slice with
  `git rebase --onto` needs a force-push, so it still asks the person (ADR 0025). The verdict rule is unchanged: a
  non-author verdict names its commit, and a later change outside `plans/<KEY>/` voids it. This amends ADR 0026's kept
  rule "The person pushes: the AI holds no push credential", which stays the rule for a team that gives no such
  credential.
- **Every hand-off defined.**
  - G1: `aidlc-start` writes BRANCH lines in the index. Every row runs on the code branch `<type>/<KEY>-<slug>`; at
    Tier 2 and 3, the spec travels first on `docs/<KEY>-spec` and the design with the plan on `docs/<KEY>-plan`, each
    merging before the next starts from the default branch (ADR 0020). Every stage reads its branch there.
  - G2: `aidlc-specify` at Tier 2 and 3, `aidlc-plan` when its plan merges first, and `aidlc-design` for the home
    design pull request of a story across several repositories end by writing the wait in their row, committing, and
    pushing their branch (or asking the person to), and stop: a person opens the pull request.
  - G3: a document that merges first is not edited after its approval. The story's index holds the record: the next
    start that finds the pull request approved and merged (the approval checked in the review tool or given by the
    decider in the session, the merge checked with git) first makes the next row's branch, then marks the document's
    row `done: approved in pull request <n> by <who>, <how it was confirmed>` there (ADR 0023). Approved but not merged
    is a stop for the person's merge. The document's approval slot names its pull request.
  - One rule for a wait: a document's decision (Ready, Design + plan, a brief's confirmation) waits in that
    document's own row, in place of done, and ends with the row's record; every other wait goes in the row of the next
    unfinished stage, as a lane writes it.
  - G4: `aidlc-start` writes a `merged` row on every route.
  - G6: a red CI run the change caused (it passes on the base and fails again after one fresh run), or a high or
    medium review finding the engineer accepts, returns the work to build in the same slice: the build row reads
    `to do: fix <what>`, the verify and review rows `to do`, the stage that found it ends there, and build, verify and
    review run again.
  - G10, G11: every stage that marks a row ends with a short hand-off: what it did, the next row and where it runs,
    who it waits on, and the tracker move to suggest. Posting to the tracker asks first (ADR 0023).
- **One route table.** The table in `using-aidlc` is the one source of which stages each route runs.
  `docs/operating-model/routes.md`, `lifecycle.md`, `aidlc-start` and the README point to it, and a test checks that
  every listing agrees.
- **Playbooks.** For one kind of work, a playbook says what to do, in what order, which practices the bundle names and
  what proof that kind needs. Eight are adapted from pstack's, in `skills/story-run/references/`, with pstack's MIT
  notice in `skills/NOTICE`. `aidlc-plan` writes a `PLAYBOOK` line in each task bundle; build and verify read the
  playbook it names, whoever runs them. A playbook, like a stage's reference, never holds or lifts a gate.
- **Kept.** Every decision in the tiers file's decisions table (ADR 0026, ADR 0027). A person opens every pull request
  and merges; the AI never approves or merges (ADR 0023). aidlc ships instructions only and needs no code-host feature
  (ADR 0024); `story-run` names a tool's own features only as "where your AI tool has one".

## Consequences
- A Tier 1 story needs a start for each person's decision, not one per stage.
- The push credential is the main risk. The code host's rules keep it off the default branch; without such a
  credential, nothing changes.
- A long session can fill up. Every stop writes the index, so the next start can be a fresh session.
- `scripts/test_connect_flow.py` holds the structure checks, and `scripts/validate.py` checks that a playbook holds no
  gate section. Behaviour cases under `evals/` are written for `story-run`; they run when an API key or token is
  available. The existing tests that pinned the old wording change only as the plan's "Needs the owner's decision"
  lists.
