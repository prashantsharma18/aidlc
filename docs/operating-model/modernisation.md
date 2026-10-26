# How modernisation runs

Modernisation work runs through the normal aidlc lifecycle, with the `aidlc-modernize` plugin switched on in the
repositories being modernised. The method follows the guide's chapter 15.

## Switching it on
1. Enable `aidlc-modernize@aidlc` in the repository's `.claude/settings.json` (or copy its skills for Copilot, Codex
   or Cursor).
2. Declare it in AGENTS.md:

   ```
   ## Packs used here
   - `aidlc-modernize`: `aidlc-modernize:modernize-assess`, `aidlc-modernize:modernize-characterize`, `aidlc-modernize:modernize-parity`, `aidlc-modernize:dotnet-modernize`
   ```

3. Run `python3 scripts/check_packs.py`; CI runs it too.

## The three lanes
`modernize-assess` proposes the lane from evidence; the tech lead approves it. When unsure, the heavier lane.

| Lane | When | The flow |
|---|---|---|
| Simple | one repository, a recipe covers it, good tests | `aidlc-start` → `modernize-assess` (short) → `aidlc-plan` → `aidlc-build` with the factory (recipe commit, then fixes) → `aidlc-verify` with the dependency and vulnerability diff → `aidlc-review` → `aidlc-release` (canary) |
| Standard | one service, a major framework hop | `aidlc-start` → `modernize-assess` → `aidlc-specify` → `aidlc-plan` (slices: tools, characterise, recipe, fixes) → `aidlc-build` per slice → `modernize-parity` → `aidlc-verify` → `aidlc-review` → `aidlc-release` (flag or canary) → `modernize-cutover` |
| Programme | several services or a monolith | at the workspace root: `aidlc-start` → `modernize-assess` → `aidlc-design` → `modernize-wave-plan` (each wave a story the product owner creates); then each wave runs the standard lane in its repositories, ending with `modernize-cutover` and decommissioning |

## Gates the plugin adds
- Characterisation tests green on the old version before the first change.
- No new vulnerability or licence issue against the assessment's baseline.
- A parity report approved before release or cutover: every difference explained and decided by its owner, never a
  match percentage.
- Data migration with one writer, reconciliation to zero and a tested rollback.
- Decommission only after a quiet period with zero traffic, with data retention decided.

## The one exception to core's gates
A framework upgrade may start with a **mechanical recipe commit**: a deterministic tool's output only, re-run and
checked by `scripts/check_recipe_commit.py`, the same test count before and after, reviewed on its own
([ADR 0012](../adr/0012-mechanical-recipe-commit.md)). AI-agent output never qualifies.

## Worked example
SHIP-3 moves `carrier-rates` (a .NET Framework 4.8 pricing tool) to .NET 10 through the standard lane. The record is
in `docs/verification/` once the run is done.
