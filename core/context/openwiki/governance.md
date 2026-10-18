---
id: ctx-openwiki-governance
guide: ["4.3", "4.6", "2.2", "13.4"]
---
# OpenWiki governance

OpenWiki (LangChain, MIT licence) generates a Markdown wiki in `openwiki/` and keeps a managed
block between `<!-- OPENWIKI:START -->` and `<!-- OPENWIKI:END -->` in `AGENTS.md` (and in
`CLAUDE.md` if one exists). Its output is derived knowledge (class 5): computed, possibly stale,
ranked below code, tests and runtime evidence, and adopted only if evals show it helps.

## Controls
| Concern | Control |
|---|---|
| `AGENTS.md` is a protected, owned file | Only the OpenWiki job writes the block, on its own branch, via a PR for code owners; coding sessions are denied edits |
| Block bloat | `aidlc check openwiki` fails above 15 lines or on any line that is not a heading or an `openwiki/` pointer |
| Duplicate load | The check fails if `CLAUDE.md` contains the block; the job strips it after each run |
| Staleness | Pages carry the generation commit; rules say "verify against code before relying on it" |
| Data leaving the machine | Approved route only (`model-routes.yaml`, anthropic-api, Internal); baseline `.openwikiignore` |
| Telemetry | `OPENWIKI_TELEMETRY_DISABLED=1`; LangSmith tracing off |
| Credential | `~/.openwiki/.env` (mode 600), written by a person; agents are denied reads of it |
| Cost | Init once; update on demand or weekly; `OPENWIKI_PAGE_CONCURRENCY=1` |
| Value | Adopt per repository only after an A6 comparison, recorded as a decision record |
| Search | OpenWiki's MCP server, read-only, for discovery sessions; results labelled derived |

## Running it (by a person or the update job, never inside a coding session)
1. `cp <framework>/core/context/openwiki/openwikiignore.baseline .openwikiignore` (first run) and
   copy `INSTRUCTIONS.md` to `openwiki/INSTRUCTIONS.md`.
2. On a branch `docs/openwiki-<date>`:
   `OPENWIKI_TELEMETRY_DISABLED=1 OPENWIKI_PAGE_CONCURRENCY=1 openwiki --init` (later `--update`).
3. Remove any OpenWiki block from `CLAUDE.md`; run `aidlc render --tool claude-code`.
4. `aidlc check openwiki` and `aidlc check context-drift` must pass.
5. Open a PR for the code owners; record the adoption decision (comparison results) as an ADR.
