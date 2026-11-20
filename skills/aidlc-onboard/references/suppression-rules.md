# Rules against blanket and unused suppressions

Reference for step 3 of the `aidlc-onboard` skill. For each stack in the repository, propose the rules below as
Enforced lines under the Quality bar in `AGENTS.md`. The person decides which go in.

Why these rules. aidlc ships no check of its own (ADR 0024). In a change, a new suppression, or one made wider, needs
an `aidlc-exception`: the compliance reviewer reads each added one in the session's evidence file, and the code owner
approves it. Neither sees the suppressions already in the code. The linters' own rules see the whole codebase on
every run: they reject a suppression that names no rule (a blanket one) and one that silences nothing (an unused
one). Together, a suppression stays as narrow as it was approved, and goes when it is no longer needed.

Confirm each rule and setting against the tool's official documentation for the version the repository uses before
you propose it. Names and defaults change between major versions.

## Python

| Tool | Rule or setting | What it rejects |
|---|---|---|
| Ruff | `PGH004` | a blanket `# noqa` with no rule code |
| Ruff | `RUF100` | a `# noqa` that silences nothing |
| mypy | `enable_error_code = ["ignore-without-code"]` | a `# type: ignore` with no error code |
| mypy | `warn_unused_ignores = true` | a `# type: ignore` that silences nothing |
| pylint | `useless-suppression` | a `# pylint: disable=` that silences nothing |
| pylint | `use-symbolic-message-instead` | a numeric message id (`E1101`) where the name (`no-member`) exists |

In `pyproject.toml`:

```toml
[tool.ruff.lint]
extend-select = ["PGH004", "RUF100"]

[tool.mypy]
enable_error_code = ["ignore-without-code"]
warn_unused_ignores = true
```

pylint reports `useless-suppression` and `use-symbolic-message-instead` only when enabled. Both are informational
messages, off by default, so they fail the run only when enabled and named in `--fail-on`:
`pylint --enable=useless-suppression,use-symbolic-message-instead --fail-on=useless-suppression,use-symbolic-message-instead`.

## JavaScript and TypeScript

| Tool | Rule or setting | What it rejects |
|---|---|---|
| ESLint | `linterOptions.reportUnusedDisableDirectives` (flat config), or `--report-unused-disable-directives` | an `eslint-disable` comment that silences nothing |
| `@eslint-community/eslint-plugin-eslint-comments` | `no-unlimited-disable` | an `eslint-disable` with no rule named |
| `@eslint-community/eslint-plugin-eslint-comments` | `require-description` | an `eslint-disable` without a `-- reason` |
| typescript-eslint | `@typescript-eslint/ban-ts-comment` | `@ts-ignore` and `@ts-nocheck`, and `@ts-expect-error` without a description |

Set `reportUnusedDisableDirectives` to `"error"`: a warning does not fail CI. The plugin is a new development
dependency; adding it asks first, like any other.

## Go

| Tool | Rule or setting | What it rejects |
|---|---|---|
| golangci-lint | `nolintlint` with `require-specific: true` | a `//nolint` with no linter named |
| golangci-lint | `nolintlint` with `require-explanation: true` | a `//nolint` without a `// reason` |

Enable `nolintlint` and set both options in its settings: under `linters-settings` in golangci-lint v1, under
`linters.settings` in v2.

## .NET

| Tool | Rule or setting | What it rejects |
|---|---|---|
| .NET code-style analyzers | `IDE0079` | a `#pragma warning disable` or `[SuppressMessage]` that silences nothing |

Raise its severity in `.editorconfig` (`dotnet_diagnostic.IDE0079.severity = error`); code-style rules run on build
only with `EnforceCodeStyleInBuild` set to `true`.

No built-in analyzer rejects a `#pragma warning disable` that names no code. The compliance reviewer reports a new
one, or one widened from a named code, from the evidence file; one already in the code stays until someone removes it.

## Closing directives

Removing a closing directive (`eslint-enable`, `# pylint: enable=`, `#pragma warning restore`, `c8 ignore stop`) widens
a suppression without adding a line. The evidence file lists every removed one, and the compliance reviewer reads
each. Mind pylint's scoping when you judge one:

- **Block scope.** pylint ends an own-line `disable` or `enable` inside a function or class at the end of that block.
- **Names and ids.** `no-member` and `E1101` are one message to pylint.
- **Trailing pragma.** pylint applies a pragma trailing code to that line only.

The linters' own rules narrow the gap. pylint's `use-symbolic-message-instead` reports numeric ids, so every
suppression can use one name. `useless-suppression` (above) reports a `disable` that silences nothing. Prefer a trailing
`disable` or `disable-next` on the one line that needs it.

## The Enforced lines

One line per tool, in the Quality bar's format, with the exact command the repository runs. For example:

```text
- Enforced: no blanket or unused noqa: Ruff PGH004 and RUF100, checked by `ruff check .`
- Enforced: every type: ignore names its code and is used: mypy ignore-without-code and warn_unused_ignores, checked by `mypy .`
```
