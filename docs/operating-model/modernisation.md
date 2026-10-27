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

## Running a legacy build next to the sandbox
- **New repository, new folder:** Claude Code ignores a repository's allow rules until someone accepts the folder-trust
  dialog once (open `claude` in it interactively). Headless (`-p`) and cloud sessions never show that dialog.
- **.NET Framework on WSL:** the Linux .NET SDK builds `net48` with the reference-assemblies package, and WSL interop
  runs the result on Windows' .NET Framework. The sandbox blocks the interop socket, so the few commands that launch the
  old build (run, test, parity scripts) are listed in `sandbox.excludedCommands` with matching allow rules, written by a
  person and denied to agents for editing. Code those commands start runs on Windows outside any sandbox: keep the list
  short and review the diffs. A person runs the recipe check's "before" count and parity when the agent cannot.
- **Inside the sandbox**, `dotnet build` needs `-p:EnableSourceControlManagerQueries=false` (git's configuration files
  are hidden) and NuGet needs `api.nuget.org` in `sandbox.network.allowedDomains` once packages are approved.
- **Program output is not always UTF-8:** a .NET Framework console program prints its OEM code page; the parity script
  compares bytes.

## The three lanes
`modernize-assess` proposes the lane from evidence; the tech lead approves it. When unsure, the heavier lane.

| Lane | When | The flow |
|---|---|---|
| Simple | one repository, a recipe covers it, good tests | `aidlc-start` → `modernize-assess` (short) → `aidlc-plan` → `aidlc-build` with the factory (recipe commit, then fixes) → `aidlc-verify` with the dependency and vulnerability diff → `aidlc-review` → `aidlc-release` (canary) |
| Standard | one service, a major framework hop | `aidlc-start` → `modernize-assess` → `aidlc-specify` → `aidlc-plan` (slices, each green at both ends: characterise; retarget and port, where the recipe commit is reviewed on its own and its fixes follow in the same slice; hardening) → `aidlc-build` per slice → `modernize-parity` → `aidlc-verify` → `aidlc-review` → `aidlc-release` (flag or canary) → `modernize-cutover` |
| Programme | several services or a monolith | at the workspace root: `aidlc-start` → `modernize-assess` → `aidlc-design` → `modernize-wave-plan` (each wave a story the product owner creates); then each wave runs the standard lane in its repositories, ending with `modernize-cutover` and decommissioning |

## Gates the plugin adds
- Characterisation tests green on the old version before the first change.
- No new vulnerability or licence issue against the assessment's baseline.
- A parity report approved before release or cutover: every difference explained and decided by its owner, never a
  match percentage.
- Data migration by expand, migrate and contract: one writer writing both stores in one transaction, an idempotent
  back-fill, reconciliation to zero on a schedule, and the old store dropped in a later, separate change.
- After each cutover segment, a reverse comparison (new served, old shadowed) and an outcome measure.
- Decommission only after a quiet period with zero traffic, with data retention decided.

## The one exception to core's gates
A framework upgrade may start with a **mechanical recipe commit**: a deterministic tool's output only, re-run and
checked by `scripts/check_recipe_commit.py`, the same test count before and after, reviewed on its own
([ADR 0012](../adr/0012-mechanical-recipe-commit.md)). AI-agent output never qualifies.

## Worked example
SHIP-3 moved `carrier-rates` (a .NET Framework 4.8 pricing tool) to .NET 10 through the standard lane: characterisation
on .NET Framework (47 tests, a golden master over 14 inputs), one reviewed recipe commit, the port tests-first, parity
14 of 14 the same, 70 tests green on .NET 10. The golden master found three Windows-versus-Linux differences that
reading the code had not. Record: [2026-10-26-modernize-dotnet.md](../verification/2026-10-26-modernize-dotnet.md).
