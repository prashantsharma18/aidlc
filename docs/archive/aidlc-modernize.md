# Archived: the aidlc-modernize pack

Archived on 2026-11-08 by the owner, Prashant Sharma, to focus on aidlc. Not deleted: it is in git under the tag
`aidlc-modernize-archive` (commit f8e093c), and the earlier releases under `aidlc-modernize--v0.1.0` and
`aidlc-modernize--v0.1.1`. The tags live in git only once pushed: the owner runs
`git push origin aidlc-modernize-archive` (and the two release tags) before others can restore from them.

## What it held
- Method skills: `modernize-assess`, `modernize-characterize`, `modernize-wave-plan`, `modernize-parity`,
  `modernize-cutover`.
- Factories: `dotnet-modernize` (with `scripts/retarget.py`), proven end to end on SHIP-3 (a .NET Framework 4.8
  service ported to .NET 10, 70 tests, parity 14/14; `docs/verification/2026-10-26-modernize-dotnet.md`), and
  `java-modernize`, written but not proven.
- The `parity-checker` agent and `modernize-parity/scripts/parity.py`.
- It plugged into core through the pack contract (ADR 0011), which Plan 17 removed with it (ADR 0018).

## How to restore it
1. `git checkout aidlc-modernize-archive -- plugins/aidlc-modernize`, and the tests from the same tag:
   `git checkout aidlc-modernize-archive -- scripts/test_parity.py scripts/test_retarget.py`.
2. Decide how it plugs in again: as a second plugin (a marketplace entry and a plugin folder of its own, since aidlc
   now sits at the repository root), or as skills inside aidlc. Either needs a design change, recorded as an ADR.
