# Plugins, the pack contract and the modernisation plugin (Plan 8)

Status: approved by the owner 2026-10-26 (decisions below). Visual version: the "aidlc Plugin Map" page (v3).
Reviewed twice by independent agents: a research run on cross-plugin behaviour and an adversarial design review.

## Why

aidlc will grow: modernisation factories for .NET and Java first, more later. One plugin holding everything would put
every factory in every repository. Claude Code, Copilot, Codex and Cursor all now distribute skills as plugins from a
marketplace and switch them on per repository, so aidlc becomes **one marketplace with several plugins**.

Two findings shape the design:
- A core skill that depends on an optional pack fails silently when the pack is off (research run: a missing skill
  gives "Unknown skill" and the model carries on; a missing preload is only a debug-log line; there is no optional
  plugin dependency). So **core never names a pack**.
- The eight practice skills refer to each other and splitting them saves about 500 tokens. They **stay in core**.

## Shape

| Plugin | Holds | Requires | On where |
|---|---|---|---|
| `aidlc` (core) | the 13 stage skills, the 8 practice skills, the 7 agents, the gates, the pack contract | nothing | every repository and workspace root |
| `aidlc-modernize` | method skills `modernize-assess`, `modernize-characterize`, `modernize-wave-plan`, `modernize-parity`, `modernize-cutover`; factory skills `dotnet-modernize` (first, proven end to end) and `java-modernize` (written, not yet proven); agent `parity-checker`; scripts `parity.py`, `retarget.py` | `aidlc` `^2.0` | repositories being modernised |

Layout: `plugins/aidlc/` and `plugins/aidlc-modernize/`, each with `.claude-plugin/plugin.json`; the root
`.claude-plugin/marketplace.json` lists both with relative sources. `docs/`, `scripts/` and `starter/` stay at the
root and are never inside a plugin. Install names stay `aidlc@aidlc` and `aidlc-modernize@aidlc`.

Factories split into their own plugins (`aidlc-modernize-dotnet`, `aidlc-modernize-java`, each requiring
`aidlc-modernize`) only when a second owning team, a separate release cadence or the skill-listing budget makes it
worth it (owner decision: "if things get complex, later we separate it and see the best way").

## Versions

Every plugin has a real semantic version, raised on each release: core becomes `2.0.0` (the layout and the pack
contract are breaking), `aidlc-modernize` starts at `0.1.0`. Releases are tagged `<plugin>--v<version>`. A pack
declares the version range of what it requires. A pinned version that never changes stops installed copies from
updating (Claude Code docs: the manifest version comes first).

## The pack contract (how core runs a pack without naming it)

"Requires" is about installing; at run time every enabled plugin's skills sit in one list and the model invokes them
by name. Core is written like a CI runner: it runs the skills that files a person approved name.

1. **The repository declares its packs** in an AGENTS.md section `## Packs used here`, one line per pack with its
   skills in full (`aidlc-modernize:dotnet-modernize`), or `- none`. The section is protected by CODEOWNERS.
2. **A pack check script** (`scripts/check_packs.py`, copied from the starter) runs in CI and at the start of work. It
   fails when a declared pack is not enabled in `.claude/settings.json`, when a copy install (`.github/skills/`,
   `.agents/skills/`, `.claude/skills/`, `.cursor/skills/` holding aidlc's skills) lacks a declared skill, or when the
   settings enable a pack from aidlc's marketplace that AGENTS.md does not declare. This is the guarantee; it does not
   depend on how any tool reacts to a missing skill.
3. **`aidlc-start`** reads the section, runs the pack check, and puts the pack's entry stage into the route.
4. **`aidlc-plan`** writes the skills a slice needs into the task bundle's `USE SKILLS` field, in full names.
5. **`aidlc-build`** loads each named skill; a missing or ambiguous skill is a stop. The progress note records each
   skill loaded and its plugin version, and `reviewer-compliance` checks that record against `USE SKILLS`.
6. Factory skills are model-invocable (so the build can load them) and stop unless an approved bundle names them.
   Method skills are manual, like core's stage skills.

Validator rules that keep this true: skill names unique across the marketplace (Copilot keeps the first skill of a
name); no core file names another plugin or its skills; every plugin source under `./plugins/`; core has no
dependencies; every dependency names a plugin in the marketplace; versions are semantic.

## The mechanical recipe commit (the one exception to core's gates)

Approved by the owner on these five conditions, all required:
1. Only a deterministic tool qualifies: run on the same code it gives the same diff, and a check re-runs it to prove
   that. The output of an AI agent never qualifies (for example GitHub Copilot app modernization); its changes are
   ordinary code under every gate.
2. The tool and its version are approved in the plan (the bundle's `RECIPE` field); "no new dependency without
   asking" applies to the tool itself.
3. The commit holds only the tool's output: the test count is the same before and after, and no assertion changes
   what it checks. `scripts/check_recipe_commit.py` checks the re-run and the count and lists every changed assertion
   line for the reviewer.
4. A person reviews it as its own commit, with the trailer `Recipe: <tool>@<version>`.
5. Everything after it (fixes, clean-up) goes through all the normal gates.

Precedent: large-scale change processes (Google's, Chromium's) review mechanical changes separately and still require
a human approver.

## The modernisation method

`modernize-assess` decides retire, retain, rehost, replatform or refactor; records the inventory, test coverage, an
SBOM with CVE and licence baseline, a performance baseline and the consumers; and proposes a lane a person approves.
When unsure, the heavier lane.

| Lane | When | Steps added to the core flow |
|---|---|---|
| Simple | one repository, a recipe covers it, good tests | assess (short); dependency and CVE diff at verify; canary release |
| Standard | one service, a major framework hop | assess, characterise before any change, parity before release |
| Programme | several services or a monolith | assess and design at the workspace root, wave plan (each wave a story the product owner creates), then per wave characterise, parity, cutover, decommission |

Gates the plugin adds: characterisation tests green before the first change; no new CVE or licence issue against the
baseline; a parity report approved before cutover; data migration with a tested rollback; decommission after a quiet
period with data retention, approved by the owner. Scripts run, agents read: `parity.py` runs old and new on the same
inputs (old twice, to find noise) and writes the report; the read-only `parity-checker` triages it.

The method points to core instead of repeating it: `deprecation-and-migration` (strangler fig, adapters, expand and
contract) and the characterisation rule in `aidlc-plan` and `aidlc-build`.

## .NET factory (first)

`dotnet-modernize` covers .NET Framework 4.x to .NET 10 (LTS), with references for the framework hop, ASP.NET by
strangler fig (YARP and System.Web adapters), WCF (CoreWCF, gRPC or HTTP APIs) and EF6 to EF Core (a separate, later
wave: EF6 runs on modern .NET). The .NET Upgrade Assistant is deprecated in favour of GitHub Copilot's modernization
agent, which is an AI agent and never a recipe. OpenRewrite's C# recipes come through Moderne under a proprietary
licence: an owner decision per organisation, not assumed. The factory's own deterministic recipe is `retarget.py`
(changes the target framework of SDK-style projects and drops the .NET Framework reference-assemblies package).

## Demo

A very small real .NET Framework 4.8 console app, `carrier-rates`, in `~/work/shipment-tracking`, taken through the
standard lane to .NET 10. Verified on this machine: the Linux .NET 10 SDK builds `net48` with
`Microsoft.NETFramework.ReferenceAssemblies` 1.0.3, WSL interop runs the `.exe` on Windows' .NET Framework 4.8, and
xUnit v3 2.0.3 test executables run there and exit 1 on a failure. No ASP.NET or WCF (no IIS here). The legacy app has
two real porting problems: `BinaryFormatter` (removed in .NET 9; its cache file is a one-way door) and
`ConfigurationManager` (needs a package on .NET: a dependency decision at the plan gate), plus banker's rounding that
parity must keep.

## Not in this plan

Plugin relevance suggestions, `defaultEnabled`, separate factory plugins, the Java factory's end-to-end proof, AI
review in CI (owner: later), the GitHub push and pull request (owner: later).
