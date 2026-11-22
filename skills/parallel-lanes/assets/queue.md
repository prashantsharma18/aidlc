<!-- aidlc template: queue -->
# Queue

The order of ready work, read by the `parallel-lanes` skill. It counts only on the default branch: in the repository, or in the home repository for a workspace. The coordinator
drafts new rows on its own branch when a person asks, and the person's merge of that pull request confirms them
(ADR 0030); a person may also write the file, and lanes never write it. A row's state (waiting, stopped, done or ready) is read from the row's
own files, never kept here (ADR 0025).

```text
MAX LANES   3
```

```text
STUCK AFTER   60m
WATCH EVERY   30m
```

| Order | Row | Repository | Branch | Depends on |
|---|---|---|---|---|
| 1 | SHIP-12 | . | feat/SHIP-12-eta-limit | none |
| 2 | SHIP-12 slice 3 | . | feat/SHIP-12-eta-limit-s3 | SHIP-12 slice 2 |
| 3 | SHIP-15 part 1 | orders-api | feat/SHIP-15-orders-api | none |
| 4 | SHIP-15 part 2 | web-portal | feat/SHIP-15-web-portal | SHIP-15 part 1 |

The rows above are an example: replace them with your own.

- **MAX LANES** is the most lanes running at once. The default is 3, because people's review time is the real limit.
  Lower it when the AI tool's rate limits bite: each lane is a full session on the same account.
- **STUCK AFTER** is how long a lane may go with no new commit before the watch pass counts it stuck. The default
  is 60 minutes; raise it when a step can run longer without a commit.
- **WATCH EVERY** is how often the coordinator runs its watch pass, where your AI tool can wake it on a timer. The
  default is 30 minutes.
- **Row** is an item (`<KEY>`), a slice (`<KEY> slice <n>`) or a part (`<KEY> part <n>`).
- **Repository** is `.` for this repository, or the repository's folder as `WORKSPACE.md` lists it.
- **Branch** is the row's branch, named by the existing rule (`<type>/<KEY>-<slug>`; `feat/<KEY>-<part>` across
  repositories), plus `-s<n>` for a slice; a document row may name `docs/<KEY>-spec`, `docs/<KEY>-plan` and `docs/<KEY>-<part>-plan` as the BRANCH lines name them; never an `aidlc/` prefix. Written here, it is fixed: every lane claims the
  same name.
- **Depends on** is `none` or the rows that must be done first. For parts it copies the coordination plan's order;
  for slices it copies the bundles' `DEPENDS ON` lines. A plan's independent slices need no rows: the coordinator reads
  them from the plan (ADR 0030). A slice stacked on another slice may start once its parent's
  build is done; `parallel-lanes` says how.
- Each row's worktree folder follows from the row: `.worktrees/<KEY>` for an item or a part, `.worktrees/<KEY>-s<n>`
  for a slice, `.worktrees/<KEY>-p<n>` for a second part in the same repository, and `.worktrees/<KEY>-p<n>-s<m>` for
  a slice of that part on its own branch.
- A row leaves the queue when the person removes it, after its merged row reads done on the default branch.
