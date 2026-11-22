# 0030 · The agent drafts the queue, and a lane runs to the next decision

Status: Proposed (2026-11-22). · Decider: Prashant Sharma (framework owner)
Design: `docs/design/2026-11-22-parallel-work-like-pstack.md` · Plan: `docs/plans/2026-11-22-plan-28-parallel-like-pstack.md` ·
Amends: ADR 0025 (a person writes `QUEUE.md`; a workflow skill writes no document a person approves; lane mode)

## Context
ADR 0025 made a person write `QUEUE.md`, a row for each independent slice included, copied from the plan's `DEPENDS ON`
lines that the tech lead had already approved. A lane ran one stage and ended, so a person or the coordinator started
every next stage, and a hand-started lane took two messages. Nothing watched a lane once it started, or read CI after
a push. Every sub-agent lane read the whole of `parallel-lanes`, coordinator text included. pstack (`cursor/plugins`,
folder `pstack`, MIT, Lauren Tan) schedules from the plan's dependency graph, gives each pull request one owner that
carries it to merge-ready, and runs a root layer that judges every agent by its side effects
(`skills/poteto-mode/playbooks/feature.md`, `multi-phase-plan.md`, `autopilot-full.md`, `autopilot-stack.md`,
`babysit.md`, and `skills/poteto-mode/worker.md`).

## Decision
- The plan's ORDER field is followed by pstack's throughput checkpoint: BLOCKING, APART, SHARED and SPLIT, none
  dropped. A line that does not apply reads `n/a: <reason>`; SPLIT always says why the slices are split as they are,
  or why they stay on one branch. The tech lead reads it with the plan, as today; no approval is added.
- The coordinator schedules from the approved plan: a queue row whose plan marks its slices independent stands for
  each slice the plan gave its own branch, with the `DEPENDS ON` its bundle names. A queue that lists slice rows still
  works.
- When a person asks, the coordinator drafts `QUEUE.md` rows on its own branch `docs/queue-<YYYY-MM-DD>`, and pushes
  it under ADR 0028's leave. The person opens and merges its pull request; that merge is the confirmation. The
  coordinator never writes `QUEUE.md` on the default branch, and a lane never writes it. This amends ADR 0025's "a
  person writes `QUEUE.md`" and its "writes no document a person approves", for the queue only.
- A lane is its own workflow skill, `lane-run`: it claims one row's worktree, runs `story-run` there until the next
  person's decision, and releases. A person starts a lane by hand with one message (`lane-run SHIP-12`); that start is
  the go-ahead up to the next person's decision, as ADR 0028 says for `story-run`. A sub-agent lane keeps ADR 0025's
  limits: only a row whose plan a person approved, only a delegate MODE for a build, and only build, verify and review.
  `parallel-lanes` keeps the coordinator, and its `lane` argument sends a session to `lane-run`.
- The coordinator runs a watch pass first at every start and, where the AI tool can wake a session on a timer, every
  WATCH EVERY. It judges a lane by what the lane left in git (its worktree's last commit, its uncommitted files, its
  row's state), never by the lane's own report. A lane with no activity past STUCK AFTER that is not waiting on a
  person is stuck. Only a lane this session started, with a clean worktree, that the tool can stop, is replaced by a
  fresh lane; every other stuck lane is shown to the person, and no lane's files are committed for it.
- The watch pass reads each open pull request's CI where it can. A finished run ends the row's wait, and the lane's
  `story-run` runs verify: a red run the change caused returns the slice to build (ADR 0028), and after two fixes for
  the same check the row stops for a person. A flake and a check red on the base too keep `aidlc-verify`'s rules. A
  conflict or a stale base is reported, never rebased onto the default branch or force-pushed by the AI; a stacked
  slice's `--onto` move after its parent merges keeps its rules, and its lease push asks the person (ADR 0028). The AI
  never merges.
- Every brief the coordinator or a lane writes for a sub-agent opens with
  `Read <absolute path>/skills/lane-run/references/worker.md before anything else.`, a short preamble adapted from
  pstack's `worker.md`. A stage run outside a lane is unchanged: the agent role files already hold the rules a
  reviewer needs.

## Consequences
- A person writes no slice rows, and starts no stage between two decisions inside a lane; a hand-started lane is one
  message.
- More of the AI's work runs between two people's decisions without a person watching; the watch pass, the two-fix
  stop and every stage's gate are the limits.
- A long step that commits nothing for STUCK AFTER looks stuck: the team raises STUCK AFTER. A team that wants no
  timer runs the watch pass by starting the coordinator.
- The queue has two writers: a person, and the coordinator on its own branch. Lanes still read it only on the default
  branch, so a draft counts only after a person's merge.
- Lane mode's text moves word for word to `lane-run`; ADR 0025's and Plan 23's documents keep their history.
