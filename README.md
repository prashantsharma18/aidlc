# aidlc

A tool-neutral framework that puts the guide *From Intent to Verified Change* into practice:
policies, templates, context engineering, an agent harness, verification and evals,
with a Claude Code adapter and extension points for other tools.

- Design: [docs/design/2026-10-18-aidlc-framework-design.md](docs/design/2026-10-18-aidlc-framework-design.md)
- Plans: [docs/plans/](docs/plans/)

## Requirements

Python 3.12 with PyYAML and jsonschema (Ubuntu: `sudo apt install python3-yaml python3-jsonschema`).

## Use

    bin/aidlc --help
    make test
