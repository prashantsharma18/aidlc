<!-- aidlc template: adr -->
# 0007 · Existing repositories adopt aidlc through a survey, an import patch and a ratchet

Status: Accepted (2026-10-23). · Decider: Prashant Sharma (framework owner)
Work item: none (framework decision) · Tier: 2 (changes how every existing repository joins and is judged)

## Context

- **Red forever.** An existing repository rarely passes its own lint and type checks, and often skips
  tests. Switching every check on at once makes CI red on day one, and red soon means ignored.
- **Other tools' files.** Existing `CLAUDE.md`, Copilot and Cursor rule files block `aidlc render`
  (it never overwrites a person's file) and fail the trusted CI judge as unmanaged agent
  configuration (ADR 0006).
- **The guide** says to roll out against a baseline (16.5) and to pin today's behaviour before
  changing old code (15.7).

## Decision

- **`aidlc adopt`** is a read-only survey: stack and suggested commands, other tools' agent
  configuration, existing CI, and secret-shaped text. `--import` prints a patch that moves the
  importable rule files into `AGENTS.md` and `.aidlc/rules/`; the person reads and applies it.
- **The baseline**, `.aidlc/baseline.yaml`, lists accepted debt with an owner, a review date and a
  reason: report-only command steps (never `test`, `build`, `install` or `restore`) and temporary
  skips. Trusted CI reads the base branch's copy.
- **The ratchet** is a trusted CI judge step: the baseline may only shrink, and an entry past its
  date fails. A step new in the same change may start report-only.
- **Secrets are never baselined.** The survey stops the adoption until the secrets are rotated and removed.
- **No profile per stack.** Existing repositories use `generic` with the commands the survey suggests;
  a profile is only a set of defaults, added as data when a team asks.
- **`legacy_paths`** names code without pinning tests; the plan and build-slice skills write a
  characterisation test before changing it.

## Consequences

- An expired entry turns every pull request red until it is fixed, or its owner moves the date in a
  reviewed change. That is the point: the debt cannot be forgotten.
- The local `aidlc check` honours the baseline but does not run the ratchet; the trusted CI does.
- The adoption pull request is reviewed by the code owners without the trusted CI, because the base
  has no aidlc configuration yet. The required checks are switched on after it merges.
- Enforcing `legacy_paths` in the checks is left to the Legacy plan.

## Credit

The ratchet idea, recording today's state and refusing to get worse, comes from
addyosmani/agent-skills (MIT). Our text and code are our own; nothing is installed from it.

## Rejected alternatives

- **A report-only mode for whole checks, including tests and security.** It would let a broken build
  or a leaked secret merge. Only command steps that do not decide correctness can be report-only.
- **Rewriting other tools' files automatically.** The patch is printed for a person to read and apply,
  so nothing a person wrote is changed without them.
