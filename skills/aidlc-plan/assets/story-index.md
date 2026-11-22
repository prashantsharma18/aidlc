<!-- aidlc template: story-index -->
# {{KEY}} · {{TITLE}}

```text
SOURCE     <work item link>
KIND       <new feature | change request | defect | incident follow-up | new system>
ROUTE      <F0 | F1 | F2 | C | D1 | D2 | G>   (or S: a standard change that AGENTS.md lists, ADR 0026)   (<kind of work>; Tier <n>; <one repository | n repositories>; <criteria written by owner | criteria not yet written>, ADR 0027)
LEVEL      <repository | workspace root | part <n> of <m> in <repository>>
BRANCH     code <type>/<KEY>-<slug>        (every row not named below runs on it; once a document pull request merges, it starts from the default branch)
BRANCH     spec docs/<KEY>-spec        (Tier 2 and 3: the intent and specify rows; it merges first, ADR 0020; delete the line at Tier 1)
BRANCH     plan docs/<KEY>-plan        (Tier 2 and 3: the discover, design and plan rows; it starts from the default branch once the spec merges, and merges first; a Tier 1 plan with independent slices adds it; delete the line otherwise)
CURRENT    spec v<n> · contract <provider> v<MAJOR.MINOR.PATCH>        (the story's approved versions; a part leaves this line out)
PINS       spec v<n> @ <home commit> · plan v<n> · contract <provider> v<MAJOR.MINOR.PATCH>        (a part: what its latest bundle builds on, the spec at the home repository's commit; a contract's version is its published tag's, the tag in contracts/<provider>/SOURCE; a story leaves this line out)
UNAFFECTED <repository> spec v<n>: <why>, <tech lead>, <YYYY-MM-DD>, <how it was confirmed>        (one line per part recorded as unaffected, written by the AI when the tech lead decides; delete when none)
```

The ROUTE line names the facts its route follows from; Ready shows the route, the tech lead owns it, and a technical
person checks the facts at the first technical decision (ADR 0027). A re-route writes
`<new route>   (re-routed from <old route>, <YYYY-MM-DD>: <reason>)`.
Every route has a `merged` row after `aidlc-review`; a story index at a workspace root has none, because each part's
index holds it (ADR 0028). Each stage marks its own row when it ends: done, or `stopped: <reason>`. The build row reads doing while slices remain.
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
