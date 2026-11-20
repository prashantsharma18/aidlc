<!-- aidlc template: story-index -->
# {{KEY}} · {{TITLE}}

```text
SOURCE     <work item link>
KIND       <new feature | change request | defect | incident follow-up | new system>
ROUTE      <F0 | F1 | F2 | C | D1 | D2 | G>
LEVEL      <repository | workspace root | part <n> of <m> in <repository>>
CURRENT    spec v<n> · contract <name> v<n>        (the story's approved versions; a part leaves this line out)
PINS       spec v<n> @ <home commit> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on, the spec at the home repository's commit; a story leaves this line out)
UNAFFECTED <repository> spec v<n>: <why>, <tech lead>, <YYYY-MM-DD>, <how it was confirmed>        (one line per part recorded as unaffected, written by the AI when the tech lead decides; delete when none)
```

Each stage marks its own row when it ends: done, or `stopped: <reason>`. The build row reads doing while slices remain.
Once the code owner approves, the AI checks the approval and the required checks on GitHub, marks the merged row
done in the pull request's final commit (its message says how it was confirmed) and tells the person it is ready
to merge (ADR 0023), so it reaches
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do". The story
status command checks the merged row against the real merge state and reports a row that disagrees.

Links to these documents on the tracker are GitHub permalinks at a commit (`/blob/<commit>/`), never a branch
path, which moves.

| Stage | Runs in | Status |
|---|---|---|
| {{stage}} | {{repository or workspace root}} | to do |
