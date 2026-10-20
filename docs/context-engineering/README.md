# Context engineering

Give an agent the smallest set of trustworthy information that makes its next step likely to be
right, at the moment it needs it, and keep that information owned, current and separate from
enforcement. This page maps the guide's eight context classes to where each lives in a repository
installed with this framework, and what governs it.

| Class | Lives in | Governed by |
|---|---|---|
| 1 Rules | `AGENTS.md` (+ generated `CLAUDE.md`); `.aidlc/rules/` folder rules | `aidlc render`, `aidlc check context-drift`, code owners; must-hold rules also enforced (Plan 2) |
| 2 Procedures | Skills (Plan 5); `docs/procedures/` | Skill reviews and agent-configuration evals |
| 3 Examples | Repository files named in the rules and map | Drift check (named paths must exist) |
| 4 Curated knowledge | `docs/codebase-map.md`, decision records, contracts, runbooks | Drift check (paths, owner, last-verified date and commit) |
| 5 Derived knowledge | `openwiki/` (if adopted), explorer summaries | `aidlc check openwiki`; always verified against code |
| 6 Live evidence | Search, test output, logs (fetched during the run) | Data, never instructions; masked before agents read production data |
| 7 Task bundle | `plans/<KEY>/<slice>.md` on the branch | Approval line; `aidlc scope` |
| 8 Memory | The tool's memory store | `core/policy/memory-policy.yaml`: never authoritative |

When sources disagree, the order of authority decides (framework `core/context/authority.md`).

- [Procedure A: setting up context for a repository](procedure-a.md)
- [Procedure B: assembling context for a task](procedure-b.md)
- [OpenWiki: generated documentation, governed](openwiki.md)
- [Memory](memory.md)
- [Context across repositories](cross-repo.md)

Guide: 2.1–2.14.
