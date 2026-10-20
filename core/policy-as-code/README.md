# Policy as code: the Rego pack

This folder holds the rules that judge a repository's agent configuration. They are written in Rego, the policy language of Open Policy Agent. Conftest runs them over configuration files. ADR 0001 explains the choice.

## What each namespace judges

| Namespace | Input file | Denies |
|---|---|---|
| `aidlc.settings` | `.claude/settings.json` | A disabled or optional sandbox, an unsandboxed fallback, bypass mode, a missing `Read()` deny for a secret path, a missing `Edit()` deny for a protected path, a missing `denyRead` entry, a hook without `onFailure: block`, a bare tool in `allow`. |
| `aidlc.narrowing` | `.aidlc/permissions.yaml` | An `allow_add` that re-allows a baseline deny, a loosening with no reason or owner, a wildcard network host, a write grant to a refused location. |
| `aidlc.workflows` | `.github/workflows/*.yml` | `pull_request_target`, missing or write-capable tokens, actions not pinned to a full commit SHA, untrusted pull request text expanded inside `run:`. |

## The data contract

The Rego holds logic only. The facts come from the framework's YAML and reach the rules as `data.aidlc.*`:

- `data.aidlc.effective`: the effective permissions (baseline plus the repository's narrowing), including `secret_paths` and `protected_paths`;
- `data.aidlc.sandbox_deny_read`: the `denyRead` entries the settings must contain;
- `data.aidlc.baseline.deny`: the baseline deny list from `core/policy/permissions.yaml`;
- `data.aidlc.refused_writes`: the locations a repository may never make writable.

Never copy these values into Rego. If the data is missing, every namespace denies with "policy data missing", so a run outside `aidlc` never passes silently.

Helper rules must not be named `deny_*`, `violation_*` or `warn_*`. Conftest runs those as policy rules and reports each member as a failure.

## Every rule has a failing test

Each `*_test.rego` file holds a passing case and one failing case per rule. A rule without a failing test is not accepted.

## Running it

- `make policy-test` runs the pack's own unit tests (`aidlc policy rego-test`, which is `conftest verify`).
- `aidlc policy conftest [--repo PATH]` judges one repository. It exits 0 (pass), 1 (violations, including a missing conftest) or 2 (the repository or its policy data cannot be read).
- `aidlc ci` runs the same judgement as the `config-policy` step. It is a judge: it runs before any of the change's code, with the pinned, checksum-verified conftest only. It takes the files from the change and the policy data from the base branch.

Install the pinned binary with `aidlc tools install conftest`.

Conftest never runs inside the repository being judged. It gets an empty working directory, a minimal environment and absolute paths, so a `conftest.toml` or a `CONFTEST_*` variable in the change cannot redirect the policy. A symlink or a special file where an input belongs is a failure.

## Ownership

Platform and security own this folder through CODEOWNERS. A change here changes what every repository is judged against.
