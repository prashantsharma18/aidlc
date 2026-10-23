<!-- aidlc template: codebase-map -->
# aidlc: codebase map
Owner: framework owners (Prashant Sharma) · Last verified: 2026-10-23, against commit 88f4074
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
`cli/aidlc/adapters/capabilities.py`  Loads the tool descriptors; the CI judge and trace read them (ADR 0006).
`core/adapters/`         One capability descriptor per tool (`<tool>.yaml`): what it reads and enforces, with sources.
`cli/aidlc/checks/`      Deterministic checks returning Findings (`cli/aidlc/checks/findings.py`).
`cli/aidlc/checks/onecheck.py`  The one-command check: command steps, then the built-in integrity steps.
`cli/aidlc/ci.py`        `aidlc ci`: prepare, judge, run the change sandboxed, record (GitHub mode is the trusted CI; local is a preview).
`cli/aidlc/sandbox.py`   The bubblewrap sandbox for the change's own commands in CI.
`cli/aidlc/tools.py`     Pinned, checksum-verified tools (opa, conftest) from `core/policy/tool-register.yaml`.
`core/policy/`           Policies (YAML), each validated by its schema in `core/schemas/`.
`core/templates/`        Stage-artefact templates (front matter: id, title, stage, guide, fields).
`core/context/`          Context standards, authority ladders, profiles, OpenWiki baseline.
`docs/`                  Design, plans, operating model, adapters; some files are generated.
`core/ci/`               CI templates: the GitHub workflow and its per-profile setup steps.
`core/policy-as-code/`   The Rego pack (settings, narrowing, workflows) and its tests; run by conftest.
`core/hooks/`            Harness hook sources (guard, post-check, shim); standard library only. Rendered into the hooks folder under `.aidlc` in installed repositories (generated; never edit).
`core/managed/`          Optional machine-level pieces an organisation may install through managed settings: the root guard (`docs/harness/root-guard.md`).
`core/observability/`    Metric catalogue (`core/observability/metrics.yaml`) and proposed Grafana alert rules; built on Claude Code's built-in telemetry (ADR 0003).
`.github/workflows/ai-gates.yml`  The AI gates: review and harness evals (ADR 0004); a person approves each run.
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
- New AI coding tool: its descriptor in `core/adapters/` first, then an adapter (six functions) and a shim dialect (ADR 0006).
- New harness path that should trigger evals: the scope pattern in `.github/workflows/ai-gates.yml` and its test.
- New metric: an entry in `core/observability/metrics.yaml` naming its real source; never a new emitter (ADR 0003).

## Shared capabilities (reuse; do not duplicate)
load_yaml, load_policy   `cli/aidlc/policy.py`     raise PolicyError; never return partial data
parse_front_matter       `cli/aidlc/templates.py`  accepts CRLF and BOM
find_repo_root           `cli/aidlc/paths.py`      raises FileNotFoundError outside a repository
write_rendered           `cli/aidlc/adapters/base.py`  never overwrites a non-generated file; only touches its own tool's files
render_outputs           `cli/aidlc/adapters/base.py`  the one list of an adapter's outputs

## Traps
- Generated files (`docs/traceability.md`, `docs/operating-model/tiers-table.md`, `docs/adapters/capabilities.md`, `CLAUDE.md`): edit sources, then regenerate.
- Changing `core/policy/permissions.yaml` changes every installed repository's harness: it needs a design change.
- Tests that commit must use `tests/helpers.py` (it disables the user's global git hooks).
- Hook records must keep `session` and `call` (`tool_use_id`): they are the only link from Grafana to the local record (`tests/unit/test_hook_record_ids.py`).
- `aidlc ci` must judge before the change's code runs and must never run git in the checkout afterwards: keep new steps in the right phase.

## Tests
`make test` runs everything (unittest). No network, no model calls. Tests that need `bwrap` or the
pinned `conftest` skip with a reason when it is missing; `make policy-test` runs the conftest ones and
fails on any skip. `make harness-live` runs the attack tests against a real model (opt-in).
