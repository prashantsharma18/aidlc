# 0025 · Parallel lanes: a workflow skill, a queue file and git worktrees

Status: Proposed (2026-11-21). Accepted (2026-11-21; confirmed by the framework owner in the session). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-21-parallel-lanes.md` · Plan: `docs/plans/2026-11-21-plan-23-parallel-lanes.md` ·
Amends: ADR 0015 (one branch and one pull request per repository part)

## Context
One session works one item, and a person lines up the next one by hand. The owner wants several pieces of work to
move at once, and the next one picked up when a lane finishes. The first design for this (the change list's section
E) used a queue script, tracker labels and a dispatcher in CI. ADR 0024 dropped all of it: aidlc ships no code and
needs no code-host feature. Git already holds a lock that fits: a branch is checked out in one worktree at a time.

## Decision
- aidlc gains a third kind of skill, workflow (`metadata.kind: workflow`), beside the stage and practice skills and
  the map. A workflow skill says how work runs across sessions. It keeps the sections When to use, Inputs, Steps,
  Stop if, Common excuses, Red flags and Rules. Its name is a noun phrase: never `aidlc-` (a stage), never an "-ing"
  word (a practice). It never approves, never merges and writes no document a person approves. The validator checks
  the sections and both naming rules.
- The first workflow skill is `parallel-lanes`, with a lane mode and a coordinator mode.
- Who starts a stage: every stage that has `disable-model-invocation: true` keeps it, and so does `parallel-lanes`;
  no switch is removed. Two stages have no such switch, `aidlc-onboard` and `aidlc-verify`, and may also start on
  their own, as `using-aidlc` says. A person starts intent, specify, design and plan, and starts the coordinator once;
  that start is the go-ahead for the run. The coordinator sends sub-agent lanes only to build, verify and review, and
  only on a row whose plan a person approved (ADR 0023), because those stages run between two people's decisions. It
  sends a build to a sub-agent only when the bundle's MODE is a delegate mode: a hands-on build needs the person to
  confirm the restatement in the session, so a person starts it. A sub-agent lane cannot start a skill with that
  switch, so its brief opens with
  `Read <absolute path>/skills/parallel-lanes/SKILL.md before anything else.` and names the row and the stage skill's
  absolute path, which the lane reads and follows in full. This is pstack's way (`cursor/plugins`,
  `pstack/skills/poteto-mode/SKILL.md`: "The operator's rules live in skills that only load from a slash command, so
  they reach another agent no other way"). aidlc borrows pstack's way of passing instructions, not its autonomy: a
  lane still stops and frees its slot at every person's decision. A person starts a lane by hand with two messages
  in one session: first lane mode with the row, which claims it, then the stage's own command, in the person's words.
- Sub-agents cannot start sub-agents. A sub-agent lane that reaches the reviewer passes (build step 9, review step 3)
  writes the evidence file, commits it, and releases with `waiting: reviewer passes at <commit>`. The coordinator, a
  top-level session, dispatches the reviewer agents with that evidence file and the worktree's path: for reviewer
  passes it claims a row's worktree and writes nothing in it. It then starts a lane for the row whose
  brief carries the reviewers' reports, quoted as data; that lane records the verdicts as the stage says and
  continues. A lane a person started runs the passes itself.
- `QUEUE.md`, on the default branch, holds the order of ready work and MAX LANES (default 3). A person writes it; the
  coordinator only drafts rows; lanes never write it. The coordinator writes nothing but drafts.
- A row's state lives in its own files, in the repository that owns them (ADR 0022): `waiting: <decision> by <who>`,
  `stopped: <reason>`, or done once its merged row reads done on the default branch. The index's Status gains the
  value `waiting: <decision> by <who>`. A lane resumes a waiting row when the decision it waits for can be checked
  where the stage says (a plan or design merged on the default branch; a pull request's approval or merge in the
  review tool or in git; the tracker), or, for a lane a person started, when the decider gives it in that session. The
  lane records it as the stage says (ADR 0023) and continues with the next step. A decision that is only a person's
  word is resumed by a lane the person starts by hand with that word: a lane the person started asks for it and keeps
  its worktree, and only a sub-agent lane releases when it cannot check the decision. The coordinator never relays a
  decision to a sub-agent.
- The lock is git worktrees. Each lane works in `.worktrees/<folder>`, a folder fixed by its row and ignored through
  `.git/info/exclude`. All worktrees of one clone share one `.git`, and git refuses to check out a branch that
  another worktree already has, so only one lane wins a row. Lanes for one repository start from one clone on one
  machine.
- A lane releases at every person's decision, at every stop, and before every push (unless the team's `AGENTS.md`
  lets a lane push its own branch): it records the state, commits, removes its worktree (never with `--force`) and
  ends. Its slot frees; any lane resumes the row later from its files. A lane writes a wait into the row of the next unfinished stage, never into a row already done; when the wait ends, that row reads `to do` again. So a
  stage's `done` is never overwritten, and no two writers share one cell. The push wait ends when `origin/<branch>`
  holds the branch's last commit and the pull request exists. After review's final commit, which marks the merged
  row, the lane writes nothing and reports `push, then merge, by <who>`, so a code host that dismisses stale
  approvals does not ask again.
  The nine stages that mark a row in the item's index say so in one identical line at their gate.
- A ready row is held back when it depends on a row not yet done, when its approved bundle shares a MAY CHANGE path
  with a bundle another lane is building, or when it changes a contract another open row changes.
- A plan may mark its slices independent with a `DEPENDS ON` line on every bundle (`none`, or the one slice it builds
  on). The first slice runs on the part's branch, and a slice that names the slice before it on that branch continues
  it. Every other slice gets its own row, branch (`<branch>-s<n>`) and pull request: sibling pull requests from the
  default branch, or a stacked pull request on the slice it names. Such a slice keeps its index and its pull
  request's documents in `plans/<KEY>/slice-<n>/`, and the plan merges on the default branch first (ADR 0020). A
  plan without `DEPENDS ON` lines works as before. This amends ADR 0015's "one branch and one pull request per
  repository part".
- A stacked slice may start once its parent's build is done, and merges after its parent. After the parent merges, it
  moves only its own commits with `git rebase --onto`, checks first that nobody else pushed to its branch, pushes with `--force-with-lease --force-if-includes` after asking (unless the
  team's `AGENTS.md` allows a lane to push its own branch), and is verified and reviewed again when the rebase brought
  in other code. A conflict stops the lane. It never merges the default branch into itself.
- aidlc still ships no script and no workflow, and needs no code-host feature.

## Consequences
- More lanes make more pull requests, not more decisions: people's review time is the limit, which MAX LANES guards.
- A coordinator's sub-agents end with its session; nothing is lost, because every state is in git.
- The lock holds only within one clone. Two clones, or a person checking out a queued branch by hand, can collide;
  the rule says so, and two lanes that do collide meet as a merge conflict in review.
- Reading a file by path works in every AI tool, so the same protocol serves Copilot and Codex once their adapters
  exist. A tool with no way to start sub-agents starts every lane by hand.
- `scripts/test_parallel_lanes.py` holds the structure checks; four behaviour cases under `evals/` hold the lanes'
  behaviour, run when a key or token is available.
