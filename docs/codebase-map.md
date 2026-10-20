<!-- aidlc template: codebase-map -->
# aidlc: codebase map
Owner: framework owners (Prashant Sharma) · Last verified: 2026-10-20, against commit 5bb8baa
Read this before planning a change. Paths are from the repository root.

## What this service does
A tool-neutral framework that turns the guide "From Intent to Verified Change" into policies,
templates, context standards and checks, rendered for AI coding tools by adapters. It is a CLI
(`bin/aidlc`) run against other repositories. It calls git and reads files; `aidlc ci` also runs a
repository's own commands inside bubblewrap, and `aidlc tools install` downloads pinned tools.

## Areas
`cli/aidlc/`             The CLI package. May depend on `core/` data; never on a repository it inspects.
`cli/aidlc/commands/`    One module per subcommand; importing a module registers it (`cli/aidlc/cli.py`).
`cli/aidlc/adapters/`    Tool adapters. Only here may tool file names (CLAUDE.md, .claude/) appear.
`cli/aidlc/checks/`      Deterministic checks returning Findings (`cli/aidlc/checks/findings.py`).
`cli/aidlc/checks/onecheck.py`  The one-command check: command steps, then the built-in integrity steps.
`cli/aidlc/ci.py`        Trusted CI (`aidlc ci`): prepare, judge, run the change sandboxed, verdict, record.
`cli/aidlc/sandbox.py`   The bubblewrap sandbox for the change's own commands in CI.
`cli/aidlc/tools.py`     Pinned, checksum-verified tools (opa, conftest) from `core/policy/tool-register.yaml`.
`core/policy/`           Policies (YAML), each validated by its schema in `core/schemas/`.
`core/templates/`        Stage-artefact templates (front matter: id, title, stage, guide, fields).
`core/context/`          Context standards, authority ladders, profiles, OpenWiki baseline.
`docs/`                  Design, plans, operating model, adapters; some files are generated.
`core/ci/`               CI templates: the GitHub workflow and its per-profile setup steps.
`core/policy-as-code/`   The Rego pack (settings, narrowing, workflows) and its tests; run by conftest.
`core/hooks/`            Harness hook sources (guard, post-check, shim); standard library only. Rendered into the hooks folder under `.aidlc` in installed repositories (generated; never edit).
`tests/`                 unittest suites; `tests/helpers.py` builds throwaway git repositories.

## Key flows
`bin/aidlc` -> `cli/aidlc/__main__.py` -> `cli/aidlc/cli.py` (build_parser imports `cli/aidlc/commands/`)
  -> the command module -> core data via `cli/aidlc/policy.py` or `cli/aidlc/templates.py`.
Invariant: every exit is 0 (pass), 1 (findings) or 2 (usage); nothing passes silently.

## Where common changes go
- New policy: `core/policy/<name>.yaml` + `core/schemas/<name>.schema.json`; meta.guide required; then `bin/aidlc trace`.
- New template: `core/templates/<id>.md`; pattern: `core/templates/intent.md`.
- New subcommand: `cli/aidlc/commands/<name>_cmd.py` + import line in `cli/aidlc/commands/__init__.py`.
- New check: `cli/aidlc/checks/<name>.py` + an entry in CHECKS in `cli/aidlc/commands/check_cmd.py`.
- New built-in step of the one-command check: BUILTINS in `cli/aidlc/checks/onecheck.py`; for CI, JUDGE_STEPS or AFTER_STEPS in `cli/aidlc/ci.py`.
- New Rego rule: a failing case in its `*_test.rego` first, then the rule in `core/policy-as-code/rego/`; `make policy-test`.
- New tool output: an adapter method in `cli/aidlc/adapters/`; never in the core.

## Shared capabilities (reuse; do not duplicate)
load_yaml, load_policy   `cli/aidlc/policy.py`     raise PolicyError; never return partial data
parse_front_matter       `cli/aidlc/templates.py`  accepts CRLF and BOM
find_repo_root           `cli/aidlc/paths.py`      raises FileNotFoundError outside a repository
write_rendered           `cli/aidlc/adapters/base.py`  never overwrites a non-generated file

## Traps
- Generated files (`docs/traceability.md`, `docs/operating-model/tiers-table.md`, `CLAUDE.md`): edit sources, then regenerate.
- Changing `core/policy/permissions.yaml` changes every installed repository's harness: it needs a design change.
- Tests that commit must use `tests/helpers.py` (it disables the user's global git hooks).
- `aidlc ci` must judge before the change's code runs and must never run git in the checkout afterwards: keep new steps in the right phase.

## Tests
`make test` runs everything (unittest). No network, no model calls. Tests that need `bwrap` or the
pinned `conftest` skip with a reason when it is missing; `make policy-test` runs the conftest ones and
fails on any skip. `make harness-live` runs the attack tests against a real model (opt-in).
