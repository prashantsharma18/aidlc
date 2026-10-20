# Policy as code

Some rules span several files. "The settings deny every secret path for both the Read tool and
commands" cannot be checked by a schema of one file. These rules are written in Rego and run by
Conftest in trusted CI, as [ADR 0001](../adr/0001-policy-as-code.md) decided. The pack and its own
guide are in `core/policy-as-code/`; start with `core/policy-as-code/README.md`.

## The pinned tools

Conftest and OPA are pinned: an exact version, the SHA-256 of the release asset and an entry in
`core/policy/tool-register.yaml`. The versions and hashes live there only (guide 13.9).

- `aidlc tools install [NAME ...] [--dir PATH]` downloads each pinned tool, verifies its SHA-256
  before writing anything, and installs it. It refuses a non-https URL or redirect, caps the
  download and the extracted file at 200 MiB, and refuses a symlinked destination.
- `aidlc tools status` reports each tool as `installed (pinned)`,
  `not installed; unverified <path> on PATH`, or `not installed`.

Tools install to `$AIDLC_HOME_DIR/bin`, else `~/.aidlc/bin`; `AIDLC_TOOLS_DIR` overrides both.
A pinned lookup accepts only a regular file there: a symlink is not a verified install. Install
the tools as a person or in CI, never inside an agent session: the session sandbox has no route to
the download host.

## Running the pack

- `aidlc policy conftest [--repo PATH]` judges one repository. It exits 0 on a pass and 1 on a
  violation, including "conftest is not installed". It exits 2 when the repository or its policy
  data cannot be read. Locally it uses the pinned binary, else one on PATH.
- `aidlc ci` runs the same judgement as the `config-policy` step, with the pinned binary only. See
  [trusted CI](ci.md).
- `aidlc policy rego-test` runs the pack's own unit tests.
- `make policy-test` runs those unit tests plus the live Python tests in
  `tests/unit/test_conftest_check.py` and `tests/unit/test_ci_templates.py`. A skipped test fails
  the target. Set `AIDLC_TOOLS_DIR` when the tools are not in the default place.

Conftest never runs inside the repository it judges. It gets an empty working directory, a
minimal environment with no `CONFTEST_*` variables, and absolute paths. A symlinked, special or
outside-the-checkout input fails. So does an input that would not parse, a namespace that
evaluated no rules, or more than 200 inputs.

## What the pack judges

| Namespace | Input | Examples of what it denies |
|---|---|---|
| `aidlc.settings` | `.claude/settings.json` | A sandbox that is off or optional; a secret path without both denies; `disableAllHooks`; a hook event with no entry or without `onFailure: block`; a bare tool in `allow`, including `X(*)`, `X(:*)` and `X(**)` |
| `aidlc.narrowing` | `.aidlc/permissions.yaml` | An `allow_add` that re-allows a baseline deny; a loosening without reason or owner; a wildcard host; a refused write location |
| `aidlc.workflows` | Every `.yml` or `.yaml` file in `.github/workflows/`, any case | `pull_request_target` or `workflow_run`; top-level `permissions` that is not an object or `read-all`; write grants; a step or a reusable-workflow job not pinned to a full commit SHA |

**Workflow expressions.** Inside `run:` and `with.script`, only allow-listed `${{ }}`
expressions pass: `secrets.*`, `matrix.*`, `runner.*` and a few `github.*` values that a pull
request cannot choose. The exact list is `safe_expression` in the workflows rule file. Pass
anything else through `env:` and use it as `"$VAR"`.

The Rego holds logic only. The facts reach it as `data.aidlc.*`: the effective permissions, the
expected `denyRead` entries, the baseline deny list and the refused write locations. In CI that
data comes from the base checkout, so a change cannot widen what it is judged against. The
change's own `.aidlc/permissions.yaml` is still schema-checked and write-grant-checked.

## The generated-file judge

`config-policy` also re-renders every generated file from the change's sources, using the
trusted framework code, and compares:

- `.claude/settings.json` field by field. Its `denyWrite` list may hold extra entries, but only
  entries the renderer itself would produce for a file in the change.
- Every other generated file byte for byte, including the GitHub workflow when the base or the
  change lists `ci: [github]`.

**Agent configuration the framework does not manage fails.** Paths are case-folded and
NFC-normalised, and checked at any depth:

- `.claude/settings.local.json`, `.mcp.json` and `CLAUDE.local.md`;
- any file under any `.claude/` folder that render did not produce;
- extra files under `.aidlc/hooks/`.

`.aidlc/rules/` may hold the repository's own rule sources, one level deep.

> ⚠️ **Watch out:** Until Plan 5, a team cannot commit its own `.claude/` content, such as skills
> or agents. Monorepos cannot have nested `.claude` folders. Both fail `config-policy`.

## Adding a rule

1. Write the failing test first: a bad input in the namespace's `*_test.rego` file that the rule
   must deny, next to the passing case.
2. Run `make policy-test` and watch it fail.
3. Write the rule. Read values from `data.aidlc.*`; never copy them into Rego.
4. Run `make policy-test` again, then `make test`.

A rule without a failing test is not accepted. Platform and security own the pack through
CODEOWNERS.

Guide: 3 step 9, 13.9.
