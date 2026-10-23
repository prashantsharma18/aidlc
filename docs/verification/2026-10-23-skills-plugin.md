# Evidence: the aidlc plugin, skills and agents (Plan 5a)

Date: 2026-10-23 · Decision under test: [ADR 0005](../adr/0005-skills-plugin.md) ·
Plan: `docs/plans/2026-10-22-plan-05a-skills-and-agents.md`

## Verified

- **Structure, on every change.** `make test` passes, including:
  - the agent and skill format contracts (`tests/unit/test_agents_format.py`,
    `tests/unit/test_skills_format.py`): the gate, the injection rule, "You draft; you never approve",
    Common excuses and Red flags, `invocation` (`auto` only for context-setup and verify), and the rule
    that drafting skills hand their drafts to the person;
  - the generator (`tests/unit/test_plugin.py`): the manifest and marketplace, Claude tool names from
    `core/adapters/claude-code.yaml`, `disable-model-invocation: true` on every manual skill and on
    none of the `auto` ones, clear errors for bad sources, and `test_the_committed_plugin_is_current`.
- **Claude Code accepts the plugin.** `claude plugin validate --strict .` and
  `claude plugin validate --strict plugins/aidlc` both report "Validation passed" (Claude Code
  2.1.296, run locally).
- **The skills match the framework.** A fresh reviewer checked every command, file and policy the
  skills name (`aidlc check`, `aidlc scope`, `plans/approved-bundles.txt`, the retry limit, the
  tracker policy, the evidence-table fields).

## Found and fixed by the review

- The drafting skills told the agent to write `plans/<KEY>/…` and `AGENTS.md`, which the harness
  denies. They now give the draft in the reply, and the person saves it.
- One branch per story conflicted with the single-bundle scope check. Each later bundle's MAY CHANGE
  now carries the earlier slices' paths.
- The generator raised tracebacks on bad input. It now fails with a clear error naming the file.

## Not verified

- **A live run of any skill.** The owner skipped the dry run (Task 7 step 1) on 2026-10-23.
- **Skill behaviour under evals** (pressure cases, "fires" and "stays quiet"): deferred to Plan 5c.
- **An organisation install** through managed settings, and Copilot rendering.
