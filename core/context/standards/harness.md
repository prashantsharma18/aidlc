---
id: ctx-harness
guide: ["3.4", "3.7", "3 step 9"]
---
# Standard: the harness in a repository

The harness is rendered from the framework's policy and hooks. A repository owns only its
narrowing. It never owns the rendered output.

## Rules
- Edit sources, never output. The sources are `core/policy/permissions.yaml`, `core/hooks/`
  and the repository's `.aidlc/permissions.yaml`. The output is `.claude/settings.json` and
  `.aidlc/hooks/`.
- A repository may deny more, ask more and allow less. Any `allow_add` needs a reason and an owner.
- Protected paths and secret paths are enforced twice: by permissions and by the sandbox.
- Unattended runs set `AIDLC_UNATTENDED=1` and `--permission-mode dontAsk`.
- Code owners cover `.aidlc/`, `.claude/`, `AGENTS.md` and CI, so a change to the harness needs
  a reviewer who is not the agent.

## Checks
- `aidlc doctor` passes before merge and after every Claude Code upgrade.
- `aidlc render --tool claude-code --check` reports no drift.
- The harness `version` in `.aidlc/hooks/harness.json` changes whenever the data changes.

## Where to read more
`docs/harness/README.md`
