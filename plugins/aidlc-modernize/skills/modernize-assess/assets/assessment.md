<!-- aidlc-modernize template: assessment -->
# {{KEY}} · modernisation assessment

DECISION   <retire | retain | rehost | replatform | refactor> — <why, in two sentences>
SCORE      value <..> · risk <..> · churn and pain <..> · seam <..> · tests <..>   (guide 15.2)

## Lane
| Evidence | Finding | Points to |
|---|---|---|
| Repositories touched | <n, which> | simple/standard (1) · programme (several) |
| A deterministic recipe covers the change | <yes: tool@version / no> | |
| Behaviour already pinned by tests | <none / some / good, with counts> | |
| Consumers of the output | <who, and how they read it> | |
| Stored data changes | <none / which formats> | |

LANE       <simple | standard | programme> — proposed; approved by <name> on <date>

## Inventory (cited)
- Projects and target frameworks: <path — framework>
- Packages: <name version>
- Entry points: <path:line — how it starts>
- Tests: <count, what they assert>
- Stored data: <file, table or queue — format>
- Consumers and contracts: <who — what>

## Baselines
| Baseline | Value | Command or source |
|---|---|---|
| Test count and coverage | <..> | <..> |
| SBOM: vulnerabilities and licences | <.. or "not available, because .."> | <..> |
| Performance: start-up, a representative run, memory | <..> | <..> |

## One-way doors
| What | Why it cannot go back | Proposal: migrate, rebuild or keep a reader | Decided by |
|---|---|---|---|

## Factory and recipe
FACTORY    <plugin:skill>
RECIPE     <tool@version — what it changes>
DEPENDENCIES TO APPROVE  <package version — why> | none

## Open
- <question> -> <owner>
