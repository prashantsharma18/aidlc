<!-- aidlc template: story-index -->
# {{KEY}} · {{TITLE}}

SOURCE     <work item link>
KIND       <new feature | change request | defect | incident follow-up>
ROUTE      <F1 | F2 | C | D1 | D2>
LEVEL      <repository | workspace root | part <n> of <m> in <repository>>
CURRENT    spec v<n> · contract <name> v<n>        (the story's approved versions; a part leaves this line out)
PINS       spec v<n> · plan v<n> · contract <name> v<n>        (a part: what its latest bundle builds on; a story leaves this line out)
UNAFFECTED <repository> spec v<n>: <why>, <tech lead>, <YYYY-MM-DD>        (one line per part recorded as unaffected; delete when none)

Each stage marks its own row when it ends: done, or stopped: <reason>. The build row reads doing while slices remain.
After the pull request merges, the person marks the merged row done.

| Stage | Runs in | Status |
|---|---|---|
| <stage> | <repository or workspace root> | to do |
