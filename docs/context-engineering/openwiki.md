# OpenWiki: generated documentation, governed

OpenWiki writes a wiki of the repository in `openwiki/` and a pointer block in `AGENTS.md`.
The framework treats it as derived knowledge: useful as a first map of unfamiliar code, never a
source of truth, and adopted per repository only if a before/after comparison shows it helps.

- Operating procedure and controls: framework `core/context/openwiki/governance.md`
- Baseline ignore file: framework `core/context/openwiki/openwikiignore.baseline`
- Brief OpenWiki follows: framework `core/context/openwiki/INSTRUCTIONS.md`
- Check: `aidlc check openwiki` (block size and content, no block in `CLAUDE.md`, ignore baseline kept)
- Register entry: `core/policy/tool-register.yaml` (status: pilot)

When to adopt: start from a measured problem (sessions spend long finding their way; impact
analyses miss dependants), try a better codebase map first, then pilot and keep it only if the
agent-configuration evals improve.

Guide: 4.3, 4.6, 13.4.
