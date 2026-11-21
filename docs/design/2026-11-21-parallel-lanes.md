# Parallel lanes: several pieces of work at once, with instructions only

Date: 2026-11-21 · Owner: framework owner (Prashant Sharma) · Status: approved by the framework owner in the session,
2026-11-21; to be recorded in ADR 0025 · Change list: item D1 (one autonomous lane), item D2 (slices as a dependency graph), decision D7 (one
session writes one repository), decision D1 (local git worktrees first).

## For the reviewer
- Who decides: the framework owner, in this design's review and in ADR 0025.
- Tier and main risk: a framework change. The main risk is two lanes changing the same thing at once, or a lane
  running past a person's decision. The lock, the clash rules and the release-at-every-gate rule below answer both.
- What changed: aidlc gains a third kind of skill, **workflow**, and its first skill, `parallel-lanes`, with a
  coordinator mode and a lane mode, and one template, `QUEUE.md`. Independent slices become sibling pull requests. aidlc still ships no code and needs no code-host
  feature (ADR 0024).

## Why
The owner's goal: "get multiple things done in parallel whenever possible, and post completion it picks the next
work." Today one session works one item, and a person lines up the next one by hand. The first design for this
(change list section E) used a queue script, labels and CI dispatch; ADR 0024 dropped all of it. This design gets
the same result with git worktrees, a queue file a person keeps, and the AI tool's own way of starting sessions.

## Owner decisions (2026-11-21, in the session)
| Question | Decision |
|---|---|
| Which parallel work | All three, built in this order: independent items in one repository; one item's independent slices; one story's parts across repositories |
| Where the queue lives | A file in git, `QUEUE.md`, written by a person; the coordinator may draft rows for the person to confirm |
| How lanes start | One protocol either way: the coordinator starts lanes with the AI tool's own feature where there is one (in Claude Code, background sub-agents), or a person starts one session per lane |
| A lane at a person's decision | It records its state, commits, removes its worktree and ends; the slot frees; any free lane resumes the item later from its files |
| Fitting it into the skills | Approach A: one new skill; stage skills get one line each |
| What kind of skill | A new third kind, **workflow** (`metadata.kind: workflow`), kept apart from stage skills and practice skills |
| Its name | `parallel-lanes`, invoked as `/aidlc:parallel-lanes`; no `aidlc-` prefix, because it is not a stage |
| Branch names | aidlc's existing names (`<type>/<KEY>-<slug>`), written in each queue row; never an `aidlc/` prefix |
| Who starts a stage in a lane | The middle option, done pstack's way: every stage keeps `disable-model-invocation: true`, and so does `parallel-lanes`. A person starts intent, specify, design and plan. A person starts the coordinator once; after a row's plan is approved, its sub-agent lanes run build, verify and review by reading those stage skill files by path. No switch is removed. |
| Slices | Independent slices become sibling pull requests, stacked where one builds on another, only when the plan marks them independent |

## A third kind of skill: workflow
`parallel-lanes` is not a stage: it produces no delivery document and has no gate of its own; it stops wherever the
stage it runs stops. It is not a practice: it is not an engineering habit a stage loads, and it sits above the stages,
running several at once. So aidlc gets a third kind, kept apart from the other two:

| Kind | Name | Marked by | Required sections (the validator checks them) | What it is |
|---|---|---|---|---|
| Stage | `aidlc-<stage>` | the `aidlc-` prefix | When to use, Inputs, Steps, Produces, Gate, Stop if, Common excuses, Red flags, Rules | One step of delivery, ending at a person's decision |
| Practice | `<doing>-<thing>`, such as `writing-tests` | `metadata.kind: practice` | When to use, Steps, Checks, Stop if, Common excuses, Red flags, Rules | An engineering habit a stage loads |
| **Workflow** | **a noun phrase that does not start with an "-ing" word**, such as `parallel-lanes` | **`metadata.kind: workflow`** | **When to use, Inputs, Steps, Stop if, Common excuses, Red flags, Rules** | **How work runs across sessions: queueing, lanes, coordination** |
| Map | `using-aidlc` | `metadata.kind: map` | the open format only | The overview of the other kinds |

- The validator gains the workflow kind's sections and two naming checks: a workflow name never starts with `aidlc-`
  and never starts with an "-ing" word, so it cannot be mistaken for a stage or a practice.
- `using-aidlc` and the README list the four kinds separately.
- Folders stay flat (`skills/<name>/`), because the open skills format and Claude Code's plugin loader expect that.
- A workflow skill never approves, never merges and writes no document a person approves; its Rules say so.
- Later workflow skills join this kind, for example change list item D1, one autonomous lane.

## The pieces

| Piece | What it is | Written by |
|---|---|---|
| `QUEUE.md` | The order of ready work, on the default branch: in the repository, or in the home repository for a workspace | A person. The coordinator drafts rows; the person confirms and commits them. Lanes never write it. |
| The item's own files | Its index `plans/<KEY>/README.md`, plan, bundles and progress notes, on the item's branch, as today | The lane working on it |
| A lane | One AI session working one queue row in its own git worktree | Started by the coordinator or by a person |
| The coordinator | `parallel-lanes` in coordinator mode: reads the queue and each row's state, checks clashes, starts lanes, reports | Writes nothing but drafts for the person |

### `QUEUE.md`

```text
MAX LANES   3
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-12 | . | feat/SHIP-12-eta-limit | none |
| 2 | SHIP-12 slice 3 | . | feat/SHIP-12-eta-limit-s3 | SHIP-12 slice 2 |
| 3 | SHIP-15 part 1 | orders-api | feat/SHIP-15-orders-api | none |
| 4 | SHIP-15 part 2 | web-portal | feat/SHIP-15-web-portal | SHIP-15 part 1 |

- **MAX LANES** is the most lanes running at once. The default is 3, because people's review time is the real limit.
- **Row** is an item, a slice (`<KEY> slice <n>`) or a part (`<KEY> part <n>`).
- **Branch** is the row's branch, named by the existing rule (`<type>/<KEY>-<slug>`; `feat/<KEY>-<part>` across
  repositories), plus `-s<n>` for a slice. Writing it in the row makes it fixed: every lane claims the same name.
- **Depends on** is `none` or the rows that must be merged first. For parts it copies the coordination plan's order;
  for slices it copies the bundles' `DEPENDS ON` lines.
- A row leaves the queue when the person removes it, after its merged row reads done on the default branch.

## A row's state lives in its own files
The queue holds only the order. Whether a row is ready, waiting, stopped or done is read from the row's own files, in
the repository that owns them (ADR 0022: one owner per fact):

| State | Where it is read |
|---|---|
| waiting: `<decision> by <who>` | its stage row's Status in the index, or the progress note's STATUS (`paused: …` counts as waiting) |
| stopped: `<reason>` | the same places |
| done | the index's merged row, on the default branch (`git show origin/<default branch>:plans/<KEY>/README.md`) |
| ready | none of the above, and every row it depends on is done |

The index's Status column gains one value, `waiting: <decision> by <who>`, next to `to do`, `doing`, `done` and
`stopped: <reason>`. For a part, the index is the part's own `plans/<KEY>/README.md` in its own repository, on the
part's branch; the coordinator reads it with `git -C <repository> fetch` and
`git -C <repository> show <branch>:plans/<KEY>/README.md`. No lane writes to the home repository, and no state is
kept in two places.

A slice's state is its own progress note `plans/<KEY>/progress-<slice>.md` (STATUS) and its own row in the index. A
slice pull request edits only its own progress note, its own row and the evidence file, so sibling pull requests do
not collide in the story's documents.

## The lock: git worktrees
- Each lane works in `.worktrees/<folder>` inside the row's repository. The folder name is fixed by the row: `<KEY>`
  for an item or a part (`.worktrees/SHIP-12`), `<KEY>-s<n>` for a slice (`.worktrees/SHIP-12-s3`), and `<KEY>-p<n>`
  for a second part in the same repository. The `.worktrees/` folder is ignored through `.git/info/exclude`, so
  nothing is committed.
- **Claim.** The first claim of a row creates its branch: `git worktree add -b <branch> .worktrees/<folder>
  origin/<default branch>` (a stacked slice starts from the branch it depends on). Every later claim:
  `git worktree add .worktrees/<folder> <branch>`.
- **Why only one lane wins.** All worktrees of one repository share one `.git`, and git refuses to check out a
  branch that another worktree already has. If two lanes claim the same row at the same moment, git's own lock lets
  one through; the other's command fails, and it takes the next row.
- **After claiming,** the lane reads the row's state on the branch again. If it is waiting, stopped or done after
  all, the lane removes the worktree and takes the next row.
- **The limit of this lock, stated as a rule.** Lanes for one repository start from one clone on one machine:
  worktrees of different clones do not see each other. A person does not check out a queued branch in their own
  working copy while lanes may claim it.

## `parallel-lanes`, lane mode
1. Fetch, and read `QUEUE.md` on the default branch.
2. Take the first ready row that clashes with no running lane (see Clashes). With no ready row, report and end.
3. Claim it (the lock above). If the claim fails, go back to step 2 with the next row.
4. Run the row's next unfinished stage by its stage skill, exactly as that skill says, in this worktree. Stage
   gates, the evidence file, the non-author verdict and every Stop if hold unchanged. Commit after every step.
5. Release when any of these happens, then end:
   - a person's decision is needed (answers, plan approval, a pause confirmation, the pull request review): write
     `waiting: <decision> by <who>` in the row's stage row;
   - a Stop if fires: write `stopped: <reason>`;
   - the stage asks to push or to open the pull request: write `waiting: push and open the pull request by <who>`,
     unless the team's `AGENTS.md` lets a lane push its own branch.
   Release means: commit, `git worktree remove .worktrees/<folder>` (never `--force`), and report the row and its state.
6. Never write `QUEUE.md`, never write to another repository, never approve, never merge.

## `parallel-lanes`, coordinator mode
1. Fetch every repository the queue names, read `QUEUE.md` and each row's state.
2. List worktrees (`git worktree list` in each repository). A worktree with no running lane is shown to the person;
   it is removed only after the person confirms, because it may hold uncommitted work.
3. Start lanes up to MAX LANES minus the running ones, each told only its row. Which stage decides how:
   - **build, verify and review, on a row whose plan a person approved:** start the lane with the AI tool's own way of
     starting sessions where there is one (in Claude Code, a background sub-agent per lane). The lane's brief opens
     with `Read <absolute path>/skills/parallel-lanes/SKILL.md before anything else.` and names the row and the stage
     skill's absolute path (`<plugin root>/skills/aidlc-build/SKILL.md`), which the lane reads and follows in full;
   - **intent, specify, design and plan, or a tool with no such feature:** give the person the exact words to start
     the lane by hand in its worktree, naming the stage (for example `/aidlc:aidlc-plan SHIP-15`).
4. When a lane reports back, read its row's state and start the next ready row.
5. Report one table to the person: running, waiting on whom, stopped and why, next in line.
6. Draft new queue rows (from approved plans, or from the tracker it only reads) for the person to confirm. Never
   write `QUEUE.md`, never approve, never merge.

## How a person-started run reaches its lanes
Every stage skill keeps `disable-model-invocation: true`: the AI never starts a stage by itself in an ordinary chat.
`parallel-lanes` has the same switch. Starting the coordinator is a person's act, and it is the go-ahead for the run.
A sub-agent lane cannot start a skill with that switch, so it reads the skill's file by its absolute path and follows
it in full, as pstack's delegates do (`cursor/plugins`, `pstack/skills/poteto-mode/SKILL.md`: "The operator's rules live
in skills that only load from a slash command, so they reach another agent no other way"). The coordinator sends
sub-agent lanes only to build, verify and review, and only on a row whose plan a person approved (ADR 0023), because
those stages run between two people's decisions (the plan approval and the pull request review). Intent, specify,
design and plan need a person's answers and approval anyway, so a person starts them. Reading a file by path works in
every AI tool, so the same protocol serves Copilot and Codex once their adapters exist. aidlc borrows pstack's way of
passing instructions, not its autonomy: a lane still stops and frees its slot at every person's decision.

## Clashes: when a ready row is held back
| Clash | Rule |
|---|---|
| Order | A row waits until every row it depends on is done. |
| Same files | Only once building starts: if the row's approved bundle shares a MAY CHANGE path with a bundle another lane is building, the later row waits. When in doubt, it waits. Planning and specs run side by side. |
| Same contract | One open change per API contract: a second row that changes the same contract waits. |
| A shared fact changes | The lane's existing Stop if fires (`stopped: changes <fact>`); the person decides whether to open a change request. Nothing is opened automatically. |

A held-back row is skipped, not dropped; the next ready row that clashes with nothing starts.

## The three kinds of parallel work
1. **Independent items in one repository.** Rows are items. A lane runs each item's next stage and stops wherever a
   person is needed. Several items move at once.
2. **One item's independent slices.** The plan adds a `DEPENDS ON` line to each bundle (`none`, or the slices it
   builds on), and the tech lead approves it with the plan. Each slice whose `DEPENDS ON` is not the slice before it
   becomes its own row, branch and pull request; a slice that builds on another starts from that slice's branch, and
   its pull request stacks on it. A plan without `DEPENDS ON` lines works exactly as today: one branch, one pull
   request, slices as commits.
3. **One story across repositories.** Rows are parts, in the home repository's `QUEUE.md`, ordered as the
   coordination plan orders them. Each lane claims its part in that part's repository and writes only there (decision
   D7). Each repository's code owners review and merge, in dependency order. The release stage's Parts table checks
   every part before release, as today.

## A stacked slice after its parent merges
Slice 3 stacks on slice 2, and a person merges slice 2's pull request:
1. The lane that next claims slice 3 acts, only after the merge is checked in git (slice 2's merged row reads done on
   the default branch) or the person has confirmed it (ADR 0023).
2. It moves only slice 3's own commits onto the updated default branch:
   `git fetch` then `git rebase --onto origin/<default branch> <slice 2's last commit> <slice 3's branch>`. With
   `--onto` and slice 2's old tip, this works when the host squashed slice 2 into one commit.
3. It pushes with `git push --force-with-lease`, which fails rather than overwrite anything else, on the lane's own
   branch only, and asks first unless the team's `AGENTS.md` lets a lane push its own branch.
4. Slice 3's pull request now targets the default branch. Many hosts retarget it themselves when slice 2's branch is
   deleted; otherwise a person retargets it.
5. The verdict rule applies: if the rebase brought in other code from the default branch, the earlier PASS is void,
   and slice 3 is verified and reviewed again.
6. A rebase conflict stops the lane (`stopped: rebase conflict in <files>`) and frees its slot; a person decides. If
   the team forbids force-push (a rule in its `AGENTS.md`), the lane stops and asks; it never merges the default
   branch into slice 3 by itself.

## What changes in aidlc
| New | Changed |
|---|---|
| `skills/parallel-lanes/SKILL.md` (`metadata.kind: workflow`; coordinator and lane modes; the workflow sections) | Each stage skill: one identical line, "In a lane, release at your gate as `parallel-lanes` says." |
| `skills/parallel-lanes/assets/queue.md` (the `QUEUE.md` template) | Both `story-index.md` copies: the Status column's `waiting: <decision> by <who>` value |
| ADR 0025: the workflow kind of skill, lanes, the queue, the worktree lock, sibling slice pull requests (amends ADR 0015's one pull request per part) | `aidlc-plan`: the bundle's `DEPENDS ON` line; slice rows and branches when slices are independent |
| | `aidlc-build` and `aidlc-review`: one pull request per independent slice; a slice edits only its own row and note |
| `scripts/validate.py`: the workflow kind's sections and its two naming checks (aidlc's own tooling) | `using-aidlc` and the README: the four kinds of skill, and where `parallel-lanes` fits |
| | `AGENTS.md` Standards: the workflow kind and its sections |
| | `aidlc-onboard`: the `.worktrees/` line in `.git/info/exclude`, and the one-clone rule |

aidlc still ships no script and no workflow, and needs no code-host feature.

## How it is tested
- **Free structure tests:** the workflow kind's sections and naming checks in the validator; the skill's two modes; the template's fields; the one release line
  identical in every stage skill; the Status value in both index copies; no script or tool-specific command named.
- **Behaviour evals** (paid, run when a key or token is available):
  - a lane that finds its row's worktree already taken claims the next row instead;
  - a lane that reaches the plan approval writes `waiting:`, removes its worktree and does not go on;
  - the coordinator starts no more than MAX LANES and holds back a row whose MAY CHANGE overlaps a running bundle;
  - a stacked slice after its parent merged is rebased with `--onto`, not merged.

## Out of scope
- Lanes across machines or clones; a dispatcher in CI; automatic labels or tracker moves; automatic merges.
- Copilot and Codex adapters (change list step C): the protocol is plain git and files, so they can run it once their
  adapters exist.

## Risks
- **People's review is the bottleneck.** More lanes make more pull requests, not more decisions; MAX LANES guards it.
- **A coordinator's sub-agents end with its session.** Nothing is lost, because all state is in git; a new
  coordinator, or lanes started by hand, carry on.
- **Rate limits.** Each lane is a full session on the same account; lower MAX LANES when limits bite.
- **A lane misjudges a clash.** "When in doubt, it waits" is the rule, and two lanes that do collide meet as a merge
  conflict in review, which a person resolves.
