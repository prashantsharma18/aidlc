<!-- aidlc template: story-index -->
# {{KEY}} · {{TITLE}}

```text
SOURCE     <work item link>
KIND       <new feature | change request | defect | incident follow-up | new system>
ROUTE      <F0 | F1 | F2 | C | D1 | D2 | G>   (or S: a standard change that AGENTS.md lists, ADR 0026)
LEVEL      <repository | workspace root | part <n> of <m> in <repository>>
CURRENT    spec v<n> · contract <provider> v<MAJOR.MINOR.PATCH>        (the story's approved versions; a part leaves this line out)
PINS       spec v<n> @ <home commit> · plan v<n> · contract <provider> v<MAJOR.MINOR.PATCH>        (a part: what its latest bundle builds on, the spec at the home repository's commit; a contract's version is its published tag's, the tag in contracts/<provider>/SOURCE; a story leaves this line out)
UNAFFECTED <repository> spec v<n>: <why>, <tech lead>, <YYYY-MM-DD>, <how it was confirmed>        (one line per part recorded as unaffected, written by the AI when the tech lead decides; delete when none)
```

Each stage marks its own row when it ends: done, or `stopped: <reason>`. The build row reads doing while slices remain.
A lane (`parallel-lanes`) that stops for a person's decision writes `waiting: <decision> by <who>` in the row of the
next unfinished stage, never in a row already done; when the wait ends, that row reads `to do` again.
Once the code owner approves, the AI checks the approval in the review tool and the team's CI result, marks the merged row
done in the pull request's final commit (its message says how it was confirmed) and tells the person it is ready
to merge (ADR 0023), so it reaches
the default branch only through the merge. A re-plan or a revision resets the later rows to "to do". At release,
`aidlc-release` reads the merged row on each repository's default branch with git, and a person confirms it.

Links to these documents on the tracker are permalinks at a commit (the full commit hash in the address), never a
branch path, which moves.

| Stage | Runs in | Status |
|---|---|---|
| {{stage}} | {{repository or workspace root}} | to do |
