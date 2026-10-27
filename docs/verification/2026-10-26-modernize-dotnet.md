# aidlc-modernize, end to end: SHIP-3 (Plan 8)

Run 2026-10-26 on the demo workspace `~/work/shipment-tracking`, repository `carrier-rates`. Claude Code headless
sessions (`claude -p`, model Sonnet, `--permission-mode acceptEdits`) with `--plugin-dir plugins/` (both plugins).
The owner (Prashant Sharma) decided every gate; the orchestrating session ran the person-side commands on his
instructions.

## The work item

[SHIP-3](https://prashantsharma18.atlassian.net/browse/SHIP-3), a Story: move `carrier-rates`, a small .NET Framework
4.8 console that prices shipments for carrier invoices, to .NET 10 on Linux. Invoices must not change.

The legacy app was built for the demo with three real porting traps: `BinaryFormatter` for its cache (removed in
.NET 9), `ConfigurationManager` for `App.config` (a package on .NET), and banker's rounding. It was built by the Linux
.NET 10 SDK (reference assemblies) and run on Windows' .NET Framework 4.8 through WSL interop.

## What ran, where, and what it produced

| Stage | Output | Decision |
|---|---|---|
| `aidlc-start` | One-repository route; the pack check ran; the index's first stage is `aidlc-modernize:modernize-assess` (after fix P8-F4) | Six product-owner questions answered (cache rebuilt as JSON, key unchanged; output byte-exact on handled paths; App.config via the package) |
| `modernize-assess` | Replatform, standard lane; baselines (0 tests, timing; scans run by the person); one-way door: the cache; rollback risk if the new cache reused the old name | Lane approved; new cache `rates.json`; crash paths need not match exactly |
| `aidlc-specify` | AC1-AC7, E1-E18, Q1-Q6 | Spec v1 approved; atomic cache write; the owner is the Tier 3 specialist; Jira story text updated |
| `aidlc-design` | ADR-0001 (cache format and write), ADR-0002 (configuration reader); caught a wrong citation in the assessment | Design approved |
| `aidlc-plan` | First 6 slices (red between slices), then 4 slices green at every boundary (after fix P8-F7); package versions checked on NuGet; the recipe probed on a scratch copy (exactly 4 expected errors) | Plan v2 approved: ConfigurationManager 10.0.12, xunit.v3 4.0.1; static test count for the recipe check |
| `aidlc-build` slice 1, characterise | 47 tests on .NET Framework, golden master over 14 synthetic inputs recorded from the old build, mutation proofs, 13 oddities listed (none fixed) | Cut point and groups confirmed |
| `aidlc-build` slice 2, retarget and port | Recipe commit `965eb60` (`Recipe: aidlc-retarget@1.0.0`); the person's recipe check: reproduces, 17 to 17 declared tests, 0 assertion lines; red run 5 red for the expected reasons; config and JSON cache commits; 64 green on .NET 10 | Recipe commit approved. Three platform differences found by the golden master, decided as spec v1.1: stdout in code page 437 (confirmed by `chcp`), the old NLS header rule reproduced exactly, the E9 test's Windows path made platform-neutral |
| `aidlc-build` slice 3, hardening | 70 green; E11, E16, E13 | - |
| `modernize-parity` | 14 of 14 inputs the same (bytes, line endings normalised; no noise, no ignore patterns); AC7: new and old alternating in one folder give the same output and keep their own caches; timing comparable | Parity report approved |
| `aidlc-verify` | Evidence table, local only (no CI) | - |
| `aidlc-review` | Three reviewer agents: 19 findings (none a production defect) | Fix B1, B2, B5 and record items; dismiss the rest with reasons; BQ1, BQ2 accepted as a documented risk; review approved |
| `aidlc-build` review fixes | Each strengthened test shown to fail against a broken implementation; 70 green | - |

Final state: `feat/SHIP-3-net10`, 39 commits, all with the noreply identity; 70 tests green on .NET 10; `Pricing.cs`
and `RateTable.cs` unchanged. Release and cutover were not run (the demo has no deployment).

## The pack contract and the recipe rule, as they behaved

- **The repository declared the pack** in AGENTS.md; `check_packs.py` passed at every start; `aidlc-start` routed to
  the pack's entry skill; bundles named `aidlc-modernize:modernize-characterize` and `aidlc-modernize:dotnet-modernize`
  in full; build sessions loaded them and recorded the plugin version.
- **The mechanical recipe commit** held only the tool's output, was re-run and reproduced by `check_recipe_commit.py`,
  and was reviewed on its own before any fix. Its count was static (17 declared test methods before and after, while
  the build was red), which proves no test method was added or removed, not that every data row survived; the full
  run after the port (64, then 70 executed tests) is what proves the cases.
- **Characterisation earned its keep:** the golden master found three behaviours that differ between .NET Framework on
  Windows and .NET on Linux (console code page, culture-dependent header detection, a Windows path in a test), none of
  which a reading of the code had flagged.

## Findings and fixes

| ID | Finding | Fix |
|---|---|---|
| P8-F1 | The sandbox blocks WSL interop, so a session cannot launch the .NET Framework build | Owner decision: three person-written scripts in `sandbox.excludedCommands` with allow rules, denied to agents for editing; documented in `modernisation.md` |
| P8-F2 | A never-opened repository is untrusted: its allow rules are ignored until the folder-trust dialog is accepted once | The owner trusted it; documented in the Claude Code quickstart |
| P8-F3 | The recipe check's "before" count needs the old build, which the sandbox blocks | The person runs the recipe check; a static count of declared tests while the build is red |
| P8-F4 | `aidlc-start` put the pack's entry skill after specify | `aidlc-start` step 2: before intent and specify; `modernize-assess` stage metadata |
| P8-F5 | Inside the sandbox `dotnet build` needs `-p:EnableSourceControlManagerQueries=false`, and NuGet needs `api.nuget.org` | The demo's settings and AGENTS.md; documented |
| P8-F6 | `modernize-assess` cited wrong line numbers | It spot-checks its own citations |
| P8-F7 | The planner left the suite red between slices, which `aidlc-build` stops on | `aidlc-plan` step 5: every slice starts and ends green; a recipe commit shares a slice with the fixes it forces |
| P8-F8 | The planner named a manual stage skill in USE SKILLS, which a build cannot load | `aidlc-plan` step 7: USE SKILLS lists only build-time skills |
| P8-F9 | The demo's scripts built without the sandbox flag | The person fixed the scripts |
| P8-F10 | `parity.py` decoded output as UTF-8 and crashed on code page 437 | It compares bytes (test first) |

## Open

- Release, cutover and the first nightly comparisons on real input (BQ1, BQ2) are not run.
- The stale-surcharge cache key (the key ignores the fuel surcharge) is a separate defect to raise.
- The owner was also author, reviewer and specialist: accepted for the demo, not for real work.
- Secrets scan and SAST were not run (UNPROVED).
