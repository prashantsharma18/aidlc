# Adopting an existing repository

An existing repository joins aidlc without a rewrite and without "red forever". You record today's
debt, with a name and a date, and from then on the repository can only get better. The decision is
[ADR 0007](../adr/0007-adoption-and-ratchet.md). The `aidlc-adopt` skill walks you through it.

## The flow

```text
existing repo
  1. aidlc adopt            read-only survey → adoption report (stack, commands, agent config, CI, secrets)
  2. aidlc init-repo        scaffold (never overwrites a file)
  3. aidlc adopt --import   a patch: CLAUDE.md, Copilot and Cursor rule files → AGENTS.md and .aidlc/rules/
     git apply <patch>      you read it, then apply it
  4. .aidlc/baseline.yaml   today's debt: report-only steps and temporary skips, each with owner and date
  5. adoption pull request  normal review; then switch on the required checks
     every later pull request: the baseline may only shrink (the trusted CI's "baseline" step)
```

| Step | Writes | Who |
|---|---|---|
| `aidlc adopt` | nothing; prints the report. Exit 1 when it finds secret-shaped text | anyone |
| `aidlc init-repo . --profile generic …` | `.aidlc/config.yaml`, `AGENTS.md`, the codebase map; skips every file that exists | you |
| `aidlc adopt --import > adopt.patch` | nothing; prints a patch. `git apply adopt.patch` changes the files | you read, then apply |
| `aidlc render --tool claude-code` | the generated tool files | you |
| `.aidlc/baseline.yaml` | the accepted debt | you write it; code owners review it |

**Any stack works.** The survey suggests commands from `core/context/stack-hints.yaml`: Python,
Maven, Gradle and Go use the `generic` profile with the suggested commands in `.aidlc/config.yaml`.
Test results are read as JUnit XML, JSON or TRX, which most test runners write.

## The baseline

```yaml
# .aidlc/baseline.yaml
report_only:          # the step runs and is shown, but does not fail the check until the date
  - {step: lint, owner: "@orders-team", review_by: "2027-01-31", reason: "1,240 existing lint errors"}
skips:                # the test may be skipped until the date
  - {test: "orders.tests.test_export.ExportTest.test_pdf", owner: "@orders-team", review_by: "2027-01-31",
     reason: "needs the PDF service; tracked in SHIP-77"}
```

- `report_only` takes command steps such as lint, format and typecheck. Never `test`, `build`,
  `install` or `restore`: a failing build or failing tests are a broken repository, fixed first.
- **Secrets are never baselined.** `aidlc adopt` stops until they are rotated and removed.
- The judge steps (scope, protected tests, secrets, config-policy) have no baseline: they are the harness.
- A report-only step shows as `reported` in the check output, with its owner and date.

## The ratchet

The trusted CI compares the change's baseline with the base branch's copy:

- **A new entry fails**: the baseline may only shrink. The one exception is a step that is new in
  the same change, which may start report-only.
- **An entry past its `review_by` date fails** every pull request until it is fixed, or its owner
  moves the date in a reviewed change.
- **Removing an entry always passes.** The check output says how many were paid off.
- The trusted CI reads the base branch's copy, so a pull request cannot widen its own allowance.

Your local `aidlc check` honours the baseline but does not run the ratchet; the trusted CI does.

## Code without tests: `legacy_paths`

```yaml
# .aidlc/config.yaml
legacy_paths: ["src/billing/**", "lib/old_*.py"]
```

The plan and build-slice skills change a matching file only after a characterisation test records
what it does today. The Legacy plan adds enforcement in the checks.

## Why the adoption pull request is merged before the required checks

The trusted CI judges a change with the base branch's aidlc configuration, and the base has none
yet. So the code owners review the adoption pull request themselves. After it merges, the owner adds
the required checks to branch protection: from then on every pull request goes through them, and the
ratchet keeps the baseline shrinking. New repositories follow the same order.
