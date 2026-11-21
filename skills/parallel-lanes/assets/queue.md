<!-- aidlc template: queue -->
# Queue

The order of ready work, read by the `parallel-lanes` skill. A person writes this file and commits it on the default
branch: in the repository, or in the home repository for a workspace. The coordinator only drafts rows for that
person to confirm, and lanes never write it. A row's state (waiting, stopped, done or ready) is read from the row's
own files, never kept here (ADR 0025).

```text
MAX LANES   3
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
- **Row** is an item (`<KEY>`), a slice (`<KEY> slice <n>`) or a part (`<KEY> part <n>`).
- **Repository** is `.` for this repository, or the repository's folder as `WORKSPACE.md` lists it.
- **Branch** is the row's branch, named by the existing rule (`<type>/<KEY>-<slug>`; `feat/<KEY>-<part>` across
  repositories), plus `-s<n>` for a slice; never an `aidlc/` prefix. Written here, it is fixed: every lane claims the
  same name.
- **Depends on** is `none` or the rows that must be done first. For parts it copies the coordination plan's order;
  for slices it copies the bundles' `DEPENDS ON` lines. A slice stacked on another slice may start once its parent's
  build is done; `parallel-lanes` says how.
- Each row's worktree folder follows from the row: `.worktrees/<KEY>` for an item or a part, `.worktrees/<KEY>-s<n>`
  for a slice, and `.worktrees/<KEY>-p<n>` for a second part in the same repository.
- A row leaves the queue when the person removes it, after its merged row reads done on the default branch.
