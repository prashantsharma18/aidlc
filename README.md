# aidlc

A tool-neutral framework that puts the guide *From Intent to Verified Change* into practice:
policies, templates, context engineering, an agent harness, verification and evals,
with a Claude Code adapter and extension points for other tools.

- Design: [docs/design/2026-10-18-aidlc-framework-design.md](docs/design/2026-10-18-aidlc-framework-design.md)
- Plans: [docs/plans/](docs/plans/)

## Documentation

- [Operating model: lifecycle](docs/operating-model/lifecycle.md), [tiers](docs/operating-model/tiers.md), [roles](docs/operating-model/roles.md), [autonomy and maturity](docs/operating-model/autonomy-and-maturity.md)
- [Context engineering](docs/context-engineering/README.md)
- [Adapters](docs/adapters/interface.md): [tool capabilities](docs/adapters/capabilities.md), [Copilot (planned)](docs/adapters/copilot.md), [ADR 0006 multi-tool foundation](docs/adr/0006-multi-tool-foundation.md)
- [Harness](docs/harness/README.md): [permissions and sandbox](docs/harness/permissions-and-sandbox.md), [hooks](docs/harness/hooks.md), [doctor](docs/harness/doctor.md)
- [Checks](docs/checks/README.md): [the one-command check](docs/checks/README.md), [trusted CI](docs/checks/ci.md), [policy as code](docs/checks/policy-as-code.md), [AI gates](docs/checks/ai-gates.md)
- [Observability](docs/observability/README.md): [runbooks](docs/observability/runbooks.md), [proposed platform changes](docs/observability/platform-patch.md)
- [Traceability to the guide](docs/traceability.md)
- [Codebase map](docs/codebase-map.md)

## Requirements

Python 3.12 with PyYAML and jsonschema (Ubuntu: `sudo apt install python3-yaml python3-jsonschema`).

## Use

    bin/aidlc --help
    make test
